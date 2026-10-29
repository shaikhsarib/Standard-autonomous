import json
import re
import logging
from typing import Dict, Any, Optional
from src.models.lead import BusinessProfile, OutreachDraft, AuditReport
from src.services.llm import ProductionLLMClient

logger = logging.getLogger(__name__)

ANALYSIS_SYSTEM_PROMPT = """You are a senior business development consultant specializing in digital solutions, web apps, and automated bookings for local businesses in India and globally.

Analyze the business profile AND technical audit findings provided. Return a STRICT JSON object with these exact keys:
{
  "pain_points": ["Specific audit-backed pain point 1", "Specific audit-backed pain point 2", "Specific pain point 3"],
  "business_loss": "Quantified statement of revenue or clients lost daily/weekly",
  "whatsapp_message": "Friendly, high-converting 2-3 line WhatsApp message citing the specific audit findings with low-friction CTA (Hinglish/English friendly)",
  "email_subject": "Punchy 4-7 word professional subject line citing the finding",
  "email_body": "Short consultative cold email (under 120 words), genuine observation of their audited flaws, specific solution, low-pressure CTA"
}

Important Rules:
1. Cite real audit flaws (e.g., slow load time, missing WhatsApp ordering widget, broken mobile layout, or high aggregator commissions).
2. Do NOT use fake placeholders like '[Your Name]' — sign off as 'Growth & Tech Team'.
3. Output ONLY valid raw JSON without any markdown formatting or code blocks.
"""

class BusinessAnalyzer:
    def __init__(self, llm_client: Optional[ProductionLLMClient] = None):
        self.llm = llm_client or ProductionLLMClient()

    def analyze(self, profile: BusinessProfile, audit: Optional[AuditReport] = None) -> OutreachDraft:
        audit_info = "Not audited yet"
        if audit:
            audit_info = (
                f"Load Time: {audit.load_time_seconds or 'N/A'}s | "
                f"SSL Secure: {audit.has_ssl} | "
                f"Mobile Responsive: {audit.is_mobile_responsive} | "
                f"Has WhatsApp Widget: {audit.has_whatsapp_widget} | "
                f"Has Online Booking: {audit.has_online_booking}\n"
                f"Key Detected Flaws: {', '.join(audit.key_flaws)}\n"
                f"Calculated Impact: {audit.quantified_loss}"
            )

        prompt = (
            f"Business Name: {profile.company_name}\n"
            f"Category/Industry: {profile.business_type}\n"
            f"City/Location: {profile.location}\n"
            f"Has Website: {'Yes (' + profile.website + ')' if profile.has_website and profile.website else 'No'}\n"
            f"Rating: {profile.rating or 'N/A'}\n"
            f"Technical Audit Findings:\n{audit_info}\n"
        )

        # If LLM client is not initialized with an API key, use domain-specific playbook
        if hasattr(self.llm, "client") and hasattr(self.llm.client, "client") and not self.llm.client.client:
            return self._fallback_draft(profile, audit)

        raw_response = self.llm.generate_response(prompt, system_message=ANALYSIS_SYSTEM_PROMPT)
        
        # Clean markdown code blocks if any
        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_response.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip())

        try:
            data = json.loads(cleaned)
            # If response is the generic dummy fallback, route to vertical playbook
            if "Hi, noticed your business is growing!" in data.get("whatsapp_message", ""):
                return self._fallback_draft(profile, audit)

            return OutreachDraft(
                whatsapp_message=data.get("whatsapp_message"),
                email_subject=data.get("email_subject"),
                email_body=data.get("email_body"),
                pain_points=data.get("pain_points", audit.key_flaws if audit else []),
                business_loss=data.get("business_loss", audit.quantified_loss if audit else None)
            )
        except Exception as e:
            logger.warning(f"Failed parsing LLM analysis JSON for {profile.company_name}: {e}. Falling back to rule-based draft.")
            return self._fallback_draft(profile, audit)

    def _fallback_draft(self, profile: BusinessProfile, audit: Optional[AuditReport] = None) -> OutreachDraft:
        from src.services.vertical_playbooks import detect_vertical, get_playbook, BusinessVertical
        vert = detect_vertical(profile.business_type, profile.company_name)
        playbook = get_playbook(vert)
        company = profile.company_name
        loc = profile.location

        if vert == BusinessVertical.LOGISTICS_TRANSPORT:
            wa_msg = playbook.whatsapp_pitch_template.format(company=company, location=loc)
            subj = playbook.email_subject_template.format(company=company)
            body = playbook.email_body_template.format(company=company, location=loc)
            points = audit.key_flaws if audit and audit.key_flaws else playbook.target_problems
            loss = playbook.quantified_loss_template
            return OutreachDraft(
                whatsapp_message=wa_msg,
                email_subject=subj,
                email_body=body,
                pain_points=points,
                business_loss=loss
            )
        elif vert == BusinessVertical.EVENT_MANAGEMENT:
            wa_msg = playbook.whatsapp_pitch_template.format(company=company, location=loc)
            subj = playbook.email_subject_template.format(company=company)
            body = playbook.email_body_template.format(company=company, location=loc)
            points = audit.key_flaws if audit and audit.key_flaws else playbook.target_problems
            loss = playbook.quantified_loss_template
            return OutreachDraft(
                whatsapp_message=wa_msg,
                email_subject=subj,
                email_body=body,
                pain_points=points,
                business_loss=loss
            )
        else:
            btype = profile.business_type.lower()
            if not profile.has_website:
                return OutreachDraft(
                    whatsapp_message=f"Hi team {company}, noticed you're doing great work in {loc}! We build direct online booking websites so you don't lose commission to aggregators. Would you be open to a 2-min demo?",
                    email_subject=f"Idea for {company}'s direct customer bookings",
                    email_body=f"Hi Team {company},\n\nI was looking at top-rated {btype}s in {loc} and came across your profile. Noticed you don't currently have a dedicated direct website for online orders/bookings.\n\nWe help businesses like yours launch modern mobile-friendly websites with automated WhatsApp booking systems in under 48 hours.\n\nWould you be open to a quick 5-min demo this week to see how it works?\n\nWarm regards,\nGrowth & Tech Team",
                    pain_points=audit.key_flaws if audit and audit.key_flaws else [
                        "No direct booking system",
                        "Losing potential clients who search online",
                        "Relying on aggregator platforms with high commissions"
                    ],
                    business_loss="Losing 15-25% margin and direct customer relationships"
                )
            else:
                return OutreachDraft(
                    whatsapp_message=f"Hi team {company}, love what you've built in {loc}! We help local brands double their lead conversion through automated WhatsApp response bots. Open to a quick preview?",
                    email_subject=f"Quick question regarding {company}'s customer flow",
                    email_body=f"Hi Team {company},\n\nLoved checking out your business in {loc}. We specialize in adding automated instant WhatsApp lead capture to existing websites to boost conversion by 30%.\n\nWould you be open to seeing a 2-minute video preview of how it would work for {company}?\n\nWarm regards,\nGrowth & Tech Team",
                    pain_points=audit.key_flaws if audit and audit.key_flaws else [
                        "Slow lead response times",
                        "Manual booking coordination on phone",
                        "Missing after-hours inquiries"
                    ],
                    business_loss="Losing prospective customers who don't get immediate replies"
                )

    generate_outreach_draft = analyze

analyzer = BusinessAnalyzer()
lead_analyzer = analyzer
