# 11 — F10 — Scenario Interpreter + scenario UI

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: A second LLM orchestrator reusing F5's perception-action loop and F6's approval path — sequenced after the core explore/approve/replay/heal loop is proven, since it's additive coverage. Gains its scenario submission form.

---

## F10 — Scenario Interpreter + scenario UI

### Story F10.S1 — Scenario submission & interpretation loop

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F10-010 | Implement `POST /projects/{id}/scenarios` accepting free-text scenario, persisted to `scenario_sessions/scenario_<ts>.json` | F10.S1 | F10 | F0-050, F1-080 | Integration test: POST a scenario string, assert a session file is written with the text persisted | Not Started |
| F10-020 | Implement `ScenarioInterpreter` reusing F5-010's perception-action loop with goal-directed prompting | F10.S1 | F10 | F5-010 | Integration test: interpreter attempts a known-feasible scenario against the demo page and takes at least one correct action | Not Started |
| F10-030 | Implement "stuck" detection and a structured "couldn't complete, here's where I got stuck" report path | F10.S1 | F10 | F10-020 | Integration test: an infeasible scenario triggers the stuck-report path instead of emitting a bad test case | Not Started |
| F10-040 | Implement emission of resulting test case(s) with created_by:scenario_interpreter and source_scenario_ref | F10.S1 | F10 | F10-020, F1-050 | Manual file inspection: a feasible scenario's resulting pending/ test case has both fields set correctly | Not Started |
| F10-050 | Manual test: feasible scenario → sensible pending test case; infeasible scenario → stuck-report instead of bad test case | F10.S1 | F10 | F10-030, F10-040 | Manual behavioral test: both branches produce the documented outcome | Not Started |

**F10-010 — How to build it**: Extend `src/maya/api/routers/` with a `scenarios.py` router; `POST /api/v1/projects/{id}/scenarios` accepts `{"text": str, "environment_id": str}`, writes a session record (just `{id, text, environment_id, submitted_at, status: "pending_interpretation"}`) to `scenario_sessions/scenario_<timestamp>.json`, and (synchronously for now, matching F7-090's precursor pattern) kicks off interpretation. (see plan.md §5.b step 1)

**F10-020 — How to build it**: `src/maya/agents/scenario_interpreter.py`, class `ScenarioInterpreter(llm, driver)` reusing `ExplorationAgent`'s perception→reasoning→action loop machinery (consider extracting a shared base class or composing rather than duplicating `step()`'s perceive/call-LLM/act sequence from F5-010) but with a goal-directed prompt template (`prompts/scenario.txt`) that includes the scenario text as the objective instead of open-ended "explore and find interesting flows." (see plan.md §2.3 Scenario Interpreter row)

**F10-030 — How to build it**: Add a stuck-detection condition to the loop: if N consecutive steps produce no progress toward the stated goal (the LLM itself can be asked each step "are you still making progress, or stuck?" as part of its structured response) or a step budget is exhausted without a completion signal, stop and emit a `{"status": "stuck", "blocked_at": ..., "reason": ...}` report instead of a test case — persisted back into the same `scenario_sessions/scenario_<id>.json` file rather than `pending/`. (see plan.md §9 "Scenario Interpreter getting stuck")

**F10-040 — How to build it**: On successful completion, build a `UITestCase` (F1-030) exactly as `F5-040` does, but set `created_by="scenario_interpreter"` and `source_scenario_ref` pointing at the `scenario_sessions/scenario_<id>.json` file — written via the same `TestCaseStore.create()` call. (see plan.md §5.b step 3)

**F10-050 — How to build it**: Manual test with two scenario strings against the demo page: one matching the actual login+click flow ("a user logs in and clicks the counter button") expecting a real test case in `pending/`; one describing a nonexistent flow ("a user adds an item to a shopping cart" — not present on the demo page) expecting the stuck-report path from F10-030 instead.

### Story F10.S2 — Scenario submission UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F10-060 | Build scenario submission form (free-text input + environment selector) with a status view for in-progress/stuck/completed | F10.S2 | F10 | F10-050, F0-090 | Manual UI walkthrough: submit a feasible scenario, watch it transition to completed with a linked test case; submit an infeasible one, see the stuck reason displayed | Not Started |

**F10-060 — How to build it**: `frontend/src/pages/ScenarioSubmit.tsx` with a multiline MUI `TextField` for the scenario text and an environment `Select`, posting to `F10-010`'s endpoint; poll or re-fetch `GET /api/v1/projects/{id}/scenarios/{session_id}` (add this small read endpoint alongside F10-010 if not already present) to show status transitions, rendering either a link to the resulting `pending/` test case (via F6-050's list, filtered by `source_scenario_ref`) or the stuck reason text. Add this as a new page reachable from the project detail view rather than a top-level nav route, since it's scoped to one project.
