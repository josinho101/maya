# 06 — F5 — Autonomous UI Exploration Agent

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: The first LLM-driven capability; needs F2 (adapters), F3 (a project/environment/package to explore against), F4 (perception primitives). Produces the first `pending/` test cases.

---

## F5 — Autonomous UI Exploration Agent

### Story F5.S1 — Perception-action loop skeleton

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F5-010 | Implement `ExplorationAgent` skeleton: perceive (AX-tree+screenshot) → LLM tool-calling prompt → parse one action → act via BrowserDriver | F5.S1 | F5 | F2-030, F2-070, F2-080 | Integration test: against the demo page, agent perceives and successfully performs at least one click action chosen by the LLM | Not Started |
| F5-020 | Implement step/page budget cutoff and coverage-plateau stop condition (no new view_identity in N steps) | F5.S1 | F5 | F5-010, F4-030 | Unit/integration test: agent stops within the configured budget; stops early if no new view_identity appears for N consecutive steps | Not Started |
| F5-030 | Implement login-flow handling at exploration start using resolved ui package credentials + session persistence | F5.S1 | F5 | F3-080, F2-100 | Integration test: agent logs in via package credentials against the demo login form, confirmed via post-login DOM state | Not Started |

**F5-010 — How to build it**: `src/maya/agents/exploration_agent.py`, class `ExplorationAgent(llm: LLMClient, driver: BrowserDriver)` with a `step()` method: call `driver.get_ax_tree()` + `driver.screenshot()`, build a tool-calling prompt describing available actions (`click`, `type`, `navigate`, `upload_file`) and the current perception, call `llm.generate(prompt, images=[screenshot], tools=[...])`, parse the structured tool-call response into one action, execute it via the matching `driver` method. Keep the prompt template in a separate `prompts/exploration.txt` or similar so it's editable without touching code. (see plan.md §1.1, §2.3 Exploration Agent row)

**F5-020 — How to build it**: Wrap `step()` in a `run(max_steps, plateau_steps)` loop tracking `seen_view_identities: set[str]` (computed via `ViewSnapshotEngine.capture()` from F4-030 after each action) — stop when `max_steps` reached or no new identity has been seen in `plateau_steps` consecutive steps. Read both budgets from `project.json`'s `exploration` config block (F1-010). (see plan.md §2.3: "stops on a step/page budget or coverage plateau")

**F5-030 — How to build it**: Before the main loop, call `ProjectManager.get_resolved_package(...)` (F3-080) to get real credentials, locate the login form via the AX-tree (or a configured locator strategy), `driver.type()` username/password, `driver.click()` submit, then `driver.save_storage_state(...)` (F2-100) so subsequent runs/healing calls reuse the session instead of re-logging in every time. (see plan.md §5.a step 2)

### Story F5.S2 — Test case proposal output

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F5-040 | Translate a recorded action sequence into a structured `UITestCase` JSON written to `pending/` | F5.S2 | F5 | F5-010, F1-050, F1-030 | Manual: run a short exploration, open `pending/tc_*.json`, confirm steps[] is well-formed | Not Started |
| F5-050 | Wire `view_identity` (from F4-030) into produced test cases | F5.S2 | F5 | F5-040, F4-030 | Manual: confirm the test case JSON's `view_identity` field is non-null and matches the captured snapshot's identity | Not Started |
| F5-060 | End-to-end test: run `ExplorationAgent` against the demo page with login + one clickable flow; inspect output | F5.S2 | F5 | F5-030, F5-050 | Manual file/JSON inspection: `pending/tc_*.json` has well-formed, replayable-looking steps and a valid view_identity | Not Started |

**F5-040 — How to build it**: As `ExplorationAgent.run()` executes actions, accumulate them into an in-memory list of `UIStep` objects (action/target/input); when a coherent flow concludes (loop ends, or the agent's prompt signals "flow complete"), construct a `UITestCase` (F1-030) with `created_by="exploration_agent"`, `status="pending"`, and call `TestCaseStore.create()` (F1-050) to persist it. One run may emit more than one test case if multiple distinct flows were exercised. (see plan.md §5.a step 4)

**F5-050 — How to build it**: Tag each accumulated `UIStep` (or the resulting `UITestCase` as a whole) with the `view_identity` captured via `F4-030` immediately before/after the relevant action — this is what later lets F8's diff gate group test cases by view for the reuse/re-explore decision. (see plan.md §4 closing paragraph: "Test case references view_identity instead of route")

**F5-060 — How to build it**: `tests/agents/test_exploration_agent_e2e.py`, an integration test (requires live Ollama + Playwright) running `ExplorationAgent.run()` against `F2-110`'s demo page with a small step budget (e.g. 5), then reading back whatever landed in `pending/` and asserting at minimum one well-formed step with a valid locator strategy/value and a non-null `view_identity`.

### Story F5.S3 — Wiring into Project/Environment

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F5-070 | Implement `run_exploration(project_id, environment_id)` entry point loading project/environment/package and constructing the agent | F5.S3 | F5 | F5-060, F3-050 | Manual: call the entry point directly (script or test), confirm it runs without manually wiring adapters | Not Started |
| F5-080 | Manual verification: create a real project via ProjectManager pointed at the demo page, trigger exploration, confirm scoped pending/ output | F5.S3 | F5 | F5-070 | Manual: end-to-end from `ProjectManager.create_project()` through to a `pending/` test case file under that project's directory | Not Started |

**F5-070 — How to build it**: `src/maya/runners/exploration_runner.py`, function `run_exploration(root_dir, project_id, environment_id)` that loads the `Project`/`Environment` (via `ProjectManager`), resolves the `ui` package (F3-080), constructs a `PlaywrightAdapter` + `OllamaAdapter` (with `task_role="ui_explore_heal"`), and instantiates/runs `ExplorationAgent`. This is the function later epics (F12's scheduler, F13's REST trigger) call into — keep its signature stable. (see plan.md §5.a)

**F5-080 — How to build it**: A manual or scripted test: `ProjectManager.create_project("demo-proj", ...)` → `add_environment("dev")` → `update_package("dev", "ui", base_url=f"file://{demo_page_path}", auth=...)` → `run_exploration("demo-proj", "dev")` → assert `framework-data/projects/demo-proj/test_cases/pending/` is non-empty. This is the first true end-to-end proof the whole F1–F5 stack works together. (see plan.md §10 Verification Plan)
