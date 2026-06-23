# 18 — F18 — API Discovery Agent + review UI extension

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: The API analog of F5; needs F16 (SpecParser), F17 (an api package), and the already-built LLMClient (F2) / Test Case Store (F1). Adds the API protocol tab to F6's review screen.

---

## F18 — API Discovery Agent + review UI extension

### Story F18.S1 — Spec-reading discovery loop

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F18-010 | Implement `APIDiscoveryAgent` skeleton: reads dereferenced spec directly, calls LLMClient (text-only, api_reasoning role) to identify resources and propose operations | F18.S1 | F18 | F16-070, F2-040 | Integration test: against the demo API's spec, agent identifies the /orders resource and its available operations | Not Started |
| F18-020 | Implement steered CRUD-lifecycle-chain proposal logic: POST→GET→PUT→GET→DELETE→GET with extract/inject threading | F18.S1 | F18 | F18-010 | Integration test: against /orders, agent proposes the full 6-step chain with correct extract/inject linkage | Not Started |
| F18-030 | Implement fallback to simpler single-call/partial-chain tests for resources lacking a full CRUD set | F18.S1 | F18 | F18-020 | Integration test: against a read-only endpoint, agent proposes a single GET test instead of attempting a chain | Not Started |
| F18-040 | Implement assertion authoring beyond schema validation (e.g. post-DELETE GET expects 404) | F18.S1 | F18 | F18-020 | Integration test: the proposed chain's final verify-deleted step asserts expected_status 404, not just schema_match | Not Started |
| F18-050 | Implement consumption of package instructions field to scope/steer proposals | F18.S1 | F18 | F18-010, F17-040 | Integration test: an instructions field excluding a path prefix results in no proposed test cases for that prefix | Not Started |

**F18-010 — How to build it**: `src/maya/agents/api_discovery_agent.py`, class `APIDiscoveryAgent(llm: LLMClient)` with a `discover(spec: dict) -> list[ResourcePlan]` method that prompts the LLM (via `llm.generate(prompt, task_role="api_reasoning")`, no images — F2-040's text-only model role) with the dereferenced spec's paths/operations, asking it to group operations into resources (path template families like `/orders`, `/orders/{id}`) and identify which CRUD operations exist per resource. (see plan.md §2.3 API Discovery Agent row, §11.5 intro)

**F18-020 — How to build it**: For each identified resource with a full CRUD set, prompt the LLM to construct the specific 6-step chain (`POST` create → `GET` verify created → `PUT`/`PATCH` update → `GET` verify updated → `DELETE` → `GET` verify deleted) per the exact worked example in plan.md §11.3, threading the created entity's id via `extract: {"order_id": "$.body.id"}` on step 1 and `path_params: {"order_id": "${steps.s1.order_id}"}` on every subsequent step. This is the **steered default**, not one option among many — bias the prompt accordingly. (see plan.md §11.3 worked example, §11.5)

**F18-030 — How to build it**: When a resource lacks a full CRUD set (e.g., a read-only reporting endpoint with only `GET`), have the agent fall back to proposing a single-call test case (just the `GET` with basic assertions) rather than forcing a chain that can't exist. Detect this case by checking which HTTP methods the spec actually exposes for that resource before attempting chain construction. (see plan.md §11.5: "falls back to simpler single-call or partial-chain tests")

**F18-040 — How to build it**: Beyond `schema_match` (which `F16-080`'s validator already provides), have the agent author explicit behavioral assertions appropriate to each step — notably, the chain's final `GET` (verify-deleted) should assert `expected_status: 404`, not merely validate against a schema. Prompt the LLM explicitly to consider "what should happen after a delete" / "would an implausible value plausibly be rejected" as part of its proposal reasoning. (see plan.md §11.5 bullet: "Authors assertions beyond schema validation")

**F18-050 — How to build it**: Before generating proposals, pass the package's `instructions` free-text field (resolved via `F3-080`'s package read path, extended for api packages by F17-020) into the discovery prompt, instructing the LLM to exclude or de-prioritize any resources/paths matching the stated scope restriction (e.g. "treat /internal/* as out of scope" → simply don't propose test cases for matching paths). (see plan.md §11.5 bullet: "Consumes the package's optional free-text instructions")

### Story F18.S2 — Output wiring

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F18-060 | Implement translation of proposed flows into APITestCase JSON (operation_ids, spec_version_ref, field_mapping_confidence, steps[] per plan.md §11.3) written to pending/ | F18.S2 | F18 | F18-040, F1-050 | Manual file inspection: open a pending/tc_*.json for protocol:"api", confirm it matches the §11.3 schema shape | Not Started |
| F18-070 | Wire a run_api_discovery(project_id, environment_id) entry point analogous to F5-070 | F18.S2 | F18 | F18-060, F17-040 | Manual: call the entry point directly, confirm it runs without manually wiring adapters | Not Started |
| F18-080 | Manual end-to-end test: run discovery against the demo /orders resource; inspect pending output for correct chain + extract/inject linkage | F18.S2 | F18 | F18-070 | Manual file/JSON inspection: full 6-step chain present with correct id-threading | Not Started |
| F18-090 | Verify F6's approval endpoints work unmodified for protocol:"api" test cases; confirm the protocol filter (added pre-emptively in F6-010) works correctly now that both protocols coexist | F18.S2 | F18 | F18-080, F6-040 | Integration test: list pending test cases filtered by protocol=api, approve one, assert it moves correctly alongside ui ones with no cross-contamination | Not Started |

**F18-060 — How to build it**: Flesh out the `APITestCase` stub left in `F1-030` with the full shape from plan.md §11.3: `operation_ids[]`, `spec_version_ref`, `field_mapping_confidence`, `steps[]` (each with `step_id`, `operation_id`, `method`, `path`, `headers`, `body`/`body_type`, `path_params`, `query_params`, `expected_status`, `expected_schema_ref`, `extract`, `assertions[]`). Translate the agent's proposed chain (F18-020/030/040) into this model and call `TestCaseStore.create()` (F1-050) exactly as `F5-040` does for UI — same store, same `pending/` directory, different protocol discriminator. (see plan.md §11.3 full schema)

**F18-070 — How to build it**: `src/maya/runners/discovery_runner.py`, function `run_api_discovery(root_dir, project_id, environment_id)` loading the project/environment's `api` package (F17-020), reading the pinned spec (F16-070's dereferenced form), and running `APIDiscoveryAgent.discover()` end to end — structurally identical in shape to `F5-070`'s UI counterpart, so later epics (F12/F13's scheduler/REST contract extensions, F23) can treat both uniformly. (see plan.md §5.g)

