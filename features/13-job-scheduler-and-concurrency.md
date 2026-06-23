# 13 — F12 — Job Scheduler / AI-Work Queue & Concurrency (UI scope)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Manual single-job triggering has sufficed to verify F5–F11 in isolation; real concurrency (parallel replay + serialized AI queue) is layered in once there are multiple job kinds worth serializing.

---

## F12 — Job Scheduler / AI-Work Queue & Concurrency (UI scope)

### Story F12.S1 — Job abstraction

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F12-010 | Define a `Job` model (job_id, project_id, environment_id, job_type, status, requires_ai) | F12.S1 | F12 | F1-010 | Unit test: round-trip a Job through the model | Not Started |
| F12-020 | Implement `JobScheduler.submit(job)` with a queue and a simple worker loop | F12.S1 | F12 | F12-010 | Unit test: submit several jobs, assert the worker loop processes all of them and updates status to completed | Not Started |

**F12-010 — How to build it**: Add `Job` to `src/maya/storage/models.py` (F1-010's file) — `job_id`, `project_id`, `environment_id`, `job_type: Literal["explore","replay","heal_escalation","scenario"]`, `status: Literal["queued","running","completed","failed"]`, `requires_ai: bool`. This model doesn't need file persistence necessarily (an in-memory queue is fine for MVP, per the "file-based" storage principle applying to test artifacts, not transient job state) — but define it as a pydantic model regardless for consistent typing. (see plan.md §2.3 Job Scheduler row)

**F12-020 — How to build it**: `src/maya/scheduling/job_scheduler.py`, class `JobScheduler` with an internal `queue.Queue[Job]` (or two queues — see F12.S2) and a background worker thread/asyncio task calling a registered handler function per `job_type`. Keep this simple: `submit(job, handler: Callable)` enqueues; the worker loop pops and calls `handler(job)`, updating `job.status` as it goes. (see plan.md §2.3, §6)

### Story F12.S2 — Serialized AI queue + parallel replay

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F12-030 | Implement a single serialized AI-work sub-queue: requires_ai=True jobs dispatch one-at-a-time against OllamaAdapter | F12.S2 | F12 | F12-020, F2-050 | Integration test: submit 3 AI-requiring jobs simultaneously, assert their LLM calls never overlap in time | Not Started |
| F12-040 | Implement parallel dispatch for requires_ai=False jobs via independent Playwright browser contexts | F12.S2 | F12 | F12-020, F2-070 | Integration test: submit 3 replay jobs simultaneously, assert they complete concurrently (wall time ≈ single-job time, not 3×) | Not Started |
| F12-050 | Wire existing entry points (run_exploration, RunOrchestrator, healing escalation, scenario) to submit through JobScheduler instead of being called directly | F12.S2 | F12 | F12-030, F12-040, F8-040, F9-050, F10-020 | Integration test: triggering each existing entry point now routes through the scheduler and still produces identical output to calling it directly | Not Started |
| F12-060 | Manual test: 3 replay jobs + 1 exploration job simultaneously — replay unblocked, exploration AI calls serialized | F12.S2 | F12 | F12-050, F2-140 | Manual behavioral test: replay jobs finish without waiting on the AI queue; llm log shows no overlapping AI call timestamps | Not Started |

**F12-030 — How to build it**: Add a second, dedicated `queue.Queue` inside `JobScheduler` specifically for `requires_ai=True` jobs, consumed by exactly one worker thread that calls into `OllamaAdapter` — this single-consumer-thread design is what naturally serializes GPU access regardless of which task role/protocol submitted the job, with no separate locking logic needed. (see plan.md §6: "single serialized AI-work queue... because the 16GB GPU can only realistically run one inference at a time")

**F12-040 — How to build it**: For `requires_ai=False` jobs (the `none`/`cosmetic` reuse path from F8-040), dispatch each onto its own worker thread (or asyncio task) with its own `PlaywrightAdapter`/browser context (`browser.new_context()` per job) — Playwright contexts are independent enough that this needs no additional locking. Cap the number of simultaneous contexts via a config value to respect the RAM risk noted in plan.md §9. (see plan.md §6, §9 "Concurrency limits on 16GB total RAM")

**F12-050 — How to build it**: Replace direct calls to `run_exploration()` (F5-070), `RunOrchestrator.run()` (F7-060/F8-040), the healing engine's vision-tier escalation (F9-050), and `ScenarioInterpreter` (F10-020) with `JobScheduler.submit(Job(...), handler=<that function>)` calls, setting `requires_ai=True` for exploration/scenario/healing-escalation jobs and `requires_ai=False` for pure replay jobs (note: a replay job that *triggers* a structural-major re-exploration mid-run effectively spawns a second, AI-requiring job rather than blocking the original). (see plan.md §6)

**F12-060 — How to build it**: Manual test: submit 3 replay-only jobs (via F12-040's path) and 1 exploration job (via F12-030's path) at the same time; assert via wall-clock timestamps that the 3 replay jobs complete without waiting for the exploration job's AI calls, and check the `llm` log (F2-140) to confirm no two AI call entries overlap in their start/end timestamps. (see plan.md §10: "Validate the concurrency model")
