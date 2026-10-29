import json
import uuid
import logging
import re
import os
import yaml
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

from analytics.analytics import track_event
from core.schemas import BusinessProfile, Message, ConversationContext, LeadOutput, extract_lead
from services.persistence import save_conversation_context

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load claims from YAML
CLAIMS_FILE = os.path.join("config", "pitch_claims.yaml")
claims_data: dict = {"claims": []}
if os.path.exists(CLAIMS_FILE):
    with open(CLAIMS_FILE, "r") as _f:
        claims_data = yaml.safe_load(_f) or claims_data

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

# Braces inside the JSON example are doubled so .format() does not trip on them.
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


class LeadGenerationEngine:
    """Orchestrates the conversation flow and lead extraction process."""

    def __init__(self, llm_client):
        self.llm_client = llm_client

    def create_session(self, profile: BusinessProfile) -> ConversationContext:
        return ConversationContext(
            session_id=str(uuid.uuid4()),
            business_profile=profile,
            history=[],
            metadata={},
        )

    def generate_next_response(
        self, context: ConversationContext, user_input: Optional[str] = None
    ) -> str:
        if user_input:
            context.history.append(Message(role="user", content=user_input))
            track_event("user_message", {"session_id": context.session_id, "input_length": len(user_input)})

        claims_str = "\n".join([f"- {c}" for c in claims_data.get("claims", [])])
        system_message = SYSTEM_PITCH_PROMPT.format(
            company_name=context.business_profile.company_name,
            industry=context.business_profile.industry or "Unknown",
            pain_points=", ".join(context.business_profile.pain_points) or "Not identified",
            growth_goals=", ".join(context.business_profile.growth_goals) or "Not identified",
            claims=claims_str,
        )

        llm_history = [{"role": msg.role, "content": msg.content} for msg in context.history]

        if not user_input:
            llm_history.append(
                {"role": "user", "content": f"Begin the conversation with {context.business_profile.company_name}"}
            )

        response = self.llm_client.generate_chat(llm_history, system_message)
        bot_response = response or "Hmm, I am having trouble connecting. Let me get back to you."

        context.history.append(Message(role="assistant", content=bot_response))
        save_conversation_context(context)
        track_event("bot_response", {"session_id": context.session_id, "output_length": len(bot_response)})

        return bot_response

    def extract_lead(self, context: ConversationContext) -> Optional[LeadOutput]:
        history_text = "\n".join([f"{msg.role}: {msg.content}" for msg in context.history])
        prompt = SYSTEM_EXTRACTION_PROMPT.format(history=history_text)

        response = self.llm_client.generate_chat([{"role": "user", "content": prompt}])
        if not response:
            return None

        # Strip markdown fences if present
        clean = re.sub(r"^```(?:json)?\s*", "", response.strip(), flags=re.IGNORECASE)
        clean = re.sub(r"\s*```$", "", clean.strip())

        try:
            data = json.loads(clean)
        except json.JSONDecodeError as exc:
            logging.error(f"Lead extraction JSON parse failed: {exc}. Raw: {response!r}")
            return None

        try:
            return extract_lead(data, context.session_id)
        except Exception as exc:
            logging.error(f"LeadOutput construction failed: {exc}")
            return None
