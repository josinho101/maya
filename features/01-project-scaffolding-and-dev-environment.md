# 01 — F0 — Project Scaffolding & Dev Environment

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Brand-new repo — nothing else can start without a Python skeleton, dependency management, a runnable FastAPI shell, and (once that shell exists) a one-time React+MUI frontend scaffold to build every later UI story against.

---

## F0 — Project Scaffolding & Dev Environment

### Story F0.S1 — Python project skeleton

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F0-010 | Initialize repo structure: `pyproject.toml`, `src/maya/` package layout, `.gitignore` | F0.S1 | F0 | — | Manual: `pip install -e .` succeeds; `.gitignore` covers `framework-data/config/secure/`, `framework-data/logs/`, `*.local.json`, venv dirs | Not Started |
| F0-020 | Set up virtual environment + pin dependencies (Playwright, httpx, FastAPI, pydantic, prance, openapi-core, pytest) | F0.S1 | F0 | F0-010 | Manual: fresh venv + `pip install -e .[dev]` resolves with no conflicts | Not Started |
| F0-030 | Configure linting/formatting (ruff/black) and a pytest baseline with one trivial passing test | F0.S1 | F0 | F0-020 | Unit test: `pytest` exits 0 on the trivial test; `ruff check .` exits 0 | Not Started |
| F0-040 | Add dev scripts (`Makefile` or `scripts/`) for test/lint/run-dev-server | F0.S1 | F0 | F0-030 | Manual: each script runs and produces expected output | Not Started |

**F0-010 — How to build it**: Use a `src/`-layout package (`src/maya/__init__.py`, with subpackages `adapters/`, `storage/`, `agents/`, `engines/`, `api/` created empty for now). `pyproject.toml` should declare the package name `maya` and point at `src/`. The `.gitignore` needs entries matching the layout in plan.md §3.3 exactly (`framework-data/config/secure/`, `framework-data/logs/`, `*.local.json`, `framework-data/runtime/`). (see plan.md §3.3)

**F0-020 — How to build it**: Add an optional `[project.optional-dependencies] dev = [...]` group in `pyproject.toml` for pytest/ruff/black, keeping runtime deps separate. Pin Playwright, httpx, fastapi, uvicorn, pydantic v2, prance, openapi-core at compatible major versions; run `playwright install` once to fetch browser binaries. (see plan.md §2.1 adapter table for which libraries map to which adapters)

**F0-030 — How to build it**: A `tests/` directory at repo root mirroring `src/maya/`; one `tests/test_smoke.py` asserting `1 == 1` to prove the runner works. Add a `ruff.toml` or `[tool.ruff]` block in `pyproject.toml` with sane defaults (line length, import sorting). (see plan.md §10 Verification Plan, which expects a working test runner before anything else)

**F0-040 — How to build it**: Simple `Makefile` targets `test`, `lint`, `dev` (the last running `uvicorn maya.api.main:app --reload` once F0-050 exists — fine to leave a TODO comment in this task until F0-050 lands). On Windows, a thin `scripts/*.ps1` mirror is fine instead of/alongside a Makefile.

### Story F0.S2 — Minimal runnable FastAPI shell

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F0-050 | Scaffold FastAPI app with a `/health` endpoint, runnable via uvicorn | F0.S2 | F0 | F0-020 | Integration test: `GET /health` returns 200 with a JSON body | Not Started |
| F0-060 | Add a pytest + FastAPI `TestClient` test for `/health` | F0.S2 | F0 | F0-050 | Unit test: `TestClient(app).get("/health")` asserts status 200 | Not Started |

**F0-050 — How to build it**: Create `src/maya/api/main.py` with a FastAPI() instance and one `@app.get("/health")` returning `{"status": "ok"}`. This module becomes the single FastAPI entrypoint every later epic's routers mount onto (`app.include_router(...)`), so keep it deliberately thin — routing logic belongs in per-feature router modules added later (F3, F6, F13, etc). (see plan.md §2.3 REST API Layer)

**F0-060 — How to build it**: `tests/api/test_health.py` using `fastapi.testclient.TestClient` imported against `maya.api.main.app`. This establishes the test pattern (`TestClient` + real Pydantic response model) every later endpoint test in F3/F6/F13/F18 will copy.

### Story F0.S3 — Ollama environment check (manual prerequisite)

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F0-070 | Verify local Ollama install; pull `qwen2.5-vl:7b`, `qwen2.5-vl:3b`, `qwen2.5:7b-instruct` | F0.S3 | F0 | — | Manual: `ollama list` shows all three models | Not Started |

**F0-070 — How to build it**: Install Ollama locally, then `ollama pull qwen2.5-vl:7b && ollama pull qwen2.5-vl:3b && ollama pull qwen2.5:7b-instruct`. Write a throwaway `scripts/check_ollama.py` that calls `ollama list` (or hits `GET /api/tags` on Ollama's REST API) and asserts all three model names are present, failing loudly if not — this becomes the "is my dev box ready" sanity check referenced again in plan.md §10's verification plan. (see plan.md §1.1, §1.3)

### Story F0.S4 — One-time React + MUI frontend scaffold

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F0-080 | Scaffold a React + MUI app (Vite) with basic routing and a typed API client pointed at the FastAPI backend | F0.S4 | F0 | F0-060 | Manual: `npm run dev` serves a placeholder page that successfully calls `GET /health` and renders the response | Not Started |
| F0-090 | Add a shared layout shell (nav/sidebar) with empty placeholder routes for Projects, Test Cases, Runs, Healing, Notifications | F0.S4 | F0 | F0-080 | Manual UI walkthrough: navigating each placeholder route renders without console errors | Not Started |
| F0-100 | Configure frontend build/lint (eslint/prettier) and a single smoke test (e.g. Vitest rendering the layout shell) | F0.S4 | F0 | F0-090 | Unit test: smoke test passes; `npm run lint` exits 0 | Not Started |

**F0-080 — How to build it**: `npm create vite@latest frontend -- --template react-ts`, add `@mui/material`, `@mui/x-data-grid`, `react-router-dom`, and a thin `frontend/src/api/client.ts` wrapping `fetch`/`axios` against the backend base URL (env-var configurable). This is the **only** frontend scaffold task in the whole plan — every later "`<Epic>` UI" story builds pages/components inside this same `frontend/` app, never re-scaffolding. (see plan.md §2.2 component diagram — "React + MUI Dashboard")

**F0-090 — How to build it**: One `frontend/src/layout/AppShell.tsx` with MUI `Drawer`/`AppBar`, and `react-router-dom` routes for `/projects`, `/test-cases`, `/runs`, `/healing`, `/notifications` each rendering a placeholder `<div>` for now. Later epics (F3, F6, F7, F9, F10, F13, F18, F21) fill these routes in, in this exact order — don't build the real screens yet, just the shell and stable route names so later stories slot in without restructuring.

**F0-100 — How to build it**: Add `eslint` + `prettier` configs consistent with the Vite TS template defaults; add Vitest + `@testing-library/react`, with one test asserting `AppShell` renders its nav items. This establishes the frontend test pattern every later UI story's "Manual UI walkthrough" verification can optionally be backed by.
