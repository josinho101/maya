# 16 — F16 — Adapter Layer Extension: HTTP + Spec (API foundations)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

> Everything in this and subsequent API-testing epics assumes the full UI pipeline (F0–F14, files [01](01-project-scaffolding-and-dev-environment.md)–[15](15-logging-subsystem-completion.md)) is built and verified. No API-specific epic should start before F14 is done, per the UI-first constraint.

**Rationale for this position**: First API-specific epic. `HTTPClient`/`HTTPXAdapter`, `SpecParser`, `SpecDiffer` are net-new adapters nothing in F0–F14 needs — mirrors how F2 started the UI block.

---

## F16 — Adapter Layer Extension: HTTP + Spec (API foundations)

### Story F16.S1 — HTTPClient + HTTPXAdapter

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F16-010 | Define `HTTPClient` Protocol/ABC: request execution + timing capture, multipart upload support | F16.S1 | F16 | F0-020 | Unit test: a trivial stub implementation satisfies the Protocol | Not Started |
| F16-020 | Implement `HTTPXAdapter` basic request execution (GET/POST/PUT/DELETE) with per-request timing | F16.S1 | F16 | F16-010 | Integration test: issue each method against a real endpoint, assert response + latency captured | Not Started |
| F16-030 | Implement multipart/file-upload support in HTTPXAdapter, reusing F11-020's fixture_ref resolver | F16.S1 | F16 | F16-020, F11-020 | Integration test: multipart POST with a resolved fixture file succeeds against a real endpoint | Not Started |
| F16-040 | Build a tiny demo REST API (FastAPI, throwaway app) with a full CRUD resource (/orders) and one multipart endpoint | F16.S1 | F16 | — | Manual: the demo API starts, its OpenAPI spec is reachable, and each CRUD + multipart endpoint responds correctly via curl/httpx | Not Started |
| F16-050 | Integration test: GET/POST/PUT/DELETE + multipart upload against the demo API via HTTPXAdapter, assert responses and timing | F16.S1 | F16 | F16-030, F16-040 | Integration test: all five operations succeed with timing captured | Not Started |

**F16-010 — How to build it**: `src/maya/adapters/http_client.py`, a Protocol `HTTPClient` with `request(method, url, headers=None, body=None, files=None) -> HTTPResponse` where `HTTPResponse` carries status, headers, body, and timing fields (latency_ms minimum; DNS/connect/TLS/TTFB breakdown where the underlying library exposes it). Mirrors `BrowserDriver`'s role for API work — every later component (F19's Test Runner) depends on this interface, never on `httpx` directly. (see plan.md §2.1 adapter table)

**F16-020 — How to build it**: `src/maya/adapters/httpx_adapter.py`, class `HTTPXAdapter` wrapping `httpx.Client`, using `httpx`'s built-in request/response timing hooks (or wrapping calls in `time.perf_counter()` if finer DNS/connect/TLS breakdown isn't readily available — total latency is the documented minimum requirement, the breakdown is "where available"). (see plan.md §2.3 API Client Controller row)

**F16-030 — How to build it**: Extend `HTTPXAdapter.request()` to accept a `files: list[{"field": str, "fixture_ref": str}]` parameter, resolving each `fixture_ref` via `F11-020`'s resolver (the same fixture library and resolution mechanism as UI uploads — no separate fixture system for API) and passing the opened file handles to `httpx`'s `files=` parameter for a `multipart/form-data` request. (see plan.md §5.j: "shared mechanism")

**F16-040 — How to build it**: A small throwaway FastAPI app (e.g. `tests/fixtures/demo_api/app.py`, run via its own uvicorn process during integration tests or a pytest fixture that starts/stops it) exposing `/orders` (POST/GET list, GET/PUT/DELETE by id) backed by an in-memory dict (no real DB needed — this is a test target, not part of MAYA itself), plus one `/orders/{id}/attachment` multipart upload endpoint. FastAPI auto-generates the OpenAPI spec at `/openapi.json`, which F16-070 onward consumes. (see plan.md §10: "Build against... a demo API with an OpenAPI spec... at least one resource exposing a full CRUD set")

**F16-050 — How to build it**: `tests/adapters/test_httpx_adapter_integration.py` starting `F16-040`'s demo API (as a pytest fixture, e.g. via `subprocess` or an in-process `TestClient`-backed transport if `httpx` is pointed at it directly), then exercising create→read→update→delete plus the multipart upload, asserting both correctness and that timing fields are populated.

### Story F16.S2 — SpecParser + PranceOpenAPIAdapter

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F16-060 | Define `SpecParser` Protocol/ABC: dereference $refs, validate request/response against schema | F16.S2 | F16 | F0-020 | Unit test: a trivial stub implementation satisfies the Protocol | Not Started |
| F16-070 | Implement `PranceOpenAPIAdapter` spec fetch (URL or file) + $ref dereferencing using prance | F16.S2 | F16 | F16-060 | Integration test: fetch and dereference the demo API's spec, assert no unresolved $ref markers remain | Not Started |
| F16-080 | Implement request/response schema validation using openapi-core against the dereferenced spec | F16.S2 | F16 | F16-070 | Unit test: a valid request/response pair validates; a malformed one is rejected with a clear error | Not Started |
| F16-090 | Integration test: fetch/dereference the demo spec, validate a real request/response pair from F16-050 | F16.S2 | F16 | F16-080, F16-050 | Integration test: the actual HTTP traffic from F16-050 validates cleanly against the dereferenced spec | Not Started |

