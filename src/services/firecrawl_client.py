"""
Firecrawl Client for IC (Intelligence Center)
Converts prospect websites to clean LLM-ready Markdown & detects broken forms/missing widgets.
Standards: Matt Pocock (/to-spec) Contract & ECC AgentShield Safety Gate.
"""
import os
import re
import logging
from typing import Dict, Any, Optional
from pydantic import BaseModel
import httpx
from config.settings import settings

logger = logging.getLogger(__name__)


class WebsiteAuditResult(BaseModel):
    url: str
    markdown: str
    title: str = ""
    has_whatsapp_widget: bool = False
    has_contact_form: bool = False
    has_instant_quote: bool = False
    status_code: int = 200
    source: str = "firecrawl"


class FirecrawlClient:
    """
    Client for firecrawl/firecrawl.
    Supports Cloud Firecrawl (API Key), self-hosted instance, and graceful local markdown fallback.
    """
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.base_url = base_url or os.getenv("FIRECRAWL_BASE_URL", "https://api.firecrawl.dev/v1")
        self._app = None

        if self.api_key:
            try:
                from firecrawl import FirecrawlApp
                self._app = FirecrawlApp(api_key=self.api_key)
            except Exception as e:
                logger.debug(f"FirecrawlApp init error: {e}")

    def scrape_url(self, url: str) -> WebsiteAuditResult:
        """
        Scrapes a prospect URL and returns structured Markdown & feature detection.
        """
        if not url.startswith("http"):
            url = f"https://{url}"

        # 1. Attempt official Firecrawl SDK if API key available
        if self._app:
            try:
                res = self._app.scrape_url(url, params={"formats": ["markdown", "html"]})
                md = res.get("markdown", "")
                metadata = res.get("metadata", {})
                title = metadata.get("title", "")
                
                return WebsiteAuditResult(
                    url=url,
                    markdown=md[:4000],
                    title=title,
                    has_whatsapp_widget=bool(re.search(r"whatsapp|wa\.me|api\.whatsapp", md, re.I)),
                    has_contact_form=bool(re.search(r"form|contact|inquiry|book|quote", md, re.I)),
                    has_instant_quote=bool(re.search(r"instant quote|calculator|rate finder", md, re.I)),
                    source="firecrawl_sdk"
                )
            except Exception as e:
                logger.warning(f"Firecrawl SDK scrape failed for {url}: {e}. Falling back to resilient local fetcher.")

        # 2. Resilient local fallback using HTTP + Markdown regex parser
        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
            with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                resp = client.get(url, headers=headers)
                html = resp.text
                status_code = resp.status_code

                # Basic HTML to clean text
                clean_text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r"<style[^>]*>.*?</style>", "", clean_text, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r"<[^>]+>", " ", clean_text)
                clean_text = re.sub(r"\s+", " ", clean_text).strip()

                title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
                title = title_match.group(1).strip() if title_match else url

                has_wa = bool(re.search(r"whatsapp|wa\.me|api\.whatsapp", html, re.I))
                has_form = bool(re.search(r"<form|type=[\"']submit[\"']", html, re.I))
                has_quote = bool(re.search(r"instant quote|calculator|rate finder", clean_text, re.I))

                return WebsiteAuditResult(
                    url=url,
                    markdown=clean_text[:4000],
                    title=title,
                    has_whatsapp_widget=has_wa,
                    has_contact_form=has_form,
                    has_instant_quote=has_quote,
                    status_code=status_code,
                    source="local_markdown_fallback"
                )
        except Exception as e:
            logger.warning(f"Local fallback scraper failed for {url}: {e}")
            return WebsiteAuditResult(
                url=url,
                markdown="Site could not be reached or timed out.",
                title="Unreachable Domain",
                status_code=504,
                source="error_fallback"
            )


firecrawl_client = FirecrawlClient()
