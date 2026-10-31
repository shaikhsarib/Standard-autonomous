import os
import shutil
import pytest

from core.schemas import ConversationContext, BusinessProfile, LeadOutput
from services.persistence import (
    save_conversation_context,
    load_conversation_context,
    save_lead_output,
    PersistenceError,
)
import services.persistence as _persistence_mod

TEST_STORAGE = "test_storage_tmp"


@pytest.fixture(autouse=True)
def _tmp_storage(monkeypatch, tmp_path):
    sessions = str(tmp_path / "sessions")
    leads = str(tmp_path / "leads")
    monkeypatch.setattr(_persistence_mod, "SESSIONS_DIR", sessions)
    monkeypatch.setattr(_persistence_mod, "LEADS_DIR", leads)
    yield
    # tmp_path cleaned up by pytest automatically


# ---------------------------------------------------------------------------
# ConversationContext round-trip
# ---------------------------------------------------------------------------

class TestConversationContextPersistence:
    def test_save_and_load(self):
        ctx = ConversationContext(session_id="sess-001")
        save_conversation_context(ctx)
        loaded = load_conversation_context("sess-001")
        assert loaded is not None
        assert loaded.session_id == "sess-001"
        assert loaded.history == []

    def test_load_nonexistent_returns_none(self):
        assert load_conversation_context("does-not-exist") is None

    def test_save_with_history(self):
        from core.schemas import Message
        ctx = ConversationContext(session_id="sess-002")
        ctx.history.append(Message(role="user", content="hello"))
        save_conversation_context(ctx)
        loaded = load_conversation_context("sess-002")
        assert len(loaded.history) == 1
        assert loaded.history[0].content == "hello"


# ---------------------------------------------------------------------------
# LeadOutput persistence
# ---------------------------------------------------------------------------

class TestLeadOutputPersistence:
    def test_save_lead_creates_file(self, monkeypatch):
        import services.persistence as pm
        lead = LeadOutput(session_id="lead-001", qualified=True, summary="Great lead")
        save_lead_output(lead)
        file_path = os.path.join(pm.LEADS_DIR, "lead-001.json")
        assert os.path.exists(file_path)

    def test_save_lead_with_none_budget(self):
        lead = LeadOutput(session_id="lead-002", qualified=False, budget=None, summary=None)
        save_lead_output(lead)  # should not raise
