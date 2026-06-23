# MAYA — AI-Driven Test Automation Framework — Feasibility & Architecture Plan

## Context

The goal is to build **MAYA**, a Python-based test automation framework that uses a **locally-hosted LLM (via Ollama)** to autonomously explore a web application or API, propose test cases, and — after human approval — execute and verify them on an ongoing basis. The motivation is to reduce the manual effort of writing and maintaining UI and API test suites, while keeping AI usage (and therefore cost/latency) limited to only the moments it's actually needed: initial exploration, handling app/contract changes, and healing broken tests. Routine "nothing changed" runs should replay deterministically without touching the LLM at all.

This is a **feasibility study / architecture plan only** — no code will be written yet. The verdict: **yes, this is buildable** with current open-source tooling (Playwright for browser control, httpx for API calls, Ollama + open-weight models for reasoning/vision, FastAPI + React for the service/UI layer). The sections below lay out the components, data model, workflows, and risks needed to build it for real.

Target hardware: **16GB GPU, 16GB system RAM** — this caps how much model capacity can run at once and shapes the model-sizing recommendation below.

Key decisions made with the user (across multiple rounds of review):
- **Exploration**: DOM + screenshot are combined on every UI exploration/healing decision (not vision-as-rare-fallback) — sized with smaller models so both fit in 16GB VRAM together. The framework decides model selection automatically; the user doesn't pick models manually.
- **Test case format**: Structured declarative **JSON** steps interpreted at runtime — not generated Playwright/Selenium/HTTP-client code — so self-healing patches locator/mapping *data*, not code.
- **Change detection**: Diff keyed on a logical **view/app-state identity** for UI (not just URL route, so SPAs without route changes are still covered) and on **operation identity** for API (method+path or operationId), both gating whether the LLM is invoked at all.
- **Business scenarios**: User can enter a plain-text business scenario; a dedicated Scenario Interpreter agent converts it into structured test case(s), separate from the autonomous Exploration Agent.
- **UI**: FastAPI backend + **React + Material UI** frontend, for review/approval, project CRUD, and reports. New-test-case notifications surface in the web dashboard.
- **Storage**: File-based, JSON, git-friendly directory layout — no database.
- **Concurrency**: Multiple jobs/projects can run at once. Replay-only runs parallelize freely; any AI-invoking work (exploration, healing escalation, scenario interpretation, API discovery) is serialized through a single queue against the local Ollama instance.
- **Execution metrics**: Per-test-case execution time and total job time are captured in every run, for both UI and API testing.
- **Logging**: Time- and size-based rotating logs, separated into app log, LLM log, and API log.
- **Secrets/config storage**: Designed to extend beyond credentials to other maintained content later, not secrets-only — now formalized as part of the per-environment "package" (see below).
- **CI/CD integration**: Webhook/REST API triggered; the framework runs as a persistent service.
- **Naming**: the framework is called **MAYA**.
- **Project/test-type shape**: one project can host multiple test-type suites (UI, API, and future types such as mobile/performance) sharing one set of environments — not one project per test type.
- **Input packaging**: each environment carries a named **package** per test type (env vars/credentials, URL or spec, upload fixtures, optional free-text instructions) as the single formal input unit, rather than loose fields scattered across config.
- **Multi-environment**: dev/staging/prod-style environments are first-class. The data model is restructured so environment-specific history (snapshots, runs, healing logs, spec versions) doesn't leak across environments, while test cases stay environment-agnostic and reusable across all of them.
- **API testing**: added via Swagger/OpenAPI spec input, mirroring the UI flow end-to-end. Exploration is **LLM-only** — the API Discovery Agent reads the spec directly rather than relying on a Schemathesis-driven generation pipeline — with flow-based CRUD-lifecycle generation (create → verify → update → verify → delete → verify) as the **steered default** pattern, not just one inferred possibility among many.
- **Tool adapters**: every external tool (Ollama, Playwright, httpx, the spec-diff library, etc.) sits behind a formal adapter interface per category, so any one can be swapped for an alternative without touching the rest of the codebase.
- **File uploads**: both UI and API testing support file-upload coverage, backed by a small built-in fixture library with per-project override/addition.

---

## 0. Project Overview & Feature Catalog

This section is a single, comprehensive, standalone read intended to let a future session — or a different implementer — scope and break down implementation sub-tasks **without** first having to reconstruct intent from Sections 1–11. It is feature-level, not implementation-level: each entry is a short description of what the feature does and why it exists, with a cross-reference to the section holding full implementation detail. Treat each bullet as a candidate epic; derive concrete sub-tasks by following its cross-reference.

**Core Identity**
- MAYA is a locally-hosted, LLM-assisted test automation framework that autonomously explores UI and API surfaces, proposes test cases, and replays them deterministically going forward — invoking the LLM only when something needs judgment (initial exploration, contract/UI change, healing), never on routine "nothing changed" runs. (→ Context, Section 6)

**Project & Environment Model**
- Projects host one or more test types (UI, API, future types) under one shared environment set. (→ Section 3)
- Environments (dev/staging/prod, arbitrary names) are first-class, each carrying its own history (snapshots, runs, healing logs, spec versions) isolated from other environments, while test cases stay environment-agnostic and reusable across all of them. (→ Section 3)
- The "package" is the formal input unit per environment per test type: credentials/URL for UI, spec+credentials for API, plus optional upload fixtures and free-text instructions for either. (→ Section 3)

**UI Testing**
- Autonomous Exploration Agent perceives DOM (AX-tree) + screenshot together on every decision, proposing structured JSON test cases (not generated code) for human approval. (→ Section 1, Section 5.a)
- Business-scenario-driven test creation: a separate Scenario Interpreter agent turns a free-text scenario into test cases via the same goal-directed perception-action loop. (→ Section 5.b)
- View-identity-based change detection (URL + structural fingerprint + heading) gates whether routine runs touch the LLM at all — the core cost-saving mechanism. (→ Section 4, Section 5.d)
- Self-healing locator engine with a confidence-scored fallback hierarchy, auto-applying high-confidence heals and flagging low-confidence ones for review. (→ Section 5.e)
- File-upload coverage via a built-in fixture library with project-level overrides. (→ Section 5.j)

**API Testing**
- Swagger/OpenAPI spec as input, mirroring the UI flow end-to-end: an API Discovery Agent reads the spec directly (LLM-only, no Schemathesis-driven generation pipeline) and proposes structured test cases for approval. (→ Section 11.1, 11.5)
- Steered default pattern: for every resource the spec exposes, the Discovery Agent's primary search is the full CRUD-lifecycle-with-verification chain (create → verify created → update → verify updated → delete → verify deleted), threading the created entity's id through every step. (→ Section 11.3, 11.5)
- Spec-diff-based contract change detection (via oasdiff), reusing the same none/cosmetic/structural-minor/structural-major severity vocabulary as UI view-diffing, gating scoped re-discovery vs. full replay. (→ Section 11.2, 5.h)
- API Healing Engine: a confidence-scored fallback hierarchy for contract drift (renamed fields, moved params, path changes, auth scheme changes), mirroring the UI locator-healing pattern. (→ Section 11.6, 5.i)
- Multipart/file-upload endpoint coverage, sharing the same fixture library as UI testing. (→ Section 5.j)

**Shared Infrastructure**
- Formal adapter interfaces per external tool category (LLM inference, browser automation, HTTP client, spec parsing, spec diffing, notifications) so any underlying tool can be swapped without touching consumer code. (→ Section 2)
- Single serialized AI-work queue shared by UI and API LLM calls against the local GPU; replay-only work (no LLM) runs fully parallel. (→ Section 6)
- File-based, git-friendly JSON storage throughout, no database. (→ Section 3)
- Per-test-case and per-job timing metrics captured on every run, both UI and API. (→ Section 3, Section 11.3)
- Three rotating log streams (app/LLM/API). (→ Section 8)
- Credential/secrets storage generalized to any sensitive or environment-specific content, nested per environment inside the package. (→ Section 7)
- REST API + webhook trigger contract for CI/CD integration, with an explicit `environment` selector per run. (→ Section 5.f)
- React + MUI dashboard for project/environment/package CRUD, pending-test-case review and approval, scenario submission, healing review, and reporting — tabbed per test type within a project. (→ Section 2)

