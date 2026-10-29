import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from src.models.lead import Lead, LeadStatus, OutreachChannel
from src.storage.repository import lead_repo
from src.services.analyzer import BusinessAnalyzer
from src.services.site_inspector import site_inspector
from src.delivery.dispatcher import dispatcher
from src.scrapers.scrapling_scraper import ScraplingStealthScraper
from src.scrapers.firecrawl_scraper import FirecrawlScraper
from src.services.treg_tool_client import treg_client

logger = logging.getLogger(__name__)

class OutreachPipeline:
    def __init__(self, analyzer: Optional[BusinessAnalyzer] = None):
        self.analyzer = analyzer or BusinessAnalyzer()
        self.scrapling = ScraplingStealthScraper()
        self.firecrawl = FirecrawlScraper()

    def enrich_lead(self, lead: Lead) -> Lead:
        """Enriches lead with real technical site audit, Scrapling reviews, Firecrawl markdown, and AI pitch."""
        # Step 0: Treg Phone & Channel Verification
        if lead.profile.phone:
            v_res = treg_client.verify_phone(lead.profile.phone)
            if v_res.success and v_res.output.get("phone"):
                lead.profile.phone = v_res.output["phone"]

        # Step 1: Technical Site Audit (inspired by REA)
        if not lead.audit:
            logger.info(f"Conducting technical site audit for '{lead.profile.company_name}'...")
            lead.audit = site_inspector.audit(lead.profile)

        # Step 1B: Firecrawl Web-to-Markdown & Widget Detection
        if lead.profile.has_website and lead.profile.website:
            try:
                fc_data = self.firecrawl.scrape(lead.profile.website)
                if fc_data.has_whatsapp_widget:
                    lead.audit.has_whatsapp_widget = True
                if fc_data.has_booking_calendar:
                    lead.audit.has_online_booking = True
                if fc_data.phones and not lead.profile.phone:
                    lead.profile.phone = fc_data.phones[0]
                if fc_data.emails and not lead.profile.email:
                    lead.profile.email = fc_data.emails[0]
            except Exception as e:
                logger.debug(f"Firecrawl enrichment skipped: {e}")

        # Step 1C: Scrapling Stealth Negative Reviews & Public Bottlenecks
        try:
            reviews = self.scrapling.fetch_negative_reviews(lead.profile.company_name, lead.profile.location)
            for r in reviews:
                if r.quote_text not in lead.profile.pain_points:
                    lead.profile.pain_points.append(r.quote_text)
        except Exception as e:
            logger.debug(f"Scrapling review collection skipped: {e}")

        # Step 2: AI Value Synthesis & Copywriting
        if not lead.draft or not lead.draft.whatsapp_message:
            logger.info(f"Generating AI outreach draft for '{lead.profile.company_name}'...")
            lead.draft = self.analyzer.analyze(lead.profile, lead.audit)
            lead.profile.pain_points = lead.draft.pain_points
            lead.summary = lead.draft.whatsapp_message
            lead.qualified = True

        # Stage in Approval Gate
        if lead.status in [LeadStatus.DISCOVERED, LeadStatus.QUALIFIED]:
            lead.status = LeadStatus.PENDING_APPROVAL

        lead.updated_at = datetime.now(timezone.utc)
        lead_repo.save(lead)
        return lead

    def dispatch_outreach(
        self,
        lead: Lead,
        channel: OutreachChannel = OutreachChannel.WHATSAPP,
        dry_run: bool = False
    ) -> bool:
        """Sends the outreach via preferred channel (WhatsApp, Email, Telegram)."""
        lead = self.enrich_lead(lead)
        p = lead.profile
        draft = lead.draft

        if not draft:
            logger.warning(f"No outreach draft available for {p.company_name}")
            return False

        success = False

        if channel == OutreachChannel.WHATSAPP:
            phone = p.phone
            if not phone:
                logger.warning(f"Cannot send WhatsApp: No phone number for {p.company_name}")
                return False
            if dry_run:
                logger.info(f"[DRY-RUN WhatsApp] To: {phone} | Message: {draft.whatsapp_message}")
                success = True
            else:
                success = dispatcher.send_whatsapp(phone, draft.whatsapp_message)

        elif channel == OutreachChannel.EMAIL:
            email = p.email or lead.contact_email
            if not email:
                logger.warning(f"Cannot send Email: No email address for {p.company_name}")
                return False
            if dry_run:
                logger.info(f"[DRY-RUN Email] To: {email} | Subject: {draft.email_subject}")
                success = True
            else:
                success = dispatcher.send_email(email, draft.email_subject or "Business Inquiry", draft.email_body or "")

        elif channel == OutreachChannel.TELEGRAM:
            if dry_run:
                logger.info(f"[DRY-RUN Telegram] Alert for {p.company_name}")
                success = True
            else:
                dispatcher.notify_lead_captured(lead)
                success = True

        if success:
            if channel not in lead.contacted_channels:
                lead.contacted_channels.append(channel)
            lead.status = LeadStatus.CONTACTED
            lead.last_contacted_at = datetime.now(timezone.utc)
            lead_repo.save(lead)

        return success

    def run_batch(
        self,
        channel: OutreachChannel = OutreachChannel.WHATSAPP,
        limit: int = 5,
        dry_run: bool = True
    ) -> Dict[str, Any]:
        """Runs outreach across pending qualified leads."""
        pending_leads = [
            l for l in lead_repo.list_all(status=LeadStatus.QUALIFIED)
            if channel not in l.contacted_channels
        ][:limit]

        logger.info(f"Starting batch outreach for {len(pending_leads)} leads via {channel.value} (dry_run={dry_run})")
        results = {"total": len(pending_leads), "succeeded": 0, "failed": 0, "leads": []}

        for lead in pending_leads:
            ok = self.dispatch_outreach(lead, channel=channel, dry_run=dry_run)
            if ok:
                results["succeeded"] += 1
            else:
                results["failed"] += 1
            results["leads"].append({"id": lead.id, "name": lead.profile.company_name, "success": ok})

        return results

outreach_pipeline = OutreachPipeline()
