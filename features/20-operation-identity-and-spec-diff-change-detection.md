# 20 — F20 — Operation Identity & Spec-Diff Change Detection + notification extension

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: The API analog of F8; needs F18 (baseline spec) and F19 (replay to gate) plus F16's SpecDiffer. Extends F13's notification feed with contract-change alerts.

---

## F20 — Operation Identity & Spec-Diff Change Detection + notification extension

### Story F20.S1 — Diff + gate

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F20-010 | Implement operation-identity key derivation (operationId else method+path template) used to group/tag test cases | F20.S1 | F20 | F18-060 | Unit test: a spec with explicit operationIds derives those; one without derives method+path template correctly | Not Started |
| F20-020 | Implement spec re-fetch/dereference/hash/diff-against-pinned-version flow using F16-110/F16-120 | F20.S1 | F20 | F16-120, F17-040 | Integration test: re-fetch an unchanged demo spec, assert hash matches and no diff is recorded; mutate the demo spec, assert a diff with correct severity | Not Started |
| F20-030 | Wire severity into the three-way gate: none/cosmetic→silent re-pin; structural-minor→scoped discovery for new ops only; structural-major→affected test cases flagged for healing not hard-failed | F20.S1 | F20 | F20-020, F20-010, F18-070 | Integration test: each of the three severity paths produces the documented behavior against the demo API | Not Started |
| F20-040 | Persist new spec version to specs/<new_hash>/ with diff artifact, update index.json | F20.S1 | F20 | F20-020 | Manual file inspection: after a spec change, the new version directory and updated index.json both exist with correct content | Not Started |
| F20-050 | Manual verification (mirrors F8-050): unchanged spec → zero AI-queue calls on second pass; additive change → scoped-only re-discovery; breaking change → affected test cases flagged not hard-failed | F20.S1 | F20 | F20-030, F20-040 | Manual behavioral/idempotency proof: llm log shows zero entries for the unchanged-spec run; exactly the scoped delta for the additive run; affected test cases show needs_review-equivalent flag, not outright failure, for the breaking run | Not Started |

**F20-010 — How to build it**: `src/maya/perception/operation_identity.py`, function `operation_identity(spec_operation: dict, method: str, path_template: str) -> str` returning `spec_operation.get("operationId") or f"{method} {path_template}"` — note this must use the path *template* (`/orders/{id}`), never a resolved path with a real id substituted in, so the identity stays stable regardless of which specific order is exercised. This is the direct API analog of F4-030's `view_identity`. (see plan.md §11.1 concept mapping table, §4 closing paragraph)

**F20-020 — How to build it**: `src/maya/perception/spec_diff_engine.py`, function `check_for_spec_changes(environment) -> SpecDiffResult` that calls `PranceOpenAPIAdapter.fetch_and_dereference()` (F16-070) again, hashes the result, compares against `specs/index.json`'s currently pinned hash — if identical, return a `none` result immediately without invoking oasdiff at all (cheap short-circuit); if different, call `OasdiffAdapter.diff()` + `classify_severity()` (F16-110/120) between the old and new dereferenced spec files. (see plan.md §5.h step 1)

**F20-030 — How to build it**: Mirror `F8-040`'s three-way branch structure exactly, but on the API side: `none`/`cosmetic` → just re-pin the new hash silently (or skip re-pinning entirely if the hash didn't change); `structural-minor` → existing approved API test cases keep running unmodified (additive changes don't break them), and call `run_api_discovery()` (F18-070) scoped to *only* the new/changed operation identities (filter the spec passed to the agent down to just those operations); `structural-major` → identify affected test cases by intersecting their `operation_ids` with the changed operations, and mark them for the next run's healing pass (F21) rather than failing them outright now — unaffected test cases run normally. (see plan.md §5.h step 2)

**F20-040 — How to build it**: After a successful diff, write the new dereferenced spec to `environments/<env_id>/specs/<new_hash>/openapi.json`, write the diff artifact alongside it (`diff_from_previous.json`, the raw oasdiff output plus the classified severity), and update `specs/index.json` to point at the new hash as current while retaining history of prior hashes. (see plan.md §3.3 specs/ directory shape)

**F20-050 — How to build it**: Three-part manual verification mirroring `F8-050` exactly but for the API side: (1) run `check_for_spec_changes()` twice with no edits to the demo API's spec, confirm the second pass makes zero LLM calls (check the `llm` log, F2-140) since the hash-equality short-circuit in F20-020 never even reaches oasdiff; (2) add a new optional field to the demo API's response model, confirm exactly one scoped discovery call appears in the llm log, limited to the changed operation; (3) make a breaking change (remove a required field), confirm the affected test case(s) are flagged rather than hard-failed on the next run. (see plan.md §10: "Validate the spec-diff gate analogously")

### Story F20.S2 — Contract-change notification UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F20-060 | Emit a contract-change notification (via F13-070's NotificationChannel) on structural-minor/structural-major spec diffs | F20.S2 | F20 | F20-050, F13-070 | Integration test: a breaking spec change produces a notification record distinguishable from ordinary run-completed notifications | Not Started |
| F20-070 | Surface contract-change notifications distinctly in F13-080's notification feed (e.g. a "Contract Change" badge/icon) | F20.S2 | F20 | F20-060, F13-080 | Manual UI walkthrough: a breaking spec change produces a visibly distinct entry in the notification feed | Not Started |

**F20-060 — How to build it**: At the point in `F20-030` where a `structural-minor`/`structural-major` diff is detected, call `NotificationChannel.notify(...)` (F13-070) with a `type: "contract_change"` and a payload including the severity, affected operation_ids, and a link to the diff artifact — this reuses the exact same notification mechanism as run-completed/heal-flagged events, just a new `type` value. (see plan.md §2.3 Notification Service row: "contract change detected")

**F20-070 — How to build it**: In `NotificationBell.tsx` (F13-080), branch rendering on `notification.type` — `contract_change` entries get a distinct icon/color (e.g. a warning-colored chip) and link through to a simple diff view (can reuse F20-040's persisted `diff_from_previous.json`, rendered as raw JSON or a simple before/after list for MVP — a rich diff UI isn't required by the plan).
