# 21 — F21 — API Healing Engine + healing UI extension

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: The API analog of F9; triggered on F19 failures attributable to contract drift, using F20's diff context. Extends F9's healing review screen with the API protocol tab.

---

## F21 — API Healing Engine + healing UI extension

### Story F21.S1 — Failure classification

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F21-010 | Implement API failure classifier in APITestRunner: expected_status mismatch with structurally-explainable cause, schema validation failure, field-not-found at request-build time | F21.S1 | F21 | F19-020 | Unit test: each induced failure mode classifies to the correct category | Not Started |

**F21-010 — How to build it**: In `APITestRunner.run_test_case()` (F19-010), wrap request-building and response-assertion separately: a placeholder/field referenced in `step.body`/`path_params` that doesn't exist in the prior step's `extract` output → `field_not_found`; a response that fails `schema_match` → `schema_validation_failure`; an `expected_status` mismatch where the actual status is explainable by a known spec change (cross-reference against the latest `diff_from_previous.json` from F20-040) → `contract_drift_status_mismatch`. Tag every failure with one of these categories before deciding healing eligibility. (see plan.md §5.i step 1)

### Story F21.S2 — Fallback hierarchy

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F21-020 | Implement tier 1-2: exact field/param match, fuzzy name match (Levenshtein) with type-compatibility check | F21.S2 | F21 | F21-010, F20-020 | Unit test: an unchanged field matches exactly at tier 1; a renamed-but-similar field (order_id→orderId) matches at tier 2 with high confidence | Not Started |
| F21-030 | Implement tier 3: type-compatible positional match | F21.S2 | F21 | F21-020 | Unit test: a field renamed beyond fuzzy-match similarity but occupying the same schema position matches at tier 3 with lower confidence | Not Started |
| F21-040 | Implement tier 4: operationId/tag/summary match for path changes, re-binding the test case's operation reference | F21.S2 | F21 | F21-030, F20-010 | Unit test: a path change (/orders/{id}→/v2/orders/{orderId}) with a stable operationId re-binds correctly | Not Started |
| F21-050 | Implement tier 5: auth scheme migration using available package fields | F21.S2 | F21 | F21-040 | Unit test: an API-key-to-bearer-token auth scheme change attempts migration using the package's available credential fields | Not Started |
| F21-060 | Implement tier 6 (last resort): LLM semantic field remapping via LLMClient (old schema + new schema + test case intent) | F21.S2 | F21 | F21-050, F2-040 | Integration test: a drastic, non-fuzzy-matchable rename still produces a remapping candidate via the LLM tier | Not Started |
| F21-070 | Implement param-relocation handling (query↔body moves) directly from oasdiff's structured in-change output, within tier 3/4 | F21.S2 | F21 | F21-040, F16-110 | Unit test: a param moved from query to body is detected and relocated correctly without needing fuzzy inference | Not Started |

**F21-020 — How to build it**: `src/maya/engines/api_healing_engine.py`, function `generate_field_candidates(original_field, new_schema) -> list[Candidate]` — tier 1 checks if `original_field` still exists unchanged in `new_schema` (confidence 1.0, "not really a heal"); tier 2 computes Levenshtein distance (e.g. via `python-Levenshtein` or a small custom implementation) between `original_field` and every field name in `new_schema`, accepting close matches with compatible types as high-confidence candidates. (see plan.md §11.6 table rows 1-2)

**F21-030 — How to build it**: Tier 3 compares the *position*/role of `original_field` within its parent schema (e.g. "3rd property, same type, same required-ness") against fields in `new_schema` occupying an analogous position — lower confidence since this is structural rather than nominal similarity, used when fuzzy name matching alone doesn't clear its threshold. (see plan.md §11.6 table row 3)

**F21-040 — How to build it**: Tier 4 handles the case where the *path itself* changed (not just a field) — check if the test case's `operation_id` (from F20-010) still resolves to an operation in the new spec via a stable `operationId`/tag/summary text match even though the path template differs, and if so, re-bind the test case's `path`/`operation_id` reference to the new path template. (see plan.md §11.6 table row 4)

**F21-050 — How to build it**: Tier 5 triggers specifically when oasdiff's diff output (from F20-020) flags an auth-scheme-level change (e.g. `apiKey` header → `bearer` token) — attempt to construct the new auth header shape using whichever credential fields the environment's `api` package already has available (e.g. if it has a bearer token value stored under a different key, use it; if genuinely nothing maps, this tier produces no candidate and falls through to tier 6). (see plan.md §11.6 table row 5)

