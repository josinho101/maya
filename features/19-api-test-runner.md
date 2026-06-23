# 19 — F19 — API Test Runner (Deterministic Replay)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: The API analog of F7; needs F18's approved test cases and F16's HTTPClient. Must exist and be able to fail before API Healing (F21) has anything to react to.

---

## F19 — API Test Runner (Deterministic Replay)

### Story F19.S1 — Step interpreter

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F19-010 | Implement `APITestRunner.run_test_case(tc)` — resolve extract/inject threading across steps, build requests, issue via HTTPClient | F19.S1 | F19 | F16-020, F3-070, F18-060 | Integration test: replay the approved CRUD chain from F18-090, assert each step's request is built with correctly threaded values | Not Started |
| F19-020 | Implement assertion evaluators: schema_match (via F16-080), field_equals/contains/regex_match/numeric_range | F19.S1 | F19 | F19-010, F16-080 | Unit test: each assertion type evaluates correctly on sample response payloads | Not Started |
| F19-030 | Implement multipart files[]/fixture_ref step support reusing F16-030 | F19.S1 | F19 | F19-010, F16-030 | Integration test: replay a multipart step against the demo API's attachment endpoint, assert successful upload | Not Started |
| F19-040 | Implement per-step/per-test-case timing capture into the same RunSummary shape as F7-040 | F19.S1 | F19 | F19-010, F1-040 | Integration test: replay the chain, assert execution_time_ms recorded per step and per test case | Not Started |
| F19-050 | Manual test: replay the approved CRUD-chain test case against the demo API; confirm full pass with correct id-threading and timing; then break a field name and confirm clean failure (no healing yet) | F19.S1 | F19 | F19-040, F19-020, F18-090 | Integration test: happy path passes fully; intentional field-name break produces a clean, unhandled failure | Not Started |

**F19-010 — How to build it**: `src/maya/engines/api_test_runner.py`, class `APITestRunner(http: HTTPClient)` with `run_test_case(tc: APITestCase) -> TestCaseResult` iterating `tc.steps`, resolving `${steps.s1.order_id}`-style placeholders (reuse `F3-070`'s `resolve_placeholder()` pure function/grammar, extended with a `steps` namespace alongside the existing `secure` namespace — same regex-substitution approach, different lookup source) using values captured via each step's `extract` JSONPath-like expressions, then calling `http.request(...)` (F16-020) to build and issue the actual HTTP call. (see plan.md §2.3 API Test Runner row, §11.3 closing paragraph on the shared resolver grammar)

**F19-020 — How to build it**: `src/maya/engines/api_assertions.py` (sibling to F7-020's UI assertions module) — `schema_match` calls into `F16-080`'s `validate_response()`; `field_equals`/`contains`/`regex_match` extract a value via the assertion's `path` (a simple JSONPath subset is sufficient) and compare; `numeric_range` checks a numeric field falls within bounds. (see plan.md §11.3 example assertions, §9 dynamic-content risk note extended to API)

**F19-030 — How to build it**: When a step has `body_type: "multipart"` and a `files[]` array, route the request through `HTTPXAdapter`'s multipart path (F16-030) instead of the plain JSON body path, resolving each file's `fixture_ref` the same way `F11-040` does for UI uploads — same resolver, same fixture library, just invoked from the API runner instead of the Execution Engine. (see plan.md §11.3 closing paragraph: "A multipart upload step uses body_type: multipart")

**F19-040 — How to build it**: Wrap each step's HTTP call in a timer exactly as `F7-040` does for UI steps, summing into the same `RunSummary.results[]` shape (F1-040) — this is intentionally the *same* model and the *same* aggregation logic as the UI side, so F19-060 below can feed both protocols' results into one unified run report. (see plan.md §3, §11.3)

**F19-050 — How to build it**: Manual/scripted test: replay the test case approved in `F18-090` against the live `F16-040` demo API, assert all 6 steps pass with the order id correctly threaded through every `path_params` reference and timing populated; then rename a field in the demo API's response model (e.g. `status` → `order_status`) and re-run, confirming a clean, unrecovered failure on the affected `field_equals` assertion step (no healing exists yet — F21 adds that). (see plan.md §10: similar in spirit to the UI F7-050 "intentionally break" verification)

### Story F19.S2 — Run orchestration extension

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F19-060 | Extend RunOrchestrator to dispatch protocol:"api" test cases through APITestRunner instead of ExecutionEngine, grouped by operation_ids instead of view_identity | F19.S2 | F19 | F19-050, F8-040 | Integration test: a run against a project with only api test cases correctly uses APITestRunner end to end | Not Started |
| F19-070 | Manual test: trigger a run with both UI and API approved test cases, confirm both protocols execute and contribute to one run_summary.json | F19.S2 | F19 | F19-060 | Manual file inspection: one run_summary.json with results[] entries from both protocols, correctly attributed | Not Started |

**F19-060 — How to build it**: In `RunOrchestrator.run()` (F7-060/F8-040), branch on `test_case.protocol`: `"ui"` routes to `ExecutionEngine` as before (grouped by `view_identity` for the diff-gate logic), `"api"` routes to the new `APITestRunner` (F19-010), grouped by `operation_ids` instead (the change-detection gating for API, F20, plugs in here analogously to how F8-040 plugs into the UI path — but F19-060 itself doesn't need the gate yet, just correct dispatch). (see plan.md §11.1 concept mapping table)

**F19-070 — How to build it**: Manual test using the project from `F17-040` (which now has both a `ui` and `api` package on the same environment, with approved test cases of both protocols) — trigger one run via `F7-090`'s endpoint, and confirm the resulting `run_summary.json`'s `results[]` array contains correctly-attributed entries for both the UI test case (from F6/F7) and the API test case (from F18/F19), with `total_job_time_ms` summing across both. (see plan.md §10: "Verify a single project can run both a UI suite and an API suite against the same environment set")
