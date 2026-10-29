# IC (Intelligent Central) Architecture

## Overview

IC (Intelligent Central) is an Autonomous Sales Agency Operating System with a modular architecture. Each concern lives in its own layer: scraping, conversation, LLM integration, persistence, delivery, and analytics.

```
CLI (main.py)
  │
  ├─► scrapers/scrapper_module.py   ← find_businesses()
  │     CSV → Google Places → OSM Overpass (priority order)
  │     contact-page email finder (robots.txt-aware)
  │     in-memory + file-based cache per (query, location, limit)
  │
  ├─► core/engine.py                ← LeadGenerationEngine
  │     create_session()
  │     generate_next_response()    ← multi-turn conversation
  │     extract_lead()              ← LLM-powered JSON extraction
  │
  ├─► services/llm_client.py        ← LLM abstraction layer
  │     GeminiClient  (default)     ← google-genai SDK
  │     AnthropicClient (optional)  ← requires anthropic package
  │     OllamaClient  (optional)    ← local models via HTTP
  │     ProductionLLMClient         ← routes via LLM_PROVIDER env var
  │     generate_chat(messages, system_message)
  │     generate_response(prompt, system_message)
  │
  ├─► services/persistence.py       ← local file storage
  │     save/load ConversationContext  → storage/sessions/<id>.json
  │     save LeadOutput               → storage/leads/<id>.json
  │
  ├─► delivery/delivery_module.py   ← multi-channel delivery
  │     send_telegram()             ← HTML-escaped, None-safe
  │     send_email()                ← Gmail SMTP via smtplib
  │     send_whatsapp()             ← Twilio REST API
  │     deliver_lead()              ← dedup + all channels
  │
  └─► analytics/analytics.py        ← event tracking
        track_event()               → chatbot_analytics.json
```

## Key Design Decisions

**LLM provider abstraction** — `BaseLLMClient` defines `generate_chat` and `generate_response`. `ProductionLLMClient` selects the backend via `LLM_PROVIDER`. Adding a new provider means subclassing `BaseLLMClient` and adding a branch in `ProductionLLMClient.__init__`.

**Gemini role mapping** — Gemini's API uses `"model"` for assistant turns. The client maps `"assistant"` → `"model"` automatically before building conversation history.

**Retry with backoff** — `GeminiClient` retries up to 3 times on 429 and 5xx errors using exponential backoff (2s, 4s).

**Extraction prompt brace escaping** — `SYSTEM_EXTRACTION_PROMPT` uses Python doubled-braces `{{ }}` for the JSON example so `.format()` does not KeyError on the template literal.

**`qualified` bool coercion** — the `extract_lead()` helper in `schemas.py` checks if the value is a string before calling `.lower() == "true"`, avoiding the `bool("False") == True` trap.

**None-safe delivery** — every field passed to `send_telegram`, `send_email`, `send_whatsapp` is coerced via `_s(value)` which returns `"-"` for `None`, preventing `html.escape(None)` crashes.

**OSM query** — uses proper Overpass tag filters (`shop`, `office`, `craft`) combined with `name` presence, not raw search text as a tag key. Results are filtered for a `name` tag and limited after filtering.

**Deduplication** — `lead_exists(email, name)` scans `actionable_leads.json` before saving. Duplicate leads are skipped silently.

## Data Flow

```
find_businesses()
       │
       ▼
BusinessProfile
       │
       ▼
LeadGenerationEngine.create_session()
       │
       ▼
[loop] generate_next_response()  ←→  LLM (Gemini / Anthropic / Ollama)
       │                              save_conversation_context()
       ▼
extract_lead()  →  LeadOutput (JSON)
       │
       ▼
deliver_lead()
  ├── save to actionable_leads.json
  ├── send_telegram()
  ├── send_email()
  └── send_whatsapp()
```

## Folder Structure

```
├── core/
│   ├── engine.py          # LeadGenerationEngine, prompts
│   └── schemas.py         # Pydantic models, extract_lead helper
├── delivery/
│   └── delivery_module.py # Telegram, Email, WhatsApp delivery
├── scrapers/
│   └── scrapper_module.py # CSV, Google Places, OSM scraping
├── services/
│   ├── llm_client.py      # LLM clients (Gemini, Anthropic, Ollama)
│   └── persistence.py     # Session and lead file storage
├── analytics/
│   └── analytics.py       # Simple JSON event tracking
├── config/
│   └── pitch_claims.yaml  # Sales claims injected into system prompt
├── tests/                 # All unit tests (no live network calls)
├── main.py                # CLI entry point
├── requirements.txt
└── .env                   # Secrets (never committed)
```
