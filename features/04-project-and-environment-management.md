# 04 — F3 — Project & Environment Management (CRUD, Secrets) + CRUD UI

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Needs F1's schemas/storage; produces the `project.json`/`environment.json`/secure-config files every later workflow reads from. Gains its own REST endpoints (gap-fill) and CRUD screens in this same epic, so the dashboard is usable from this point forward.

---

## F3 — Project & Environment Management (CRUD, Secrets) + CRUD UI

### Story F3.S1 — Project Manager CRUD

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F3-010 | Implement `ProjectManager.create_project()` — validates input, scaffolds directories, writes `project.json` | F3.S1 | F3 | F1-080, F1-090 | Unit test: create a project, assert `project.json` exists and parses | Not Started |
| F3-020 | Implement `ProjectManager.add_environment()` — writes `environment.json` with empty packages | F3.S1 | F3 | F3-010 | Unit test: add an environment, assert `environment.json` exists with empty `packages: {}` | Not Started |
| F3-030 | Implement `ProjectManager.update_package()` for the `ui` package shape | F3.S1 | F3 | F3-020, F1-020 | Unit test: set a ui package, re-read environment, assert fields match | Not Started |
| F3-040 | Implement archive-not-purge delete for projects/environments | F3.S1 | F3 | F3-010 | Unit test: delete a project, assert directory still exists but is marked archived (e.g. moved under an `archived_projects/` root or flagged in `project.json`) | Not Started |
| F3-050 | Unit tests: create project with 2 environments, add ui package to one, verify file contents; delete and verify archived not removed | F3.S1 | F3 | F3-030, F3-040 | Unit test: full create→configure→delete flow, assert each invariant | Not Started |

**F3-010 — How to build it**: `src/maya/managers/project_manager.py`, class `ProjectManager(root_dir)` with `create_project(project_id, test_types, environments) -> Project` that builds a `Project` model (F1-010) and calls `scaffold_project()` (F1-080) to materialize it on disk. Validate `project_id` is filesystem-safe (slug) before touching disk. (see plan.md §2.3 Project Manager)

**F3-020 — How to build it**: `add_environment(project_id, env_id, label=None, schedule=None)` builds an `Environment` model (F1-020) with `packages={}` and writes it via the same JSON serialization pattern as F1-080, then appends `env_id` to the parent `project.json`'s `environments` list and re-writes it (reuse `TestCaseStore`'s atomic-write helper from F1-060 for this, since it's the same "write JSON, don't corrupt on concurrent access" problem). (see plan.md §3.4 environment.json example)

**F3-030 — How to build it**: `update_package(project_id, env_id, test_type="ui", **fields)` reads the existing `environment.json`, merges in the new `ui` package fields (base_url, auth, env_vars, upload_fixtures, instructions) validated against F1-020's `UIPackage` model, and re-writes the file. Keep `auth.secure_ref` as a plain string field here — actual secret resolution is F3-070/F3-080's job, this task only persists the *reference*. (see plan.md §3.4)

**F3-040 — How to build it**: Simplest correct approach: add an `archived: bool` field to the `Project`/`Environment` models (F1-010/F1-020) and have `delete_project`/`delete_environment` just set it `True` and re-write the JSON, rather than physically moving directories — this keeps git history clean and matches plan.md §3's "archive-not-purge" framing literally. Filter archived projects out of any "list active projects" call site added later. (see plan.md §2.3 Project Manager: "archive-not-purge on delete")

**F3-050 — How to build it**: `tests/managers/test_project_manager.py` — one test function per scenario, using `tmp_path` for isolation, chaining `create_project` → `add_environment` ×2 → `update_package` on one → `delete_project` → re-read and assert `archived=True` while files remain on disk.

### Story F3.S2 — Secrets/secure config

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F3-060 | Implement `config/secure/<project_id>.secure.json` read/write, nested by environment, gitignored by construction | F3.S2 | F3 | F1-010 | Unit test: write a secret, read it back, assert file lives under the gitignored path | Not Started |
| F3-070 | Implement `${secure.<project>.<env>.<key>}` placeholder resolver (template string + lookup → resolved string) | F3.S2 | F3 | F3-060 | Unit test: resolver on a template string with one placeholder returns the correct substituted value | Not Started |
| F3-080 | Wire resolver into `ProjectManager`/package read path so `auth.secure_ref` resolves at access time, never persisted resolved | F3.S2 | F3 | F3-070, F3-030 | Unit test: package field with a placeholder resolves correctly via a "get resolved package" call, while the on-disk file still shows the placeholder | Not Started |
| F3-090 | Unit test: store fake credential, reference via placeholder, resolve, assert original file unchanged | F3.S2 | F3 | F3-080 | Unit test: combined round trip across F3-060/070/080 | Not Started |
| F3-100 | Add startup check warning loudly if `config/secure/` is tracked by git | F3.S2 | F3 | F3-060 | Manual: `git add` the secure file on purpose, run the startup check, confirm a loud warning is printed | Not Started |