**F21-060 — How to build it**: Tier 6, only reached if tiers 1-5 produce nothing above a minimal floor, calls `LLMClient.generate()` (text-only, `task_role="api_reasoning"`, F2-040) with the old schema, new schema, and the test case's intent (inferred from its `tags`/`assertions`) as context, asking the model to propose the most likely field remapping. This is the only tier touching the AI queue. (see plan.md §11.6 table row 6)

**F21-070 — How to build it**: Since oasdiff's structured diff output explicitly reports parameter `in` changes (query→body or vice versa) as a distinct diff entry type, detect this directly from the raw diff (F16-110's output, before severity classification even) rather than trying to infer it via fuzzy matching — relocate the test case step's field from `query_params` to `body` (or back) accordingly, slotting this logic into tier 3/4's candidate generation rather than as a separate tier. (see plan.md §11.6 closing paragraph: "Param relocation... is detected directly from oasdiff's structured diff output... and handled within tier 3/4")

### Story F21.S3 — Apply/flag decision + healing log

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F21-080 | Implement auto-apply (≥0.90) and flag-for-review (<threshold) paths writing to the same healing-log shape as F9-070/080 (original_mapping generalization) | F21.S3 | F21 | F21-060, F21-070, F1-050 | Integration test: a high-confidence fuzzy-match rename auto-heals; a low-confidence ambiguous case flags needs_review | Not Started |
| F21-090 | Wire APITestRunner to invoke APIHealingEngine inline on classified failures instead of hard-failing | F21.S3 | F21 | F21-080, F21-010 | Integration test: a field_not_found failure triggers healing inline within the same run | Not Started |
| F21-100 | Manual end-to-end test: rename a field in the demo API (high-confidence fuzzy match) → auto-heal; change a path structurally → tier-4-or-lower with correct confidence-gated outcome | F21.S3 | F21 | F21-090 | Manual behavioral test: both scenarios produce the documented outcome, inspected via the healing log file | Not Started |

**F21-080 — How to build it**: Identical structure to `F9-070`/`F9-080` but operating on field/mapping candidates instead of locators: confidence ≥ `project.healing.auto_apply_threshold` → patch the test case's affected step field mapping in place via `TestCaseStore`, append a `HealingEventLogEntry` (F1-040) with `auto_applied: true` and `original_mapping` (the API-side generalization of `original_locator`, per F1-040's note) to the *same* `healing_logs/tc_<uuid>_healing.json` file shape used by UI healing — no schema divergence between protocols. (see plan.md §5.i step 2, §3.4 healing event log entry note)

**F21-090 — How to build it**: In `APITestRunner.run_test_case()`, when `F21-010`'s classifier returns `field_not_found` or `schema_validation_failure` (the API-side eligible categories, analogous to UI's `locator_not_found`/`element_changed_state`), call into `APIHealingEngine` (F21-080) before recording a final step result — same inline-invocation pattern as `F9-090`. (see plan.md §5.i step 1 intro)

**F21-100 — How to build it**: Manual test script: take the passing test case from `F19-050`, rename a response field on the demo API (e.g. `status` → `orderStatus`, a fuzzy-matchable rename) — re-run, confirm auto-heal applied and the run passes, with the healing log showing `auto_applied: true`. Then change the path structurally (`/orders/{id}` → `/v2/orders/{orderId}`) while keeping `operationId` stable — re-run, confirm tier 4's re-binding triggers with the correct confidence-gated outcome recorded in the healing log. (see plan.md §11.6 table rows 2 and 4, §10)

### Story F21.S4 — API protocol tab on healing review UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F21-110 | Extend F9-110's healing-log endpoint and F9-120's healing review screen to render API healing events (field/mapping before-after instead of locator before-after) | F21.S4 | F21 | F21-100, F9-120 | Manual UI walkthrough: an API healing event from F21-100 appears in the healing queue with field-mapping before/after rendered correctly | Not Started |

**F21-110 — How to build it**: `F9-110`'s `GET /api/v1/test-cases/{id}/healing-log` endpoint already returns whatever's in the shared healing-log file shape, so no backend change is needed beyond confirming `original_mapping` (vs `original_locator`) round-trips correctly. In `HealingQueue.tsx` (F9-120), branch the before/after rendering on whether the entry has a `original_locator` or `original_mapping` field — locator entries render strategy/value as before, mapping entries render the old/new field name and type instead of screenshots (no visual signal applies to API healing). (see plan.md §5.i step 3: "same file, same shape, just original_locator generalizes to original_mapping")
