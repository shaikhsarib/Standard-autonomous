"""
Firecrawl Web-to-Markdown & Semantic Lead Extractor for IC (Intelligent Central)
Repository: firecrawl/firecrawl
Converts target websites into clean LLM-ready Markdown and structured business profiles.
Standards: Matt Pocock (/to-spec) Contract & ECC AgentShield Gate 1 Stealth Compliance.
"""
import os
import re
import logging
from typing import Optional, Dict, Any, List
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class FirecrawlExtractedData(BaseModel):
    url: str
    markdown: str
    emails: List[str] = Field(default_factory=list)
    phones: List[str] = Field(default_factory=list)
    socials: Dict[str, str] = Field(default_factory=dict)
    executive_contacts: List[str] = Field(default_factory=list)
    services_detected: List[str] = Field(default_factory=list)
    has_whatsapp_widget: bool = False
    has_booking_calendar: bool = False


class FirecrawlScraper:
    """
    Firecrawl API client with resilient local fallback parser.
    Turns any prospect URL into clean Markdown and structured entity fields.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.base_url = base_url or os.getenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v1")
        self.timeout = 10
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
        }

    def scrape(self, url: str) -> FirecrawlExtractedData:
        """
        Scrapes a URL via Firecrawl API if configured, otherwise uses local stealth parsing.
        """
        if not url.startswith("http"):
            url = f"https://{url}"

        # 1. Attempt Firecrawl Cloud/Self-Hosted API if key exists
        if self.api_key:
            try:
                resp = requests.post(
                    f"{self.base_url}/scrape",
                    headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                    json={"url": url, "formats": ["markdown", "extract"]},
                    timeout=self.timeout
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    markdown = data.get("markdown", "")
                    return self._parse_from_markdown(url, markdown)
            except Exception as e:
                logger.warning(f"Firecrawl API call failed ({e}). Falling back to local stealth extractor.")

        # 2. Local Resilient Extraction (Zero External Dependency)
        return self._local_stealth_extract(url)

    def _local_stealth_extract(self, url: str) -> FirecrawlExtractedData:
        try:
            resp = requests.get(url, headers=self.headers, timeout=self.timeout)
            if resp.status_code != 200:
                return FirecrawlExtractedData(url=url, markdown="")

            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove scripts, styles, svg
            for tag in soup(["script", "style", "svg", "noscript"]):
                tag.decompose()

            # Extract Phone Numbers
            text = soup.get_text(separator=" ", strip=True)
            phone_pattern = re.compile(r'(?:\+?91[\-\s]?)?[6-9]\d{9}|(?:\+?1[\-\s]?)?\(?\d{3}\)?[\-\s]?\d{3}[\-\s]?\d{4}')
            raw_phones = list(set(phone_pattern.findall(text)))

            # Extract Emails
            email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
            raw_emails = [e for e in set(email_pattern.findall(text)) if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg'))]

            # Detect WhatsApp and Calendar widgets
            has_wa = bool(soup.find(lambda tag: tag.name == 'a' and 'wa.me' in tag.get('href', '')))
            has_cal = any(kw in resp.text.lower() for kw in ['calendly.com', 'cal.com', 'acuityscheduling', 'book-now'])

            # Convert main text into readable Markdown summary
            paragraphs = [p.get_text(strip=True) for p in soup.find_all(['p', 'h1', 'h2', 'h3']) if len(p.get_text(strip=True)) > 20]
            markdown_content = "\n\n".join(paragraphs[:8])

            return FirecrawlExtractedData(
                url=url,
                markdown=markdown_content,
                emails=raw_emails[:3],
                phones=raw_phones[:3],
                has_whatsapp_widget=has_wa,
                has_booking_calendar=has_cal
            )
        except Exception as err:
            logger.debug(f"Local stealth extraction error on {url}: {err}")
            return FirecrawlExtractedData(url=url, markdown="")

    def _parse_from_markdown(self, url: str, markdown: str) -> FirecrawlExtractedData:
        email_pattern = re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+')
        phone_pattern = re.compile(r'(?:\+?91[\-\s]?)?[6-9]\d{9}')
        return FirecrawlExtractedData(
            url=url,
            markdown=markdown[:2000],
            emails=list(set(email_pattern.findall(markdown)))[:3],
            phones=list(set(phone_pattern.findall(markdown)))[:3],
            has_whatsapp_widget="wa.me" in markdown or "whatsapp" in markdown.lower()
        )
