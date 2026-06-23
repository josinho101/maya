# 17 — F17 — API Project/Environment Packages + CRUD UI extension

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Extends F3's package model with the `api` shape; needs F16's SpecParser to validate/dereference what gets stored. Extends F3's CRUD screens with API package fields.

---

## F17 — API Project/Environment Packages + CRUD UI extension

### Story F17.S1 — api package shape

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F17-010 | Extend Environment/Package models (F1-020) with the full api package shape (spec_ref, env_vars, upload_fixtures, instructions, pinned_version) | F17.S1 | F17 | F1-020 | Unit test: parse the api package example from plan.md §3.4 verbatim, assert all fields populate | Not Started |
| F17-020 | Extend ProjectManager.update_package() to support writing/validating an api package, including spec ingestion via F16-070 on first save | F17.S1 | F17 | F3-030, F17-010, F16-070 | Integration test: set an api package pointing at the demo API's spec URL, assert `specs/<hash>/openapi.json` is written | Not Started |
| F17-030 | Extend project.json's test_types[] handling so a project can carry ["ui","api"] simultaneously sharing one environment set | F17.S1 | F17 | F17-020 | Integration test: a project with both test types shares one environment's credentials correctly for each package | Not Started |
| F17-040 | Manual test: add api test type + package to an existing UI project pointed at the demo API; confirm specs/ baseline and project.json reflect both test types | F17.S1 | F17 | F17-030 | Manual file inspection: `project.json` shows `test_types: ["ui","api"]`; `specs/` baseline exists under the right environment | Not Started |

**F17-010 — How to build it**: Replace the F1-020 stub `APIPackage` with the full shape from plan.md §3.4's `environment.json` example: `spec_ref: {source: "url"|"file", value: str, pinned_version: str | None}`, `env_vars: dict`, `upload_fixtures: list[str]`, `instructions: str | None`. (see plan.md §3.4)

**F17-020 — How to build it**: In `ProjectManager.update_package(test_type="api", ...)`, after persisting the package fields, if this is the first time an `api` package is set for this environment (no existing `specs/index.json`), call `PranceOpenAPIAdapter.fetch_and_dereference(spec_ref.value)` (F16-070), hash the result, and write it to `environments/<env_id>/specs/<hash>/openapi.json` plus an `index.json` recording the current pinned hash. (see plan.md §3.3 specs/ directory, §5.g step 1)

**F17-030 — How to build it**: Confirm (and adjust if needed) that `Project.test_types: list[Literal["ui","api"]]` (F1-010) already supports holding both simultaneously — the scaffolder (F1-080) should ensure both test types' environment-specific subdirectories (`view_snapshots/` for ui, `specs/` for api) get created under each environment regardless of which test types are added in which order. (see plan.md §3.1: "one project can host multiple test-type suites... sharing one set of environments")

**F17-040 — How to build it**: Manual test: take the project created in `F5-080`, call `add environment's api package` pointing `spec_ref` at `F16-040`'s demo API's `/openapi.json` URL, and confirm both `project.json`'s `test_types` array and the new `specs/<hash>/openapi.json` baseline file appear correctly, alongside the pre-existing `ui` package and its `view_snapshots/` history remaining untouched. (see plan.md §10: "Verify a single project can run both a UI suite and an API suite against the same environment set")

### Story F17.S2 — api package fields in CRUD UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F17-050 | Extend F3-140's package edit form with an "API" tab (spec URL/file input, instructions field) | F17.S2 | F17 | F17-040, F3-140 | Manual UI walkthrough: add an api package via the UI to an existing project, confirm spec baseline is fetched and the form reflects pinned_version after save | Not Started |

**F17-050 — How to build it**: In `frontend/src/pages/ProjectDetail.tsx`'s package edit section (placeholder left by F3-140), add a tab/section for the `api` package: a spec source field (URL text input, or a file upload control for local spec files), an instructions textarea, and a read-only "Pinned version" display populated after save (from the response of `F17-020`'s endpoint extension). Submits via the same `F3-110` package PUT endpoint, now also accepting `test_type="api"` bodies.
