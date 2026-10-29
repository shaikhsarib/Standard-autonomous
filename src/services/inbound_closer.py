import logging
import re
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel

from src.models.lead import Lead, LeadStatus
from src.storage.repository import lead_repo
from src.services.llm import llm_client
from src.services.workforce import workforce_manager

logger = logging.getLogger(__name__)

class ProspectIntent(str, Enum):
    INTERESTED = "interested"
    PRICE_OBJECTION = "price_objection"
    AGENCY_OBJECTION = "agency_objection"
    NOT_INTERESTED = "not_interested"
    UNSUBSCRIBE = "unsubscribe"
    GENERAL_QUERY = "general_query"

class CloserResponse(BaseModel):
    intent: ProspectIntent
    reply_message: str
    booking_link_included: bool
    recommended_status: LeadStatus
    confidence: float

class InboundCloser:
    """
    Autonomous Inbound SDR & Closer Agent.
    Handles objections, grounds answers in technical audit findings,
    and drives prospects toward a 10-minute demo booking.
    """

    def __init__(self, demo_link: str = "https://calendly.com/agency-demo/15min"):
        self.demo_link = demo_link

    def classify_intent(self, user_message: str) -> ProspectIntent:
        """Classifies incoming prospect message using regex heuristics + fallback."""
        msg = user_message.lower().strip()

        # 1. Unsubscribe triggers
        if any(w in msg for w in ["stop", "unsubscribe", "don't message", "do not call", "remove me", "spam"]):
            return ProspectIntent.UNSUBSCRIBE

        # 2. Price / Cost objections
        if any(w in msg for w in ["price", "cost", "charge", "fees", "kitna", "rates", "expensive", "budget", "paisa"]):
            return ProspectIntent.PRICE_OBJECTION

        # 3. Already have an agency
        if any(w in msg for w in ["already have", "agency", "developer", "hamare paas hai", "in-house", "someone handles"]):
            return ProspectIntent.AGENCY_OBJECTION

        # 4. Clear rejection
        if any(w in msg for w in ["not interested", "no need", "nahi chahiye", "no thanks", "busy"]):
            return ProspectIntent.NOT_INTERESTED

        # 5. Interest / Curiosity / Inquiries
        if any(w in msg for w in ["demo", "portfolio", "sample", "yes", "tell me", "explain", "call me", "details", "how does it work", "interested", "batao", "ha"]):
            return ProspectIntent.INTERESTED

        return ProspectIntent.GENERAL_QUERY

    def handle_incoming_message(self, lead_id: str, prospect_text: str) -> CloserResponse:
        """
        Receives inbound prospect reply, analyzes objection, consults audit report,
        and generates an objection-handling reply.
        """
        lead = lead_repo.get_by_id(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        intent = self.classify_intent(prospect_text)
        flaw_summary = ""
        if lead.audit and lead.audit.key_flaws:
            flaw_summary = "; ".join(lead.audit.key_flaws[:2])
        company = lead.profile.company_name

        from src.services.vertical_playbooks import detect_vertical, get_playbook, BusinessVertical
        vert = detect_vertical(lead.profile.business_type, lead.profile.company_name)
        playbook = get_playbook(vert)

        reply_text = ""
        new_status = LeadStatus.REPLIED
        booking_included = True

        lower_msg = prospect_text.lower()

        # Check for sector-specific objection triggers first
        if vert == BusinessVertical.LOGISTICS_TRANSPORT and any(w in lower_msg for w in ["broker", "load board", "brokers", "freight broker"]):
            reply_text = f"{playbook.hermes_objections.get('broker_network', '').format(company=company)}\n\nGrab a quick 5-min slot to see live carrier demo: {self.demo_link}"
            new_status = LeadStatus.REPLIED
        elif vert == BusinessVertical.LOGISTICS_TRANSPORT and any(w in lower_msg for w in ["truck", "fleet", "small", "drivers"]):
            reply_text = f"{playbook.hermes_objections.get('fleet_size', '').format(company=company)}\n\nSee how it works here: {self.demo_link}"
            new_status = LeadStatus.REPLIED
        elif vert == BusinessVertical.EVENT_MANAGEMENT and any(w in lower_msg for w in ["referral", "word of mouth", "instagram", "mouth"]):
            reply_text = f"{playbook.hermes_objections.get('word_of_mouth', '').format(company=company)}\n\nTake a look at the live date-checker prototype: {self.demo_link}"
            new_status = LeadStatus.REPLIED
        elif vert == BusinessVertical.EVENT_MANAGEMENT and any(w in lower_msg for w in ["custom", "every wedding", "unique"]):
            reply_text = f"{playbook.hermes_objections.get('custom_events', '').format(company=company)}\n\nQuick 5-min walkthrough: {self.demo_link}"
            new_status = LeadStatus.REPLIED
        elif intent == ProspectIntent.UNSUBSCRIBE:
            reply_text = "Understood! I have removed your number from our outreach list. Wishing your business continued success!"
            new_status = LeadStatus.UNQUALIFIED
            booking_included = False

        elif intent == ProspectIntent.NOT_INTERESTED:
            reply_text = f"Totally understand, {company}! If you ever want to see how other local {lead.profile.business_type} businesses automate 20+ direct orders a week, feel free to ping us. Best of luck!"
            new_status = LeadStatus.UNQUALIFIED
            booking_included = False

        elif intent == ProspectIntent.PRICE_OBJECTION:
            if vert == BusinessVertical.LOGISTICS_TRANSPORT:
                reply_text = (
                    f"Great question! Our setup pays for itself with just 1 direct freight booking that bypasses 18% broker cuts. "
                    f"Instead of giving away margin on every load, direct shippers book directly via WhatsApp.\n\n"
                    f"Let's hop on a quick 5-min screen share to see live numbers: {self.demo_link}"
                )
            elif vert == BusinessVertical.EVENT_MANAGEMENT:
                reply_text = (
                    f"Great question! Securing just 1 extra weekend venue or catering booking that would have bounced after 8 PM pays for the entire setup for the year. "
                    f"Our clients typically see a 2x increase in qualified weekend consultations.\n\n"
                    f"Let's hop on a quick 5-min screen share to see live numbers: {self.demo_link}"
                )
            else:
                reply_text = (
                    f"Great question! Our setup pays for itself within the first month. "
                    f"Most {lead.profile.business_type} owners in {lead.profile.location} lose 20-30% on aggregator commissions. "
                    f"With direct WhatsApp ordering, retaining just 2-3 extra customers covers the entire cost.\n\n"
                    f"Let's hop on a quick 5-min screen share to see live numbers: {self.demo_link}"
                )
            new_status = LeadStatus.REPLIED

        elif intent == ProspectIntent.AGENCY_OBJECTION:
            specific_mention = f" We noticed: {flaw_summary}." if flaw_summary else ""
            reply_text = (
                f"That's great that you have marketing support! Many of our clients also have an agency,"
                f" but agencies typically focus on posts rather than conversion infrastructure.{specific_mention}\n\n"
                f"We can send a free 1-page technical audit your existing team can use: {self.demo_link}"
            )
            new_status = LeadStatus.REPLIED

        elif intent == ProspectIntent.INTERESTED:
            reply_text = (
                f"Awesome to connect! We build automated WhatsApp ordering & mobile booking engines for top {lead.profile.business_type}s.\n\n"
                f"Here is a 10-minute slot where our lead architect can walk you through the live prototype: {self.demo_link}\n"
                f"Does tomorrow or Wednesday afternoon work better for you?"
            )
            new_status = LeadStatus.CONVERTED

        else:
            # General query - try LLM generation if available
            prompt = (
                f"You are an elite B2B SDR Closer for an automation agency. A prospect from '{company}' replied: '{prospect_text}'.\n"
                f"Their business type: {lead.profile.business_type}, location: {lead.profile.location}.\n"
                f"Audit flaws found on their site: {flaw_summary or 'No direct booking system'}.\n"
                f"Booking link: {self.demo_link}.\n"
                f"Write a warm, concise (under 50 words) WhatsApp reply answering their question and offering the booking link."
            )
            llm_reply = llm_client.generate(prompt)
            if llm_reply and len(llm_reply) > 15:
                reply_text = llm_reply
            else:
                reply_text = (
                    f"Thanks for reaching out! We'd love to show you how {company} can generate direct leads without commission fees.\n"
                    f"Pick a quick 5-min time slot here: {self.demo_link}"
                )
            new_status = LeadStatus.REPLIED

        # Record conversation thread in lead model
        now_iso = datetime.now(timezone.utc).isoformat()
        lead.conversation_history.append({
            "sender": "prospect",
            "message": prospect_text,
            "timestamp": now_iso,
            "intent": intent.value
        })
        lead.conversation_history.append({
            "sender": "closer_agent",
            "message": reply_text,
            "timestamp": now_iso
        })
        lead.status = new_status
        lead.updated_at = datetime.now(timezone.utc)
        lead_repo.save(lead)

        workforce_manager.track_agent("closer", tasks=1, tokens=350)

        return CloserResponse(
            intent=intent,
            reply_message=reply_text,
            booking_link_included=booking_included,
            recommended_status=new_status,
            confidence=0.92
        )

inbound_closer = InboundCloser()
