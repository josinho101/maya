# MAYA

**An AI-assisted test automation framework that explores your app, proposes tests, and keeps them running — without burning AI tokens on every routine run.**

> Status: feasibility study / architecture plan. No code has been written yet. See [`features/plan.md`](features/plan.md) for the full design.

---

## What is MAYA?

MAYA is a tool that automatically tests your web application or API for you. Instead of a human writing test scripts by hand, MAYA uses a locally-hosted AI (no cloud, nothing leaves your machine) to **explore** your app or API, figure out what the meaningful test cases are, and propose them to you. You review and approve what makes sense, and from then on MAYA runs those tests on its own.

The key idea: AI is expensive and slow, so MAYA only "thinks" when it actually needs to — the first time it sees your app, when something about it changes, or when a test breaks. A routine "did anything break?" run replays your approved tests deterministically, with **zero AI involved**, so it's fast and free.

## Key ideas

- **Explores automatically** — for UI it clicks around like a user would; for APIs it reads your OpenAPI/Swagger spec. Either way it proposes test cases for you to approve.
- **Local-only AI** — runs on Ollama with open-weight models (Qwen2.5-VL / Qwen2.5-Instruct). No data leaves your machine.
- **Self-healing** — when the app changes slightly (a button moves, a field gets renamed), MAYA tries to fix the test itself and only asks for help when it's not confident.
- **Change-aware, not blind replay** — MAYA detects when a screen or API contract actually changed and only re-investigates the parts that changed.
- **Plain-English scenarios** — you can describe a business flow ("a customer logs in, adds an item to cart, checks out") and MAYA will turn it into a real test.
- **Multi-environment** — dev/staging/prod are tracked separately, while your test cases stay reusable across all of them.

## How it works

1. **Explore** — point MAYA at a UI (with login credentials) or an API (with an OpenAPI spec). It investigates and drafts test cases.
2. **Review & approve** — you see proposed tests in a dashboard, edit if needed, approve or reject.
3. **Replay** — on a schedule or via webhook (e.g., from CI), MAYA re-runs approved tests deterministically.
4. **Detect change** — before replaying, MAYA checks whether the relevant screen/API operation actually changed since last time.
5. **Heal or re-explore** — minor breakage gets auto-healed (if confident) or flagged for review; major change triggers scoped re-exploration of just the affected part.

This loop is what keeps ongoing costs low: most runs touch step 3 only, never the AI.

---

## Architecture

```
                     React + MUI Dashboard
                  (review/approve, reports, CRUD)
                              │
                      FastAPI REST API
                    + Webhook/CI endpoints
                              │
        ┌─────────────────────┼─────────────────────────┐
        │                     │                         │
  Project Manager      Job Scheduler /            Notification Service
  (projects, envs,     Concurrency Manager
   packages)           (AI work queue +
                        parallel replay)
        │                     │
  Test Case Store    View/Spec Snapshot      Execution Engine (UI)
  (file-based JSON)  & Diff Engine            API Test Runner
                              │                         │
                    Exploration Agent /        Self-Healing Engine (UI)
                    Scenario Interpreter /      API Healing Engine
                    API Discovery Agent
                    (LLM orchestrators)
                              │
                  Ollama Client (LLMClient)
                  Qwen2.5-VL 7B/3B · Qwen2.5-Instruct
```

### Major components

| Component | Responsibility |
|---|---|
| **Exploration Agent** | Drives the browser, perceives DOM + screenshot, proposes UI test cases |
| **Scenario Interpreter** | Turns a free-text business scenario into a test case |
| **API Discovery Agent** | Reads an OpenAPI spec and proposes API test cases (CRUD-lifecycle flows by default) |
| **View/Spec Snapshot & Diff Engine** | Decides whether anything actually changed — the core cost-saving gate |
| **Self-Healing Engine / API Healing Engine** | Confidence-scored fallback chain to auto-fix broken locators or contract drift |
| **Execution Engine / API Test Runner** | Deterministically replays approved tests, no AI involved |
| **Job Scheduler / Concurrency Manager** | Runs replay jobs in parallel; serializes all AI work through one GPU queue |
| **Ollama Client** | Talks to the local LLM, auto-selects model size based on load |
| **Test Case Store / Project Manager** | File-based JSON storage for projects, environments, and test cases |
| **FastAPI REST API + React/MUI Dashboard** | CI/webhook integration and the human review/approval UI |

### Adapter layer

Every external dependency (Ollama, Playwright, httpx, spec parsing/diffing) sits behind a small interface (`LLMClient`, `BrowserDriver`, `HTTPClient`, `SpecParser`, `SpecDiffer`). The rest of the framework only talks to these interfaces, so any underlying tool can be swapped out by writing one new adapter, without touching agents or engines.

### Tech stack

- **Automation**: Playwright (browser), httpx (API calls)
- **AI**: Ollama, running Qwen2.5-VL (7B/3B, multimodal for UI) and Qwen2.5-Instruct (text-only for API reasoning)
- **Backend**: FastAPI (Python)
- **Frontend**: React + Material UI
- **Storage**: file-based JSON, git-friendly — no database

## Data & storage model

Everything is stored as plain JSON files in a git-friendly directory tree: a **project** can host multiple test types (UI, API, ...) and multiple **environments** (dev/staging/prod); each environment carries a **package** — the credentials, URL or spec, fixtures, and instructions needed to test it. Test cases themselves are environment-agnostic and reused across all environments, while snapshots, run history, and healing logs are kept strictly per-environment. Full schema in [`features/plan.md`](features/plan.md#3-data-model--file-layout).

## Concurrency & cost model

Routine replay runs (no AI needed) execute fully in parallel across projects and environments. Anything that needs the local LLM — exploration, healing escalation, scenario interpretation, API discovery — goes through a single serialized queue, since one 16GB GPU can only run one inference at a time. This keeps replay fast everywhere while AI-heavy work queues up predictably instead of crashing or contending for memory.

---

## Running locally

### Prerequisites

- Python 3.11+
- Node 18.18+ (or 20+) and npm
- [`uv`](https://docs.astral.sh/uv/) — `curl -LsSf https://astral.sh/uv/install.sh | sh`
- [Ollama](https://ollama.com) installed separately, with `qwen2.5-vl:7b`, `qwen2.5-vl:3b`, and `qwen2.5:7b-instruct` pulled (see `scripts/check_ollama.py`)

### Backend (FastAPI)

```bash
uv venv
source .venv/bin/activate
uv pip install -e .[dev]
playwright install
make dev
```

- API: http://localhost:9091
- Swagger UI: http://localhost:9091/docs
- ReDoc: http://localhost:9091/redoc

### Frontend (React + MUI)

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

- Dashboard: http://localhost:9090

### Tests & lint

```bash
make test            # backend pytest
make lint             # backend ruff
cd frontend && npm run test   # frontend Vitest
cd frontend && npm run lint   # frontend eslint
```

### Ollama sanity check

```bash
make check-ollama
```

### Keeping `requirements.txt` in sync

`pyproject.toml` is the source of truth for Python dependencies. `requirements.txt`/`requirements-dev.txt` are generated from it for tools that expect plain pip-style files — regenerate after any dependency change:

```bash
make requirements
```

---

## Learn more

This README is intentionally short. For the full feasibility study — model sizing, detailed workflows, data schemas, risks, and the complete API-testing design — see [`features/plan.md`](features/plan.md).
