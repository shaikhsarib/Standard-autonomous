import json
import pytest
from unittest.mock import MagicMock, patch

from core.engine import LeadGenerationEngine
from core.schemas import BusinessProfile, ConversationContext, Message, extract_lead, LeadOutput


def _make_engine(response_text: str = ""):
    mock_llm = MagicMock()
    mock_llm.generate_chat.return_value = response_text
    with patch("core.engine.save_conversation_context"), patch("core.engine.track_event"):
        engine = LeadGenerationEngine(mock_llm)
    return engine, mock_llm


def _session(engine, name="Test Co"):
    profile = BusinessProfile(company_name=name, pain_points=[], growth_goals=[])
    return engine.create_session(profile)


# ---------------------------------------------------------------------------
# extract_lead: fenced JSON
# ---------------------------------------------------------------------------

class TestExtractLead:
    def _run(self, raw_response: str):
        engine, mock_llm = _make_engine(raw_response)
        session = _session(engine)
        session.history.append(Message(role="user", content="hello"))
        session.history.append(Message(role="assistant", content="hi"))
        with patch("core.engine.save_conversation_context"):
            return engine.extract_lead(session)

    def test_fenced_json(self):
        payload = json.dumps({
            "contact_name": "Jane Doe",
            "contact_email": "jane@example.com",
            "qualified": True,
            "interest_level": "High",
            "budget": "$2000",
            "summary": "Good fit",
        })
        lead = self._run(f"```json\n{payload}\n```")
        assert lead is not None
        assert lead.contact_name == "Jane Doe"
        assert lead.qualified is True

    def test_qualified_true_string(self):
        """'True' as a string must become bool True."""
        payload = json.dumps({
            "contact_name": "Bob",
            "contact_email": "bob@b.com",
            "qualified": "True",
            "interest_level": "Medium",
            "budget": None,
            "summary": None,
        })
        lead = self._run(payload)
        assert lead.qualified is True

    def test_qualified_false_string(self):
        payload = json.dumps({
            "contact_name": "Carol",
            "contact_email": "carol@c.com",
            "qualified": "False",
            "interest_level": "Low",
            "budget": None,
            "summary": None,
        })
        lead = self._run(payload)
        assert lead.qualified is False

    def test_budget_none(self):
        payload = json.dumps({
            "contact_name": "Dan",
            "contact_email": "dan@d.com",
            "qualified": True,
            "interest_level": "High",
            "budget": None,
            "summary": "No budget stated",
        })
        lead = self._run(payload)
        assert lead is not None
        assert lead.budget is None

    def test_garbage_response_returns_none(self):
        lead = self._run("I could not extract anything useful.")
        assert lead is None

    def test_null_fields(self):
        payload = json.dumps({
            "contact_name": None,
            "contact_email": None,
            "qualified": False,
            "interest_level": None,
            "budget": None,
            "summary": None,
        })
        lead = self._run(payload)
        assert lead is not None
        assert lead.contact_name is None
        assert lead.contact_email is None
        assert lead.interest_level == "None"


# ---------------------------------------------------------------------------
# extract_lead helper (schema-level)
# ---------------------------------------------------------------------------

class TestExtractLeadHelper:
    def test_true_string_coercion(self):
        lead = extract_lead({"qualified": "True", "interest_level": "High"}, "s1")
        assert lead.qualified is True

    def test_false_string_coercion(self):
        lead = extract_lead({"qualified": "False", "interest_level": "Low"}, "s1")
        assert lead.qualified is False

    def test_defaults(self):
        lead = extract_lead({}, "s2")
        assert lead.qualified is False
        assert lead.interest_level == "None"
        assert lead.budget is None
        assert lead.summary is None


# ---------------------------------------------------------------------------
# Multilingual: engine passes system prompt in English and relies on LLM
# ---------------------------------------------------------------------------

class TestMultilingual:
    def test_system_prompt_contains_language_instruction(self):
        from core.engine import SYSTEM_PITCH_PROMPT
        assert "language" in SYSTEM_PITCH_PROMPT.lower()

    def test_hinglish_input_reaches_llm(self):
        engine, mock_llm = _make_engine("Bilkul, hum madad kar sakte hain!")
        session = _session(engine)
        with patch("core.engine.save_conversation_context"), patch("core.engine.track_event"):
            resp = engine.generate_next_response(session, "Kya aap mujhe help kar sakte ho?")
        mock_llm.generate_chat.assert_called_once()
        assert "Bilkul" in resp

    def test_spanish_input_reaches_llm(self):
        engine, mock_llm = _make_engine("¡Claro que sí!")
        session = _session(engine)
        with patch("core.engine.save_conversation_context"), patch("core.engine.track_event"):
            resp = engine.generate_next_response(session, "¿Pueden ayudarme con software?")
        assert "Claro" in resp
