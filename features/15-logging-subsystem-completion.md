# 15 — F14 — Logging Subsystem completion (rotation + cross-component verification)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Rotation/separation verification is more meaningful once there's enough real cross-component activity (F5–F13) to actually generate log volume.

---

## F14 — Logging Subsystem completion (rotation + cross-component verification)

### Story F14.S1 — Rotation

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F14-010 | Add size-based AND time-based rotating handlers to the three loggers from F2-130, configurable retention count | F14.S1 | F14 | F2-130 | Integration test: lower the size threshold temporarily, generate enough volume, confirm rotation occurs and old files are retained per policy | Not Started |
| F14-020 | Instrument remaining components (app log: job scheduling/concurrency decisions, project CRUD, errors; api log: FastAPI request/response middleware) | F14.S1 | F14 | F14-010, F12-050, F13-010 | Manual: trigger a project CRUD action and an API request, confirm corresponding entries in app/api logs respectively | Not Started |
| F14-030 | Manual test: force size-based rotation and separately verify time-based rotation; confirm app/llm/api logs remain cleanly separated | F14.S1 | F14 | F14-020 | Manual behavioral test: both rotation triggers fire correctly and independently; no cross-contamination between the three log streams | Not Started |

**F14-010 — How to build it**: Replace `F2-130`'s plain `FileHandler` with Python's `logging.handlers.TimedRotatingFileHandler` wrapped or combined with `RotatingFileHandler` logic — since the stdlib doesn't have a single handler that does both size AND time, the practical approach is a custom handler subclass (or a small wrapper) that checks both conditions on each emit and rotates on whichever fires first, per plan.md's explicit "both conditions configured, not either/or" requirement. Configure retention count (`backupCount`) per stream. (see plan.md §8 rotation policy paragraph)

**F14-020 — How to build it**: Add `logger.info(...)`/`logger.error(...)` calls at: `JobScheduler`'s submit/dispatch/complete transitions (F12-020) and `ProjectManager`'s CRUD operations (F3-010 through F3-040) → `app` logger; and a FastAPI middleware (`@app.middleware("http")`) logging method/path/status/latency/caller for every request → `api` logger (distinct from the LLM log, and distinct from calls *to* the target system under test, which live in run reports per plan.md's explicit clarification). (see plan.md §8 table + the clarifying paragraph directly below it)

**F14-030 — How to build it**: Manual test: temporarily set the size threshold very low (e.g. 1KB) in config, generate enough log volume (a loop of dummy log calls or a few real operations), confirm a rotated backup file appears; separately, set the time window very short (e.g. a few seconds) and confirm a time-triggered rotation also occurs independent of size. Visually confirm app/llm/api entries never appear in each other's files. (see plan.md §10: "Confirm log rotation actually triggers on both size and time thresholds")
