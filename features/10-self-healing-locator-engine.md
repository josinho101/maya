# 10 — F9 — Self-Healing Locator Engine + healing review UI

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Triggered on step failure during F7 execution — cannot precede F7 (nothing to fail) or F4 (nothing to re-perceive with). Gains its healing review queue screen.

---

## F9 — Self-Healing Locator Engine + healing review UI

### Story F9.S1 — Failure classification

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F9-010 | Implement failure classifier in ExecutionEngine: locator_not_found / element_changed_state / assertion_failure / timeout | F9.S1 | F9 | F7-010 | Unit test: each induced failure mode classifies to the correct category | Not Started |

**F9-010 — How to build it**: In `ExecutionEngine.run_test_case()` (F7-010), wrap the locator-resolution step specifically: a Playwright "element not found" exception → `locator_not_found`; an element found but in an unexpected state (disabled, hidden) → `element_changed_state`; an assertion mismatch after a successful action → `assertion_failure`; a Playwright timeout exception → `timeout`. Only the first two are eligible for locator healing per plan.md — tag the result with this classification regardless, since it's useful diagnostic info either way. (see plan.md §5.e step 1)

### Story F9.S2 — Fallback hierarchy

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F9-020 | Implement candidate generation tier 1-2: data-testid match, aria-label/role match against current AX-tree | F9.S2 | F9 | F2-080, F9-010 | Unit test: given a mutated AX-tree, tier 1/2 candidate generators return plausible matches with expected attributes | Not Started |
| F9-030 | Implement tier 3-4: visible-text match, relative DOM position match | F9.S2 | F9 | F9-020 | Unit test: synthetic case where only text/position matching succeeds returns a sane candidate | Not Started |
| F9-040 | Implement tier 5: XPath similarity scoring | F9.S2 | F9 | F9-030 | Unit test: candidate XPath similarity score reflects expected ranking on a synthetic before/after pair | Not Started |
| F9-050 | Implement tier 6 (last resort): combined DOM+vision re-grounding via LLMClient multimodal call | F9.S2 | F9 | F9-040, F2-030 | Integration test: a drastic mutation with no structural similarity still produces a candidate via the vision fallback | Not Started |
| F9-060 | Implement confidence scoring (attribute similarity, element stability, specificity, context match, visual match weighted combination) | F9.S2 | F9 | F9-050 | Unit test: known-good rename scores high confidence; known-bad ambiguous case scores low | Not Started |

**F9-020 — How to build it**: `src/maya/engines/healing_engine.py`, function `generate_candidates(original_locator, current_ax_tree) -> list[Candidate]` — tier 1 looks for an exact `data-testid` match elsewhere in the tree (handles simple renames where the *value* changed but other attributes are stable); tier 2 looks for matching `aria-label`/`role` combination. Each candidate carries its tier and a raw similarity score before final confidence weighting (F9-060). (see plan.md §2.3 Self-Healing Engine row, §5.e step 2)

**F9-030 — How to build it**: Tier 3 does fuzzy text matching (e.g. `difflib.SequenceMatcher`) against visible text nodes near the original locator's last-known position; tier 4 compares the element's position in the DOM tree relative to stable siblings/ancestors (e.g. "3rd button inside the same form"). Both append to the same `candidates` list with their tier tagged.

**F9-040 — How to build it**: Tier 5 computes an XPath-like path string for both the original (from the last healthy snapshot) and each current-tree element, scoring similarity via edit distance — this catches cases where the element moved in the tree but kept a recognizably similar path shape.

**F9-050 — How to build it**: Tier 6 (only reached if tiers 1-5 produced nothing above a minimal floor) calls `LLMClient.generate()` (F2-030) with the current AX-tree text + screenshot + a description of what the original element was/did, asking the model to identify the most likely replacement element — this is the *only* tier touching the AI queue, consistent with plan.md's framing of vision-as-last-resort for healing specifically (distinct from exploration, which always uses vision). (see plan.md §1.1 contrast, §5.e step 2 "combined DOM+vision re-grounding as last resort")