**F3-060 — How to build it**: `src/maya/managers/secrets_store.py`, class `SecretsStore(root_dir)` reading/writing `framework-data/config/secure/<project_id>.secure.json` as a nested dict `{"<env_id>": {"<key>": "<value>"}}`. No encryption for MVP — plan.md §7 flags at-rest encryption as an *optional stronger mode*, not required now. Ensure the directory is created with the `.gitignore` entry from F0-010 already covering it. (see plan.md §7)

**F3-070 — How to build it**: A pure function `resolve_placeholder(template: str, secrets: SecretsStore) -> str` using a regex like `\$\{secure\.([^.]+)\.([^.]+)\.([^}]+)\}` to extract project/env/key, look it up via `SecretsStore.get(project, env, key)`, and substitute. Keep this stateless/pure so it's trivially unit-testable without any file I/O (pass a stub/dict in tests instead of a real `SecretsStore`). (see plan.md §3.4, §7)

**F3-080 — How to build it**: Add a `ProjectManager.get_resolved_package(project_id, env_id, test_type) -> dict` that reads the raw package (as persisted, placeholders intact) and runs every string field through `resolve_placeholder()` before returning — this resolved dict is what Browser Controller (F5-030) and API Client Controller (F19) actually consume; the raw, unresolved package is what gets serialized back to disk on any update. Never call `update_package` with a resolved value. (see plan.md §3.4 closing note: "secrets... resolved at runtime... never written back into persisted files")

**F3-090 — How to build it**: `tests/managers/test_secrets.py` combining all three: store `{"staging": {"api_key": "sk-fake-123"}}`, set a package field to `"${secure.acme.staging.api_key}"`, call `get_resolved_package`, assert it returns `"sk-fake-123"`, then re-read the raw `environment.json` and assert it still contains the literal placeholder string.

**F3-100 — How to build it**: At FastAPI startup (`F0-050`'s `main.py`, in a startup event handler), shell out to `git check-ignore framework-data/config/secure` (or walk `.gitignore` patterns manually if avoiding a subprocess call) and log a `logging.getLogger("maya.app").warning(...)` at top volume if the path is *not* ignored or *is* tracked (`git ls-files` check). (see plan.md §7: "framework should warn loudly if it detects this path is tracked")

### Story F3.S3 — REST endpoints for Project/Environment/Package (gap-fill)

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F3-110 | Implement REST CRUD endpoints for Project/Environment/Package (`POST/GET /projects`, `POST /projects/{id}/environments`, `PUT /projects/{id}/environments/{env_id}/packages/{type}`) | F3.S3 | F3 | F3-090 | Integration test: full CRUD sequence via `TestClient`, asserting each endpoint's effect matches the underlying `ProjectManager` call | Not Started |

**F3-110 — How to build it**: `src/maya/api/routers/projects.py`, a FastAPI `APIRouter` exposing thin wrappers over `ProjectManager` (F3-010 through F3-090) — `POST /api/v1/projects` calls `create_project`, `GET /api/v1/projects/{id}` returns the `Project` model, `POST /api/v1/projects/{id}/environments` calls `add_environment`, `PUT /api/v1/projects/{id}/environments/{env_id}/packages/{test_type}` calls `update_package`. Mount this router on the `app` instance from F0-050. This was identified as a structural gap during planning — the dashboard (F3.S4 below) has nothing to call without it, so it must land first. (see plan.md §5.f for the sibling run-trigger contract this mirrors in style)

### Story F3.S4 — Project/Environment/Package CRUD UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F3-120 | Build Projects list + create-project screen | F3.S4 | F3 | F3-110, F0-090 | Manual UI walkthrough: create a project via the form, confirm it appears in the list and `project.json` exists on disk | Not Started |
| F3-130 | Build Environment management screen (add environment, set schedule/is_destructive_safe) within a project's detail view | F3.S4 | F3 | F3-120 | Manual UI walkthrough: add an environment via the UI, confirm `environment.json` is written correctly | Not Started |
| F3-140 | Build UI Package edit form (base_url, auth strategy, env_vars, instructions) within an environment's detail view | F3.S4 | F3 | F3-130 | Manual UI walkthrough: fill in and save a ui package, confirm fields persist and reload correctly | Not Started |

**F3-120 — How to build it**: `frontend/src/pages/ProjectsList.tsx` using MUI `DataGrid` to list projects (via `GET /api/v1/projects`), plus a `ProjectsList`-adjacent `CreateProjectDialog.tsx` MUI dialog with a form (id, test_types checkboxes) posting to `F3-110`'s `POST /api/v1/projects`. Wire this into the `/projects` route placeholder created in F0-090. (see plan.md §2.3 React + MUI Dashboard row)

**F3-130 — How to build it**: `frontend/src/pages/ProjectDetail.tsx` with an "Environments" tab/section listing existing environments and an "Add Environment" form (id, label, cron schedule input, is_destructive_safe checkbox) posting to `F3-110`'s environment endpoint. Navigate here from a row click in `F3-120`'s list.

**F3-140 — How to build it**: Within `ProjectDetail.tsx`, an environment's detail expands to a package edit form bound to the `ui` package shape (base_url text field, auth strategy dropdown, env_vars key-value editor, instructions free-text area) submitting via `PUT` to `F3-110`'s package endpoint. Leave a placeholder/disabled section for the future `api` package type (filled in by F17-040's UI extension task).
