# Legacy Architecture (V1 Archive)

This directory contains the original V1 proof-of-concept implementation of the lead generation and outbound messaging bot.

## Organization
- `v1_core/`: Original engine (`engine.py`) and schema definitions (`schemas.py`).
- `v1_delivery/`: Original dispatch engine (`delivery_module.py`).
- `v1_scrapers/`: Initial synchronous scraping script (`scrapper_module.py`).
- `v1_services/`: Early LLM and persistence handlers (`llm_client.py`, `persistence.py`).
- `v1_outreach/`: Standalone scraper experiments (`gmaps_scraper.py`, `sulekha_scraper.py`, `email_finder.py`).
- `v1_analytics/`: Early event counter (`analytics.py`).
- `v1_scripts/`: Early CLI runners (`main_outbound.py`, `show_leads.py`).
- `tests/`: Original unit test suite for V1 modules.

## Modern Replacement
All modern production development takes place under `src/`:
- Multi-agent orchestration: `src/agents/`
- Command center & API: `src/api/`
- Resilient scraping: `src/scrapers/`
- Pipelines & verification: `src/pipelines/` and `src/services/`
- Persistence: `src/storage/`

