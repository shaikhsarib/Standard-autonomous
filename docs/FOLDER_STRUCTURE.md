# Standard Autonomous • Project Architecture & Directory Structure

A production-grade, modular multi-agent autonomous operating system designed for B2B discovery, technical flaw auditing, and multi-channel consensus outreach.

---

## High-Level Repository Architecture

```text
Standard-autonomous/
├── .agents/                        # Autonomous Swarm Skills & Multi-Agent Workflows
│   └── skills/agency-agents/       # Role specifications (Auditors, Copywriters, Closers)
│
├── config/                         # Centralized Application Configuration
│   ├── ic.config.json              # Platform & swarm configuration
│   ├── pitch_claims.yaml           # Ground-truth value propositions & empirical rules
│   └── settings.py                 # Pydantic BaseSettings environment loader
│
├── data/                           # Application Data Layer (Gitignored)
│   ├── leads/                      # Serialized lead records ({lead_id}.json)
│   ├── sessions/                   # Chat conversation records
│   ├── screenshots/                # Visual site audit captures
│   └── exports/                    # Generated CSV/JSON reports
│
├── docs/                           # Documentation, Technical Specifications & Reports
│   ├── ARCHITECTURE.md             # System topology & component diagrams
│   ├── FOLDER_STRUCTURE.md         # Comprehensive directory & module guide
│   ├── UI_UX_AND_FLOW_ARCHITECTURE.md # Dashboard UI/UX, consensus swarms & specs
│   └── reports/                    # Executive & Engineering PDF Reports
│       ├── Agent_Engineering_Playbook_Research_and_Build_Blueprint.pdf
│       ├── IC_Intelligence_Center_Audit_and_Upgrade_Report.pdf
│       ├── IC_Master_Action_Plan.pdf
│       └── IC_Unified_System_Architecture.pdf
│
├── legacy/                         # Preserved V1 Proof-of-Concept Archive
│   ├── v1_core/                    # Original engine.py and schemas.py
│   ├── v1_delivery/                # Original delivery_module.py
│   ├── v1_scrapers/                # Initial synchronous scrapper_module.py
│   ├── v1_services/                # Early llm_client.py and persistence.py
│   ├── v1_outreach/                # Standalone experimental scrapers
│   ├── v1_analytics/               # Basic event logger
│   └── tests/                      # Unit tests for V1 modules
│
├── logo/                           # Official Brand & Identity Assets
│   ├── logo-C-loop-lockup.svg      # Primary Light Mode Lockup (Original Vector)
│   ├── logo-C-loop-dark-lockup.svg # Primary Dark Mode Lockup (Monochrome White)
│   ├── logo-C-loop-mark.svg        # Standalone Mark (Black on transparent)
│   ├── logo-C-loop-mark-dark.svg   # Standalone Mark (White on transparent)
│   └── ...                         # Historical concept exploration vectors
│
├── logs/                           # Runtime Application Logs (Rotating)
│   └── .gitkeep
│
├── src/                            # Production Application Source Code
│   ├── agents/                     # Multi-Agent Coordination & Safety
│   │   ├── __init__.py
│   │   └── ecc_shield.py           # PII redaction, SQLi protection & prompt firewall
│   │
│   ├── api/                        # Backend REST API & Web Command Center
│   │   ├── __init__.py
│   │   ├── server.py               # FastAPI application & REST endpoints
│   │   ├── static/                 # Brand assets, high-DPI favicons, icons
│   │   └── templates/              # Modern reactive Dashboard UI (dashboard.html)
│   │
│   ├── core/                       # Core Protocols & System Contracts
│   │   ├── __init__.py
│   │   └── contracts.py            # Typed interfaces, protocols & status enums
│   │
│   ├── delivery/                   # Multi-Channel Dispatch Engine
│   │   ├── __init__.py
│   │   └── dispatcher.py           # WhatsApp (Twilio), Telegram & SMTP delivery
│   │
│   ├── models/                     # Pydantic Domain Models
│   │   ├── __init__.py
│   │   ├── conversation.py         # Dialogue contexts & message threads
│   │   └── lead.py                 # Lead schema, business profiles & outreach drafts
│   │
│   ├── pipelines/                  # End-to-End Workflow Orchestration
│   │   ├── __init__.py
│   │   ├── chat_pipeline.py        # Consultative AI sales objection handler
│   │   ├── discovery_pipeline.py   # Discover -> Sanitize -> Deduplicate -> Triage
│   │   └── outreach_pipeline.py    # AI enrichment & verified pitch generation
│   │
│   ├── scrapers/                   # Resilient Extraction Engines
│   │   ├── __init__.py
│   │   ├── base.py                 # Abstract scraper base interface
│   │   ├── firecrawl_scraper.py    # Deep website crawling adapter
│   │   ├── gmaps.py                # Google Maps extraction engine
│   │   ├── gosom_scraper.py        # High-concurrency scraper adapter
│   │   ├── scrapling_scraper.py    # Headless dynamic browser scraper
│   │   └── web_discovery.py        # Search engine discovery & domain resolver
│   │
│   ├── services/                   # Business Logic, LLM Gateway & Verification
│   │   ├── __init__.py
│   │   ├── agency_swarm.py         # Multi-agent consensus swarm coordinator
│   │   ├── analyzer.py             # Pain-point detection & copy generator
│   │   ├── deep_research.py        # Corporate telemetry & intelligence research
│   │   ├── dev_harness.py          # Propose-Probe-Compose test harness
│   │   ├── evidence_verifier.py    # Empirical flaw validation engine
│   │   ├── firecrawl_client.py     # Firecrawl API integration
│   │   ├── harness_engine.py       # Self-healing copy optimization engine
│   │   ├── inbound_closer.py       # High-converting objection handler
│   │   ├── llm.py                  # Multi-provider LLM gateway (Groq, Gemini)
│   │   ├── paperclip_bridge.py     # Paperclip ticketing & workflow bridge
│   │   ├── scheduled_cadence.py    # Automated follow-up cadences
│   │   ├── site_inspector.py       # Speed, SSL & DOM audit service
│   │   ├── treg_client.py          # Regulatory compliance checker
│   │   ├── vertical_playbooks.py   # Industry-specific outreach playbooks
│   │   ├── visual_auditor.py       # Screenshot analysis & visual audit
│   │   └── workforce.py            # Agent workforce coordinator
│   │
│   └── storage/                    # Repository & Data Persistence Layer
│       ├── __init__.py
│       └── repository.py           # Thread-safe JSON/CSV persistence
│
├── tests/                          # Automated Pytest Test Suite
│   ├── conftest.py                 # Test fixtures & path configuration
│   ├── test_ecc_shield.py          # Security shield verification tests
│   ├── test_paperclip_integration.py # Paperclip bridge integration tests
│   ├── test_pstack_harness_evals.py # Propose-Probe-Compose harness tests
│   ├── test_v2_architecture.py     # End-to-end pipeline & triage tests
│   ├── test_verticals_and_pstack.py # Vertical playbook verification tests
│   └── test_workforce_closer.py    # Workforce & closer handling tests
│
├── tools/                          # Developer Tooling & Research Harnesses
│   └── scrapling_research.py       # Dynamic browser experimentation harness
│
├── .env.example                    # Environment variable configuration template
├── .gitignore                      # Comprehensive Git exclusion rules
├── cli.py                          # Unified Rich Command Line Interface
├── main.py                         # Production Entrypoint (Server, CLI, or Pipelines)
├── pyproject.toml                  # Standard Python packaging & tool configuration
├── pytest.ini                      # Pytest suite configuration
├── README.md                       # Complete Project Overview & Getting Started Guide
├── requirements.txt                # Production Python dependencies
├── run_server.py                   # One-command server launcher
└── start_ic.bat                    # Windows startup batch script
```

---

## Key Architectural Principles

1. **Clean Separation of Concerns**: All production business logic resides under `src/`, categorized by architectural layer (`models`, `pipelines`, `scrapers`, `services`, `storage`, `api`).
2. **Deterministic Imports**: No ambiguity between old and new code. Root duplicate folders have been archived under `legacy/`.
3. **Enterprise Safety & Redaction**: The ECC Shield (`src/agents/ecc_shield.py`) validates and redacts PII and sensitive tokens before messages reach external dispatch channels.
4. **Resilient Data Layer**: Data persists safely in `data/leads/` and `data/sessions/`, gitignored to prevent accidental commits of business records.