**Open Risks Worth Tracking** (one line each, full detail in Section 9)
- LLM hallucination in generated tests, view/operation-identity false positives, GPU/RAM contention under concurrency, dynamic-content assertions, CAPTCHA/2FA limits, healing drift, scenario/discovery agents getting stuck, exploration coverage-vs-cost tuning, API-specific risks (stateful sequencing, spec drift, environment-behavior false positives, destructive side effects, fixture mismatch, adapter abstraction leakage).

---

## 1. Local LLM Model Strategy (Ollama, 16GB GPU / 16GB RAM)

### 1.1 Sizing for combined DOM+vision on every decision, plus text-only API reasoning

Because the decision was to **always feed both DOM text and a screenshot** into the model for UI work (not just on fallback), and the GPU has 16GB VRAM, model sizes must be picked to leave headroom for the browser process, OS, and Ollama's own overhead — not just the raw model weights. API reasoning never involves a screenshot, so it gets its own smaller, text-only model rather than reusing the multimodal one.

| Role | Model | Size / VRAM (Q4_K_M) | Notes |
|---|---|---|---|
| Primary reasoning + vision (UI exploration, healing, scenario interpretation) | **Qwen2.5-VL 7B** | ~6-8GB | A single multimodal model that accepts both the AX-tree-as-text *and* the screenshot in one prompt, avoiding the need to run two separate models concurrently. Strong UI/layout grounding plus solid tool-calling. |
| Fallback for tighter memory situations | **Qwen2.5-VL 3B** | ~4GB | Framework-selectable automatically (see 1.2) when concurrent jobs or other load make 7B impractical at that moment. |
| API reasoning (Discovery Agent spec analysis, flow/assertion authoring, last-resort field remapping) | **Qwen2.5 7B-Instruct** | ~5GB | Text-only sibling of the vision model family (same tokenizer/behavior, same Ollama pull pattern) — skips the vision encoder entirely since API reasoning never involves a screenshot. Joins the *same* AI-work queue as UI calls (Section 6); avoids wasting shared GPU time on multimodal overhead for a task that has no images. |
| (Optional, future) Complex custom assertion logic | **Qwen2.5-Coder 7B** | ~6GB | Not required for MVP since assertions are declarative; flagged as a future extension point. |

Using **one combined multimodal model** for UI work rather than a separate text-reasoning model + separate vision model is the practical choice here: it fits comfortably in 16GB with room for the browser/OS, and avoids the latency/complexity of swapping two models in and out of VRAM for every single step. This directly answers the "can DOM+screenshot combined be more accurate" question — yes, a multimodal model reasoning over both signals at once typically resolves ambiguous cases (e.g., visually distinct but DOM-identical buttons, or canvas-rendered UI) that DOM-only reasoning would miss, at the cost of extra tokens/latency per call. For API reasoning, the same logic runs in reverse: paying multimodal overhead for a task with no images would be pure waste and would extend the AI-queue backlog for everyone, including concurrent UI jobs, since both share one GPU queue.

### 1.2 Automatic model selection (framework-managed, not user-managed)

