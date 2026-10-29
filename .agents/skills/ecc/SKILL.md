---
name: ecc
description: Everything Claude Code (ECC) by affaan-m - Dual development harness and runtime compliance shield (AgentShield, pre-commit security, outbound pitch compliance, and zero-slop anti-hallucination gates).
---

# Everything Claude Code (ECC) Harness & Runtime Shield

Source: [https://github.com/affaan-m/ECC](https://github.com/affaan-m/ECC) by Affaan Mustafa.

ECC operates as a dual-engine architecture:
1. **Development Harness**: Code security scanner, 5-phase engineering loop, context-drift mitigation, and pre-commit security verification (`AgentShield`).
2. **Agency OS Runtime Engine**: Outbound pitch compliance, anti-slop verification, PII redaction, and SDR objection review.

---

## Directives

### 1. `AgentShield` (Development Code Security)
Before committing or executing new code:
- **Credential Protection**: Detect any hardcoded API keys (e.g., Telegram tokens, OpenAI keys, Gemini keys, database URIs).
- **Injection Defense**: Flag unsanitized SQL queries, dangerous `os.system` / `eval` calls, or unsanitized user inputs.
- **Dependency Guard**: Ensure all imports exist within `requirements.txt` or standard library.

### 2. `5-Phase Engineering Cycle`
Execute every non-trivial engineering change in 5 distinct phases:
1. **Plan**: Define strict boundaries, types, and input/output contracts.
2. **Test (TDD)**: Write or maintain failing tests verifying requirements before implementation.
3. **Implement**: Minimal, clean code adhering to the architecture.
4. **Review (ECC Code Reviewer)**: Verify 100% passing tests, no regressions, and pure design tokens.
5. **Remember**: Save architectural context to avoid memory drift.

### 3. `Runtime Outbox Compliance Shield` (Agency OS Step 3)
Before an outbound outreach pitch (WhatsApp or Email) is dispatched to a prospective business:
- **Grounded Claims Only**: Every technical or financial claim must have an empirical backing in the lead's `AuditReport` (e.g. TTFB ms, SSL status, lack of WhatsApp button).
- **No Hallucinated Names or Stats**: No made-up case study numbers or unverified percentages.
- **PII & Internal Data Redaction**: Ensure database primary keys, internal agent prompts, or scraping raw payloads are not exposed.
- **Spam & Anti-Phishing Guard**: Proper opt-out mechanism, respectful non-pushy tone, and accurate sender identification.

### 4. `Hermes SDR Reviewer Agent` (Agency OS Step 4)
- Intercepts incoming prospect replies.
- Validates that the SDR objection counter matches the prospect's vertical playbook.
- Confirms the Calendly or meeting booking link is functional before sending.
