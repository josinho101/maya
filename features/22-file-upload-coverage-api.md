# 22 — F22 — File-Upload Coverage (API side / multipart)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Shares F11's fixture library; adds multipart support to F16's HTTPXAdapter and F18's Discovery Agent. Small, sequenced after the core API loop is proven.

---

## F22 — File-Upload Coverage (API side / multipart)

### Story F22.S1 — Multipart discovery + execution

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F22-010 | Extend APIDiscoveryAgent to detect multipart/form-data request bodies in the spec and select a fixture, emitting body_type:"multipart" steps | F22.S1 | F22 | F18-020, F11-020 | Integration test: against the demo API's attachment endpoint, agent proposes a multipart step with a valid fixture_ref | Not Started |
| F22-020 | Confirm APITestRunner's multipart step execution (F19-030) end-to-end against the demo's multipart endpoint with an agent-proposed test case | F22.S1 | F22 | F22-010, F19-030 | Integration test: replay the agent-proposed multipart test case, assert the upload succeeds | Not Started |
| F22-030 | Manual test: run discovery against the multipart endpoint, approve, replay, confirm successful upload using a built-in fixture | F22.S1 | F22 | F22-020 | Manual end-to-end test across discovery, approval, and replay | Not Started |

**F22-010 — How to build it**: In `APIDiscoveryAgent.discover()` (F18-010/020), when an operation's request body schema indicates `multipart/form-data` content type, propose a step with `body_type: "multipart"` and `files: [{"field": <field_name_from_spec>, "fixture_ref": <selected>}]` instead of a plain JSON `body` — select the fixture the same way `F11-030` does for UI (package's `upload_fixtures` first, falling back to built-ins by MIME compatibility via `F11-020`'s resolver). (see plan.md §11.5 bullet: "Selects upload fixtures for multipart endpoints", §5.j step 1)

**F22-020 — How to build it**: Run `F18-070`'s discovery flow against `F16-040`'s `/orders/{id}/attachment` endpoint specifically, take the resulting proposed test case (not a hand-written one — this validates the agent's own proposal, not just the runner's plumbing), approve it via F6, and replay via `F19-030`'s already-built multipart execution path, confirming the file actually arrives at the demo API correctly.

**F22-030 — How to build it**: End-to-end manual test combining F22-010 and F22-020 into one human-driven walkthrough: trigger discovery, observe the multipart step proposal in the dashboard (F18-100's detail view), approve it, trigger a run, confirm success in the report — using a built-in fixture (not a project-supplied one) to specifically confirm the built-in fallback path works for API uploads too. (see plan.md §10: "Verify file-upload coverage end-to-end: a UI file-input field and an API multipart endpoint both resolve fixture_ref correctly")