**F18-080 — How to build it**: Manual/scripted test: call `run_api_discovery()` against the project configured in `F17-040` (pointed at `F16-040`'s demo API), then open the resulting `pending/tc_*.json` and visually confirm the 6-step CRUD chain with correct `extract`/`inject` linkage matches the worked example shape from plan.md §11.3. (see plan.md §5.g step 3, §10: "exercising... API discovery... end-to-end")

**F18-090 — How to build it**: Re-run `F6-010`'s `GET /api/v1/projects/{id}/test-cases?status=pending&protocol=api` against a project now containing both a UI test case (from F5) and an API test case (from F18-080) in the same `pending/` directory — confirm the filter correctly isolates the API one, and that approving it via `F6-020`'s move logic works identically regardless of protocol (since `TestCaseStore` was always protocol-agnostic at the storage level, only the listing endpoint needed the explicit filter). This closes the second structural gap flagged during planning. (see plan.md §5.c: "same approval path... reused verbatim")

### Story F18.S3 — API protocol tab on pending review UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F18-100 | Enable the previously-disabled "API" tab on F6-050's pending list and extend F6-060's detail view to render API step fields (method/path/body/assertions) | F18.S3 | F18 | F18-090, F6-060 | Manual UI walkthrough: an API test case from F18-080 appears under the API tab and its CRUD chain steps render correctly with extract/inject values visible | Not Started |

**F18-100 — How to build it**: In `TestCasesPending.tsx` (F6-050), activate the API `ToggleButtonGroup` option (left disabled since F6-050) to call the same endpoint with `protocol=api`. In `TestCaseDetail.tsx` (F6-060), branch the step-rendering table on `protocol`: API steps render method/path/headers/body/expected_status/assertions columns instead of the UI action/target/input columns, with `extract`/`path_params` values visibly shown so a human reviewer can confirm the id-threading makes sense before approving. (see plan.md §2.3 React + MUI Dashboard row: "tabbed per test type")
