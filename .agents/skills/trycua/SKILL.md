---
name: trycua
description: trycua/cua Computer-Use Agent (CUA) infrastructure - Sandboxed desktop drivers, background OS automation, mouse/keyboard control, and end-to-end form verification.
---

# trycua/cua - Computer-Use Agent Infrastructure

Source: [https://github.com/trycua/cua](https://github.com/trycua/cua)  
Core: Python & TypeScript SDK (`cua`)

An open-source infrastructure and execution harness for Computer-Use Agents (CUA) that provides sandboxed OS environments and background desktop automation without stealing user focus.

## Core Capabilities in Agency OS

### 1. Background Sandboxed Browser & Desktop Execution
- Unlike local browser windows that pop up and steal cursor focus, `trycua` runs agents inside isolated virtualized drivers or sandboxed headless display servers.
- Executes OS-level actions: mouse move, click, double click, scroll, keyboard entry, hotkeys, and full display framebuffer capture.

### 2. Live Interactive Lead Form & Quote Latency Probes
- Beyond static DOM inspection, the CUA agent actively tests the prospect's quote calculator or inquiry form:
  - Types sample route inquiries (e.g. "Navi Mumbai to Pune, 10 Ton Container").
  - Clicks submit to verify if the business has instant quote automation or a broken email form.
  - Measures true end-to-end latency and error states.

### 3. Visual Mobile & Desktop Screencast
- Captures framebuffers and accessibility trees.
- Feeds live visual inspection directly into the Agency OS Web Desktop Workstation.

### 4. Integration with Matt Pocock `/to-spec` Contracts
- Wrapped inside `CuaAuditResultSpec` to deliver deterministic, empirical findings to the `Reality Checker` and `Hermes SDR Closer`.
