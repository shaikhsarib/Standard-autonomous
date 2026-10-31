"""
Email Finder
------------
Given a business name and city, tries to find their contact email by:
1. Searching DuckDuckGo for their website
2. Scraping the website's contact/about page for an email
3. Respects robots.txt, uses polite delays
"""

import re
import time
import logging
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

UA = "LeadBot/1.0 (contact@example.com)"
HEADERS = {"User-Agent": UA}

# Pages most likely to have contact info
CONTACT_PATHS = [
    "/contact", "/contact-us", "/contactus",
    "/about", "/about-us", "/reach-us",
    "/get-in-touch", "/support",
]

# Domains we don't want as "the business website"
NOISE_DOMAINS = [
    "justdial", "sulekha", "indiamart", "tradeindia",
    "google", "facebook", "instagram", "twitter", "linkedin",
    "youtube", "zomato", "swiggy", "practo", "tripadvisor",
    "wikipedia", "yellowpages", "yelp", "quora", "reddit",
]

# Email patterns to ignore (belong to the directory sites)
NOISE_EMAIL_KEYWORDS = [
    "sulekha", "justdial", "noreply", "no-reply", "example",
    "test@", "info@sulekha", "support@",
]


def _is_noise_domain(url: str) -> bool:
    domain = urlparse(url).netloc.lower()
    return any(n in domain for n in NOISE_DOMAINS)


def _clean_email(email: str) -> Optional[str]:
    """Return email if it looks like a real business email, else None."""
    if any(n in email.lower() for n in NOISE_EMAIL_KEYWORDS):
        return None
    # Basic validity check
    if re.match(r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}$', email):
        return email
    return None


def _extract_emails_from_text(text: str) -> list:
    raw = re.findall(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}', text)
    return [e for e in raw if _clean_email(e)]


def _can_fetch(url: str) -> bool:
    """Check robots.txt — return True if allowed."""
    try:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch(UA, url)
    except Exception:
        return True  # allow on error


def _fetch(url: str, timeout: int = 8) -> Optional[str]:
    """Fetch a URL and return HTML text, or None on failure."""
    if not _can_fetch(url):
        logging.debug(f"robots.txt blocks: {url}")
        return None
    try:
        time.sleep(1)
        resp = requests.get(url, headers=HEADERS, timeout=timeout)
        if resp.ok:
            return resp.text
    except Exception as exc:
        logging.debug(f"Fetch failed {url}: {exc}")
    return None


def _find_website_via_ddg(business_name: str, city: str) -> tuple:
    """
    Search DuckDuckGo for the business.
    Returns (website_url, email_from_snippet) — email may be found directly in search results.
    """
    query = f'{business_name} {city} email contact'
    try:
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS  # type: ignore

        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=8))

        found_website = None
        for r in results:
            url = r.get("href", "")
            snippet = r.get("body", "") + " " + r.get("title", "")

            # Check snippet directly for email
            snippet_emails = _extract_emails_from_text(snippet)
            if snippet_emails:
                logging.info(f"  Email found in snippet: {snippet_emails[0]}")
                return url, snippet_emails[0]

            # Save first non-noise URL as website candidate
            if url and not _is_noise_domain(url) and not found_website:
                found_website = url

        if found_website:
            logging.info(f"  Website candidate: {found_website}")
        return found_website, None

    except Exception as exc:
        logging.debug(f"DDG search failed for {business_name!r}: {exc}")
        return None, None


def _scrape_email_from_website(website_url: str) -> Optional[str]:
    """
    Try to find a contact email on the website.
    Checks homepage first, then common contact paths.
    """
    base = website_url.rstrip("/")
    pages_to_try = [base] + [base + path for path in CONTACT_PATHS]

    for url in pages_to_try:
        html = _fetch(url)
        if not html:
            continue

        emails = _extract_emails_from_text(html)
        if emails:
            logging.info(f"  Email found on {url}: {emails[0]}")
            return emails[0]

        # Also check mailto: links specifically
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("mailto:"):
                email = href.replace("mailto:", "").split("?")[0].strip()
                cleaned = _clean_email(email)
                if cleaned:
                    logging.info(f"  Mailto found on {url}: {cleaned}")
                    return cleaned

    return None


def find_email_for_business(business_name: str, city: str) -> Optional[str]:
    """
    Main function: given a business name and city,
    try to find their contact email address.
    Returns email string or None.
    """
    logging.info(f"Finding email for: {business_name!r} in {city!r}")

    # Step 1: Search DDG — may find email directly in snippet
    website, snippet_email = _find_website_via_ddg(business_name, city)

    if snippet_email:
        return snippet_email

    if not website:
        logging.info(f"  No website found for {business_name!r}")
        return None

    # Step 2: Scrape email from website pages
    email = _scrape_email_from_website(website)
    if email:
        return email

    logging.info(f"  No email found for {business_name!r}")
    return None
