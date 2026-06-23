# 08 — F7 — UI Execution Engine (Deterministic Replay) + run/report UI

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Consumes `approved/` test cases (F6) and replays them; must exist and be able to fail before Self-Healing (F9) has anything to react to. Gains its run-trigger and report-viewer screen.

---

## F7 — UI Execution Engine (Deterministic Replay) + run/report UI

### Story F7.S1 — Step interpreter

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F7-010 | Implement `ExecutionEngine.run_test_case(tc)` — resolve locator, perform action, evaluate assertion | F7.S1 | F7 | F2-070, F1-030 | Integration test: replay an approved test case from F6 against the demo page, assert pass | Not Started |
| F7-020 | Implement assertion types: `equals`/`contains`/`not_empty`/`regex_match` | F7.S1 | F7 | F7-010 | Unit test: each assertion type evaluates correctly on sample actual/expected pairs | Not Started |
| F7-030 | Implement screenshot-on-failure capture | F7.S1 | F7 | F7-010, F2-080 | Integration test: force a failing step, assert a screenshot file is written and referenced in the result | Not Started |
| F7-040 | Implement per-step and per-test-case timing capture into `RunSummary` (F1-040) | F7.S1 | F7 | F7-010, F1-040 | Integration test: run a test case, assert `execution_time_ms` is recorded and plausible | Not Started |
| F7-050 | Manual/integration test: run an approved test case, confirm pass + timing; break a locator, confirm clean failure with screenshot (no healing yet) | F7.S1 | F7 | F7-040, F7-030, F6-040 | Integration test: both the happy path and the intentional-break path behave as described | Not Started |

**F7-010 — How to build it**: `src/maya/engines/execution_engine.py`, class `ExecutionEngine(driver: BrowserDriver)` with `run_test_case(tc: UITestCase) -> TestCaseResult` iterating `tc.steps`, resolving each `step.target` (the same `Locator` resolution logic introduced in F2-070) and calling the matching `driver` method (`click`/`type`/`upload_file`/etc), then evaluating `step.assertion` if present. No healing logic here yet — failures just propagate as a result status for now (F9 hooks in later without changing this method's core shape, only wrapping the failure path). (see plan.md §2.3 Execution Engine row)

**F7-020 — How to build it**: `src/maya/engines/assertions.py`, a small dispatch dict/function `evaluate_assertion(type: str, actual, expected) -> bool` covering the four MVP types named in plan.md §9's dynamic-content risk note — this is intentionally a small starting set, with the full typed-strategy set (numeric_range, etc.) coming later if needed. (see plan.md §9 "Dynamic content in assertions")

**F7-030 — How to build it**: In `run_test_case`'s per-step loop, wrap each action+assertion in a try/except (or check a boolean result) — on failure, call `driver.screenshot()` (F2-080) and persist it to the active run's `runs/run_<ts>_<uuid>/screenshots/` directory, storing the relative path on the step result. (see plan.md §2.3: "captures screenshots on failure")

**F7-040 — How to build it**: Wrap each step in a `time.perf_counter()` timer summed into a per-test-case `execution_time_ms`, attached to the `RunSummary.results[]` entry (F1-040) for this test case. This is the metric plan.md repeatedly calls out as required on every run. (see plan.md §3, §11.3)

**F7-050 — How to build it**: `tests/engines/test_execution_engine.py` — take the test case approved in `F6-040`, run it via `ExecutionEngine`, assert pass + timing recorded; then mutate the demo page's button `data-testid` (or point the test case's locator at a nonexistent one) and re-run, asserting a clean `locator_not_found`-style failure with a screenshot path populated and no auto-recovery (since F9 doesn't exist yet).

### Story F7.S2 — Run orchestration & report shell

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F7-060 | Implement `RunOrchestrator` loading all approved test cases for a project+environment, running each, aggregating into `run_summary.json` | F7.S2 | F7 | F7-050 | Integration test: run against a project with 2+ approved test cases, assert one aggregated run_summary with both results | Not Started |
| F7-070 | Implement minimal JSON-only run report writer to `environments/<env>/runs/run_<ts>_<uuid>/run_summary.json` | F7.S2 | F7 | F7-060, F1-080 | Manual file inspection: open the written file, confirm shape matches F1-040's `RunSummary` model | Not Started |
| F7-080 | Manual test: trigger a run against a project with 2+ approved test cases, inspect run_summary.json for correct timing | F7.S2 | F7 | F7-070 | Manual file inspection: per-test and total_job_time_ms both present and plausible | Not Started |

**F7-060 — How to build it**: `src/maya/runners/run_orchestrator.py`, function/class `RunOrchestrator.run(project_id, environment_id)` calling `TestCaseStore.list("approved")` scoped to the project, running each via `ExecutionEngine` (F7-010), and summing into a `RunSummary` (F1-040) with `total_job_time_ms` = sum of all `results[].execution_time_ms`. This is the function F8-040 will modify to add the diff-gate branching, and F13-010 will call from the REST trigger. (see plan.md §2.3 row, §5.d steps 2-5)

**F7-070 — How to build it**: After `RunOrchestrator.run()` completes, serialize the resulting `RunSummary` via its pydantic `model_dump_json()` to `environments/<env_id>/runs/run_<timestamp>_<uuid4>/run_summary.json`, creating the directory first. HTML rendering (`report.html`) is explicitly deferred — F7 only needs the JSON source-of-truth; an HTML view can be added in the F7.S3 UI story below directly from the frontend rather than server-rendered. (see plan.md §3.3 file layout)

**F7-080 — How to build it**: Manual test script: approve two test cases from `F6-040`'s flow (or hand-craft a second simple one), call `RunOrchestrator.run()`, open the resulting `run_summary.json`, and visually confirm both test cases' `execution_time_ms` and the top-level `total_job_time_ms` are present and sane (not zero, not absurdly large).

### Story F7.S3 — Run trigger + report viewer UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F7-090 | Add a minimal `POST /projects/{id}/runs` + `GET /runs/{run_id}` API (synchronous, no job queue yet — F12/F13 add the async/webhook version later) | F7.S3 | F7 | F7-080, F0-050 | Integration test: POST a run trigger, GET it back, confirm the run_summary content matches | Not Started |
| F7-100 | Build a "Run Now" button on the project detail screen and a basic report viewer (per-test pass/fail + timing table) | F7.S3 | F7 | F7-090, F3-130 | Manual UI walkthrough: click Run Now, see the report render with correct pass/fail and timing per test case | Not Started |

**F7-090 — How to build it**: `src/maya/api/routers/runs.py`, a *minimal* synchronous version for now: `POST /api/v1/projects/{id}/runs?environment=<env_id>` directly calls `RunOrchestrator.run()` and returns the `RunSummary` inline (blocking) — this gets replaced/extended with async job dispatch in F12-050/F13-010 once the scheduler exists; building the synchronous version now is what makes F7 demoable end-to-end through the UI without waiting on F12/F13. `GET /api/v1/runs/{run_id}` reads the persisted `run_summary.json` back by id. (see plan.md §5.f, but note this task is intentionally the *simple* precursor to that full contract)

**F7-100 — How to build it**: On `ProjectDetail.tsx` (from F3-130), add a "Run Now" button (with an environment selector dropdown) calling `F7-090`'s POST endpoint; on response, navigate to a new `RunReport.tsx` page rendering `results[]` as an MUI `Table` (test case id, status, execution_time_ms) plus the `total_job_time_ms` total at the top. Wire into the `/runs` route placeholder from F0-090.
