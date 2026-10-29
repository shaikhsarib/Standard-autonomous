---
name: pstack
description: Cursor pstack plugin harness: prove-it-works, /poteto-mode, /architect, /create-verification-skill, zero-slop evidence verification.
---

# Pstack Engineering Harness (Cursor Plugin)

Source: [https://github.com/cursor/plugins/tree/main/pstack](https://github.com/cursor/plugins/tree/main/pstack)

A multi-agent workflow harness designed to bring rigorous engineering practices, structured playbooks, and fearless parallelism to AI-assisted coding.

## Core Directives

### 1. `prove-it-works` (Anti-Slop Standard)
- Every claim must have verifiable proof:
  - Real live URL inspection (HTTP response code, load time ms, SSL status, viewport presence).
  - Verified web search citations (real URLs, snippets, and verified timestamps).
  - Playwright headless screenshot proof artifacts.
- No ungrounded claims, simulated statistics, or vague assertions.

### 2. `/poteto-mode` (Workflow Routing)
- Evaluates the user goal and establishes a verifiable success check.
- Automatically selects the appropriate playbook (Logistics, Events, Local SMBs).

### 3. `/architect`
- Settle types, boundaries, and caller usage before writing production code.
- Prevent regressions across existing integration endpoints.

### 4. `/create-verification-skill`
- Build automated verification test loops (e.g. pytest test suites, curl inspection commands).
- Require 100% test passing before declaring work complete.