The user should never need to pick a model by name. The **Ollama Client** component (implemented as the `OllamaAdapter`, see Section 2's adapter layer) owns a small policy:
- On startup/first use, probe available VRAM and currently loaded Ollama models.
- Maintain a ranked preference list **per task role** (e.g., `ui_explore_heal: [qwen2.5-vl:7b, qwen2.5-vl:3b]`, `api_reasoning: [qwen2.5:7b-instruct]`) in `global_config.json`, but treat this as an internal default, not something the end user configures per run.
- Before a call, check current load (how many concurrent AI-invoking jobs are queued/running — see Section 6) and downgrade to the smaller model automatically if multiple jobs are contending for the GPU, or if a previous call at the larger size hit an OOM/timeout.
- Log which model was actually used for each call (in the LLM log, Section 8) so behavior is auditable even though it's automatic.

### 1.3 Ollama operational notes
- Quantization: Q4_K_M for VRAM-constrained setups, Q5/Q6 when quality matters more and headroom allows.
- Set `OLLAMA_MAX_LOADED_MODELS` based on observed concurrency needs; since UI work mostly uses one combined model and API work uses a separate smaller one, swapping is a function of how often UI and API jobs interleave, not a constant concern.
- Fully local — no cloud dependency, consistent with the requirement.
- All of the above (model-selection policy, quantization choice, `OLLAMA_MAX_LOADED_MODELS`) lives entirely inside `OllamaAdapter`, the concrete implementation of the `LLMClient` interface (Section 2). Every agent calls `LLMClient.generate(...)` and never touches Ollama's REST API or model-name strings directly — this is what makes the local-inference backend swappable later without touching agent code.

---

## 2. System Architecture / Components

### 2.1 Adapter layer (cross-cutting)

Every external tool/library MAYA depends on sits behind a **formal adapter interface per category** — an abstract base class (Python `Protocol`/ABC) that the rest of the framework depends on, never the underlying library directly. Concrete adapters implement the interface; only the adapter module imports the third-party library. This means swapping Ollama for another local-inference backend, or Playwright for another browser driver, means writing one new adapter class, not touching call sites scattered across agents and engines.

| Category | Interface | Default concrete adapter | What it abstracts |
|---|---|---|---|
| Local LLM inference | `LLMClient` | `OllamaAdapter` | `generate(prompt, images?, tools?) -> response`; model load/selection policy (Section 1.2) lives entirely behind this interface |
| Browser automation | `BrowserDriver` | `PlaywrightAdapter` | `navigate`, `click`, `type`, `get_ax_tree`, `screenshot`, `upload_file`, session/storage-state handling |
| HTTP client (API testing) | `HTTPClient` | `HTTPXAdapter` | request execution + timing capture, multipart upload support |
| Spec parsing/validation | `SpecParser` | `PranceOpenAPIAdapter` (prance + openapi-core) | dereference `$ref`s, validate request/response against schema |
| Spec diffing | `SpecDiffer` | `OasdiffAdapter` | spec-to-spec diff + severity classification |
| Notification delivery | `NotificationChannel` | `DashboardChannel` (+ optional `EmailChannel`/`SlackChannel`) | in-dashboard is primary; email/Slack are additional channels behind the same interface |

Each agent/engine (Exploration Agent, Scenario Interpreter, API Discovery Agent, Execution Engine, API Test Runner, Self-Healing Engine, API Healing Engine) is constructed with injected adapter instances rather than importing Playwright/httpx/Ollama's SDK directly. Adding API testing to MAYA means adding new adapters (`HTTPXAdapter`, `OasdiffAdapter`, `PranceOpenAPIAdapter`) and new agents that consume them, without modifying the existing `PlaywrightAdapter`/`OllamaAdapter` or their consumers at all.

### 2.2 Component diagram

```
                         ┌────────────────────────┐
                         │  React + MUI Dashboard  │  (project/env/package CRUD, review/approve,
                         └───────────┬─────────────┘   reports, notifications — tabbed per test type)
                                     │ HTTP/JSON
                         ┌───────────▼─────────────┐
                         │      REST API Layer      │ (FastAPI)
                         │  + Webhook/CI endpoints  │
                         └───────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────────────────────────────┐
              │                      │                                              │
   ┌──────────▼─────────┐ ┌──────────▼───────────┐               ┌──────────────────▼──────────┐
   │  Project Manager     │ │  Job Scheduler /      │               │ Notification Service          │
   │  (CRUD, env/package) │ │  Concurrency Manager  │               │ (in-dashboard primary;        │
   └──────────┬────────────┘ │  (queues, job runner) │               │  email/Slack via adapter)     │
              │              └──────────┬────────────┘               └────────────────┬──────────────┘
              │                         │                                              │
              │              ┌──────────┴────────────────┐                             │
   ┌──────────▼─────┐ ┌──────▼───────┐   ┌──────────────▼──────────┐                  │
   │ Test Case Store  │ │ View Snapshot│   │  Execution Engine /      │                  │
   │ (file-based CRUD,│ │ & Diff Engine│   │  Step Runner (UI)         │                  │
   │  protocol-tagged)│ │ (UI)         │   │  API Test Runner (API)    │                  │
   └──────────┬───────┘ └──────┬───────┘   └──────────────┬──────────┘                  │
              │                │                           │                             │
              │      ┌─────────▼─────────┐      ┌──────────▼──────────┐                  │
              │      │ Exploration Agent  │      │ Self-Healing Engine  │                  │
              │      │ Scenario Interpreter│◄────┤ (UI, locator fallback│                  │
              │      │ API Discovery Agent │     │ API Healing Engine    │──────────────────┘
              │      │ (LLM orchestrators)  │     │ (API, contract fallback)│
              │      └─────────┬─────────┘      └──────────┬──────────┘
              │                │                            │
              │      ┌─────────▼─────────┐                  │
              │      │ Browser Controller │◄──────────────────┘
              │      │ (via BrowserDriver) │
              │      │ API Client Controller│
              │      │ (via HTTPClient)     │
              │      └─────────┬─────────┘
              │                │
              │      ┌─────────▼─────────┐         ┌─────────────────────┐
              │      │  Ollama Client      │         │  Spec Manager        │
              │      │  (via LLMClient)     │         │  (via SpecParser/    │
              │      │  - Qwen2.5-VL 7B/3B  │         │   SpecDiffer)         │
              │      │  - Qwen2.5 7B-Instr. │         └─────────────────────┘
              │      └────────────────────┘
              │
   ┌──────────▼───────────┐         ┌────────────────────────┐
   │  Reporting Engine     │         │ Logging Subsystem        │ (app/LLM/API logs,
   │ (incl. timing metrics)│         │ size+time rotation)       │  Section 8)
   └────────────────────────┘         └────────────────────────┘
```

### 2.3 Component responsibilities

| Component | Responsibility |
|---|---|
| **Browser Controller** (via `BrowserDriver` / `PlaywrightAdapter`) | Owns the browser session: `navigate`, `click`, `type`, `get_ax_tree()`, `screenshot()`, `get_dom_html()`, `upload_file()` (resolves a test step's `fixture_ref` to an actual file path and drives the native file-input dialog). Handles login flows, session/cookie persistence per environment. Supports isolated browser contexts per concurrent job. |
| **API Client Controller** (via `HTTPClient` / `HTTPXAdapter`) | Owns HTTP execution for API test steps: builds requests from resolved step JSON (headers/body/params after placeholder + `extract`/`inject` resolution), issues via httpx, captures response + timing (minimum: total latency per request; DNS/connect/TLS/TTFB breakdown where available) — same per-step/per-test-case timing pattern as UI. Owns auth header/token injection per environment, and multipart file uploads via the same `fixture_ref` resolution mechanism as Browser Controller. No browser, no DOM. |
| **Spec Manager** (via `SpecParser`/`SpecDiffer` — prance + openapi-core + oasdiff) | Fetches/parses/dereferences OpenAPI specs on ingestion and on each scheduled/triggered re-check; validates requests/responses against the dereferenced schema at execution time; diffs spec versions and classifies severity (Section 11.2). This is the API analog of the View Snapshot & Diff Engine — the gate deciding whether the API Discovery Agent is invoked at all. |
| **View Snapshot & Diff Engine** (UI) | After each navigation/state change, extracts a normalized structural representation **and** a screenshot, and computes a **logical view identity** (Section 4) rather than relying on URL alone — covers SPA tab/modal/state changes with no route change. Hashes and diffs vs. last snapshot for that view identity; classifies severity: none / cosmetic / structural-minor / structural-major. **This is the gate that decides whether the LLM is invoked at all.** |
| **Exploration Agent** (LLM orchestrator) | Runs a perception → reasoning → action loop, feeding the combined model both AX-tree-as-text and a screenshot each step. Proposes candidate test cases as structured JSON steps; stops on a step/page budget or coverage plateau. Selects upload fixtures from the environment's package when it encounters a file-input field (Section 5.j). |
| **Scenario Interpreter** (LLM orchestrator, distinct entry point) | Takes a user-entered free-text business scenario, runs a goal-directed perception-action loop (same Browser Controller/Ollama Client, different prompting/objective than open exploration) to fulfill the described scenario, and emits one or more structured test cases for review — same `pending` approval path as exploration output. |
| **API Discovery Agent** (LLM orchestrator) | Reads the dereferenced OpenAPI spec directly (LLM-only — no Schemathesis-driven generation pipeline) and proposes structured API test cases. Steered to attempt the full CRUD-lifecycle-with-verification chain per resource as its primary pattern (Section 11.5). Selects upload fixtures for multipart endpoints. Same `pending` approval path as the other agents. |
| **Self-Healing Engine** (UI) | Triggered on step failure. Classifies failure type, then runs a ranked locator fallback hierarchy (`data-testid` → `aria-label`/role → visible text → relative DOM position → XPath similarity → combined DOM+vision re-grounding as last resort), scoring each candidate's confidence. Auto-applies high-confidence heals; flags low-confidence ones for human review. |
| **API Healing Engine** | Triggered on API step failure attributable to contract drift. Runs a ranked field/contract fallback hierarchy (exact match → fuzzy name match → type-compatible positional match → operationId/tag match → auth scheme migration → LLM semantic remapping as last resort), scoring each candidate's confidence. Same auto-apply/flag pattern as Self-Healing Engine (Section 11.6). |
| **Execution Engine / Step Runner** (UI) | Deterministic interpreter for approved UI test cases — resolves locators, performs actions (including `upload_file`), evaluates assertions, captures screenshots on failure. Records **per-step and per-test-case timing**. Invokes Self-Healing Engine inline on locator/assertion failures. |
| **API Test Runner** | Deterministic interpreter for approved API test cases — resolves `extract`/`inject` value threading across steps, invokes API Client Controller per step, evaluates assertions (`schema_match`, `field_equals`/`contains`/`regex_match`/`numeric_range`), records per-step/per-test-case timing. Invokes API Healing Engine inline on contract mismatches. |
| **Test Case Store** | File-based CRUD across lifecycle states (`pending` → `approved` → `archived`), with versioning for healed test cases and file locking to avoid concurrent-write corruption. JSON format throughout, `protocol`-discriminated (`ui` / `api`, extensible to future types) but otherwise shared across protocols. |
| **Project Manager** | CRUD for projects (each = one target system, hosting one or more test-type suites); manages environments and their packages; scaffolds directory structure on create; archive-not-purge on delete (consistent with git-friendly storage). |
| **Job Scheduler / Concurrency Manager** | Accepts run requests (manual, scheduled, webhook) and dispatches them as jobs against a specific project + environment. Tracks **total job time** alongside per-test timings. Enforces the concurrency policy: replay-only jobs run fully in parallel (isolated browser contexts / independent HTTP calls); any job needing AI (UI exploration/healing-escalation/scenario interpretation, API discovery/healing) is placed on a single serialized AI-work queue against the local Ollama instance, so GPU contention is controlled centrally rather than per-component. |
| **Ollama Client** (via `LLMClient` / `OllamaAdapter`) | Wrapper around Ollama's REST API implementing the automatic model-selection policy (Section 1.2) and the AI-work queue consumption (one in-flight inference at a time, ordered fairly across jobs, regardless of which task role or protocol requested it). |
| **Notification Service** (via `NotificationChannel`) | In-dashboard notifications are the primary channel (new pending test cases, run completed, auto-heal applied, heal flagged for review, run failed, contract change detected) with optional email/Slack adapters for events the user wants to also receive outside the dashboard. |
| **Reporting Engine** | Renders HTML (+ JSON source-of-truth) run reports: pass/fail per test, failure reasons, before/after screenshots or field mappings, healing events with confidence scores, **and timing breakdown (per-test-case + total job duration)** — shared rendering pipeline across UI and API protocols. |
| **REST API Layer** (FastAPI) | Single entry point for the React dashboard and CI: project/environment/package CRUD, test-case CRUD, approval, scenario submission, run triggering (with explicit `environment` selector), report retrieval, webhook ingestion. Runs as a persistent service. |
| **React + MUI Dashboard** | Frontend for project/environment/package CRUD, pending test case review/approve/reject/edit (tabbed per test type), business-scenario submission form, report browsing, in-dashboard notification center, healing review queue. Talks only to the REST API. |
| **Logging Subsystem** | Structured, rotating logs split into **app log**, **LLM log**, **API log** (Section 8), each with both size- and time-based rotation. |

---

## 3. Data Model / File Layout

### 3.1 Projects host multiple test types; environments are first-class

A project is the unit for "one target system" — it can host **one or more test-type suites** (UI, API, and future types) simultaneously, sharing one set of environments rather than requiring a separate project per test type. `project.json` carries `test_types: ["ui", "api"]`.

An **environment** (dev/staging/prod, or any other name) is a deployment of that same system. Environments are nested under the project (not a sibling top-level concept), because a project's test cases are shared across all its environments — only the *target* (host, credentials, spec version) and the *history* (snapshots, runs, healing logs) differ per environment.

**The "package"** is the formal input unit per environment, per test type: a named sub-document inside `environment.json` holding everything needed to run that test type against that environment — env vars/credentials, base URL or spec reference, optional upload fixtures, and optional free-text instructions. This replaces ad hoc loose fields (`base_url`, `auth`, `spec_ref` as scattered siblings) with one consistent concept: "the package is the input."

### 3.2 Avoiding combinatorial directory explosion

Split by what's actually environment-specific vs. environment-agnostic:
- **Environment-agnostic (stays project-level):** `test_cases/` (steps/locators/assertions don't reference a host — a login button's `data-testid` doesn't change between dev and prod), `scenario_sessions/`, `uploads/` (project-supplied fixture files, reused across environments).
- **Environment-specific (lives under `environments/<environment_id>/`):** `view_snapshots/` (UI structure can genuinely differ per environment — feature flags, data volume), `specs/` (API projects may pin different spec versions per environment), `runs/` (a run is always against a specific environment), `healing_logs/` (a heal valid in staging must never silently apply to prod).

### 3.3 File layout

Git-friendly root layout, JSON throughout (secrets/config excluded from git via `.gitignore`):

```
/framework-data/
├── .gitignore                          # excludes config/secure/, *.local.json, runtime/, logs/
├── global_config.json                  # Ollama host, model preference list per task role, default thresholds
├── fixtures/                            # built-in default upload fixtures, shipped with MAYA itself
│   ├── sample.pdf
│   ├── sample.png
│   ├── sample.csv
│   └── sample_large.pdf
├── config/
│   └── secure/                          # gitignored — see Section 7 (secrets + other sensitive content)
│       └── <project_id>.secure.json
├── logs/                                # gitignored — see Section 8
│   ├── app/
│   ├── llm/
│   └── api/
└── projects/
    └── <project_id>/
        ├── project.json                 # protocol-agnostic project config, test_types[], environments[], default_environment
        ├── test_cases/                  # environment-agnostic, protocol-discriminated
        │   ├── pending/tc_<uuid>.json
        │   ├── approved/tc_<uuid>.json
        │   └── archived/tc_<uuid>.json
        ├── scenario_sessions/
        │   └── scenario_<timestamp>.json
        ├── uploads/                      # project-supplied fixture files, referenced by packages
        │   └── <filename>
        └── environments/
            ├── dev/
            │   ├── environment.json       # packages: { ui: {...}, api: {...} }, schedule, is_destructive_safe
            │   ├── view_snapshots/         # ui package only
            │   │   ├── index.json
            │   │   └── <view_identity_slug>/<timestamp>.json
            │   ├── specs/                  # api package only
            │   │   ├── index.json          # current pinned version + history
            │   │   └── <spec_version_hash>/
            │   │       ├── openapi.json
            │   │       └── diff_from_previous.json
            │   ├── runs/
            │   │   └── run_<timestamp>_<uuid>/
            │   │       ├── run_summary.json     # includes timing metrics
            │   │       ├── report.html
            │   │       ├── screenshots/          # ui projects
            │   │       └── diffs/
            │   └── healing_logs/
            │       └── tc_<uuid>_healing.json    # append-only history per test case
            ├── staging/
            │   └── ... (same shape)
            └── prod/
                └── ... (same shape)
```

`uploads/` is project-level, not per-environment, since the same dummy file is normally reused across dev/staging/prod; a package's `upload_fixtures` array references files from either `fixtures/` (built-in) or `<project_id>/uploads/` (project-supplied) by a `builtin:` or project-relative reference, never duplicated per environment.

### 3.4 Schema sketches

**`project.json`**:
```json
{
  "id": "acme-webapp",
  "test_types": ["ui", "api"],
  "default_environment": "staging",
  "environments": ["dev", "staging", "prod"],
  "exploration": { "...": "budgets — shared defaults, overridable per-environment" },
  "healing": { "auto_apply_threshold": 0.90, "vision_fallback_after_attempts": 2 },
  "notifications": { "...": "..." },
  "concurrency": { "...": "any project-level override" }
}
```

**`environment.json`**:
```json
{
  "id": "staging",
  "label": "Staging",
  "schedule": { "cron": "0 */6 * * *" },
  "is_destructive_safe": true,
  "packages": {
    "ui": {
      "base_url": "https://staging.acme.com",
      "auth": { "strategy": "form_login", "secure_ref": "acme-webapp.staging" },
      "env_vars": { "FEATURE_FLAG_X": "true" },
      "upload_fixtures": ["builtin:sample.pdf", "builtin:sample.png"],
      "instructions": null
    },
    "api": {
      "spec_ref": { "source": "url", "value": "https://api-staging.acme.com/openapi.json", "pinned_version": "v2.3.1" },
      "env_vars": { "API_KEY": "${secure.acme-webapp.staging.api_key}" },
      "upload_fixtures": ["builtin:sample.csv"],
      "instructions": "Treat /internal/* endpoints as out of scope."
    }
  }
}
```

**Test case** (`tc_<uuid>.json`, shared top-level shape, protocol-discriminated steps):
- Shared fields: `id`, `protocol` (`"ui"` / `"api"`), `status` (pending/approved/needs_review/archived), `created_by` (`exploration_agent` / `scenario_interpreter` / `api_discovery_agent` / `human`), `source_scenario_ref` (if applicable), `tags`, `healing_history_ref`, `last_run_status`, `last_execution_time_ms`.
- UI-specific: `view_identity`, `locator_confidence`, `steps[]` (each: `action`, `target: {strategy, value}`, `input`/`assertion`; `action: "upload_file"` steps carry `fixture_ref`).
- API-specific: `operation_ids[]`, `spec_version_ref`, `field_mapping_confidence`, `steps[]` (each: `step_id`, `operation_id`, `method`, `path`, `headers`, `body` or `body_type: "multipart"` + `files[]` with `fixture_ref`, `path_params`, `query_params`, `expected_status`, `expected_schema_ref`, `extract`, `assertions[]`). See Section 11.3 for the full worked example.

**View snapshot record**: `view_identity`, `captured_at`, `page_hash`, `screenshot_ref`, `elements[]` (ref, role, name, data-testid, path_fingerprint), `diff_against_previous` (severity, added/removed/changed).

**Execution report** (`run_summary.json`): `run_id`, `environment_id`, `trigger` + metadata, `decision` (replay vs. re-explore per view/operation), `total_job_time_ms`, `results[]` (per-test status incl. `healed_pass`, `execution_time_ms`, healing event refs, screenshots/mappings), `summary` (counts).

**Healing event log entry**: `heal_id`, `run_id`, `step_id`, `failure_type`, `original_locator` / `original_mapping`, `candidates[]` (strategy, value, confidence, signal breakdown), `applied`, `auto_applied`, `escalated_to_vision` / `escalated_to_llm`.

Secrets and the placeholder resolution mechanism (`${secure.<project>.<environment>.<key>}`) are detailed in Section 7 — conceptually, secrets now live inside the package rather than as a sibling concept, with no change to the resolution mechanism itself.

---

## 4. Defining "View Identity" for SPA-Aware Change Detection (UI)

Since many SPAs change visible content/state without a URL or route change, the View Snapshot & Diff Engine keys snapshots on a **logical view identity** computed from multiple signals combined, not URL alone:
1. URL + hash fragment + query params, if present (still useful when available).
2. A structural fingerprint of the **main content container** (e.g., hash of the primary content region's role/landmark structure — `main`, top-level `role="tabpanel"`, modal/dialog root, etc.), so distinct tabs, modals, or client-rendered "pages" get distinct identities even at the same URL.
3. A stable title/heading signal (e.g., the active heading or document title text) as a tiebreaker signal when structural fingerprints are close.

This composite key is what `view_snapshots/<view_identity_slug>/` is organized by. Test cases reference `view_identity` instead of `route`. This means a test case tied to "Settings > Notifications tab" is tracked and diffed independently from "Settings > Profile tab" even if both live under `/settings`.

The API testing analog — **operation identity** — is simpler and doesn't need a composite signal; see Section 11.1.

---

## 5. Core Workflows

### 5.a Initial UI exploration (new project)
1. User creates project via API/Dashboard, chooses one or more test types (UI/API), adds one or more environments, each with a package (credentials/URL for UI, spec+credentials for API, optional upload fixtures and instructions for either) → Project Manager scaffolds directories, writes `project.json` + environment configs + secure config file.
2. Browser Controller logs in using the UI package's credentials; View Snapshot Engine takes a baseline snapshot (no prior snapshot exists, so this unconditionally triggers exploration).
3. Exploration Agent loops: perceive AX-tree-as-text **+ screenshot** → reason via the combined Qwen2.5-VL model (tool-calling) → act via Browser Controller → repeat until budget exhausted or coverage plateaus. Selects upload fixtures from the package when a file-input field is encountered (Section 5.j).
4. Coherent flows become structured JSON test cases (`protocol: "ui"`) written to `test_cases/pending/`; snapshots persisted per view identity under the active environment.
5. Notification Service raises an **in-dashboard** notification: "N new test cases pending review."

### 5.b Business-scenario-driven test creation
1. User submits a free-text business scenario via the dashboard (e.g., "A returning customer logs in, adds two items to the cart, and checks out using a saved address").
2. Scenario Interpreter agent runs a goal-directed perception-action loop against the live app (same DOM+screenshot input as Exploration Agent) attempting to fulfill the described scenario, recording each action and resulting state as it goes.
3. On completion (or on getting stuck, in which case it reports back what blocked it), it emits one or more structured test cases capturing the executed flow, written to `test_cases/pending/` with `created_by: scenario_interpreter` and `source_scenario_ref` pointing at the original scenario text.
4. Same approval path as 5.c below; an in-dashboard notification is raised the same way.

### 5.c User review/approval
1. Dashboard lists `pending/` test cases (via API), tabbed by protocol (UI/API), regardless of whether they came from autonomous exploration, a submitted scenario, or API discovery. User views steps/assertions, edits inline if needed.
2. Approve → file moves `pending/` → `approved/` (`status: approved`). Reject → moves to `archived/` with a rejection reason.

### 5.d Routine UI execution run (the cost-saving core loop)
1. Trigger arrives (schedule, webhook, or manual "Run Now") naming a project **and environment**. Job Scheduler accepts the run as a job; if it's replay-only it can run immediately in parallel with other jobs, subject only to general resource limits.
2. Run Orchestrator (within the job) loads approved UI test cases grouped by **view identity**.
3. For each view: Browser Controller reaches that state; View Snapshot Engine hashes/diffs against the last stored snapshot for that view identity, scoped to the run's environment.
4. **Decision gate per view**:
   - `none`/`cosmetic` diff → **Reuse**: Execution Engine runs existing approved tests directly with stored locators. **No LLM call**, job stays off the AI queue.
   - `structural-minor` → **Reuse, healing-ready**: run normally; only invoke Self-Healing Engine reactively if a specific locator fails (this does join the AI queue, but only for the affected test case's healing call).
   - `structural-major` → **Re-explore (scoped)**: invoke Exploration Agent for just that view to propose updated/new test cases — this job now needs the AI queue; unaffected views' existing tests still execute without waiting on it.
5. Execution Engine records **per-test-case execution time**; Job Scheduler records **total job time** across all test cases in the run.
6. Any step failure routes through Self-Healing Engine inline before being recorded as a final failure.
7. Reporting Engine renders the run report (including timing breakdown); Notification Service announces completion in-dashboard (with healing/flag callouts).

### 5.e Self-healing flow (UI)
1. On step failure, classify: `locator_not_found`, `element_changed_state`, `assertion_failure`, or `timeout`. Only the first two are eligible for locator healing.
2. Self-Healing Engine runs the fallback hierarchy against the current AX-tree **and current screenshot**, scoring each candidate (attribute similarity, element stability, specificity, context match, visual match — modeled on Healenium's weighted approach but with the visual signal available immediately rather than as a late fallback).
3. **Confidence-based decision**:
   - ≥ threshold (default 0.90) → auto-patch the test case's locator, bump version, log as `auto_applied: true`, resume the run, notify passively (in-dashboard).
   - below threshold → don't patch; mark `status: needs_review`, fail the step for this run, notify actively in-dashboard with before/after locator + screenshots.
   - no viable candidate → flag for full regeneration, optionally trigger scoped Exploration Agent re-run.
4. Every attempt (successful or not) is appended to the test case's healing log for audit.

### 5.f CI/CD-triggered run via webhook/API
- `POST /api/v1/projects/{project_id}/runs` — body includes `environment` (required; falls back to `default_environment` with a loud log line if omitted), `trigger`, `metadata` (CI job id, commit), `mode` (`auto`/`force_reexplore`/`replay_only`), optional `callback_url`. Returns `202 Accepted` with `run_id` (async default) or a short-wait sync result for small suites.
- `GET /api/v1/runs/{run_id}` — poll status/result, including live timing data while running.
- Framework POSTs the full result to `callback_url` on completion if provided (webhook-out, with retry).
- `GET /api/v1/runs/{run_id}/report` — fetch HTML/JSON report.
- Auth via simple API key/bearer token (sufficient for a locally-hosted tool).
- Standard CRUD endpoints for projects, environments/packages, test cases (approve/reject), scenario submission, and notifications round out the API.

### 5.g Initial API exploration (new API project/test type)
1. Project (or an existing UI project) adds the `api` test type with at least one environment whose `api` package specifies a spec source (URL or uploaded file) + credentials → Project Manager scaffolds `specs/`, Spec Manager fetches and dereferences the initial spec, writes it as the baseline (no diff — no prior version exists).
2. API Discovery Agent reads the dereferenced spec directly (**LLM-only** — see Section 11.5 for why this isn't a Schemathesis-driven pipeline) and, for every resource it identifies, attempts the **full CRUD-lifecycle-with-verification chain** as its primary pattern (Section 11.5), falling back to simpler single-call tests for resources that don't expose a full CRUD set. Selects upload fixtures from the package for any multipart endpoints it finds (Section 5.j).
3. Structured API test cases (`protocol: "api"`) written to `test_cases/pending/`.
4. Notification Service raises the same in-dashboard "N new test cases pending review" notification — no separate notification path needed.

### 5.h API contract change detection + scoped re-exploration
1. On schedule or trigger, Spec Manager re-fetches the spec for a given environment, dereferences it, hashes it, and diffs against the last pinned version via oasdiff.
2. Severity classification (Section 11.2) drives the same three-way gate as 5.d:
   - `none`/`cosmetic` → no action, spec re-pinned silently (or not re-pinned at all if hash identical).
   - `structural-minor` → existing approved API test cases keep running unchanged (additive changes don't break them); API Discovery Agent is invoked *scoped to only the new/changed operations* to propose additional candidate test cases — joins AI queue, but only for the delta.
   - `structural-major` → affected test cases (those whose `operation_ids` intersect the changed operations) are flagged for healing on next run (5.i) rather than immediately failed outright, since the change might be auto-healable; unaffected test cases continue running normally.
3. New spec version persisted to `specs/<new_hash>/`, `index.json` updated, diff artifact stored alongside.

### 5.i API self-healing flow
1. On step failure (`expected_status` mismatch with a structurally-explainable cause, schema validation failure, or a field-not-found at request-build time), API Healing Engine runs the fallback hierarchy (Section 11.6) against the current spec version and the prior known-good mapping.
2. **Confidence-based decision** — identical structure to 5.e: ≥ threshold auto-patches the test case's field/operation mapping, bumps version, logs `auto_applied: true`; below threshold marks `needs_review` and fails the step for this run with before/after mapping surfaced in-dashboard; no viable candidate flags for regeneration, optionally triggering a scoped Discovery Agent re-run for just that operation.
3. Every attempt appended to the test case's healing log — same file, same shape, just `original_locator` generalizes to `original_mapping` to cover both protocols without diverging the schema.

### 5.j File-upload coverage (UI and API, shared mechanism)
1. Exploration Agent (UI) or API Discovery Agent (API), on encountering a file-input field or a multipart/form-data request body, selects an appropriate fixture from the environment's package `upload_fixtures` — falling back to MAYA's built-in `fixtures/` library by file-type/MIME compatibility if the package doesn't specify one — and generates a test step referencing it by `fixture_ref`.
2. Execution Engine (UI `upload_file` action) or API Test Runner (API `files[]` with `fixture_ref`) resolves `fixture_ref` to an actual file path (`fixtures/` or `<project>/uploads/`) at run time — file bytes are never inlined into the test case JSON.

---

## 6. Concurrency Model

- **Replay-only jobs** (no LLM needed — the `none`/`cosmetic` path in 5.d, or routine API replay with no contract change) run **fully in parallel** across projects, environments, and protocols, each with its own isolated Playwright browser context or independent HTTP calls, since they're just automation with no shared GPU resource contention.
- **Any AI-invoking work** — UI exploration/re-exploration/healing-escalation/scenario interpretation, **and** API discovery/scoped re-discovery/healing-escalation — goes through a **single serialized AI-work queue** owned by the Job Scheduler/Ollama Client, because the 16GB GPU can only realistically run one inference at a time, regardless of which task role or protocol requested it. Jobs queue fairly (FIFO, or priority if needed later) for their AI calls but don't block their non-AI work while waiting.
- This means a busy day with many projects can still get fast replay-only feedback everywhere, while exploration/healing/discovery-heavy work backs up predictably on the GPU queue rather than causing OOM crashes or silently-slow contention.
- File-based storage requires write-locking discipline in the Test Case Store to handle concurrent jobs touching the same project's files safely.

---

## 7. Credential & Sensitive Config Handling

- Dedicated `config/secure/<project_id>.secure.json`, **excluded from git** by default; framework should warn loudly if it detects this path is tracked. This directory is intentionally named generically (not `secrets/`) because other sensitive or environment-specific content beyond credentials lives here too (e.g., API keys for notification adapters, OAuth client secrets for API testing) — the schema is a flexible key-value/document store per project, not hardcoded to just username/password fields.
- Nested by environment, mirroring the package structure in Section 3: `{"dev": {...}, "staging": {...}, "prod": {...}}`. Conceptually, these secrets "live inside the package" for whichever environment/test-type references them, even though they're stored in this separate gitignored file rather than inside `environment.json` itself (keeping sensitive content physically isolated from the git-tracked config tree).
- Test cases/project config reference sensitive values only via placeholders — `${secure.acme-webapp.<environment_id>.username}` — resolved at runtime by Browser Controller/API Client Controller and never written back into persisted files; reports/logs must redact any string matching a known sensitive value.
- Optional stronger mode: encrypt `config/secure/*.json` at rest with a key sourced from an env var or OS keychain (never committed) — keeps the rest of the system file-based/diffable while protecting sensitive content.
- For SSO/2FA-protected apps, support a `sso_manual` auth strategy: one-time manual login with session/cookie capture (Playwright `storage_state`), reused until expiry — flagged as a real limitation, not silently retried.

---

## 8. Logging Subsystem

Three separate, structured, rotating log streams (Python `logging` with rotating handlers — both time- and size-based triggers active, whichever fires first rotates the file):

| Log | Captures |
|---|---|
| **App log** | Component lifecycle, job scheduling decisions, concurrency queue state, project/environment CRUD, errors/exceptions across the framework outside of LLM calls and HTTP traffic specifically. |
| **LLM log** | Every Ollama call: which agent triggered it (Exploration/Scenario Interpreter/Self-Healing/API Discovery/API Healing), which model was auto-selected (Section 1.2) and why, prompt/response size, latency, and outcome — this is the audit trail for AI cost/behavior and is essential for debugging hallucinated steps or slow healing. |
| **API log** | Every REST API request/response *to MAYA's own FastAPI service* (method, path, status, latency, caller — e.g., dashboard vs. CI webhook), separate from app-internal logs so API/CI integration issues are easy to isolate. |

Note the distinction: API Client Controller's HTTP calls *to the target system under test* are not the same thing as the API log above (which captures calls *to MAYA's own* REST API). Target-system call timing and outcomes are captured in run reports (Reporting Engine) and, for unexpected failures, the app log — not conflated with MAYA's own API log.

Rotation policy (both conditions configured, not either/or): rotate when a file exceeds a configured size (e.g., 50MB) **or** when a configured time window elapses (e.g., daily), whichever comes first; retain a configurable number of rotated backups. Logs live under `/framework-data/logs/{app,llm,api}/` and are git-ignored.

---

## 9. Key Risks / Open Questions

- **LLM hallucination in test generation** — mitigated by the mandatory human-approval gate, but unreviewed batch quality at scale needs monitoring; start with small exploration budgets.
- **View-identity false positives/negatives** — the composite structural+URL+heading signal (Section 4) will need iterative, possibly per-project, tuning; getting this wrong either causes spurious re-exploration (cosmetic SPA re-renders treated as structural) or misses real changes (two genuinely different views hashing as the same identity).
- **Combined DOM+vision cost** — calling the multimodal model on every exploration/healing step (rather than vision-as-rare-fallback) means more GPU time per action; combined with the AI-work queue (Section 6), heavy concurrent AI demand across projects could create a visible backlog. Worth surfacing queue depth/wait time in the dashboard so users understand why an AI-heavy job is slow.
- **Concurrency limits on 16GB total RAM** — multiple parallel replay-only browser contexts plus Ollama's own model residency compete for system RAM, not just GPU VRAM; a sensible default cap on simultaneous browser contexts (independent of the AI queue limit) is needed to avoid host-level thrashing.
- **Dynamic content in assertions** — dates, IDs, counters will break naive exact-match assertions. The assertion schema needs typed strategies (`regex_match`, `contains`, `not_empty`, `numeric_range`) from the start, and both the Exploration Agent, Scenario Interpreter, and API Discovery Agent should prefer these when they detect likely-dynamic content.
- **CAPTCHA/2FA** — blocks full automation; the manual-session-capture workaround is partial and sessions expire — surface this clearly per project rather than silently failing.
- **Healing drift** — repeated auto-heals could quietly drift a test away from its original intent (heals to a visually-similar but wrong element, or a plausible-but-wrong field mapping). Consider periodic "re-confirm" prompts after N accumulated heals on the same test case.
- **Scenario Interpreter getting stuck** — a business scenario that doesn't match how the app actually works (wrong terminology, a flow that doesn't exist) needs a clear "I couldn't complete this, here's where I got stuck and why" report back to the user rather than silently producing a wrong or partial test case.
- **Exploration coverage vs. cost** — budget caps are a blunt instrument; "good enough coverage" will likely need empirical, per-app tuning rather than a fixed default.
- **Stateful cross-endpoint sequencing is a generation challenge, not just an execution one** — the API Discovery Agent must infer flows (e.g. `POST /orders` → `GET /orders/{id}` → `DELETE /orders/{id}`) from naming/schema-overlap heuristics alone, since exploration is LLM-only with no Schemathesis-driven scaffolding; it can guess wrong on ambiguous schemas (two different `id` fields that aren't actually related). Mitigate by always surfacing inferred `extract`/`inject` linkage explicitly in the dashboard at approval time, not just the raw steps.
- **Spec drift between documented and deployed behavior** — oasdiff only catches changes to the spec file itself; a deployed API can silently diverge from its own documented spec. Mitigate by running `openapi-core` response-schema validation as a standing runtime assertion on every replay, not just at discovery time, so undocumented breaks still surface as ordinary assertion failures even when the spec hash hasn't moved.
- **Environment-specific behavior differences causing false-positive contract changes** — feature flags, environment-specific middleware, or partial rollouts can make dev/staging/prod genuinely answer the same operation differently even on identical spec versions. Mitigate by keeping spec snapshots and healing history strictly environment-scoped (Section 3) and treating cross-environment behavioral mismatches as a distinct, explicitly labeled finding rather than folding them into ordinary spec-diff severity.
- **Destructive test side effects on shared environments** — a test case that legitimately exercises `POST`/`PUT`/`DELETE` against a shared staging environment can corrupt state for other concurrent test runs or real users of that environment. Mitigate via the `is_destructive_safe` environment flag (Section 3): environments not marked safe should default destructive API test cases to a sandboxed/cleanup-wrapped execution mode (e.g., automatic compensating `DELETE` after a `POST` in the same test case); flagged as needing a concrete cleanup-strategy decision before any destructive API testing is enabled against a shared environment, not something the framework can fully solve generically.
- **Built-in fixtures may not satisfy app-specific upload validation** — a built-in `sample.pdf` might fail an app's content-specific validation (e.g. a resume parser expecting real resume-shaped text, an image dimension minimum). Mitigate by treating built-in fixtures as a baseline-coverage default only; the Discovery/Exploration agents should flag (not silently pass/fail) upload steps where the response suggests content-based rejection, prompting the user to supply a project-specific fixture via the package.
- **Adapter abstraction overhead vs. flexibility tradeoff** — a formal interface per tool category (Section 2.1) adds a layer of indirection that could leak tool-specific concepts anyway if not designed carefully (e.g. Playwright-specific `Locator` objects escaping `BrowserDriver`'s otherwise-generic interface). Flag this as a design discipline risk to watch during implementation, not a blocker now.

---

## 10. Verification Plan (once implementation begins)

- Stand up Ollama locally with Qwen2.5-VL (7B and 3B) and Qwen2.5 7B-Instruct pulled; verify combined DOM+screenshot tool-calling works against a simple test page, and verify text-only API reasoning works against a simple spec, before pointing at a real app/API.
- Build against a small, deliberately imperfect demo web app **and** a demo API with an OpenAPI spec — including at least one SPA-style view change with no URL change, a couple of dynamic-content fields, and at least one resource exposing a full CRUD set — to exercise exploration, scenario interpretation, API discovery, approval, replay, change-detection gating (both view-identity and spec-diff), and self-healing (both UI and API) end-to-end before trying a real target.
- Validate the view-diff gate by making a no-op run (expect zero LLM calls) vs. a structural-change run (expect scoped re-exploration only) — this is the core cost-saving mechanism and should be the first thing proven. Validate the spec-diff gate analogously: an unchanged spec triggers zero AI-queue calls; an additive-only spec change triggers scoped discovery only for the new surface.
- Validate the concurrency model by running several replay-only jobs simultaneously alongside one AI-invoking job, confirming replay jobs aren't blocked by the AI queue and the AI queue serializes correctly across both UI and API task roles without GPU OOM.
- Exercise the webhook API contract with a real CI system (e.g., a GitHub Actions job) calling `POST /runs` with an explicit `environment` and polling/receiving a callback, to confirm the integration story holds up outside local dev.
- Confirm log rotation actually triggers on both size and time thresholds, and that app/LLM/API logs are cleanly separated and readable independently.
- Verify a single project can run both a UI suite and an API suite against the same environment set, with shared environment credentials resolving correctly into each test-type's package without cross-contamination.
- Verify file-upload coverage end-to-end: a UI file-input field and an API multipart endpoint both resolve `fixture_ref` correctly from both the built-in `fixtures/` library and a project-supplied `uploads/` file.
- Verify the adapter layer's swappability claim concretely for at least one category before broader implementation: write a second, trivial `LLMClient` adapter (even a stub) and confirm no call site outside the adapter module needs to change.
- Exercise a multi-environment run against a demo API with two environments pinned to two different spec versions, confirming environment-scoped spec/healing isolation (a heal applied in one environment must not appear in or affect the other).

---

## 11. API Testing via OpenAPI/Swagger

This section maps every UI testing concept onto its API equivalent, reusing the shared infrastructure described in Sections 1, 2, 6, 7, 8 rather than duplicating it.

### 11.1 Concept mapping (UI → API)

| UI concept | API equivalent |
|---|---|
| View identity (URL + structural fingerprint + heading) | **Operation identity** = `operationId` if the spec defines one, else `method + path template` (e.g., `GET /orders/{id}`) — path *templates*, not resolved paths, so the identity is stable regardless of which id is exercised |
| View snapshot & diff (page hash, severity classification) | **Spec snapshot & diff**, powered by oasdiff — severity reuses the existing none/cosmetic/structural-minor/structural-major vocabulary (Section 11.2) |
| Exploration Agent | **API Discovery Agent** — reads the spec directly (LLM-only, see 11.5) rather than perceiving DOM+screenshot |
| Self-Healing Engine (locator fallback hierarchy) | **API Healing Engine** (contract-fallback hierarchy, Section 11.6) |
| Execution Engine / Step Runner (Playwright-driven) | **API Test Runner** (httpx-driven, via `HTTPClient`) |
| Browser Controller | **API Client Controller** (sibling component, not an overload — Section 2.3) |
| Locator (`strategy`/`value`) | Field/parameter mapping (`location`, `name`, `type`) |

No "composite signal" is needed for operation identity the way view identity needs URL+structure+heading combined — the spec already provides a clean, stable identifier.

### 11.2 Spec diff severity mapping

| Severity | oasdiff classification | Examples |
|---|---|---|
| `none` | No diff detected (spec hash unchanged after dereferencing) | Re-fetch is byte- or semantically-identical |
| `cosmetic` | Non-breaking, no schema/contract impact | Description/summary text changes, examples added/changed, tag reorganization, deprecation marker added |
| `structural-minor` | Non-breaking, additive | New optional field, new optional query/header param, new response field, new enum value added, new endpoint added |
| `structural-major` | Breaking | Removed endpoint, new required field/param, removed required response field, type change on an existing field, enum value removed, auth scheme removed/changed, path parameter renamed |

### 11.3 API test case schema

```json
{
  "id": "tc_8f2a...",
  "protocol": "api",
  "status": "pending",
  "created_by": "api_discovery_agent",
  "source_scenario_ref": null,
  "tags": ["orders", "crud-flow"],
  "operation_ids": ["createOrder", "getOrder", "updateOrder", "deleteOrder"],
  "spec_version_ref": "v2.3.1",
  "steps": [
    {
      "step_id": "s1",
      "operation_id": "createOrder",
      "method": "POST",
      "path": "/orders",
      "headers": { "Content-Type": "application/json" },
      "body": { "sku": "WIDGET-1", "quantity": 2 },
      "expected_status": 201,
      "expected_schema_ref": "#/components/schemas/Order",
      "extract": { "order_id": "$.body.id" },
      "assertions": [
        { "type": "schema_match" },
        { "type": "field_equals", "path": "$.body.status", "value": "created" }
      ]
    },
    {
      "step_id": "s2",
      "operation_id": "getOrder",
      "method": "GET",
      "path": "/orders/{order_id}",
      "path_params": { "order_id": "${steps.s1.order_id}" },
      "expected_status": 200,
      "assertions": [{ "type": "field_equals", "path": "$.body.id", "value": "${steps.s1.order_id}" }]
    },
    {
      "step_id": "s3",
      "operation_id": "updateOrder",
      "method": "PUT",
      "path": "/orders/{order_id}",
      "path_params": { "order_id": "${steps.s1.order_id}" },
      "body": { "quantity": 5 },
      "expected_status": 200
    },
    {
      "step_id": "s4",
      "operation_id": "getOrder",
      "method": "GET",
      "path": "/orders/{order_id}",
      "path_params": { "order_id": "${steps.s1.order_id}" },
      "expected_status": 200,
      "assertions": [{ "type": "field_equals", "path": "$.body.quantity", "value": 5 }]
    },
    {
      "step_id": "s5",
      "operation_id": "deleteOrder",
      "method": "DELETE",
      "path": "/orders/{order_id}",
      "path_params": { "order_id": "${steps.s1.order_id}" },
      "expected_status": 204
    },
    {
      "step_id": "s6",
      "operation_id": "getOrder",
      "method": "GET",
      "path": "/orders/{order_id}",
      "path_params": { "order_id": "${steps.s1.order_id}" },
      "expected_status": 404
    }
  ],
  "healing_history_ref": "tc_8f2a..._healing.json",
  "field_mapping_confidence": 1.0,
  "last_run_status": "passed",
  "last_execution_time_ms": 412
}
```

This worked example is the **steered default shape** (Section 11.5) — create, verify created, update, verify updated, delete, verify deleted — not just one possible flow among many. A multipart upload step uses `body_type: "multipart"` and `files: [{"field": "attachment", "fixture_ref": "builtin:sample.pdf"}]` in place of `body`.

The `${steps.s1.order_id}` interpolation mirrors the existing `${secure....}` placeholder grammar (Section 7) — same resolution mechanism, different namespace, shared resolver in the API Test Runner. Top-level fields (`id`, `status`, `created_by`, `tags`, `healing_history_ref`, `last_run_status`, `last_execution_time_ms`) are unchanged from the UI schema; only `view_identity` → `operation_ids` and `locator_confidence` → `field_mapping_confidence` are protocol-specific renames.

### 11.4 File layout

Covered in Section 3.3 — `environments/<environment_id>/specs/` parallels `view_snapshots/<view_identity_slug>/` in intent: versioned history of the thing being tested against, scoped per environment because different environments can legitimately pin different spec versions (staging on v2.3.1 while prod is still on v2.2.0 mid-rollout is a normal, expected state).

### 11.5 API Discovery Agent: LLM-only exploration, steered toward CRUD-lifecycle flows

**Exploration is LLM-only** — the API Discovery Agent reads the dereferenced spec directly and proposes all test cases itself. Schemathesis, if used at all, is an optional internal helper for request-data generation, not the primary coverage mechanism; this keeps the API flow conceptually parallel to UI exploration (one LLM-driven agent reasoning over the available surface) rather than splitting coverage between a deterministic fuzzer and an LLM sequencer.

**Steered default pattern**: for every resource the Discovery Agent identifies in the spec (a resource = a path template family like `/orders`, `/orders/{id}`), its **primary search** is the full CRUD-lifecycle-with-verification chain:

`POST` (create) → `GET` (verify created — assert returned fields match what was sent) → `PUT`/`PATCH` (update) → `GET` (verify updated) → `DELETE` → `GET` (verify deleted, typically expecting `404`)

This is steered as the default the agent looks for first, not one inferred possibility among many — it falls back to simpler single-call or partial-chain tests only when a resource doesn't expose the full set of operations (e.g. a read-only reporting endpoint with no `POST`/`PUT`/`DELETE`). It uses the existing `extract`/`inject` step-chaining mechanism (Section 11.3) to thread the created entity's id through every subsequent step.

Beyond the CRUD-lifecycle pattern, the Discovery Agent also:
- **Authors assertions beyond schema validation** — schema conformance is necessary but not sufficient (e.g., a `DELETE` followed by `GET` should now 404; a `POST` with an implausible value should plausibly be rejected even if the schema doesn't say so).
- **Consumes the package's optional free-text instructions** — analogous to how Scenario Interpreter consumes free-text for UI, the Discovery Agent cross-references the package's `instructions` field (Section 3.4) against the spec to scope or steer proposed test cases (e.g. "treat `/internal/*` as out of scope").
- **Selects upload fixtures** for multipart endpoints from the package's `upload_fixtures`, falling back to built-ins (Section 5.j).

**Output**: structured JSON test cases written to the same `test_cases/pending/` store, `protocol: "api"`, same approval lifecycle as UI test cases (5.c is reused verbatim).

This agent does not need vision and does not need DOM/screenshot grounding — see Section 1.1 for why it runs on a separate text-only model (`Qwen2.5 7B-Instruct`) rather than the multimodal model used for UI work.

### 11.6 API Healing Engine — fallback hierarchy

Directly analogous structure to the UI locator hierarchy, same confidence-threshold auto-apply/flag pattern as 5.e:

| Order | Strategy | Triggers when |
|---|---|---|
| 1 | **Exact field/param match** | Default — field/param name unchanged in new spec. Confidence 1.0, not really a "heal." |
| 2 | **Fuzzy name match (Levenshtein)** | Field renamed but similar (`order_id` → `orderId`, `orderID`). High confidence if distance is small and type matches. |
| 3 | **Type-compatible positional match** | Field renamed beyond fuzzy-match similarity but occupies the same schema position/role — lower confidence, needs corroborating signal. |
| 4 | **operationId/tag/summary match for path changes** | Path itself changed (`/orders/{id}` → `/v2/orders/{orderId}`) but `operationId` or tag/summary text matches closely — re-binds the test case's operation reference, not just a field. |
| 5 | **Auth scheme migration** | oasdiff flags an auth scheme change (e.g., API key header → bearer token) — attempt automatic credential-shape migration using the per-environment package's available fields before failing. |
| 6 (last resort) | **LLM semantic field remapping** | None of the above resolve with sufficient confidence — the API Discovery Agent's model is invoked with old schema + new schema + the test case's intent (from its assertions/tags) to propose a remapping. Only tier touching the AI queue. |

Same default 0.90 auto-apply threshold and `needs_review`/before-after-mapping-surfaced pattern as 5.e. Param **relocation** (query param moved to body, or vice versa) is detected directly from oasdiff's structured diff output (it reports parameter `in` changes explicitly) and handled within tier 3/4 rather than needing fuzzy inference.

Upload-capable (multipart) endpoints are covered by the same fixture mechanism as UI testing — see Section 5.j.
