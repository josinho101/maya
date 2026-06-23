# 02 — F1 — Shared Data Model & File Storage

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Project/environment/package/test-case JSON schemas and the file-based Test Case Store must exist before any agent or engine has somewhere to read/write.

---

## F1 — Shared Data Model & File Storage

### Story F1.S1 — Core JSON schemas (pydantic models)

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F1-010 | Define `Project` pydantic model matching `project.json` (id, test_types, default_environment, environments, exploration/healing/notifications/concurrency config) | F1.S1 | F1 | F0-020 | Unit test: round-trip a sample dict through the model, assert no data loss | Not Started |
| F1-020 | Define `Environment`/`Package` models matching `environment.json` (ui/api package sub-shapes, schedule, is_destructive_safe) | F1.S1 | F1 | F1-010 | Unit test: parse the `environment.json` example from plan.md §3.4 verbatim, assert all fields populate | Not Started |
| F1-030 | Define shared `TestCase` model (id, protocol, status, created_by, source_scenario_ref, tags, healing_history_ref, last_run_status, last_execution_time_ms) plus `UITestCase` subtype (view_identity, locator_confidence, steps) | F1.S1 | F1 | F1-010 | Unit test: parse a hand-written UI test case JSON, assert discriminated union resolves to `UITestCase` | Not Started |
| F1-040 | Define `ViewSnapshotRecord`, `RunSummary`, `HealingEventLogEntry` models per plan.md §3.4 | F1.S1 | F1 | F1-010 | Unit test: round-trip one sample of each model | Not Started |

**F1-010 — How to build it**: `src/maya/storage/models.py`, a pydantic `BaseModel` subclass `Project` with fields typed exactly as the `project.json` sketch in plan.md §3.4 (nested sub-models for `exploration`, `healing`, `notifications`, `concurrency` config blocks — each can start as a loose `dict[str, Any]` and be tightened later as concrete fields are needed). Use pydantic v2 `model_validate`/`model_dump` for round-tripping. (see plan.md §3.4)

**F1-020 — How to build it**: Same file, `Environment` model with `packages: dict[str, UIPackage | APIPackage]` — define `UIPackage` (base_url, auth, env_vars, upload_fixtures, instructions) now; `APIPackage` can be a minimal stub today (spec_ref, env_vars, upload_fixtures, instructions) and gets fully fleshed out in F17. Use the exact field names from the `environment.json` example in plan.md §3.4 so later JSON files are directly parseable. (see plan.md §3.4)

**F1-030 — How to build it**: Define `TestCaseBase` with the shared fields, then `UITestCase(TestCaseBase)` adding `view_identity`, `locator_confidence`, `steps: list[UIStep]` where `UIStep` has `action`, `target: {strategy, value}`, `input`/`assertion`. Use a pydantic discriminated union on the `protocol` literal field (`"ui"` vs `"api"`) so `TestCaseStore` (F1-050) can parse either shape from one `tc_<uuid>.json` file without knowing the type ahead of time — leave `APITestCase` as a stub class (just the shared fields) until F18-060 fleshes it out. (see plan.md §3.4, §11.3)

**F1-040 — How to build it**: Three small models in the same `models.py`: `ViewSnapshotRecord` (view_identity, captured_at, page_hash, screenshot_ref, elements, diff_against_previous), `RunSummary` (run_id, environment_id, trigger, decision, total_job_time_ms, results, summary), `HealingEventLogEntry` (heal_id, run_id, step_id, failure_type, original_locator/original_mapping, candidates, applied, auto_applied, escalated_to_vision/escalated_to_llm). Keep `original_locator`/`original_mapping` as the same field generalized across UI/API per plan.md §5.i note 3. (see plan.md §3.4)

### Story F1.S2 — File-based Test Case Store

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F1-050 | Implement `TestCaseStore` CRUD across `pending/`/`approved/`/`archived/` directories using F1-030 models | F1.S2 | F1 | F1-030 | Unit test: create in pending, list, read, move to approved, move to archived; assert directory contents at each step | Not Started |
| F1-060 | Implement file-locking discipline (atomic write-then-rename or advisory lock file) for concurrent writes | F1.S2 | F1 | F1-050 | Unit test: simulate two concurrent writers to the same test case file, assert no corruption (valid JSON survives) | Not Started |
| F1-070 | Write the full unit test suite for F1-050/F1-060 combined | F1.S2 | F1 | F1-060 | Unit test: full pending→approved→archived round trip plus the concurrency simulation, all green | Not Started |

**F1-050 — How to build it**: `src/maya/storage/test_case_store.py`, class `TestCaseStore(root_dir)` with methods `create(test_case) -> id`, `get(id) -> TestCase`, `list(status) -> list[TestCase]`, `move(id, from_status, to_status)`. Internally just file I/O over `<root>/test_cases/{pending,approved,archived}/tc_<uuid>.json`, serializing via the F1-030 models' `model_dump_json()`. This is the single chokepoint every agent/engine writes test cases through — no other component should touch these directories directly. (see plan.md §2.3 Test Case Store, §3.3)

**F1-060 — How to build it**: Write to a temp file in the same directory (`tc_<uuid>.json.tmp`) then `os.replace()` to the final name — this is atomic on both POSIX and Windows and avoids needing a real lock file for the common case. For the "move" operation (which is a cross-directory rename), wrap in a `try/except FileExistsError` to detect a races and retry once. (see plan.md §6 "File-based storage requires write-locking discipline")

**F1-070 — How to build it**: `tests/storage/test_test_case_store.py` — use `tmp_path` pytest fixture for an isolated directory tree; for the concurrency simulation, spawn two threads both calling `create()` with different test cases simultaneously and assert both files exist and parse cleanly afterward (true OS-level concurrent-process testing isn't necessary for MVP confidence here).

### Story F1.S3 — Directory scaffolding utility

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F1-080 | Implement `ProjectDirectoryScaffolder` creating the full `/framework-data/projects/<id>/...` tree per plan.md §3.3 | F1.S3 | F1 | F1-010, F1-020 | Unit test: scaffold a project with 2 environments, assert every expected subdirectory exists | Not Started |
| F1-090 | Unit test scaffolding output is re-parseable via F1-010/F1-020 models | F1.S3 | F1 | F1-080 | Unit test: read back the written `project.json`/`environment.json`, assert they parse via the pydantic models | Not Started |

**F1-080 — How to build it**: `src/maya/storage/scaffolder.py`, function `scaffold_project(root_dir, project: Project)` that creates `test_cases/{pending,approved,archived}/`, `scenario_sessions/`, `uploads/`, and for each environment in `project.environments`: `environments/<env>/{view_snapshots,specs,runs,healing_logs}/`. Write `project.json` and each `environment.json` using the F1-010/F1-020 models' serialization. Use `pathlib.Path.mkdir(parents=True, exist_ok=True)` throughout. (see plan.md §3.3 file layout diagram)

**F1-090 — How to build it**: Extend the F1-080 test to additionally call `Project.model_validate_json(Path(.../"project.json").read_text())` and assert the round-tripped object equals the input — proves the scaffolder and the schema models stay in sync, which matters because they'll be touched independently in later epics.
