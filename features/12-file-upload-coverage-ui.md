# 12 — F11 — File-Upload Coverage (UI side)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Needs F5 (agent recognizes file-input fields) and F7 (`upload_file` execution action) already working; a small, isolable addition.

---

## F11 — File-Upload Coverage (UI side)

### Story F11.S1 — Fixture library + resolution

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F11-010 | Create built-in fixture files (sample.pdf, .png, .csv, sample_large.pdf) checked into the repo | F11.S1 | F11 | F0-010 | Manual: files exist under `fixtures/` and open correctly in their respective viewers | Not Started |
| F11-020 | Implement fixture_ref resolver: resolves `builtin:<name>` or `<project>/uploads/<name>` to an actual filesystem path | F11.S1 | F11 | F11-010, F1-080 | Unit test: both reference forms resolve to correct, existing file paths; an unknown reference raises a clear error | Not Started |
| F11-030 | Extend ExplorationAgent to detect file-input fields and select a fixture, emitting an upload_file step with fixture_ref | F11.S1 | F11 | F5-040, F11-020 | Integration test: against a demo page with a file input, agent proposes an upload_file step with a valid fixture_ref | Not Started |
| F11-040 | Extend ExecutionEngine's upload_file action to resolve fixture_ref and drive PlaywrightAdapter.upload_file | F11.S1 | F11 | F11-020, F7-010, F2-090 | Integration test: replay an upload_file step, assert the file is actually attached via the page's file input state | Not Started |
| F11-050 | Manual test: add a file-input element to the demo page; explore, confirm proposal; approve and replay, confirm upload succeeds | F11.S1 | F11 | F11-030, F11-040, F6-040 | Manual end-to-end test across exploration, approval, and replay | Not Started |

**F11-010 — How to build it**: Add real (small) sample files under `framework-data/fixtures/` (or a repo-root `fixtures/` mirrored into the data dir at first run) — `sample.pdf`, `sample.png`, `sample.csv`, and a larger `sample_large.pdf` for upload-size-limit testing. These ship with MAYA itself, distinct from any project's own `uploads/`. (see plan.md §3.3, §5.j)

**F11-020 — How to build it**: `src/maya/storage/fixture_resolver.py`, function `resolve_fixture_ref(ref: str, project_id: str, root_dir) -> Path` — if `ref.startswith("builtin:")`, look under `framework-data/fixtures/`; otherwise treat it as relative to `framework-data/projects/<project_id>/uploads/`. Raise a clear `FixtureNotFoundError` if the resolved path doesn't exist, since a silently-missing fixture would otherwise surface as a confusing Playwright error much later. (see plan.md §3.3 closing paragraph, §5.j step 2)

**F11-030 — How to build it**: In `ExplorationAgent`'s perception step (F5-010), detect `<input type="file">` elements in the AX-tree/DOM; when encountered, instead of a generic click/type action, emit an `upload_file` step choosing a fixture from the environment's resolved `ui` package `upload_fixtures` list (F3-080) — falling back to a built-in by matching the input's `accept` attribute MIME type if the package doesn't specify one. (see plan.md §5.j step 1)

**F11-040 — How to build it**: In `ExecutionEngine.run_test_case()` (F7-010), handle `action == "upload_file"` by resolving `step.target.fixture_ref` via `F11-020` and calling `driver.upload_file(locator, resolved_path)` (F2-090). File bytes are never inlined into the test case JSON — only the `fixture_ref` string is persisted. (see plan.md §5.j step 2, §3.4 closing note on UI steps)

**F11-050 — How to build it**: Add a `<input type="file">` to `F2-110`'s demo page, re-run exploration (F5-080's flow) to confirm a sensible `upload_file` step is proposed, approve it via F6's UI, then replay via F7 and confirm (e.g. by checking the resulting DOM state or a confirmation message the demo page shows on file select) that the upload actually went through.
