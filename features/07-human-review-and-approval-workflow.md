# 07 — F6 — Human Review & Approval Workflow + review UI

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Once `pending/` test cases exist (F5), the approval lifecycle must exist before anything can be promoted to deterministic replay. Gains its review/approve/reject/edit screen in this epic.

---

## F6 — Human Review & Approval Workflow + review UI

### Story F6.S1 — Approval API endpoints

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F6-010 | Implement `GET /projects/{id}/test-cases?status=pending&protocol=`, `POST /test-cases/{id}/approve`, `POST /test-cases/{id}/reject` | F6.S1 | F6 | F1-050, F0-050 | Integration test: list pending test cases from F5-080's output, approve one, assert it moves to approved | Not Started |
| F6-020 | Wire endpoints to `TestCaseStore` move operations (pending→approved, pending→archived with rejection reason) | F6.S1 | F6 | F6-010, F1-050 | Integration test: reject a pending test case with a reason, assert it lands in archived/ with the reason persisted | Not Started |
| F6-030 | Add inline-edit support: `PATCH /test-cases/{id}` to modify steps before approval | F6.S1 | F6 | F6-010 | Integration test: PATCH a pending test case's steps, re-GET it, assert the edit persisted | Not Started |
| F6-040 | API tests: approve a pending test case produced by F5, assert moved with status; reject one, assert archived with reason | F6.S1 | F6 | F6-020, F5-080 | Integration test: full pending→approved and pending→archived flows against a real F5-produced test case | Not Started |

**F6-010 — How to build it**: `src/maya/api/routers/test_cases.py`, FastAPI router with `GET /api/v1/projects/{project_id}/test-cases` accepting `status` and optional `protocol` query params (the `protocol` param is the explicitly tracked gap-fill item — add it now even though only `"ui"` test cases exist until F18, so the contract doesn't need to change later), `POST .../approve`, `POST .../reject` (body: `{"reason": str}`). Each thinly wraps `TestCaseStore` (F1-050) calls. (see plan.md §5.c, and the tracked gap noted in the plan: protocol filter added pre-emptively)

**F6-020 — How to build it**: `approve` calls `TestCaseStore.move(id, "pending", "approved")` and updates the test case's `status` field to `"approved"` before re-writing; `reject` calls `move(id, "pending", "archived")`, additionally stamping a `rejection_reason` field (extend `TestCaseBase` in F1-030 with an optional field, or store it in a sidecar — prefer adding the field directly to the model for simplicity). (see plan.md §5.c)

**F6-030 — How to build it**: `PATCH /api/v1/test-cases/{id}` reads the current test case (regardless of which status directory it's in — `TestCaseStore` needs a `find(id) -> (test_case, current_status)` helper if it doesn't have one yet), applies a partial update to `steps`, and re-writes in place (no status change). This is what lets a human fix a slightly-wrong locator before approving rather than rejecting outright. (see plan.md §5.c: "User views steps/assertions, edits inline if needed")

**F6-040 — How to build it**: `tests/api/test_test_case_approval.py` using `TestClient`, seeded by first running `F5-080`'s exploration flow (or a hand-written fixture test case dropped directly into `pending/` to avoid a live-LLM dependency in this test) — assert the full approve and reject flows via HTTP calls only.

### Story F6.S2 — Pending test case review/approve/reject/edit UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F6-050 | Build pending test case list screen (filterable by protocol, though only "ui" exists for now) | F6.S2 | F6 | F6-040, F0-090 | Manual UI walkthrough: pending test cases from a real exploration run appear in the list | Not Started |
| F6-060 | Build test case detail/edit view (steps table, inline field editing) | F6.S2 | F6 | F6-050 | Manual UI walkthrough: open a pending test case, edit a step's locator value, save, confirm persisted via F6-030 | Not Started |
| F6-070 | Wire Approve/Reject actions (reject requires a reason) into the detail view | F6.S2 | F6 | F6-060 | Manual UI walkthrough: approve one test case and reject another with a reason; confirm both land in the correct status via the API | Not Started |

**F6-050 — How to build it**: `frontend/src/pages/TestCasesPending.tsx` using MUI `DataGrid` calling `GET /api/v1/projects/{id}/test-cases?status=pending`, with a protocol filter `ToggleButtonGroup` (UI/API tabs — API tab stays empty/disabled until F18-extends this screen). Wire into the `/test-cases` route placeholder from F0-090. (see plan.md §2.3: "tabbed per test type")

**F6-060 — How to build it**: Clicking a row opens `TestCaseDetail.tsx` rendering `steps[]` as an editable MUI `Table` (one row per step, fields for action/target.strategy/target.value/input editable in place), saving via `F6-030`'s PATCH endpoint on blur or an explicit Save button.

**F6-070 — How to build it**: Add "Approve" and "Reject" buttons to `TestCaseDetail.tsx` — Approve calls `F6-010`'s approve endpoint directly; Reject opens a small MUI dialog requiring a reason string before calling the reject endpoint. On success, navigate back to the list and confirm the row disappears from the pending filter.
