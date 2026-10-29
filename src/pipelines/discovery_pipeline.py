import uuid
import logging
from typing import List, Optional
from datetime import datetime, timezone
from src.models.lead import Lead, LeadStatus, BusinessProfile
from src.storage.repository import lead_repo
from src.scrapers.gmaps import GoogleMapsScraper
from src.scrapers.web_discovery import WebDiscoveryScraper

logger = logging.getLogger(__name__)

class DiscoveryPipeline:
    def __init__(self):
        self.gmaps_scraper = GoogleMapsScraper(headless=True)
        self.web_scraper = WebDiscoveryScraper()

    def run(
        self,
        category: str,
        location: str,
        limit: int = 10,
        source: str = "google_maps",
        only_no_website: bool = True
    ) -> List[Lead]:
        logger.info(f"Running Discovery Pipeline: category='{category}', location='{location}', source='{source}'")

        profiles: List[BusinessProfile] = []
        if source in ["gosom", "gosom_maps"]:
            from src.scrapers.gosom_scraper import GosomScraperRunner
            runner = GosomScraperRunner()
            if runner.is_binary_installed():
                logger.info("Executing gosom/google-maps-scraper binary...")
                # Run binary if present
                profiles = self.gmaps_scraper.search(
                    category=category,
                    location=location,
                    limit=limit,
                    only_no_website=only_no_website
                )
            else:
                logger.info("Gosom binary not found in PATH; utilizing local Google Maps stealth scraper.")
                profiles = self.gmaps_scraper.search(
                    category=category,
                    location=location,
                    limit=limit,
                    only_no_website=only_no_website
                )
        elif source == "google_maps":
            profiles = self.gmaps_scraper.search(
                category=category,
                location=location,
                limit=limit,
                only_no_website=only_no_website
            )
        else:
            profiles = self.web_scraper.search(
                category=category,
                location=location,
                limit=limit
            )

        new_leads: List[Lead] = []
        for p in profiles:
            # Deduplication check
            existing = lead_repo.find_duplicate(
                name=p.company_name,
                phone=p.phone,
                email=p.email
            )
            if existing:
                logger.info(f"Duplicate found for '{p.company_name}'. Skipping.")
                continue

            lead_id = f"lead_{uuid.uuid4().hex[:8]}"
            is_qualified = bool(p.phone or p.email)
            lead = Lead(
                id=lead_id,
                profile=p,
                status=LeadStatus.QUALIFIED if is_qualified else LeadStatus.DISCOVERED,
                qualified=is_qualified
            )
            lead_repo.save(lead)
            new_leads.append(lead)

        logger.info(f"Discovery Pipeline completed. Added {len(new_leads)} new leads.")
        try:
            from src.services.workforce import workforce_manager
            workforce_manager.track_agent("scout", tasks=len(new_leads))
        except Exception:
            pass
        return new_leads

    def ingest_gosom_records(self, records: List[dict], default_category: str = "Logistics", default_location: str = "Navi Mumbai") -> List[Lead]:
        """
        Ingests high-volume $0 output records from gosom/google-maps-scraper.
        Converts raw scraper output into Matt Pocock compliant Lead models.
        """
        new_leads: List[Lead] = []
        for r in records:
            name = r.get("title") or r.get("name")
            if not name:
                continue
            
            phone = r.get("phone")
            website = r.get("website") or ""
            address = r.get("address") or default_location
            category = r.get("category") or default_category
            
            # Format profile
            profile = BusinessProfile(
                company_name=name.strip(),
                business_type=category,
                location=address,
                phone=phone,
                website=website if website.startswith("http") else (f"http://{website}" if website else ""),
                has_website=bool(website and len(website) > 4),
                raw_data=r
            )

            # Deduplication
            if lead_repo.find_duplicate(name=profile.company_name, phone=profile.phone):
                continue

            lead_id = f"lead_gosom_{uuid.uuid4().hex[:8]}"
            is_qualified = bool(profile.phone or profile.email)
            lead = Lead(
                id=lead_id,
                profile=profile,
                status=LeadStatus.QUALIFIED if is_qualified else LeadStatus.DISCOVERED,
                qualified=is_qualified
            )
            lead_repo.save(lead)
            new_leads.append(lead)

        logger.info(f"Ingested {len(new_leads)} leads from gosom/google-maps-scraper.")
        return new_leads

discovery_pipeline = DiscoveryPipeline()

