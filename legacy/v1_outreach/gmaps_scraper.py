"""
Google Maps Scraper
--------------------
Uses Selenium + headless Chrome to search Google Maps for businesses.
Filters only those WITHOUT a website — these are our best outreach targets.
Returns: name, phone, address, category, rating, website (None if missing).
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def _make_driver() -> webdriver.Chrome:
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    opts.add_argument("--window-size=1280,900")
    opts.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=opts,
    )


def _safe_text(el) -> str:
    try:
        return el.text.strip()
    except Exception:
        return ""


def scrape_business_panel(driver: webdriver.Chrome) -> Dict[str, Any]:
    """
    Extract details from the currently open business side panel on Google Maps.
    """
    wait = WebDriverWait(driver, 6)
    data: Dict[str, Any] = {
        "name": None, "phone": None, "address": None,
        "website": None, "rating": None, "category": None,
        "has_website": False,
    }

    try:
        # Name — h1 inside the panel
        name_el = wait.until(EC.presence_of_element_located(
            (By.CSS_SELECTOR, "h1.DUwDvf, h1.fontHeadlineLarge")
        ))
        data["name"] = _safe_text(name_el)
    except Exception:
        return data

    page_src = driver.page_source

    # Phone — look for Indian numbers
    phones = re.findall(r'(?:\+91[\s-]?)?[6-9]\d{9}', page_src)
    if phones:
        data["phone"] = phones[0].replace(" ", "").replace("-", "")

    # Address
    try:
        addr_el = driver.find_element(
            By.CSS_SELECTOR,
            "button[data-item-id='address'] .Io6YTe, [data-tooltip='Copy address'] .Io6YTe"
        )
        data["address"] = _safe_text(addr_el)
    except Exception:
        pass

    # Website
    try:
        web_el = driver.find_element(
            By.CSS_SELECTOR,
            "a[data-item-id='authority'], a[aria-label*='website'], a[aria-label*='Website']"
        )
        href = web_el.get_attribute("href") or ""
        if href and "google.com" not in href and "maps.google" not in href:
            data["website"] = href
            data["has_website"] = True
    except Exception:
        data["has_website"] = False

    # Rating
    try:
        rating_el = driver.find_element(By.CSS_SELECTOR, "div.F7nice span[aria-hidden='true']")
        data["rating"] = _safe_text(rating_el)
    except Exception:
        pass

    # Category
    try:
        cat_el = driver.find_element(By.CSS_SELECTOR, "button.DkEaL, span.YhemCb")
        data["category"] = _safe_text(cat_el)
    except Exception:
        pass

    return data


def search_gmaps(
    business_type: str,
    city: str,
    limit: int = 20,
    driver: webdriver.Chrome = None,
) -> List[Dict[str, Any]]:
    """
    Search Google Maps for a business type in a city.
    Returns list of businesses — only those WITHOUT a website.
    Accepts an existing driver to avoid repeated browser startup.
    """
    query = f"{business_type} in {city}"
    maps_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"

    logging.info(f"Google Maps search: {query!r}")

    own_driver = driver is None
    if own_driver:
        driver = _make_driver()

    businesses: List[Dict[str, Any]] = []
    try:
        driver.get(maps_url)
        time.sleep(3)

        results_container = None
        for sel in ["div[role='feed']", "div.m6QErb[aria-label]", "div.ecceSd"]:
            try:
                results_container = driver.find_element(By.CSS_SELECTOR, sel)
                break
            except Exception:
                pass

        seen_links: set = set()
        scroll_attempts = 0
        max_scrolls = 8

        while len(seen_links) < limit * 2 and scroll_attempts < max_scrolls:
            cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc, a[href*='/maps/place/']")
            for card in cards:
                href = card.get_attribute("href") or ""
                if href and href not in seen_links:
                    seen_links.add(href)
            if results_container:
                driver.execute_script("arguments[0].scrollTop += 1500", results_container)
            else:
                driver.execute_script("window.scrollBy(0, 1500)")
            time.sleep(1.5)
            scroll_attempts += 1

        logging.info(f"  Found {len(seen_links)} listing links")

        for link in list(seen_links)[:limit * 2]:
            if len(businesses) >= limit:
                break
            try:
                driver.get(link)
                time.sleep(2)
                biz = scrape_business_panel(driver)
                if not biz.get("name"):
                    continue

                biz["business_type"] = business_type
                biz["location"] = city
                biz["source_url"] = link
                biz["source"] = "google_maps"
                biz["contacted"] = False

                if not biz["has_website"]:
                    businesses.append(biz)
                    logging.info(
                        f"  [NO WEBSITE] {biz['name'][:40]} | "
                        f"phone={biz['phone']} | rating={biz['rating']}"
                    )
                time.sleep(1)
            except Exception as exc:
                logging.debug(f"Panel scrape failed: {exc}")
                continue

    except Exception as exc:
        logging.error(f"Google Maps scrape failed: {exc}")
    finally:
        if own_driver:
            driver.quit()

    logging.info(f"  No-website businesses: {len(businesses)}")
    return businesses[:limit]


def gmaps_discover_businesses(
    city: str,
    business_types: List[str],
    limit_per_type: int = 10,
) -> List[Dict[str, Any]]:
    """
    Discover businesses across multiple types via Google Maps.
    Reuses ONE browser instance for all searches — much faster.
    Only returns businesses with NO website.
    """
    all_businesses: List[Dict[str, Any]] = []
    seen_names: set = set()

    logging.info("Starting single Chrome instance for all searches...")
    driver = _make_driver()

    try:
        for btype in business_types:
            results = search_gmaps(btype, city, limit=limit_per_type, driver=driver)
            for biz in results:
                name_key = biz.get("name", "").lower().strip()
                if name_key and name_key not in seen_names:
                    seen_names.add(name_key)
                    all_businesses.append(biz)
            time.sleep(1)
    finally:
        driver.quit()
        logging.info("Browser closed.")

    logging.info(f"Google Maps total: {len(all_businesses)} no-website businesses in {city}")
    return all_businesses
