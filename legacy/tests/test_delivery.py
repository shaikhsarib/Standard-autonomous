import json
import os
import pytest
from unittest.mock import patch, MagicMock
import html

import delivery.delivery_module as dm


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_leads_file(tmp_path, monkeypatch):
    """Redirect LEADS_FILE to a temp path for every test."""
    fake = str(tmp_path / "actionable_leads.json")
    monkeypatch.setattr(dm, "LEADS_FILE", fake)
    yield fake


# ---------------------------------------------------------------------------
# send_telegram
# ---------------------------------------------------------------------------

class TestSendTelegram:
    def test_skips_when_config_missing(self, monkeypatch):
        monkeypatch.setattr(dm, "TELEGRAM_BOT_TOKEN", None)
        monkeypatch.setattr(dm, "TELEGRAM_CHAT_ID", "123")
        assert dm.send_telegram({"name": "X"}) is False

    def test_success(self, monkeypatch, requests_mock):
        monkeypatch.setattr(dm, "TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setattr(dm, "TELEGRAM_CHAT_ID", "42")
        requests_mock.post("https://api.telegram.org/bottok/sendMessage", json={"ok": True})

        result = dm.send_telegram({"name": "Acme", "website": "acme.com", "budget": "$1000", "email": "a@b.com"})
        assert result is True

    def test_html_escaping(self, monkeypatch, requests_mock):
        """'A&B <Co>' must be properly escaped in the Telegram payload."""
        monkeypatch.setattr(dm, "TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setattr(dm, "TELEGRAM_CHAT_ID", "42")
        adapter = requests_mock.post("https://api.telegram.org/bottok/sendMessage", json={"ok": True})

        dm.send_telegram({"name": "A&B <Co>", "website": None, "budget": None, "email": None})

        sent_body = adapter.last_request.json()
        assert html.escape("A&B <Co>") in sent_body["text"]
        assert "A&B <Co>" not in sent_body["text"]

    def test_none_values_do_not_crash(self, monkeypatch, requests_mock):
        monkeypatch.setattr(dm, "TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setattr(dm, "TELEGRAM_CHAT_ID", "42")
        requests_mock.post("https://api.telegram.org/bottok/sendMessage", json={"ok": True})

        # All fields None — must not raise
        result = dm.send_telegram({"name": None, "website": None, "budget": None, "email": None})
        assert result is True

    def test_budget_none_shows_dash(self, monkeypatch, requests_mock):
        monkeypatch.setattr(dm, "TELEGRAM_BOT_TOKEN", "tok")
        monkeypatch.setattr(dm, "TELEGRAM_CHAT_ID", "42")
        adapter = requests_mock.post("https://api.telegram.org/bottok/sendMessage", json={"ok": True})

        dm.send_telegram({"name": "Test", "website": "t.com", "budget": None, "email": "t@t.com"})
        assert "-" in adapter.last_request.json()["text"]


# ---------------------------------------------------------------------------
# deliver_lead per-channel dict
# ---------------------------------------------------------------------------

class TestDeliverLead:
    def _patch_channels(self, mocker, telegram=True, email=True, whatsapp=True):
        mocker.patch.object(dm, "send_telegram", return_value=telegram)
        mocker.patch.object(dm, "send_email", return_value=email)
        mocker.patch.object(dm, "send_whatsapp", return_value=whatsapp)

    def test_all_pass(self, mocker):
        self._patch_channels(mocker)
        status = dm.deliver_lead({"name": "Acme", "email": "a@b.com"})
        assert status == {"file": True, "telegram": True, "email": True, "whatsapp": True}

    def test_one_channel_fails(self, mocker):
        self._patch_channels(mocker, telegram=False, whatsapp=False)
        status = dm.deliver_lead({"name": "Acme", "email": "a@b.com"})
        assert status["telegram"] is False
        assert status["whatsapp"] is False
        assert status["email"] is True
        assert status["file"] is True

    def test_dedup_skips_save(self, mocker, _no_leads_file):
        """Second call with same email+name must not double-write."""
        self._patch_channels(mocker)
        lead = {"name": "Dup Co", "email": "dup@co.com"}
        dm.deliver_lead(lead)
        dm.deliver_lead(lead)  # second call

        with open(_no_leads_file) as f:
            saved = json.load(f)
        assert len(saved) == 1  # only one entry

    def test_file_save_failure_reflected_in_status(self, mocker):
        self._patch_channels(mocker)
        mocker.patch.object(dm, "save_lead_to_file", return_value=False)
        status = dm.deliver_lead({"name": "Bad", "email": "b@b.com"})
        assert status["file"] is False


# ---------------------------------------------------------------------------
# Persistence round-trip via load_actionable_leads / save_lead_to_file
# ---------------------------------------------------------------------------

class TestLeadsFilePersistence:
    def test_round_trip(self, _no_leads_file):
        lead = {"name": "RoundTrip Co", "email": "rt@co.com", "budget": "$500"}
        dm.save_lead_to_file(lead)
        loaded = dm.load_actionable_leads()
        assert len(loaded) == 1
        assert loaded[0]["email"] == "rt@co.com"

    def test_empty_file_returns_empty_list(self, _no_leads_file):
        assert dm.load_actionable_leads() == []
