# 03 — F2 — Adapter Layer Foundations (LLM + Browser) + minimal logging

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Every later agent/engine depends on `LLMClient`/`OllamaAdapter` and `BrowserDriver`/`PlaywrightAdapter` existing behind formal interfaces — the architecture's explicit swappability spine. Minimal 3-stream logging is added here too, so LLM calls are auditable from the very first call onward.

---

## F2 — Adapter Layer Foundations (LLM + Browser) + minimal logging

### Story F2.S1 — LLMClient interface + OllamaAdapter

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F2-010 | Define `LLMClient` Protocol/ABC: `generate(prompt, images=None, tools=None) -> response` | F2.S1 | F2 | F0-020 | Unit test: a trivial stub implementation satisfies the Protocol via `isinstance`/structural check | Not Started |
| F2-020 | Implement `OllamaAdapter` calling local Ollama REST API for text-only generation | F2.S1 | F2 | F2-010, F0-070 | Integration test: call `generate("say hello")` against local Ollama, assert non-empty response | Not Started |
| F2-030 | Extend `OllamaAdapter` to accept image input (multimodal `qwen2.5-vl`) | F2.S1 | F2 | F2-020 | Integration test: call `generate(prompt, images=[png_bytes])`, assert response references image content | Not Started |
| F2-040 | Implement model-selection policy stub: ranked preference list per task role read from `global_config.json`, static selection (no load-based downgrade yet) | F2.S1 | F2 | F2-020, F1-010 | Unit test: given a task role string, the adapter selects the first model in that role's configured list | Not Started |
| F2-050 | Integration test: call `LLMClient.generate()` with text-only and (prompt+screenshot) pairs against running Ollama | F2.S1 | F2 | F2-030, F2-040 | Integration test: both calls return well-formed, non-empty responses | Not Started |

**F2-010 — How to build it**: `src/maya/adapters/llm_client.py`, a `typing.Protocol` (or `abc.ABC`) named `LLMClient` with one abstract method `generate(self, prompt: str, images: list[bytes] | None = None, tools: list[dict] | None = None) -> LLMResponse`. Every later agent (F5, F9, F10, F18, F21) depends on this interface only, never on Ollama's SDK/REST API directly — this is the swap point referenced by the F23-090 verification task later. (see plan.md §2.1 adapter table, §1.3)

