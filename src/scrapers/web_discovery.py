import re
import time
import logging
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
from src.scrapers.base import BaseScraper
from src.models.lead import BusinessProfile
from src.scrapers.gmaps import clean_business_name, format_phone_number

logger = logging.getLogger(__name__)

DIRECTORY_DOMAINS = [
    "justdial.com", "sulekha.com", "indiamart.com", "tradeindia.com", "yellowpages.com",
    "google.com", "facebook.com", "instagram.com", "twitter.com", "x.com",
    "linkedin.com", "yelp.com", "tripadvisor.com", "zomato.com", "swiggy.com",
    "practo.com", "wikipedia.org", "youtube.com"
]

class WebDiscoveryScraper(BaseScraper):
    def __init__(self):
        pass

    def _is_real_website(self, url: Optional[str]) -> bool:
        if not url:
            return False
        netloc = urlparse(url).netloc.lower()
        return not any(d in netloc for d in DIRECTORY_DOMAINS)

    def search(self, category: str, location: str, limit: int = 10) -> List[BusinessProfile]:
        query = f"{category} in {location} phone number contact"
        logger.info(f"Searching web discovery via DuckDuckGo: {query}")

        try:
            from ddgs import DDGS
        except ImportError:
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                logger.error("ddgs / duckduckgo_search not installed")
                return []

        results: List[BusinessProfile] = []
        seen_names = set()

        try:
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=limit * 4))

            for item in ddg_results:
                if len(results) >= limit:
                    break

                title = item.get("title", "")
                snippet = item.get("body", "")
                href = item.get("href", "")

                cleaned_name = clean_business_name(title)
                if not cleaned_name or cleaned_name.lower() in seen_names:
                    continue

                seen_names.add(cleaned_name.lower())

                # Find phone in snippet
                phone = None
                phone_match = re.search(r"(?:\+91[\s-]?)?[6-9]\d{9}", snippet)
                if phone_match:
                    phone = format_phone_number(phone_match.group(0))

                # Find email in snippet
                email = None
                email_match = re.search(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}", snippet)
                if email_match:
                    e_cand = email_match.group(0).lower()
                    if not any(noise in e_cand for noise in ["sulekha", "justdial", "example", "domain"]):
                        email = e_cand

                has_site = self._is_real_website(href)

                profile = BusinessProfile(
                    company_name=cleaned_name,
                    business_type=category,
                    location=location,
                    phone=phone,
                    email=email,
                    website=href if has_site else None,
                    has_website=has_site,
                    source="web_discovery",
                    source_url=href
                )
                results.append(profile)

        except Exception as e:
            logger.error(f"Web discovery error: {e}")

        return results
