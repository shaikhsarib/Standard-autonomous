# Project Architecture & Folder Structure (v2.0)

This codebase has been completely refactored into a modular, production-grade architecture following standard Python software engineering best practices.

## Directory Structure

```text
ic-central/
│
├── config/                          # Centralized Settings & Declarative Configuration
│   ├── settings.py                  # Pydantic BaseSettings with .env validation
│   └── pitch_claims.yaml            # Sales pitch claims & value propositions
│
├── src/                             # Core Application Source Code
│   ├── models/                      # Domain Models (Pydantic v2, Timezone-aware UTC)
│   │   ├── lead.py                  # Lead, LeadStatus, BusinessProfile, OutreachDraft
│   │   └── conversation.py          # ConversationContext, Message, ChatSession
│   │
│   ├── scrapers/                    # Resilient Scraping Engine
│   │   ├── base.py                  # BaseScraper abstract interface
│   │   ├── gmaps.py                 # Scoped Google Maps scraper (exact panel CSS selectors)
│   │   └── web_discovery.py         # DuckDuckGo search with strict name sanitization
│   │
│   ├── services/                    # Business Logic & External Integrations
│   │   ├── llm.py                   # Multi-provider LLM service (Gemini, Groq, OpenAI)
│   │   └── analyzer.py              # AI pain-point & high-converting outreach generator
│   │
│   ├── pipelines/                   # Workflow Pipeline Orchestration
│   │   ├── discovery_pipeline.py    # Discover -> Sanitize -> Deduplicate -> Store
│   │   ├── outreach_pipeline.py     # AI Enrichment -> WhatsApp / Cold Email dispatch
│   │   └── chat_pipeline.py         # Multi-turn consultative sales conversation engine
│   │
│   ├── delivery/                    # Multi-Channel Dispatch Engine
│   │   └── dispatcher.py            # Telegram alerts, WhatsApp (Twilio), Email (SMTP)
│   │
│   ├── storage/                     # Persistence & Repository Layer
│   │   └── repository.py            # LeadRepository & SessionRepository (JSON/CSV)
│   │
│   └── api/                         # Backend Web API & Dashboard
│       └── server.py                # FastAPI REST endpoints + Modern Command Center UI
│
├── data/                            # Persistent Application Data (Ignored by Git)
│   ├── leads/                       # Individual lead records ({id}.json)
│   ├── sessions/                    # Chat session records ({session_id}.json)
│   └── exports/                     # Generated CSV / JSON reports
│
├── logs/                            # Rotating Application Logs
│   ├── app.log                      # Standardized application log
│   └── archive/                     # Archived previous run logs
│
├── tests/                           # Pytest Test Suite
│   ├── test_delivery.py
│   ├── test_engine.py
│   ├── test_llm_client.py
│   ├── test_persistence.py
│   └── test_v2_architecture.py      # Tests for new pipelines and sanitizers
│
├── cli.py                           # Modern, rich CLI tool (typer + rich)
├── run_server.py                    # One-command runner for FastAPI web server & dashboard
├── main.py                          # Backward-compatible entrypoint
├── requirements.txt                 # Clean project dependencies
└── .env.example                     # Environment configuration template
```

## How to Run

### 1. Launch the Web Command Center Dashboard
```bash
python run_server.py
```
Open **http://127.0.0.1:8000** in your browser to view the interactive dashboard, trigger discovery pipelines, view leads, and dispatch outreach.

### 2. Run via Unified CLI
```bash
# Discover prospects in any category and city
python cli.py discover --category "dental clinic" --location "Mumbai" --limit 5

# View all stored leads
python cli.py list-leads

# Run AI enrichment and outreach preview
python cli.py outreach --channel whatsapp --dry-run

# Export leads to CSV
python cli.py export --output data/exports/leads.csv

# Start an interactive AI sales pitch chat
python cli.py chat --company "Dazzle Dental" --category "dental clinic"
```

### 3. Run Unit Tests
```bash
python -m pytest tests/ -v
```
