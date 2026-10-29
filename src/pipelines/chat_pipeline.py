import os
import uuid
import yaml
import json
import logging
from typing import Optional, List, Dict, Any
from pathlib import Path

from config.settings import settings
from src.models.lead import BusinessProfile, Lead, LeadStatus, LeadOutput
from src.models.conversation import ConversationContext, Message
from src.storage.repository import session_repo, lead_repo
from src.services.llm import ProductionLLMClient

logger = logging.getLogger(__name__)

# Load claims
CLAIMS_FILE = settings.base_dir / "config" / "pitch_claims.yaml"
claims_data: dict = {"claims": []}
if CLAIMS_FILE.exists():
    with open(CLAIMS_FILE, "r", encoding="utf-8") as f:
        claims_data = yaml.safe_load(f) or claims_data

SYSTEM_PITCH_PROMPT = (
    "You are a senior business development representative for an expert software agency.\n"
    "Your goal is to converse with a business representative, understand their needs, and pitch custom software solutions "
    "focusing specifically on growth benefits, increased efficiency, or revenue generation.\n"
    "Reply in the user's conversation language (support English, Hinglish, and Spanish).\n\n"
    "Here is the profile of the business you are contacting:\n"
    "CompanyName: {company_name}\n"
    "Industry: {industry}\n"
    "Pain Points: {pain_points}\n"
    "Growth Goals: {growth_goals}\n\n"
    "Follow this conversation flow:\n"
    "1. Initially acknowledge their business situation based on the profile.\n"
    "2. Ask probing questions to confirm their pain points and quantify the impact.\n"
    "3. Pitch how our custom software services directly address those pain points to fuel their Growth Goals.\n"
    "4. Use these claims as evidence:\n"
    "{claims}\n\n"
    "Maintain a professional, consultative, and value-driven tone."
)

SYSTEM_EXTRACTION_PROMPT = (
    "Analyze the following conversation history between a salesperson and a potential client.\n"
    "Extract actionable lead information into a strict JSON format.\n\n"
    "Constraints:\n"
    "- Output only JSON (no markdown, no extra text).\n"
    "- If a piece of information is missing, use null.\n\n"
    "Fields to extract:\n"
    '{{\n'
    '  "contact_name": "Full name of the person represented by \'user\'",\n'
    '  "contact_email": "Official email address",\n'
    '  "budget": "Their stated or implied maximum budget (string, e.g. \'$5000\') or null",\n'
    '  "interest_level": "High, Medium, Low, or None based on tone and engagement",\n'
    '  "qualified": true or false,\n'
    '  "summary": "Key details of their needs and our potential solution"\n'
    '}}\n\n'
    "Conversation History:\n"
    "{history}"
)

class ChatPipeline:
    def __init__(self, llm_client: Optional[ProductionLLMClient] = None):
        self.llm = llm_client or ProductionLLMClient()

    def create_session(self, profile: BusinessProfile) -> ConversationContext:
        session = ConversationContext(
            session_id=f"sess_{uuid.uuid4().hex[:8]}",
            business_profile=profile
        )
        session_repo.save(session)
        return session

    def generate_next_response(self, session: ConversationContext, user_input: Optional[str] = None) -> str:
        if user_input:
            session.history.append(Message(role="user", content=user_input))

        claims_str = "\n".join([f"- {c}" for c in claims_data.get("claims", [])])
        system_msg = SYSTEM_PITCH_PROMPT.format(
            company_name=session.business_profile.company_name,
            industry=session.business_profile.business_type or "General",
            pain_points=", ".join(session.business_profile.pain_points) or "Not specified",
            growth_goals=", ".join(session.business_profile.growth_goals) or "Online growth",
            claims=claims_str
        )

        history_msgs = [{"role": m.role, "content": m.content} for m in session.history]
        if not user_input:
            history_msgs.append({"role": "user", "content": f"Begin the conversation with {session.business_profile.company_name}"})

        response = self.llm.generate_chat(history_msgs, system_message=system_msg)
        session.history.append(Message(role="assistant", content=response))
        session_repo.save(session)
        return response

    def extract_lead(self, session: ConversationContext) -> Optional[LeadOutput]:
        conversation_text = "\n".join([f"{m.role.capitalize()}: {m.content}" for m in session.history])
        prompt = SYSTEM_EXTRACTION_PROMPT.format(history=conversation_text)
        raw = self.llm.generate_response(prompt)

        try:
            import re
            cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
            cleaned = re.sub(r"\s*```$", "", cleaned.strip())
            data = json.loads(cleaned)
            
            # Coerce qualified boolean safely
            q = data.get("qualified")
            if isinstance(q, str):
                q = q.lower() == "true"
            elif not isinstance(q, bool):
                q = False

            return LeadOutput(
                contact_name=data.get("contact_name"),
                contact_email=data.get("contact_email"),
                budget=data.get("budget"),
                interest_level=data.get("interest_level"),
                qualified=q,
                summary=data.get("summary")
            )
        except Exception as e:
            logger.error(f"Failed parsing lead extraction: {e}")
            return None

chat_pipeline = ChatPipeline()
