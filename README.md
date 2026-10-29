# IC • Intelligence Center (v2.5)

A production-grade, multi-agent Intelligence Center, Technical Audit, and Autonomous Sales Development Representative (SDR) platform inspired by **Paperclip** (multi-agent workforce management) and **REA** (Reverse-Engineering Anything / Chrome DevTools).

---

## ⚡ Key Capabilities & Autonomous Workforce

### 🤖 1. Specialized Agent Org Chart (Paperclip-Style)
- **`ScoutAgent`**: Autonomous lead discovery across Google Maps and Web search. Extracts verified phone numbers (+91 / E.164), sanitizes business names, and filters duplicates.
- **`AuditorAgent` (REA-Inspired)**: Deep technical & mobile site audits. Inspects TTFB response time, SSL certificates, smartphone viewport responsiveness (iPhone 14 390x844), missing WhatsApp direct ordering widgets (`wa.me`), and missing 1-click booking systems. Captures headless mobile snapshots via Playwright.
- **`CopywriterAgent`**: Synthesizes real audited flaws and quantified revenue loss into persuasive, conversion-focused WhatsApp (Hinglish/English) and consultative cold emails.
- **`ApprovalGate` (Human-in-the-Loop)**: Staging queue in the dashboard. Prevents cold-call spamming: managers can review, edit pitch copy, or 1-click approve for WhatsApp/Email dispatch.
- **`CloserAgent` (Inbound SDR)**: Evaluates incoming prospect replies, classifies intent (pricing objections, competitor agency objections, demo requests, unsubscribe), counters with audit proof, and drives prospects to book a meeting (Calendly).

### 🎯 2. Specialized Vertical Playbooks
- **Freight & Logistics**: Spotlights missing track-and-trace widgets, load booking friction, and slow RFQ turnaround.
- **Event Venues & Planners**: Audits mobile date availability checkers, virtual tours, and 1-click WhatsApp quote requests.
- **Local High-Ticket SMBs**: Focuses on mobile loading speed, click-to-call buttons, and local search visibility.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. Configure Environment
Copy `.env.example` to `.env` and set your credentials:
```bash
cp .env.example .env
```
Key configuration:
- `GEMINI_API_KEY`: Google Gemini API key (for AI value synthesis and SDR chats)
- `LLM_MODEL`: `gemini-2.5-flash`
- `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`: For instant lead capture alerts
- `TWILIO_ACCOUNT_SID` & `TWILIO_AUTH_TOKEN`: For WhatsApp message delivery
- `EMAIL_SENDER` & `EMAIL_PASSWORD`: For cold email delivery

---

## 🖥️ Running the Command Center

### Option A: Web Command Center (Recommended)
Launch the modern FastAPI web dashboard:
```bash
python run_server.py
```
Open **`http://127.0.0.1:8000`** in your browser to access:
1. **Step 1: Live Discovery & Scouting:** Discover leads by category and location.
2. **Step 2: REA Mobile Viewport Auditor:** Live iPhone 14 bezel displaying authentic mobile snapshots and Pstack proof verification.
3. **Step 3: Outbox Human Sign-off:** Side-by-side WhatsApp & Cold Email preview with 1-click dispatch.
4. **Step 4: Hermes Live Deals Desk:** Multi-turn inbound objection handling with instant objection pills and Calendly booking.
5. **Paperclip Live Studio Drawer:** Direct embedded connection to your standalone Paperclip instance running on `http://localhost:3100`.

### Option B: Unified Terminal CLI
```bash
# 1. Scout businesses (e.g., restaurants in Mumbai)
python cli.py discover --category "restaurant" --location "Mumbai" --limit 5

# 2. View workforce status, tokens, and conversion funnel
python cli.py workforce

# 3. Approve a staged lead from the outbox
python cli.py approve-lead <lead_id> --channel whatsapp --dry-run

# 4. Test Closer Agent on objections
python cli.py simulate-reply <lead_id> --msg "What are your charges?"
python cli.py simulate-reply <lead_id> --msg "We already have an agency"

# 5. Export leads to CSV
python cli.py export --output data/exports/leads.csv
```

---

## 🧪 Automated Testing
Run the 51-test automated suite (all mocked, zero external API costs):
```bash
python -m pytest tests/ -v
```

---

## 📂 Architecture Overview
For detailed documentation on system design and file organization:
- [`architecture.md`](file:///c:/Users/JUBER/Downloads/main/leads_gen_bot-main/leads_gen_bot-main/architecture.md)
- [`folder_structure.md`](file:///c:/Users/JUBER/Downloads/main/leads_gen_bot-main/leads_gen_bot-main/folder_structure.md)


