---
name: ruflo
description: Ruflo multi-agent swarm orchestration, swarm topologies (mesh, hierarchical, consensus), and adaptive shared memory.
---

# Ruflo Multi-Agent Swarm Orchestration (ruvnet/ruflo)

Source: [https://github.com/ruvnet/ruflo](https://github.com/ruvnet/ruflo)

Enterprise multi-agent execution harness providing coordinated swarm topologies and adaptive shared memory across autonomous AI agents.

## Swarm Topologies

### 1. Hierarchical Dispatch (Lead Coordinator ➔ Specialized Workers)
- A coordinator agent (`WorkforceManager`) receives high-level tasks, breaks them into subtasks, and assigns them to specialized role agents (`Scout`, `Researcher`, `Auditor`, `Copywriter`, `Closer`).

### 2. Mesh Collaboration
- Agents communicate peer-to-peer using strongly typed handoff contracts (`HandoffEnvelope`), allowing findings from the `Auditor` to directly inform the `Copywriter` without loss of context.

### 3. Consensus & Quality Gating (Reality Checker Gate)
- Outputs from creative agents (`Copywriter`) must be validated by adversarial check agents (`Reality Checker` / `PstackVerifier`) before passing to human review.

## Shared Memory & RAG
- Centralized lead state store (`LeadRepository`) with persistent conversation history, technical audit logs, and search citations accessible across all agents in the swarm.
