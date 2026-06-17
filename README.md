# ⛓️ SHACKLE

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

> **The 1-Line Runtime Circuit Breaker for Autonomous AI Agents.**
> Stop runaway token loops, unhandled tool cascades, and accidental $4,000 API bills before they happen.

---

## ⚡ The Problem

AI agents are highly capable, but their error-handling is fundamentally broken. When an agent hits an unhandled tool error (401 Unauthorized, changed API payload, dead endpoint), it rarely self-corrects. Instead, it enters a **"Loop of Death"** — retrying the exact same tool with the exact same input, burning your context window and running up massive API bills in minutes.

Frameworks like **CrewAI**, **AutoGen**, and **LangGraph** lack native, framework-agnostic spending guardrails or deterministic loop breakers.

## 🛡️ The Solution

SHACKLE is a lightweight, zero-dependency governance layer that sits inside your runtime via dynamic Python shims. It intercepts **LLM calls** and **tool executions** client-side, monitoring execution state deterministically.

When an agent breaches your boundaries, SHACKLE trips the circuit breaker, halts execution, and drops you into an interactive terminal console.

### Key Features

- **1-Line Install** — no refactoring your agent topology
- **Loop of Death Prevention** — detects identical sequential tool calls and error cascades
- **Budget Enforcement** — real-time token tracking against a client-side pricing table
- **Execution Timeouts** — prevents hung threads on dead APIs
- **HITL Console** — interactive terminal with Resume / Skip / Abort options
- **100% Client-Side** — no telemetry, no phone-home, no hidden SaaS

---

## 🚀 Quick Start

### 1. Install

```bash
pip install shackle-guard
```

### 2. Guard Your Workflow

```python
from shackle import Guard
from crewai import Crew, Agent, Task

# Your normal CrewAI setup
my_crew = Crew(agents=[...], tasks=[...])

# One line to add circuit breaking
@Guard(budget=0.25, max_repeat_calls=3, timeout_seconds=180)
def run():
    return my_crew.kickoff()

run()
```

That's it. SHACKLE dynamically hooks the underlying interpreters — no CrewAI source changes needed.

---

## ⚙️ The Four Circuit Breakers

| Trigger | Condition | Default | What Happens |
|---|---|---|---|
| **REPETITIVE_TOOL_CALL** | Same tool + same input called N times, or input contains error signals | 3 attempts | Drops to HITL console |
| **BUDGET_EXCEEDED** | Accumulated token cost exceeds limit (via local pricing table) | $0.20 | Hard execution freeze |
| **TIMEOUT_REACHED** | Wall-clock execution exceeds threshold | 180 seconds | Immediate halt |
| **MAX_TOOL_CALLS** | Total tool invocations exceed limit | 50 calls | Hard stop |

### Error Loop Amplification

SHACKLE **amplifies sensitivity** when tool inputs contain error signals (`401`, `500`, `timeout`, `unauthorized`, etc.) — catching the "I'll just try again" loop before the agent burns tokens on a permission error it can't fix.

---

## 🛠️ The HITL Console

When a breaker trips, SHACKLE renders an interactive terminal:

```
⛓️ SHACKLE CIRCUIT BREAKER: REPETITIVE_TOOL_CALL

Agent:         ResearchAgent
Tool:          web_search
Input:         {"query": "latest AI news", "error": "401 Unauthorized"}
Call Count:    3x
━━━ Session Stats ━━━
Tokens:        In: 8,400 | Out: 1,200
Session Cost:  $0.02850
Time Running:  47.2s

Options:
  [R] Resume/Reset — clear history, continue execution
  [S] Skip — return dummy output, attempt context flush
  [A] Abort — hard terminate the current run

Select action (R/S/A):
```

---

## 🔌 Works With

| Framework | Support | Notes |
|---|---|---|
| **CrewAI** | ✅ Full | litellm hook + BaseTool hook + Agent.execute_task (experimental) |
| **LangChain / LangGraph** | ✅ Full | litellm + BaseTool hooks cover all paths |
| **AutoGen** | ✅ Full | litellm interception catches all LLM calls |
| **Smolagents** | 🧪 Experimental | Manager Agent reasoning loop detection active |

---

## 🔮 Roadmap

- [x] Budget enforcement (client-side pricing table)
- [x] Loop of Death detection (repeat tool calls + error amplification)
- [x] HITL terminal interface (Resume / Skip / Abort)
- [x] Execution timeout guard
- [ ] `.shackle.yaml` config file support
- [ ] Webhook mode for async HITL (instead of CLI)
- [ ] Multi-agent cost attribution dashboard (Pro)
- [ ] `.shackle.json` audit log export (Pro)
- [ ] Slack / PagerDuty alerts (Pro)

---

## 📄 License

MIT. Run your compute freely, sovereignly, and with total safety.

---

## 🤝 Contributing

### Pricing Table Updates

As model providers update pricing, submit PRs to `shackle/core.py` → `MODEL_PRICING`. Contributors who submit verified pricing updates get credited in release notes.

### Adding Framework Hooks

SHACKLE's architecture supports pluggable runtime hooks. To add support for a new framework:

1. Add a `_patch_<framework>()` function following the pattern in `core.py`
2. Register it in `_apply_patches()`
3. Submit a PR with integration tests
