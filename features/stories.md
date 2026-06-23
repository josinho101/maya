# MAYA — Implementation Stories & Tasks

## How to read this file

This file used to contain the full buildable backlog derived from [`plan.md`](plan.md): **Features (epics) → Stories (demoable vertical slices) → Tasks** (small, independently implementable and verifiable units). All task content has moved into one file per epic under `features/`, numbered by implementation order (see the index below). This file is now just the legend and the index.

- **Task ID**: `<Fn>-<seq>`, e.g. `F5-040`. The prefix names the owning epic; sequence numbers are gapped (010, 020, 030...) so later tasks can be inserted without renumbering.
- **Depends On**: other Task IDs that must be complete first — real technical dependencies only.
- **Verification**: how to confirm the task works, given this is a file-based, no-database, human-approval-gated system. One of:
  1. *Unit test* — pure functions/classifiers/schemas.
  2. *Integration test* — against a real demo target (Playwright/Ollama/httpx).
  3. *Manual file/JSON inspection* — open the actual file on disk and confirm its shape/values.
  4. *Manual behavioral/idempotency proof* — e.g. "run twice, confirm zero new LLM-log entries the second time."
  5. *Manual UI walkthrough* — exercise a dashboard screen and confirm the result persists/reflects correctly.
- **Status**: `Not Started` / `In Progress` / `Done` / `Blocked`. All tasks start `Not Started`.
- **How to build it**: directly below each task's table row (in its per-feature file), a short paragraph naming the file/class to create, the existing pattern/adapter/model to reuse, and the core approach — enough to start coding without re-deriving design from `plan.md`. Each closes with a pointer back to the relevant `plan.md` section.

Within each per-feature file, rows are ordered top-to-bottom in **strict implementation sequence**: story order, then task order within a story. The index below lists files in overall epic implementation order — building straight down the index, file by file, top to bottom within each file, is a valid build plan.

**UI-first constraint**: every epic through F14 is UI/shared-infrastructure scope. API-testing-specific epics (F16 onward) only begin once the full UI pipeline — explore → review/approve → replay → change-detection gate → self-heal → scenario interpretation → file uploads → concurrency → REST/webhook trigger → logging — is complete and verified. There is **no standalone dashboard epic** — each epic that produces something a human needs to see or act on carries its own trailing "`<Epic>` UI" story, so every epic is checkable end-to-end (backend *and* the screen that exercises it) before moving to the next one. The one-time React+MUI scaffold happens once, early, in F0.

---

## Epics, in implementation order

