# 09 — F8 — View Identity & Change Detection (Diff Gate)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Needs both an Exploration Agent (F5, produces snapshots) and an Execution Engine (F7, replays per view) to make the none/cosmetic/structural-minor/structural-major gate meaningful and testable.

---

## F8 — View Identity & Change Detection (Diff Gate)

### Story F8.S1 — Snapshot diff + severity classification

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F8-010 | Implement `ViewSnapshotEngine.diff(current, previous) -> severity` (none/cosmetic/structural-minor/structural-major) | F8.S1 | F8 | F4-030 | Unit test: identical snapshots → none; text-only change → cosmetic; non-breaking addition → structural-minor; key element removed/renamed → structural-major | Not Started |
| F8-020 | Implement `elements[]` extraction (ref, role, name, data-testid, path_fingerprint) feeding diff granularity | F8.S1 | F8 | F4-030 | Unit test: extract elements from a sample AX-tree, assert expected fields populate per element | Not Started |
| F8-030 | Unit tests covering all four severity tiers using fixture snapshot JSON (no live browser needed) | F8.S1 | F8 | F8-010, F8-020 | Unit test: four fixture pairs, one per severity tier, all classify correctly | Not Started |

**F8-010 — How to build it**: Extend `src/maya/perception/snapshot_engine.py` with `diff(current: ViewSnapshotRecord, previous: ViewSnapshotRecord) -> Severity` comparing `elements[]` (F8-020) sets: no changes → `none`; only text/non-structural changes → `cosmetic`; added elements with no removals of pre-existing ones → `structural-minor`; any removed/renamed key element (especially one a test case's locator references) → `structural-major`. Model the severity vocabulary as a shared `Severity` enum reused again in F16-120 for the API side. (see plan.md §4, and the severity table in §11.2 which this directly mirrors)

**F8-020 — How to build it**: `extract_elements(ax_tree: dict) -> list[ElementRecord]` walking the AX-tree and pulling `ref` (a stable-ish path-based id), `role`, `name`, `data-testid` (read from the underlying DOM via `get_dom_html()` cross-referenced by role+name, or directly if Playwright's AX snapshot exposes it), and a `path_fingerprint` (positional hash). This granularity is what `diff()` (F8-010) actually compares element-by-element. (see plan.md §3.4 View snapshot record: "elements[] (ref, role, name, data-testid, path_fingerprint)")

**F8-030 — How to build it**: `tests/perception/test_snapshot_diff.py` using four hand-crafted `ViewSnapshotRecord` JSON fixture pairs (no Playwright/browser needed) — one pair per severity tier, written directly as test fixtures rather than captured live, so this test suite runs fast and deterministically in CI.

### Story F8.S2 — Decision gate wired into Run Orchestrator

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F8-040 | Modify `RunOrchestrator` to snapshot each view before running, diff against last stored snapshot, and branch: none/cosmetic→reuse, structural-minor→reuse+healing-ready flag, structural-major→mark for scoped re-exploration | F8.S2 | F8 | F8-030, F7-060, F5-070 | Integration test: unchanged page → reuse path taken (asserted via a flag/log, not just pass/fail); structurally mutated page → re-exploration path triggered | Not Started |
| F8-050 | Manual verification: run twice with zero changes, confirm zero LLM calls on the second run; mutate structurally, confirm scoped re-exploration only | F8.S2 | F8 | F8-040, F2-140 | Manual behavioral/idempotency proof: second identical run's llm log (F2-140) has zero new entries; post-mutation run's llm log shows exactly the scoped re-exploration call | Not Started |

**F8-040 — How to build it**: In `RunOrchestrator.run()` (F7-060), before executing each view's test cases, call `ViewSnapshotEngine.capture()` (F4-030) then `diff()` (F8-010) against the last persisted snapshot for that `view_identity`. Branch per plan.md §5.d step 4: `none`/`cosmetic` → just call `ExecutionEngine.run_test_case()` as before, no LLM touched; `structural-minor` → same, but set a `healing_ready: true` flag consulted later when F9 exists; `structural-major` → instead of running the stale test cases, call `run_exploration()` (F5-070) scoped to just that view (passing the specific view_identity to limit scope — a simple filter on which views the agent targets is sufficient for MVP scoping, full "only look at this exact view" steering can be refined later). (see plan.md §5.d)

**F8-050 — How to build it**: This is the single most important verification in the whole plan (explicitly called out in plan.md §10 as "the first thing to prove"). Script: run `RunOrchestrator.run()` twice back-to-back against an unchanged demo page, then `grep`/parse the `llm` log file (F2-140) for entries with a timestamp after the first run's completion — assert zero. Then mutate the demo page's DOM structurally (e.g. add a new required field), run a third time, and assert exactly one scoped exploration-related LLM log entry appears (not a full re-exploration of unrelated views). (see plan.md §10, §5.d)
