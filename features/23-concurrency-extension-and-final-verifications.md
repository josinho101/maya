# 23 — F23 — Concurrency Extension & cross-cutting final verifications

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Extends F12's scheduler so API discovery/healing also serialize on the shared GPU queue; closes with the full set of Section 10 end-to-end verifications spanning both protocols.

---

## F23 — Concurrency Extension & cross-cutting final verifications

### Story F23.S1 — Shared AI queue across protocols

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F23-010 | Extend JobScheduler's AI-work queue so API discovery, scoped re-discovery, and API healing escalation jobs join the same single serialized queue as UI jobs | F23.S1 | F23 | F12-030, F18-070, F20-030, F21-060 | Integration test: submit a UI exploration job and an API discovery job simultaneously, assert their LLM calls never overlap | Not Started |
| F23-020 | Manual test (mirrors plan.md §10's concurrency validation): several replay-only jobs (mixed UI+API) in parallel alongside one UI exploration + one API discovery job; confirm replay unblocked and AI queue serializes fairly across both protocols without GPU OOM | F23.S1 | F23 | F23-010, F14-020 | Manual behavioral test: replay jobs complete without waiting; llm log shows fair, non-overlapping serialization across both protocols | Not Started |

**F23-010 — How to build it**: Register `run_api_discovery()` (F18-070), the scoped re-discovery path (F20-030), and the API healing engine's LLM tier (F21-060) as `requires_ai=True` job handlers in `JobScheduler` (F12-030) exactly the same way UI's exploration/healing-escalation/scenario jobs were registered in `F12-050` — since the AI queue is already a single-consumer-thread design keyed only on `requires_ai`, not on protocol, this should require no new locking logic, only wiring the new handlers in. (see plan.md §6: "regardless of which task role or protocol requested it")

**F23-020 — How to build it**: Manual test extending `F12-060`'s scenario: submit a mix of UI and API replay-only jobs (several) plus one UI exploration job and one API discovery job, all at once — confirm via wall-clock timestamps that replay jobs aren't blocked, and inspect the `llm` log (F14-020's fully-instrumented version) to confirm the exploration and discovery jobs' AI calls never overlap in time, regardless of submission order. (see plan.md §10: "Validate the concurrency model by running several replay-only jobs simultaneously alongside one AI-invoking job... confirming... the AI queue serializes correctly across both UI and API task roles without GPU OOM")

### Story F23.S2 — Cross-cutting final verifications from plan.md §10

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F23-030 | Manual test: a single project running both UI and API suites against the same environment set, confirming shared credentials resolve correctly into each test-type's package without cross-contamination | F23.S2 | F23 | F19-070, F17-040 | Manual end-to-end test using the dual-protocol project, confirming credential isolation between ui/api packages | Not Started |
| F23-040 | Manual test: a multi-environment run against the demo API with two environments pinned to two different spec versions; confirm a heal applied in one environment doesn't appear in or affect the other | F23.S2 | F23 | F21-100, F17-040 | Manual end-to-end test confirming environment-scoped healing log isolation | Not Started |
| F23-050 | Manual test: verify adapter swappability — write a second, trivial LLMClient stub adapter and confirm no call site outside the adapter module needs to change | F23.S2 | F23 | F2-050 | Manual: swap the adapter via dependency injection only, run an existing test suite, confirm it passes unmodified except for the injection point | Not Started |

**F23-030 — How to build it**: Using the dual-protocol project from `F17-040`/`F19-070`, set deliberately distinct credential values in the `ui` package's `auth.secure_ref` vs. the `api` package's `env_vars` (via `F3-070`'s secrets resolver), trigger a run, and confirm — by inspecting the actual requests/actions performed — that each protocol's engine used only its own package's resolved credentials, with no leakage between the two. (see plan.md §10 closing bullets)

**F23-040 — How to build it**: Create a second environment on the same project (e.g. `staging` alongside `dev`), pin it to a *different* version of the demo API's spec (modify the demo API slightly and let `staging`'s package point at the new spec while `dev` stays on the old one), trigger a heal in `dev` via `F21-100`'s approach, and confirm `staging`'s `healing_logs/` directory remains completely untouched — proving the environment-scoping built into the file layout since `F1-080` actually holds under real multi-environment use. (see plan.md §10: "confirming environment-scoped spec/healing isolation")

**F23-050 — How to build it**: Write a `src/maya/adapters/stub_llm_adapter.py` with a trivial `StubLLMClient(LLMClient)` returning a canned response, swap it in for `OllamaAdapter` purely via whatever dependency-injection point exists (constructor parameter to `ExplorationAgent`/`APIDiscoveryAgent`, or a config-driven adapter factory if one was introduced along the way), and run an existing integration test (e.g. `F5-060`'s) against it — confirm the test still exercises the same code path with no changes needed outside the adapter module itself, proving the swappability claim plan.md makes throughout §2.1. (see plan.md §10: "Verify the adapter layer's swappability claim concretely for at least one category")