**F16-060 — How to build it**: `src/maya/adapters/spec_parser.py`, a Protocol `SpecParser` with `fetch_and_dereference(source: str) -> dict` and `validate(request_or_response, schema_ref) -> bool|ValidationError`. This is the API analog of `BrowserDriver`'s perception role — every later spec-consuming component (F18's Discovery Agent, F19's Test Runner) depends only on this interface. (see plan.md §2.1 adapter table)

**F16-070 — How to build it**: `src/maya/adapters/prance_adapter.py`, class `PranceOpenAPIAdapter` using the `prance.ResolvingParser` to fetch (from a URL or local file path) and fully dereference all `$ref`s in one pass, returning the flattened spec dict — this dereferenced form is what gets persisted as the baseline in `specs/<hash>/openapi.json` (F17-020) and is what the Discovery Agent (F18) reads directly. (see plan.md §2.1, §2.3 Spec Manager row)

**F16-080 — How to build it**: Use `openapi_core`'s `Spec.from_dict(dereferenced_spec)` plus its request/response validator classes to check a built request/response pair against the spec's schema for a given operation — wrap this in a simple `validate_request(operation_id, request) -> ValidationResult` / `validate_response(operation_id, response) -> ValidationResult` pair of functions. This is reused twice: once at discovery time (informing F18's proposals) and once as a standing runtime assertion on every replay (F19-020), per the spec-drift risk noted in plan.md §9. (see plan.md §9 "Spec drift between documented and deployed behavior")

**F16-090 — How to build it**: `tests/adapters/test_spec_validation_integration.py` — run `F16-050`'s actual create-order HTTP exchange through `F16-080`'s validators using the spec fetched/dereferenced via `F16-070` from the live demo API, confirming the full pipeline (fetch → dereference → validate real traffic) works end to end.

### Story F16.S3 — SpecDiffer + OasdiffAdapter

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F16-100 | Define `SpecDiffer` Protocol/ABC: spec-to-spec diff + severity classification | F16.S3 | F16 | F0-020 | Unit test: a trivial stub implementation satisfies the Protocol | Not Started |
| F16-110 | Implement `OasdiffAdapter` wrapping oasdiff for raw diff output | F16.S3 | F16 | F16-100 | Integration test: diff two hand-crafted spec versions, assert oasdiff's raw output is returned in a parseable form | Not Started |
| F16-120 | Implement severity classification mapping (none/cosmetic/structural-minor/structural-major per plan.md §11.2) on raw oasdiff output | F16.S3 | F16 | F16-110 | Unit test: each example change type from plan.md §11.2's table classifies to the documented severity | Not Started |
| F16-130 | Unit tests using two hand-crafted spec fixture pairs covering each severity tier | F16.S3 | F16 | F16-120 | Unit test: four fixture pairs (no live API needed), one per tier, all classify correctly | Not Started |

**F16-100 — How to build it**: `src/maya/adapters/spec_differ.py`, a Protocol `SpecDiffer` with `diff(old_spec_path, new_spec_path) -> SpecDiffResult` where `SpecDiffResult` carries the raw diff plus a `severity: Severity` (reusing the same enum defined in F8-010 for UI — one shared vocabulary across both protocols, per plan.md's explicit intent). (see plan.md §2.1, §11.2)

**F16-110 — How to build it**: `src/maya/adapters/oasdiff_adapter.py`, class `OasdiffAdapter` shelling out to the `oasdiff` CLI binary (via `subprocess`) comparing two spec file paths and parsing its JSON output mode (`oasdiff breaking` / `oasdiff diff --format json` depending on which subcommand best surfaces breaking-vs-non-breaking distinctions) into a structured Python object. (see plan.md §2.1 adapter table: "OasdiffAdapter")

**F16-120 — How to build it**: `classify_severity(raw_diff: dict) -> Severity` implementing the exact table from plan.md §11.2: no diff → `none`; description/example/tag-only changes → `cosmetic`; new optional field/param/endpoint/enum value → `structural-minor`; removed endpoint, new required field, removed required response field, type change, enum removal, auth scheme change, path param rename → `structural-major`. Map oasdiff's own breaking/non-breaking classification flags onto this vocabulary rather than re-deriving it from scratch where oasdiff already tells you. (see plan.md §11.2 table)

**F16-130 — How to build it**: `tests/adapters/test_spec_diff_severity.py` — four hand-written OpenAPI spec fixture pairs (small, focused YAML/JSON files, not the full demo API spec) each engineered to trigger exactly one severity tier, run through `OasdiffAdapter.diff()` + `classify_severity()`, asserting the expected tier each time.