**F2-020 — How to build it**: `src/maya/adapters/ollama_adapter.py`, class `OllamaAdapter` implementing `LLMClient` by POSTing to `http://localhost:11434/api/generate` (or `/api/chat`) using `httpx`. Keep the HTTP call itself simple at this stage — error handling for OOM/timeout comes later (F2's model-selection policy in F2-040 only needs the *interface* to exist now). (see plan.md §1.3)

**F2-030 — How to build it**: Extend the same adapter's `generate()` to base64-encode any `images` bytes and include them in the Ollama chat payload's multimodal message format (Ollama's `/api/chat` supports an `images` field per message). This is what lets F5's Exploration Agent send AX-tree-as-text + screenshot in one call. (see plan.md §1.1)

**F2-040 — How to build it**: Add a `model_preferences: dict[str, list[str]]` section to `global_config.json` (e.g. `{"ui_explore_heal": ["qwen2.5-vl:7b", "qwen2.5-vl:3b"], "api_reasoning": ["qwen2.5:7b-instruct"]}`), loaded by `OllamaAdapter.__init__`. Add a `generate(..., task_role: str)` parameter that picks `model_preferences[task_role][0]` for now — VRAM/load-based downgrade logic is explicitly deferred (plan.md §1.2 frames this as the *eventual* behavior, not MVP). (see plan.md §1.2, §1.3)

**F2-050 — How to build it**: `tests/adapters/test_ollama_adapter.py` (marked as an integration test requiring a live Ollama, e.g. via a pytest marker skipped in CI without Ollama running) — one call with `task_role="api_reasoning"` text-only, one call with `task_role="ui_explore_heal"` plus a real screenshot PNG loaded from a fixture file.

### Story F2.S2 — BrowserDriver interface + PlaywrightAdapter

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F2-060 | Define `BrowserDriver` Protocol/ABC: `navigate`, `click`, `type`, `get_ax_tree`, `screenshot`, `get_dom_html`, `upload_file`, session/storage-state handling | F2.S2 | F2 | F0-020 | Unit test: a trivial stub implementation satisfies the Protocol | Not Started |
| F2-070 | Implement `PlaywrightAdapter.navigate/click/type` against a real Playwright browser | F2.S2 | F2 | F2-060 | Integration test: navigate to a local file URL, click a button, type into a field, assert resulting DOM state | Not Started |
| F2-080 | Implement `PlaywrightAdapter.get_ax_tree()` and `screenshot()` | F2.S2 | F2 | F2-070 | Integration test: assert AX-tree includes expected roles/names; screenshot file is written and non-empty | Not Started |
| F2-090 | Implement `PlaywrightAdapter.get_dom_html()` and `upload_file()` | F2.S2 | F2 | F2-080 | Integration test: assert HTML contains expected markup; file upload via native dialog handling succeeds | Not Started |
| F2-100 | Implement session/storage-state persistence (login cookie reuse) | F2.S2 | F2 | F2-090 | Integration test: log in once, save storage state, start a new context loading that state, assert still authenticated | Not Started |
| F2-110 | Build a tiny static demo HTML page (login form + button + file input) as the integration target for all later UI tasks | F2.S2 | F2 | — | Manual: open the page in a browser, confirm all three elements render and are interactive | Not Started |
| F2-120 | Integration test: drive `PlaywrightAdapter` against F2-110's demo page end-to-end | F2.S2 | F2 | F2-100, F2-110 | Integration test: navigate, click, type, screenshot, get_ax_tree, upload_file all succeed against the demo page | Not Started |

**F2-060 — How to build it**: `src/maya/adapters/browser_driver.py`, a Protocol `BrowserDriver` with methods matching plan.md §2.3's Browser Controller responsibility list: `navigate(url)`, `click(locator)`, `type(locator, text)`, `get_ax_tree() -> dict`, `screenshot() -> bytes`, `get_dom_html() -> str`, `upload_file(locator, file_path)`, `save_storage_state(path)`/`load_storage_state(path)`. Define a simple `Locator` dataclass (`strategy`, `value`) here too, shared by Execution Engine (F7) and Self-Healing (F9). (see plan.md §2.1, §2.3)

**F2-070 — How to build it**: `src/maya/adapters/playwright_adapter.py`, class `PlaywrightAdapter` wrapping a `playwright.sync_api` (or async, pick one consistently — sync is simpler for the agent loop's sequential nature) `Browser`/`Page`. Implement `navigate` as `page.goto(url)`, `click`/`type` resolving the `Locator` to a Playwright locator via strategy (`data-testid` → `page.get_by_test_id()`, `role` → `page.get_by_role()`, etc — this resolution function is reused again in F9's healing hierarchy). (see plan.md §2.3)

**F2-080 — How to build it**: `get_ax_tree()` uses Playwright's `page.accessibility.snapshot()`, returning the raw tree (later normalized by F4-010's structural fingerprint function). `screenshot()` uses `page.screenshot(path=...)` or returns raw bytes — pick bytes-returning so callers (F4, F5, F9) decide persistence. (see plan.md §2.3, §4)

**F2-090 — How to build it**: `get_dom_html()` is `page.content()`. `upload_file()` uses Playwright's `page.set_input_files(locator, file_path)` which handles the native OS file dialog without needing real dialog automation — this is the mechanism F11's `fixture_ref` resolution ultimately calls into. (see plan.md §2.3)

**F2-100 — How to build it**: Use Playwright's `browser_context.storage_state(path=...)` to dump cookies/localStorage after a successful login, and `browser.new_context(storage_state=path)` to restore it on a later run — this is what F5-030 calls to avoid re-logging-in on every exploration run. (see plan.md §2.3, §7 "sso_manual" note for the related but distinct manual-session case)

**F2-110 — How to build it**: A single static `tests/fixtures/demo_app/index.html` (no server needed — `file://` URL is fine for Playwright) with a `<form>` (username/password inputs + submit button with a `data-testid="login-button"`), a counter `<button>` elsewhere on the page, and a `<input type="file">`. Keep it intentionally simple now; F8-040/F9-100 will later need a *second* demo page or a modal/tab to exercise SPA-style view changes — note that as a follow-up, don't over-build this page now.

**F2-120 — How to build it**: `tests/adapters/test_playwright_adapter_integration.py` chaining all the above calls against `F2-110`'s page in one test, asserting each step's expected effect (e.g., after `type()` into the username field, `get_dom_html()` contains the typed value).

### Story F2.S3 — Minimal logging setup

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F2-130 | Configure basic Python `logging` with three named loggers (app/llm/api), console + file handlers, no rotation yet | F2.S3 | F2 | F0-010 | Manual: trigger one log call per logger, confirm three separate files under `framework-data/logs/{app,llm,api}/` | Not Started |
| F2-140 | Instrument `OllamaAdapter` calls to log to the `llm` logger (agent name, model used, latency, outcome) | F2.S3 | F2 | F2-130, F2-050 | Manual: call `generate()`, inspect the llm log file for a structured entry with all expected fields | Not Started |

**F2-130 — How to build it**: `src/maya/logging_setup.py`, a `configure_logging(root_dir)` function creating three `logging.Logger` instances (`maya.app`, `maya.llm`, `maya.api`) each with a `FileHandler` pointed at `framework-data/logs/{app,llm,api}/<name>.log` plus a shared console handler for dev visibility. Call this once at FastAPI app startup (`F0-050`'s `main.py`). Full rotating-handler upgrade is explicitly deferred to F14. (see plan.md §8)

**F2-140 — How to build it**: Wrap `OllamaAdapter.generate()` with a `time.perf_counter()` timer and a `logger.info(...)` call after the response returns, logging a structured (JSON-formatted log line, or key=value) entry: which agent/task_role triggered it, which model was selected (from F2-040), prompt/response sizes, latency_ms, outcome (success/error). This is the audit trail every later "zero LLM calls" verification task (F8-050, F20-050, F12-060) inspects. (see plan.md §8 LLM log row)
