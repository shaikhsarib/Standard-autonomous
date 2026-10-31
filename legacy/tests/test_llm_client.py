"""
Tests for services/llm_client.py:
  - Gemini role mapping (assistant -> model)
  - 429 retry with backoff (mocked)
  - generate_response convenience wrapper
"""
import pytest
from unittest.mock import MagicMock, patch, call


# ---------------------------------------------------------------------------
# GeminiClient unit tests (all network calls mocked)
# ---------------------------------------------------------------------------

class TestGeminiClient:
    def _make_client(self):
        """Create GeminiClient with a fully mocked google.genai."""
        with patch.dict("sys.modules", {
            "google": MagicMock(),
            "google.genai": MagicMock(),
            "google.genai.types": MagicMock(),
        }):
            from importlib import reload
            import services.llm_client as lm
            reload(lm)

            mock_genai = MagicMock()
            mock_types = MagicMock()

            with patch.object(lm.GeminiClient, "__init__", lambda self, *a, **kw: None):
                client = lm.GeminiClient.__new__(lm.GeminiClient)
                client._genai = mock_genai
                client._types = mock_types
                client.api_key = "fake-key"
                client.model = "gemini-test"
                client.client = MagicMock()
            return client, mock_genai, mock_types, lm

    def test_role_mapping_assistant_to_model(self):
        client, _, mock_types, _ = self._make_client()

        # Capture Content() calls
        content_calls = []
        def fake_content(role, parts):
            content_calls.append(role)
            return MagicMock()
        mock_types.Content.side_effect = fake_content
        mock_types.Part.return_value = MagicMock()
        mock_types.GenerateContentConfig.return_value = MagicMock()

        mock_chat = MagicMock()
        mock_chat.send_message.return_value = MagicMock(text="reply")
        client.client.chats.create.return_value = mock_chat

        messages = [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "final question"},
        ]
        result = client.generate_chat(messages, "sys")
        assert result == "reply"
        # history has first 2 messages; the assistant one should be mapped to "model"
        assert "model" in content_calls
        assert "assistant" not in content_calls

    def test_429_retry_then_success(self):
        client, _, mock_types, lm = self._make_client()
        mock_types.Content.return_value = MagicMock()
        mock_types.Part.return_value = MagicMock()
        mock_types.GenerateContentConfig.return_value = MagicMock()

        mock_chat = MagicMock()
        client.client.chats.create.return_value = mock_chat

        # Fail twice with 429, succeed on third attempt
        mock_chat.send_message.side_effect = [
            Exception("429 Too Many Requests"),
            Exception("429 Too Many Requests"),
            MagicMock(text="ok"),
        ]

        with patch("services.llm_client.time.sleep") as mock_sleep:
            result = client.generate_chat(
                [{"role": "user", "content": "q"}], ""
            )

        assert result == "ok"
        assert mock_sleep.call_count == 2  # slept twice before success

    def test_exhausted_retries_returns_none(self):
        client, _, mock_types, lm = self._make_client()
        mock_types.Content.return_value = MagicMock()
        mock_types.Part.return_value = MagicMock()
        mock_types.GenerateContentConfig.return_value = MagicMock()

        mock_chat = MagicMock()
        client.client.chats.create.return_value = mock_chat
        mock_chat.send_message.side_effect = Exception("429 rate limit")

        with patch("services.llm_client.time.sleep"):
            result = client.generate_chat([{"role": "user", "content": "q"}], "")

        assert result is None

    def test_generate_response_wrapper(self):
        client, _, mock_types, _ = self._make_client()
        mock_types.Content.return_value = MagicMock()
        mock_types.Part.return_value = MagicMock()
        mock_types.GenerateContentConfig.return_value = MagicMock()

        mock_chat = MagicMock()
        mock_chat.send_message.return_value = MagicMock(text="single-turn")
        client.client.chats.create.return_value = mock_chat

        result = client.generate_response("What is 2+2?", "You are a calculator.")
        assert result == "single-turn"


# ---------------------------------------------------------------------------
# Scraper: CSV path and mocked OSM path
# ---------------------------------------------------------------------------

class TestScraper:
    def test_csv_path(self, tmp_path):
        import scrapers.scrapper_module as sm
        csv_file = tmp_path / "leads_input.csv"
        csv_file.write_text("name,website,email,phone,city\nAcme,acme.com,hi@acme.com,555,SF\n")

        with patch.object(sm, "LEADS_FILE", str(tmp_path / "actionable_leads.json")):
            import importlib, sys
            # Patch csv path temporarily
            original = sm.get_csv_businesses
            def patched_csv(limit):
                import csv
                businesses = []
                with open(str(csv_file), mode="r", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for i, row in enumerate(reader):
                        if i >= limit:
                            break
                        businesses.append({
                            "name": row.get("name", "Unknown"),
                            "website": row.get("website", ""),
                            "email": row.get("email", ""),
                            "phone": row.get("phone", ""),
                            "city": row.get("city", ""),
                            "contacted": False,
                        })
                return businesses
            sm.get_csv_businesses = patched_csv
            try:
                results = sm.find_businesses("tech", "SF", 5)
            finally:
                sm.get_csv_businesses = original

        assert len(results) == 1
        assert results[0]["name"] == "Acme"

    def test_osm_path_mocked(self, monkeypatch):
        import scrapers.scrapper_module as sm

        monkeypatch.setattr(sm, "geocode_location", lambda loc: (37.7749, -122.4194))
        monkeypatch.setattr(sm, "_load_cache", lambda key: None)
        monkeypatch.setattr(sm, "_save_cache", lambda key, data: None)
        monkeypatch.setattr(sm, "_existing_lead_names", lambda: set())
        monkeypatch.setattr(sm, "query_overpass", lambda q: [
            {"tags": {"name": "OSM Shop", "website": "shop.com", "email": "", "phone": ""}},
            {"tags": {}},  # no name – should be skipped
        ])
        monkeypatch.setattr(sm, "get_csv_businesses", lambda limit: [])
        monkeypatch.setattr(sm, "get_google_places_businesses", lambda q, l, lim: [])

        results = sm.find_businesses("shop", "San Francisco", 5)
        assert len(results) == 1
        assert results[0]["name"] == "OSM Shop"

    def test_already_contacted_skipped(self, monkeypatch):
        import scrapers.scrapper_module as sm

        monkeypatch.setattr(sm, "geocode_location", lambda loc: (37.7749, -122.4194))
        monkeypatch.setattr(sm, "_load_cache", lambda key: None)
        monkeypatch.setattr(sm, "_save_cache", lambda key, data: None)
        monkeypatch.setattr(sm, "_existing_lead_names", lambda: {"osm shop"})
        monkeypatch.setattr(sm, "query_overpass", lambda q: [
            {"tags": {"name": "OSM Shop"}},
        ])
        monkeypatch.setattr(sm, "get_csv_businesses", lambda limit: [])
        monkeypatch.setattr(sm, "get_google_places_businesses", lambda q, l, lim: [])

        results = sm.find_businesses("shop", "SF", 5)
        assert results == []
