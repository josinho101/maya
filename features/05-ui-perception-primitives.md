# 05 — F4 — UI Perception Primitives (View Snapshot baseline)

See [`stories.md`](stories.md) for the legend/conventions and [`plan.md`](plan.md) for architecture context.

**Rationale for this position**: Before the Exploration Agent can "perceive," the Browser Controller must deterministically capture and persist a baseline view snapshot — a non-LLM capability that later change-detection (F8) consumes.

---

## F4 — UI Perception Primitives (View Snapshot baseline)

### Story F4.S1 — Structural fingerprint + baseline snapshot capture

| Task ID | Task | Story | Feature | Depends On | Verification | Status |
|---|---|---|---|---|---|---|
| F4-010 | Implement structural-fingerprint function: hash of main-content-container role/landmark structure from AX-tree | F4.S1 | F4 | F2-080 | Unit test: two AX-trees differing only in non-structural text hash identically; a structurally different tree hashes differently | Done |
| F4-020 | Implement heading/title signal extraction | F4.S1 | F4 | F2-080 | Unit test: extract heading text from a sample AX-tree/DOM, assert correct string returned | Done |
| F4-030 | Implement `ViewSnapshotEngine.capture(page) -> ViewSnapshotRecord` combining URL+hash+heading into a composite view-identity key, persisting to `view_snapshots/<slug>/<timestamp>.json` | F4.S1 | F4 | F4-010, F4-020, F1-040, F2-080 | Integration test: capture against the demo page, assert a `ViewSnapshotRecord` JSON file is written with a non-empty `view_identity` | Done |
| F4-040 | Integration test: view_identity is stable across two captures with no DOM change, and differs for a structurally distinct second view | F4.S1 | F4 | F4-030 | Integration test: capture twice unchanged → same slug; capture after opening a modal/second view → different slug | Done |

**F4-010 — How to build it**: `src/maya/perception/view_identity.py`, function `structural_fingerprint(ax_tree: dict) -> str` that walks the AX-tree (from F2-080's `get_ax_tree()`), extracts just the `role`/landmark-relevant nodes (main, tabpanel, dialog root) ignoring leaf text content, serializes that reduced structure deterministically (sorted keys), and returns a hash (`hashlib.sha256(...).hexdigest()[:16]` is plenty). This is signal #2 of the composite key in plan.md §4. (see plan.md §4)

**F4-020 — How to build it**: `heading_signal(ax_tree: dict, dom_html: str) -> str` — prefer the AX-tree's active heading-role node text; fall back to `<title>` from `get_dom_html()` (F2-090) if no heading node is found. This is signal #3, used as a tiebreaker when fingerprints are close. (see plan.md §4)

**F4-030 — How to build it**: `src/maya/perception/snapshot_engine.py`, class `ViewSnapshotEngine(root_dir)` with `capture(driver: BrowserDriver, project_id, env_id) -> ViewSnapshotRecord` that calls `driver.get_ax_tree()`/`screenshot()`, combines `page.url` (signal #1) + `structural_fingerprint()` (signal #2) + `heading_signal()` (signal #3) into a `view_identity` string (e.g. `f"{url_path}::{fingerprint}::{slugify(heading)}"`), builds a `ViewSnapshotRecord` (F1-040), and writes it under `environments/<env_id>/view_snapshots/<slugified_view_identity>/<timestamp>.json`. (see plan.md §4, §3.3)

**F4-040 — How to build it**: `tests/perception/test_snapshot_engine.py` against `F2-110`'s demo page — capture, capture again unchanged, assert identical `view_identity`; then add a second demo fixture page (or a button that reveals a hidden modal-like section with a different landmark structure on the same page) and assert a third capture against that state produces a different `view_identity` slug.