**F9-060 — How to build it**: `score_confidence(candidate) -> float` combining attribute similarity, element stability (has this candidate's underlying ref been seen consistently across recent snapshots), specificity (does the candidate uniquely match, or is it ambiguous among several), context match (same parent form/section as original), and visual match (screenshot region similarity, when the vision tier ran) into one weighted 0-1 score — model the weights after Healenium's approach per plan.md's explicit reference. (see plan.md §5.e step 2: "modeled on Healenium's weighted approach")

### Story F9.S3 — Apply/flag decision + healing log

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F9-070 | Implement auto-apply path: confidence ≥ 0.90 → patch locator, bump version, log auto_applied:true, resume run | F9.S3 | F9 | F9-060, F1-050 | Integration test: high-confidence rename auto-heals and the run continues to pass | Not Started |
| F9-080 | Implement flag-for-review path: confidence < threshold → needs_review, fail step, healing log with before/after | F9.S3 | F9 | F9-060, F1-050 | Integration test: low-confidence mutation flags needs_review and the run reports a failure | Not Started |
| F9-090 | Wire ExecutionEngine to invoke the healing engine inline on eligible failures instead of immediately failing | F9.S3 | F9 | F9-070, F9-080, F7-010 | Integration test: a locator_not_found failure triggers healing inline within the same run, not a separate pass | Not Started |
| F9-100 | Manual end-to-end test: rename a data-testid (high-confidence heal) → auto-heal + pass; drastic change (low-confidence) → needs_review + failure with healing log entry | F9.S3 | F9 | F9-090 | Manual behavioral test: both scenarios produce the documented outcome, inspected via the healing log file | Not Started |

**F9-070 — How to build it**: When the top-scored candidate from F9-060 has `confidence >= project.healing.auto_apply_threshold` (default 0.90, from `Project` model F1-010), patch the test case's step `target` in place via `TestCaseStore` (bumping a `locator_confidence`/version field on the `UITestCase`), append a `HealingEventLogEntry` (F1-040) with `auto_applied=true` to `healing_logs/tc_<uuid>_healing.json`, and resume execution using the new locator for this step. (see plan.md §5.e step 3 first bullet)

**F9-080 — How to build it**: Below threshold, do *not* patch the test case — set `status: needs_review` on the test case (or a side annotation, since the test case itself might still be otherwise valid), record the failed step as a final failure for this run, and append a `HealingEventLogEntry` with `auto_applied=false`, including both `original_locator` and the best (rejected) candidate for human comparison. (see plan.md §5.e step 3 second bullet)

**F9-090 — How to build it**: In `ExecutionEngine.run_test_case()`, change the failure path so that when `F9-010`'s classifier returns `locator_not_found` or `element_changed_state`, call into `HealingEngine` (F9-070/080) *before* recording a final step result — only if healing produces no viable candidate at all does it fall through to a hard failure (optionally flagging for full regeneration, a stretch goal noted in plan.md but not required for MVP). (see plan.md §5.e step 1 intro, §2.3 Execution Engine: "Invokes Self-Healing Engine inline on locator/assertion failures")

**F9-100 — How to build it**: Manual test script: take a passing approved test case from F7, rename its target's `data-testid` on the demo page HTML (small, high-similarity change) — re-run, confirm the run still passes and `healing_logs/tc_<id>_healing.json` shows `auto_applied: true`. Then make a drastic change (remove the element entirely, or change it beyond recognition) — re-run, confirm the run fails this step, the test case is flagged `needs_review`, and the healing log shows `auto_applied: false` with both locators recorded. (see plan.md §5.e step 3 closing, §10)

### Story F9.S4 — Healing review queue UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F9-110 | Add `GET /test-cases/{id}/healing-log` and `POST /healing/{heal_id}/resolve` (accept/reject a flagged heal) endpoints | F9.S4 | F9 | F9-100, F0-050 | Integration test: fetch a healing log for a flagged test case, resolve it, assert status updates | Not Started |
| F9-120 | Build healing review queue screen listing needs_review items with before/after locator + screenshots | F9.S4 | F9 | F9-110, F0-090 | Manual UI walkthrough: a flagged heal from F9-100's drastic-change scenario appears in the queue with both screenshots visible | Not Started |

**F9-110 — How to build it**: `src/maya/api/routers/healing.py`, `GET /api/v1/test-cases/{id}/healing-log` reads `healing_logs/tc_<id>_healing.json` and returns the list of `HealingEventLogEntry` records; `POST /api/v1/healing/{heal_id}/resolve` accepts `{"action": "accept"|"reject"}` — accept behaves like a manual auto-apply (patches the locator using the flagged candidate), reject clears the `needs_review` flag without changing the locator (human will fix it manually via F6's edit UI instead). (see plan.md §5.e step 3: "notify actively in-dashboard with before/after locator + screenshots")

**F9-120 — How to build it**: `frontend/src/pages/HealingQueue.tsx` listing all `needs_review` test cases project-wide (or per-project, filtered) via `F9-110`'s endpoint, each row expandable to show the before/after locator values and the two screenshots side-by-side (failure screenshot from F7-030, plus any vision-tier screenshot from F9-050), with Accept/Reject buttons calling the resolve endpoint. Wire into the `/healing` route placeholder from F0-090.
