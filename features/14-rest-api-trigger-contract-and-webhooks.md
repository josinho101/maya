# 14 — F13 — REST API Trigger Contract & Webhooks (UI scope) + notification UI

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: CI/CD-facing contract on top of F12's scheduler — needs a real scheduler behind it to be meaningful. Gains the in-dashboard notification feed.

---

## F13 — REST API Trigger Contract & Webhooks (UI scope) + notification UI

### Story F13.S1 — Run-trigger endpoints

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F13-010 | Implement `POST /api/v1/projects/{id}/runs` (environment required, falls back to default with logged warning; trigger, metadata, mode params) — submits via JobScheduler | F13.S1 | F13 | F12-050 | Integration test: POST without explicit environment falls back to default_environment and logs a warning; POST with explicit environment uses it | Not Started |
| F13-020 | Implement `GET /api/v1/runs/{run_id}` for status/live timing polling | F13.S1 | F13 | F13-010, F7-070 | Integration test: poll a running job, observe status transition from queued/running to completed | Not Started |
| F13-030 | Implement `GET /api/v1/runs/{run_id}/report` returning JSON report | F13.S1 | F13 | F13-020 | Integration test: fetch report after completion, assert it matches the persisted run_summary.json | Not Started |
| F13-040 | Implement callback_url webhook-out on run completion with retry | F13.S1 | F13 | F13-020 | Integration test: a local HTTP listener stub receives the callback payload after run completion; simulate one failed delivery and confirm a retry occurs | Not Started |
| F13-050 | Implement simple API key/bearer auth middleware for these endpoints | F13.S1 | F13 | F13-010 | Integration test: request without a valid key is rejected with 401; with a valid key, succeeds | Not Started |
| F13-060 | Manual/integration test: POST a run trigger with explicit environment, poll to completion, fetch report, confirm callback_url received the result | F13.S1 | F13 | F13-040, F13-050 | Integration test: full trigger→poll→report→callback flow in one test | Not Started |

**F13-010 — How to build it**: Upgrade `F7-090`'s synchronous run-trigger endpoint to the full async contract from plan.md §5.f: accept `environment` (optional, defaulting to `project.default_environment` with a `logger.warning(...)` call when omitted), `trigger` (manual/webhook/schedule), `metadata` (free-form dict for CI job id/commit), `mode` (`auto`/`force_reexplore`/`replay_only`) — submit a `Job` via `JobScheduler.submit()` (F12-050) and return `202 Accepted` with a `run_id` immediately rather than blocking. (see plan.md §5.f)

**F13-020 — How to build it**: `GET /api/v1/runs/{run_id}` looks up the job's current status (in-memory from `JobScheduler`, or by checking whether `runs/run_<id>/run_summary.json` exists yet on disk) and returns a status payload — `queued`/`running`/`completed`/`failed`, plus live per-test timing if the run is still in progress and partial results are available. (see plan.md §5.f)

**F13-030 — How to build it**: `GET /api/v1/runs/{run_id}/report` reads the completed `run_summary.json` (F7-070) and returns it as JSON — this is the HTML-free, JSON-only contract; an HTML rendering can be layered on later as a nice-to-have but isn't required by plan.md's REST contract section. (see plan.md §5.f)

**F13-040 — How to build it**: On job completion (inside the `JobScheduler` worker or a completion callback), if the originating run request included a `callback_url`, POST the full `RunSummary` JSON to it via `httpx`, with a simple retry (e.g. 3 attempts with backoff) on connection failure/non-2xx response. (see plan.md §5.f: "Framework POSTs the full result to callback_url on completion if provided (webhook-out, with retry)")

**F13-050 — How to build it**: A FastAPI dependency (`Depends(verify_api_key)`) checking an `Authorization: Bearer <token>` header against a configured key (from `global_config.json` or an env var) — apply this dependency to the runs router (and ideally the F3/F6/F9/F10 routers too, though that can be a fast-follow rather than blocking this task). (see plan.md §5.f: "Auth via simple API key/bearer token")

**F13-060 — How to build it**: `tests/api/test_runs_webhook.py` spinning up a tiny local HTTP server (e.g. via `http.server` in a background thread, or a pytest fixture using `httpx`'s mock transport) to act as the `callback_url` target, then exercising the full POST→poll→report→callback sequence against a real (small) approved test case set.

### Story F13.S2 — In-dashboard notification feed UI

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F13-070 | Implement `NotificationChannel`/`DashboardChannel`: backend notification store + `GET /notifications` endpoint, emitting on new-pending-test-cases, run-completed, heal-applied/flagged, run-failed | F13.S2 | F13 | F13-010, F9-100, F6-040 | Integration test: trigger each notification-worthy event, assert a corresponding notification record appears | Not Started |
| F13-080 | Build the in-dashboard notification feed (bell icon + list) | F13.S2 | F13 | F13-070, F0-090 | Manual UI walkthrough: trigger a run and an exploration, see both completion notifications appear in the feed | Not Started |

**F13-070 — How to build it**: `src/maya/adapters/notification_channel.py` defining a `NotificationChannel` Protocol (per plan.md §2.1's adapter table) with a `DashboardChannel` concrete implementation that just appends to a simple file-backed or in-memory list of `{id, type, message, created_at, read: bool}` records — call `.notify(...)` from the relevant existing call sites (end of `F5-080`'s exploration run, end of `F13-010`'s run completion, F9-070/080's apply/flag paths, run failure paths). Expose `GET /api/v1/notifications` to list them. (see plan.md §2.1 adapter table, §2.3 Notification Service row)

**F13-080 — How to build it**: Add a `NotificationBell.tsx` component in `AppShell.tsx` (from F0-090) polling `GET /api/v1/notifications` periodically (or on-demand on click), showing an unread count badge and a dropdown list of recent notifications, each clickable to navigate to the relevant test case/run/healing item. (see plan.md §2.3: "New-test-case notifications surface in the web dashboard")
