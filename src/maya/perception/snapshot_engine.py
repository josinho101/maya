"""`ViewSnapshotEngine`: captures a deterministic baseline `ViewSnapshotRecord` for
whatever view a `BrowserDriver` is currently on, keyed by the composite view-identity
from plan.md §4 (URL signal + structural fingerprint + heading tiebreaker), and
(F8-010) diffs two such records into a `Severity` classification."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from maya.adapters.browser_driver import BrowserDriver
from maya.managers.slugify import slugify
from maya.perception.elements import extract_elements
from maya.perception.view_identity import heading_signal, structural_fingerprint
from maya.storage.atomic import atomic_write_bytes, atomic_write_json
from maya.storage.models import Severity, ViewSnapshotElement, ViewSnapshotRecord


def _element_key(element: ViewSnapshotElement) -> str:
    return element.data_testid or element.path_fingerprint or element.ref


def _url_signal(url: str) -> str:
    parts = urlsplit(url)
    signal = parts.path or "/"
    if parts.query:
        signal += f"?{parts.query}"
    if parts.fragment:
        signal += f"#{parts.fragment}"
    return signal


class ViewSnapshotEngine:
    def __init__(self, root_dir: Path) -> None:
        self._root_dir = Path(root_dir)

    def _env_view_snapshots_dir(self, project_id: str, env_id: str) -> Path:
        return self._root_dir / "projects" / project_id / "environments" / env_id / "view_snapshots"

    def capture(self, driver: BrowserDriver, project_id: str, env_id: str) -> ViewSnapshotRecord:
        ax_tree = driver.get_ax_tree()
        dom_html = driver.get_dom_html()

        fingerprint = structural_fingerprint(ax_tree)
        heading = heading_signal(ax_tree, dom_html)
        heading_slug = slugify(heading) if heading else "untitled"
        view_identity = f"{_url_signal(driver.current_url())}::{fingerprint}::{heading_slug}"

        view_dir = self._env_view_snapshots_dir(project_id, env_id) / slugify(view_identity)
        view_dir.mkdir(parents=True, exist_ok=True)

        captured_at = datetime.now(UTC)
        timestamp = captured_at.strftime("%Y%m%dT%H%M%S%fZ")
        screenshot_ref = f"{timestamp}.png"
        atomic_write_bytes(view_dir / screenshot_ref, driver.screenshot())

        record = ViewSnapshotRecord(
            view_identity=view_identity,
            captured_at=captured_at,
            page_hash=fingerprint,
            screenshot_ref=screenshot_ref,
            elements=extract_elements(ax_tree, dom_html),
        )
        atomic_write_json(view_dir / f"{timestamp}.json", record)
        return record

    def load_latest(
        self, project_id: str, env_id: str, view_identity: str
    ) -> ViewSnapshotRecord | None:
        """Most recently persisted snapshot for `view_identity`, or `None` if none
        exists yet (e.g. no exploration/run has captured this view before) — F8-040
        treats that absence as `Severity.NONE` (nothing to diff against)."""
        view_dir = self._env_view_snapshots_dir(project_id, env_id) / slugify(view_identity)
        if not view_dir.is_dir():
            return None
        json_files = sorted(view_dir.glob("*.json"))
        if not json_files:
            return None
        return ViewSnapshotRecord.model_validate_json(json_files[-1].read_text())

    def diff(self, current: ViewSnapshotRecord, previous: ViewSnapshotRecord) -> Severity:
        """F8-010: classify the change between two snapshots of (logically) the same
        view by comparing their `elements[]` sets, keyed by the most locator-stable
        signal available (`data_testid` > `path_fingerprint` > `ref`)."""
        prev_by_key = {_element_key(e): e for e in previous.elements}
        curr_by_key = {_element_key(e): e for e in current.elements}

        removed = prev_by_key.keys() - curr_by_key.keys()
        added = curr_by_key.keys() - prev_by_key.keys()
        common = prev_by_key.keys() & curr_by_key.keys()

        renamed = any(prev_by_key[key].role != curr_by_key[key].role for key in common)
        text_changed = any(prev_by_key[key].name != curr_by_key[key].name for key in common)

        if removed or renamed:
            return Severity.STRUCTURAL_MAJOR
        if added:
            return Severity.STRUCTURAL_MINOR
        if text_changed:
            return Severity.COSMETIC
        return Severity.NONE
