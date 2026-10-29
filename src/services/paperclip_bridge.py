"""
Paperclip Swarm Bridge for IC (Intelligence Center)
Unifies IC FastAPI (:8000), Paperclip Server (:3100), and React Studio (:5173) into a single cohesive engine.
"""
import logging
from typing import Dict, Any, List, Optional
import httpx
from src.models.lead import Lead

logger = logging.getLogger(__name__)

PAPERCLIP_API_URL = "http://127.0.0.1:3100/api"
DEFAULT_COMPANY_ID = "fc52c515-6c63-4f40-b5f8-2496ffd76e79"


class PaperclipBridge:
    def __init__(self, base_url: str = PAPERCLIP_API_URL, company_id: str = DEFAULT_COMPANY_ID):
        self.base_url = base_url.rstrip("/")
        self.company_id = company_id

    def get_company(self) -> Optional[Dict[str, Any]]:
        """Fetches active Paperclip company details."""
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.get(f"{self.base_url}/companies/{self.company_id}")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.debug(f"Paperclip get_company error: {e}")
        return None

    def get_agents(self) -> List[Dict[str, Any]]:
        """Fetches live autonomous agents registered in Paperclip."""
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.get(f"{self.base_url}/companies/{self.company_id}/agents")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.debug(f"Paperclip get_agents error: {e}")
        return []

    def get_issues(self) -> List[Dict[str, Any]]:
        """Fetches active issues / tasks from Paperclip."""
        try:
            with httpx.Client(timeout=4.0) as client:
                res = client.get(f"{self.base_url}/companies/{self.company_id}/issues")
                if res.status_code == 200:
                    return res.json()
        except Exception as e:
            logger.debug(f"Paperclip get_issues error: {e}")
        return []

    def create_issue_from_lead(self, lead: Lead) -> Optional[Dict[str, Any]]:
        """
        Creates a formal Paperclip task/issue from an IC prospect lead.
        Assigns to the Copywriter / SDR Closer for human approval.
        """
        try:
            profile = lead.profile
            title = f"Qualify & Pitch: {profile.company_name} ({profile.business_type})"
            description = (
                f"**Lead ID:** {lead.id}\n"
                f"**Company:** {profile.company_name}\n"
                f"**Location:** {profile.location}\n"
                f"**Phone:** {profile.phone or 'N/A'}\n"
                f"**Website:** {profile.website or 'None'}\n\n"
                f"**HyperResearch Leak:** {getattr(lead, 'business_loss', 'Platform commissions & quote delays')}\n"
                f"**Pitch Draft:** {getattr(lead, 'whatsapp_message', '') or getattr(lead, 'email_body', '')}"
            )

            with httpx.Client(timeout=4.0) as client:
                payload = {
                    "title": title,
                    "description": description,
                    "status": "todo",
                    "priority": "high"
                }
                res = client.post(f"{self.base_url}/companies/{self.company_id}/issues", json=payload)
                if res.status_code in [200, 201]:
                    logger.info(f"Successfully synced lead {lead.id} to Paperclip issue.")
                    return res.json()
        except Exception as e:
            logger.warning(f"Failed to create Paperclip issue for lead {lead.id}: {e}")
        return None


paperclip_bridge = PaperclipBridge()
