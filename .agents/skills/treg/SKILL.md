---
name: treg
description: Open-source tool registry and proxy gateway (superdesigndev/treg) for IC agents. Provides dynamic catalog discovery, unified MCP endpoints, and local team secret vaults.
---

# Treg Tool Gateway (OpenRouter for Agent Tools)

**Repository:** `https://github.com/superdesigndev/treg`  
**Standard:** Matt Pocock (`/to-spec`) Typed Contracts + ECC (`AgentShield`) Gate 4 Cost Governance

---

## 1. Overview
Treg acts as a unified proxy and catalog for agent tools. Instead of managing 15+ different API credentials, IC agents invoke Treg dynamically.

### Key Capabilities
1. **Dynamic Tool Catalog**: Over 3,600 endpoints indexed (phone verification, company director search, SEO, sentiment, scrapers).
2. **Team Secret Vault**: Securely holds API keys (`GROQ_API_KEY`, `NVIDIA_NIM_API_KEY`, search tokens) locally in SQLite/Postgres.
3. **MCP Integration**: Compatible with Claude Code, Cursor, and Paperclip autonomous agents.

---

## 2. Setup & Execution

### Local Install (via NPX or CLI)
```bash
npx skills add superdesigndev/treg -s treg
# or
treg mcp install
```

### Python SDK Integration in IC
```python
from src.services.treg_client import treg_client, TregToolRequest

# Execute tool via Treg gateway
res = treg_client.execute_tool(TregToolRequest(
    tool_name="verify_whatsapp",
    arguments={"phone": "+919820123456"}
))
print(res.data)
```

---

## 3. Compliance Rules (ECC AgentShield Gate 4)
* **Budget Cap**: Tool executions are hard-limited to **$0.01 per lead** to preserve SDR unit economics.
* **Fallbacks**: When the local self-hosted Treg daemon is offline, `treg_client` falls back gracefully to internal zero-cost normalization handlers.
