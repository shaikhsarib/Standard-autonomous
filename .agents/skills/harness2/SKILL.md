---
name: harness2
description: Recursive Agent Harnessing (google-research/harness2) for IC. Propose-Probe-Compose cycle for autonomous self-improvement of pitch hooks, tools, and execution strategies.
---

# Harness²: Recursive Agent Harnessing for an Open World

Source: [https://github.com/google-research/harness2](https://github.com/google-research/harness2)  
Paper: [arXiv:2610.14224](https://arxiv.org/pdf/2610.14224)

Harness² is Google Research's framework for **recursive agent harnessing** in open-world environments, where agents encounter tasks unseen during original harness design. It operates at two levels of recursion while keeping model weights fixed:

## 1. Task-Level Recursion (Propose–Probe–Compose)
- **Propose:** Generates candidate adjustments to prompts, claims, scraper selectors, and objection handlers.
- **Probe:** Evaluates candidate effects on real-world lead interactions and feedback without requiring labeled ground truth.
- **Compose:** Synthesizes the highest-performing improvements into the runtime harness (`config/pitch_claims.yaml`).

## 2. Harnessing-Level Recursion (Persistent Self-Evolution)
- Updates a persistent library of validated hooks and resilient scraper selectors across runs.
- Feeds lessons learned back into the `WorkforceManager` to continuously improve conversion rates.

## Integration in IC (Intelligent Central)
- **Agent Role:** `harness_optimizer` (Agent #9 in the 12-agent Ruflo Swarm).
- **Core Service:** `src/services/harness_engine.py`.
- **Telemetry & Controls:** Integrated in `/api/paperclip/agents` and dashboard telemetry stream.
