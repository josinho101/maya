"""`ViewSnapshotEngine`: captures a deterministic baseline `ViewSnapshotRecord` for
whatever view a `BrowserDriver` is currently on, keyed by the composite view-identity
from plan.md §4 (URL signal + structural fingerprint + heading tiebreaker)."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlsplit

from maya.adapters.browser_driver import BrowserDriver
from maya.managers.slugify import slugify
from maya.perception.view_identity import heading_signal, structural_fingerprint
from maya.storage.atomic import atomic_write_bytes, atomic_write_json
from maya.storage.models import ViewSnapshotRecord


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
        )
        atomic_write_json(view_dir / f"{timestamp}.json", record)
        return record
