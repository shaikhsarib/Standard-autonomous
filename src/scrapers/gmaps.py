import time
import re
import logging
from typing import List, Dict, Any, Optional
from src.scrapers.base import BaseScraper
from src.models.lead import BusinessProfile

logger = logging.getLogger(__name__)

# List of junk strings that indicate an invalid scraped name
INVALID_NAME_PATTERNS = [
    r"^contact(\s+us)?$",
    r"^inquire(\s+&\s+contact)?$",
    r"^top\s+\d+",
    r"^best\s+.*in\s+",
    r"^list\s+of\s+",
    r"directory",
    r"reviews\s+and\s+ratings",
]

def clean_business_name(name: str) -> Optional[str]:
    if not name or len(name.strip()) < 3:
        return None
    
    # Try segments separated by common title delimiters (| - • :)
    segments = re.split(r"\s*[|\-•:]\s*", name.strip())
    for seg in segments:
        seg = seg.strip()
        if len(seg) < 3 or len(seg) > 50:
            continue
        is_invalid = any(re.search(pat, seg, re.IGNORECASE) for pat in INVALID_NAME_PATTERNS)
        if not is_invalid and not re.search(r"\b(companies|services|agencies|in\s+mumbai|in\s+delhi)\b", seg, re.IGNORECASE):
            return seg
            
    # Fallback: check first segment
    first = segments[0].strip()
    if not any(re.search(pat, first, re.IGNORECASE) for pat in INVALID_NAME_PATTERNS):
        return first
    return None

def format_phone_number(phone_raw: str) -> Optional[str]:
    digits = re.sub(r"\D", "", phone_raw)
    if digits.startswith("91") and len(digits) == 12:
        return f"+91 {digits[2:7]} {digits[7:]}"
    elif len(digits) == 10 and digits[0] in "6789":
        return f"+91 {digits[:5]} {digits[5:]}"
    elif len(digits) >= 10:
        return f"+{digits}"
    return None


class GoogleMapsScraper(BaseScraper):
    def __init__(self, headless: bool = True):
        self.headless = headless

    def _get_driver(self):
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        from selenium.webdriver.chrome.service import Service
        from webdriver_manager.chrome import ChromeDriverManager

        opts = Options()
        if self.headless:
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
            options=opts
        )

    def scrape_panel(self, driver) -> Dict[str, Any]:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        data = {
            "name": None,
            "phone": None,
            "address": None,
            "website": None,
            "has_website": False,
            "rating": None,
            "category": None
        }

        # 1. Scoped Name - Headline in business side panel
        try:
            name_el = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "h1.DUwDvf, h1.fontHeadlineLarge, div.TIHn2 h1"))
            )
            raw_name = name_el.text.strip()
            data["name"] = clean_business_name(raw_name)
        except Exception:
            return data

        if not data["name"]:
            return data

        # 2. Scoped Phone - ONLY target phone buttons inside the active panel
        try:
            phone_el = None
            phone_selectors = [
                "button[data-item-id^='phone:tel:']",
                "button[data-tooltip*='phone' i]",
                "button[aria-label*='Phone' i]",
                "button[data-item-id^='phone'] .Io6YTe"
            ]
            for sel in phone_selectors:
                elements = driver.find_elements(By.CSS_SELECTOR, sel)
                if elements:
                    phone_el = elements[0]
                    break

            if phone_el:
                raw_phone = phone_el.get_attribute("data-item-id") or phone_el.text or phone_el.get_attribute("aria-label") or ""
                # Extract number
                m = re.search(r"(\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}", raw_phone) or re.search(r"\d{10,12}", raw_phone)
                if m:
                    data["phone"] = format_phone_number(m.group(0))
        except Exception as e:
            logger.debug(f"Phone parse failed: {e}")

        # 3. Scoped Address
        try:
            addr_el = driver.find_element(
                By.CSS_SELECTOR,
                "button[data-item-id='address'] .Io6YTe, [data-tooltip='Copy address'] .Io6YTe, button[data-item-id='address']"
            )
            data["address"] = addr_el.text.strip()
        except Exception:
            pass

        # 4. Scoped Website
        try:
            web_el = driver.find_element(
                By.CSS_SELECTOR,
                "a[data-item-id='authority'], a[aria-label*='website' i], a[aria-label*='Website' i]"
            )
            href = web_el.get_attribute("href") or ""
            if href and "google.com" not in href and "maps.google" not in href:
                data["website"] = href
                data["has_website"] = True
        except Exception:
            data["has_website"] = False

        # 5. Rating
        try:
            rating_el = driver.find_element(By.CSS_SELECTOR, "div.F7nice span[aria-hidden='true']")
            data["rating"] = rating_el.text.strip()
        except Exception:
            pass

        return data

    def search(self, category: str, location: str, limit: int = 10, only_no_website: bool = True) -> List[BusinessProfile]:
        from selenium.webdriver.common.by import By

        query = f"{category} in {location}"
        maps_url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
        logger.info(f"Initiating Google Maps Search: {query}")

        driver = None
        results: List[BusinessProfile] = []

        try:
            driver = self._get_driver()
            driver.get(maps_url)
            time.sleep(3)

            # Locate feed
            feed = None
            for sel in ["div[role='feed']", "div.m6QErb[aria-label]", "div.ecceSd"]:
                try:
                    feed = driver.find_element(By.CSS_SELECTOR, sel)
                    break
                except Exception:
                    pass

            links = set()
            scroll_count = 0
            while len(links) < limit * 2 and scroll_count < 6:
                cards = driver.find_elements(By.CSS_SELECTOR, "a.hfpxzc, a[href*='/maps/place/']")
                for card in cards:
                    href = card.get_attribute("href")
                    if href and "/maps/place/" in href:
                        links.add(href)
                
                if feed:
                    driver.execute_script("arguments[0].scrollTop += 1200", feed)
                else:
                    driver.execute_script("window.scrollBy(0, 1200)")
                time.sleep(1.2)
                scroll_count += 1

            logger.info(f"Discovered {len(links)} candidate links on Google Maps for {query}")

            for link in list(links)[:limit * 2]:
                if len(results) >= limit:
                    break
                try:
                    driver.get(link)
                    time.sleep(1.5)
                    data = self.scrape_panel(driver)
                    if not data.get("name"):
                        continue

                    if only_no_website and data.get("has_website"):
                        continue

                    profile = BusinessProfile(
                        company_name=data["name"],
                        business_type=category,
                        location=location,
                        phone=data["phone"],
                        website=data["website"],
                        has_website=data["has_website"],
                        address=data["address"],
                        rating=data["rating"],
                        source="google_maps",
                        source_url=link
                    )
                    results.append(profile)
                    logger.info(f"Captured: {profile.company_name} | Phone: {profile.phone or 'N/A'} | Has Website: {profile.has_website}")
                except Exception as e:
                    logger.debug(f"Error scraping listing {link}: {e}")

        except Exception as e:
            logger.error(f"Google Maps scraper encountered an error: {e}")
        finally:
            if driver:
                try:
                    driver.quit()
                except Exception:
                    pass

        return results