| Seq | Epic | File | Rationale for this position |
|---|---|---|---|
| 01 | F0 — Project Scaffolding & Dev Environment | [01-project-scaffolding-and-dev-environment.md](01-project-scaffolding-and-dev-environment.md) | Brand-new repo — nothing else can start without a Python skeleton, dependency management, a runnable FastAPI shell, and (once that shell exists) a one-time React+MUI frontend scaffold to build every later UI story against. |
| 02 | F1 — Shared Data Model & File Storage | [02-shared-data-model-and-file-storage.md](02-shared-data-model-and-file-storage.md) | Project/environment/package/test-case JSON schemas and the file-based Test Case Store must exist before any agent or engine has somewhere to read/write. |
| 03 | F2 — Adapter Layer Foundations (LLM + Browser) + minimal logging | [03-adapter-layer-foundations-llm-and-browser.md](03-adapter-layer-foundations-llm-and-browser.md) | Every later agent/engine depends on `LLMClient`/`OllamaAdapter` and `BrowserDriver`/`PlaywrightAdapter` existing behind formal interfaces — the architecture's explicit swappability spine. Minimal 3-stream logging is added here too, so LLM calls are auditable from the very first call onward. |
| 04 | F3 — Project & Environment Management (CRUD, Secrets) + CRUD UI | [04-project-and-environment-management.md](04-project-and-environment-management.md) | Needs F1's schemas/storage; produces the `project.json`/`environment.json`/secure-config files every later workflow reads from. Gains its own REST endpoints (gap-fill) and CRUD screens in this same epic, so the dashboard is usable from this point forward. |
| 05 | F4 — UI Perception Primitives (View Snapshot baseline) | [05-ui-perception-primitives.md](05-ui-perception-primitives.md) | Before the Exploration Agent can "perceive," the Browser Controller must deterministically capture and persist a baseline view snapshot — a non-LLM capability that later change-detection (F8) consumes. |
| 06 | F5 — Autonomous UI Exploration Agent | [06-autonomous-ui-exploration-agent.md](06-autonomous-ui-exploration-agent.md) | The first LLM-driven capability; needs F2 (adapters), F3 (a project/environment/package to explore against), F4 (perception primitives). Produces the first `pending/` test cases. |
| 07 | F6 — Human Review & Approval Workflow + review UI | [07-human-review-and-approval-workflow.md](07-human-review-and-approval-workflow.md) | Once `pending/` test cases exist (F5), the approval lifecycle must exist before anything can be promoted to deterministic replay. Gains its review/approve/reject/edit screen in this epic. |
| 08 | F7 — UI Execution Engine (Deterministic Replay) + run/report UI | [08-ui-execution-engine.md](08-ui-execution-engine.md) | Consumes `approved/` test cases (F6) and replays them; must exist and be able to fail before Self-Healing (F9) has anything to react to. Gains its run-trigger and report-viewer screen. |
| 09 | F8 — View Identity & Change Detection (Diff Gate) | [09-view-identity-and-change-detection.md](09-view-identity-and-change-detection.md) | Needs both an Exploration Agent (F5, produces snapshots) and an Execution Engine (F7, replays per view) to make the none/cosmetic/structural-minor/structural-major gate meaningful and testable. |
| 10 | F9 — Self-Healing Locator Engine + healing review UI | [10-self-healing-locator-engine.md](10-self-healing-locator-engine.md) | Triggered on step failure during F7 execution — cannot precede F7 (nothing to fail) or F4 (nothing to re-perceive with). Gains its healing review queue screen. |
| 11 | F10 — Scenario Interpreter + scenario UI | [11-scenario-interpreter.md](11-scenario-interpreter.md) | A second LLM orchestrator reusing F5's perception-action loop and F6's approval path — sequenced after the core explore/approve/replay/heal loop is proven, since it's additive coverage. Gains its scenario submission form. |
| 12 | F11 — File-Upload Coverage (UI side) | [12-file-upload-coverage-ui.md](12-file-upload-coverage-ui.md) | Needs F5 (agent recognizes file-input fields) and F7 (`upload_file` execution action) already working; a small, isolable addition. |
| 13 | F12 — Job Scheduler / AI-Work Queue & Concurrency (UI scope) | [13-job-scheduler-and-concurrency.md](13-job-scheduler-and-concurrency.md) | Manual single-job triggering has sufficed to verify F5–F11 in isolation; real concurrency (parallel replay + serialized AI queue) is layered in once there are multiple job kinds worth serializing. |
| 14 | F13 — REST API Trigger Contract & Webhooks (UI scope) + notification UI | [14-rest-api-trigger-contract-and-webhooks.md](14-rest-api-trigger-contract-and-webhooks.md) | CI/CD-facing contract on top of F12's scheduler — needs a real scheduler behind it to be meaningful. Gains the in-dashboard notification feed. |
| 15 | F14 — Logging Subsystem completion (rotation + cross-component verification) | [15-logging-subsystem-completion.md](15-logging-subsystem-completion.md) | Rotation/separation verification is more meaningful once there's enough real cross-component activity (F5–F13) to actually generate log volume. |
| — | **API-specific epics begin here**, after the F0–F14 UI pipeline above is complete | | |
| 16 | F16 — Adapter Layer Extension: HTTP + Spec (API foundations) | [16-adapter-layer-extension-http-and-spec.md](16-adapter-layer-extension-http-and-spec.md) | First API-specific epic. `HTTPClient`/`HTTPXAdapter`, `SpecParser`, `SpecDiffer` are net-new adapters nothing in F0–F14 needs — mirrors how F2 started the UI block. |
| 17 | F17 — API Project/Environment Packages + CRUD UI extension | [17-api-project-and-environment-packages.md](17-api-project-and-environment-packages.md) | Extends F3's package model with the `api` shape; needs F16's SpecParser to validate/dereference what gets stored. Extends F3's CRUD screens with API package fields. |
| 18 | F18 — API Discovery Agent + review UI extension | [18-api-discovery-agent.md](18-api-discovery-agent.md) | The API analog of F5; needs F16 (SpecParser), F17 (an api package), and the already-built LLMClient (F2) / Test Case Store (F1). Adds the API protocol tab to F6's review screen. |
| 19 | F19 — API Test Runner (Deterministic Replay) | [19-api-test-runner.md](19-api-test-runner.md) | The API analog of F7; needs F18's approved test cases and F16's HTTPClient. Must exist and be able to fail before API Healing (F21) has anything to react to. |
| 20 | F20 — Operation Identity & Spec-Diff Change Detection + notification extension | [20-operation-identity-and-spec-diff-change-detection.md](20-operation-identity-and-spec-diff-change-detection.md) | The API analog of F8; needs F18 (baseline spec) and F19 (replay to gate) plus F16's SpecDiffer. Extends F13's notification feed with contract-change alerts. |
| 21 | F21 — API Healing Engine + healing UI extension | [21-api-healing-engine.md](21-api-healing-engine.md) | The API analog of F9; triggered on F19 failures attributable to contract drift, using F20's diff context. Extends F9's healing review screen with the API protocol tab. |
| 22 | F22 — File-Upload Coverage (API side / multipart) | [22-file-upload-coverage-api.md](22-file-upload-coverage-api.md) | Shares F11's fixture library; adds multipart support to F16's HTTPXAdapter and F18's Discovery Agent. Small, sequenced after the core API loop is proven. |
| 23 | F23 — Concurrency Extension & cross-cutting final verifications | [23-concurrency-extension-and-final-verifications.md](23-concurrency-extension-and-final-verifications.md) | Extends F12's scheduler so API discovery/healing also serialize on the shared GPU queue; closes with the full set of Section 10 end-to-end verifications spanning both protocols. |

See [`plan.md`](plan.md) for the full architecture/feasibility writeup these stories were derived from.
