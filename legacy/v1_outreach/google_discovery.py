"""
Business Discovery Module
--------------------------
Uses DuckDuckGo (free, no API key) to find local businesses,
scrapes their details, and checks if they have an online presence.
"""

import time
import logging
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

BUSINESS_TYPES = [
    "restaurant", "dhaba", "salon", "parlour", "gym",
    "medical store", "coaching center", "clinic",
    "bakery", "boutique", "hardware store", "tailor",
    "ca firm", "hotel", "automobile workshop",
]

# Directory sites — these are NOT business websites
DIRECTORY_DOMAINS = [
    "justdial", "sulekha", "indiamart", "tradeindia", "yellowpages",
    "google.com", "facebook.com", "instagram.com", "twitter.com",
    "linkedin.com", "yelp.com", "tripadvisor", "zomato", "swiggy",
    "practo", "99acres", "magicbricks", "wikipedia.org", "youtube.com",
]

SKIP_IN_SEARCH = ["youtube.com", "wikipedia.org", "twitter.com", "instagram.com", "facebook.com"]


def _ddg_search(query: str, max_results: int = 15) -> List[Dict[str, str]]:
    """DuckDuckGo search — free, no API key needed."""
    try:
        # Try new package name first (ddgs), fallback to old (duckduckgo_search)
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
            return results  # each has: href, title, body
    except Exception as exc:
        logging.error(f"DuckDuckGo search failed: {exc}")
        return []


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    match = re.search(r"(?:\+91[\s-]?)?[6-9]\d{9}", text)
    return match.group(0) if match else None


def _has_real_website(url: Optional[str]) -> bool:
    if not url:
        return False
    domain = urlparse(url).netloc.lower()
    return not any(d in domain for d in DIRECTORY_DOMAINS)


def scrape_business_details(url: str) -> Dict[str, Any]:
    """Try to get email, phone, and linked website from a page."""
    details: Dict[str, Any] = {"email": None, "phone": None, "website": None}
    try:
        resp = requests.get(url, headers=HEADERS, timeout=8)
        if not resp.ok:
            return details
        soup = BeautifulSoup(resp.text, "html.parser")
        text = soup.get_text(separator=" ")
        details["email"] = _extract_email(text)
        details["phone"] = _extract_phone(text)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("http") and _has_real_website(href):
                details["website"] = href
                break
    except Exception as exc:
        logging.debug(f"Scrape failed for {url}: {exc}")
    return details


def search_businesses(
    business_type: str,
    location: str,
    limit: int = 10,
) -> List[Dict[str, Any]]:
    """
    Search DuckDuckGo for businesses of a given type in a location.
    Extracts name, email, phone, and checks for website presence.
    """
    query = f'{business_type} {location} contact email phone number'
    logging.info(f"Searching: {query!r}")

    ddg_results = _ddg_search(query, max_results=limit * 3)
    if not ddg_results:
        return []

    businesses: List[Dict[str, Any]] = []
    seen_names: set = set()

    for result in ddg_results:
        if len(businesses) >= limit:
            break

        url = result.get("href", "")
        ddg_title = result.get("title", "")
        ddg_body = result.get("body", "")

        if not url or any(d in url for d in SKIP_IN_SEARCH):
            continue

        # Use DDG title as name (faster than fetching page)
        name = ddg_title.split("|")[0].split("-")[0].strip()
        if not name or name.lower() in seen_names:
            continue

        # Try to extract email/phone from DDG snippet first (no HTTP needed)
        email = _extract_email(ddg_body)
        phone = _extract_phone(ddg_body)

        # Only fetch page if we didn't get email from snippet
        if not email:
            time.sleep(1)
            details = scrape_business_details(url)
            email = details.get("email")
            phone = phone or details.get("phone")
            linked_website = details.get("website")
        else:
            linked_website = None

        has_website = _has_real_website(linked_website) or _has_real_website(url)

        seen_names.add(name.lower())
        businesses.append({
            "name": name,
            "business_type": business_type,
            "location": location,
            "email": email,
            "phone": phone,
            "website": linked_website if _has_real_website(linked_website) else None,
            "has_website": has_website,
            "source_url": url,
            "contacted": False,
        })
        logging.info(f"  → {name} | email={email} | phone={phone} | has_website={has_website}")

    # Best targets first: no website + has email
    businesses.sort(key=lambda x: (x["has_website"], x["email"] is None))
    return businesses


def discover_businesses(
    location: str,
    business_types: Optional[List[str]] = None,
    limit_per_type: int = 5,
) -> List[Dict[str, Any]]:
    """
    Discover businesses across multiple types in a location.
    Priority: Sulekha (best data) → DuckDuckGo (fallback)
    """
    from outreach.sulekha_scraper import get_sulekha_businesses

    types_to_search = business_types or BUSINESS_TYPES[:4]
    all_businesses: List[Dict[str, Any]] = []

    for btype in types_to_search:
        # 1. Try Sulekha first — real names + phones
        found = get_sulekha_businesses(btype, location, limit=limit_per_type)

        # 2. Fallback to DuckDuckGo if Sulekha returns nothing
        if not found:
            logging.info(f"Sulekha returned nothing for {btype!r}, trying DuckDuckGo...")
            found = search_businesses(btype, location, limit_per_type)

        all_businesses.extend(found)
        time.sleep(2)

    # Deduplicate by name
    seen: set = set()
    unique: List[Dict[str, Any]] = []
    for b in all_businesses:
        key = b["name"].lower().strip()
        if key not in seen:
            seen.add(key)
            unique.append(b)

    logging.info(f"Total unique businesses discovered: {len(unique)}")
    return unique
