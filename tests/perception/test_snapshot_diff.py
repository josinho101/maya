from __future__ import annotations

from datetime import UTC, datetime

from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.models import Severity, ViewSnapshotElement, ViewSnapshotRecord

_NOW = datetime(2026, 1, 1, tzinfo=UTC)

_BASELINE_ELEMENTS = [
    ViewSnapshotElement(ref="el:0", role="main", path_fingerprint="fp-main"),
    ViewSnapshotElement(
        ref="el:0.0", role="button", name="Count: 0", data_testid="counter-button"
    ),
    ViewSnapshotElement(
        ref="el:0.1", role="button", name="Settings", data_testid="reveal-panel-button"
    ),
]


def _record(elements: list[ViewSnapshotElement]) -> ViewSnapshotRecord:
    return ViewSnapshotRecord(
        view_identity="demo-view", captured_at=_NOW, page_hash="hash", elements=elements
    )


def _engine() -> ViewSnapshotEngine:
    return ViewSnapshotEngine(root_dir="/tmp/unused")


def test_diff_identical_snapshots_is_none():
    current = _record(_BASELINE_ELEMENTS)
    previous = _record(_BASELINE_ELEMENTS)
    assert _engine().diff(current, previous) == Severity.NONE


def test_diff_text_only_change_is_cosmetic():
    previous = _record(_BASELINE_ELEMENTS)
    changed = [
        e.model_copy(update={"name": "Count: 1"}) if e.data_testid == "counter-button" else e
        for e in _BASELINE_ELEMENTS
    ]
    current = _record(changed)
    assert _engine().diff(current, previous) == Severity.COSMETIC


def test_diff_non_breaking_addition_is_structural_minor():
    previous = _record(_BASELINE_ELEMENTS)
    added = [
        *_BASELINE_ELEMENTS,
        ViewSnapshotElement(
            ref="el:0.2", role="button", name="Help", data_testid="help-button"
        ),
    ]
    current = _record(added)
    assert _engine().diff(current, previous) == Severity.STRUCTURAL_MINOR


def test_diff_removed_key_element_is_structural_major():
    previous = _record(_BASELINE_ELEMENTS)
    removed = [e for e in _BASELINE_ELEMENTS if e.data_testid != "counter-button"]
    current = _record(removed)
    assert _engine().diff(current, previous) == Severity.STRUCTURAL_MAJOR


def test_diff_renamed_key_element_is_structural_major():
    previous = _record(_BASELINE_ELEMENTS)
    renamed = [
        e.model_copy(update={"data_testid": "counter-button-v2"})
        if e.data_testid == "counter-button"
        else e
        for e in _BASELINE_ELEMENTS
    ]
    current = _record(renamed)
    assert _engine().diff(current, previous) == Severity.STRUCTURAL_MAJOR


def test_diff_role_change_at_same_path_is_structural_major():
    # No data_testid here, so the match key falls back to path_fingerprint — the
    # element at the same position changing role (e.g. button -> link) is exactly
    # the "renamed" case, distinct from an outright add/remove.
    previous = _record(
        [ViewSnapshotElement(ref="el:0", role="button", name="Go", path_fingerprint="fp-0")]
    )
    current = _record(
        [ViewSnapshotElement(ref="el:0", role="link", name="Go", path_fingerprint="fp-0")]
    )
    assert _engine().diff(current, previous) == Severity.STRUCTURAL_MAJOR


def test_load_latest_returns_none_when_no_history(tmp_path):
    engine = ViewSnapshotEngine(tmp_path)
    assert engine.load_latest("proj", "dev", "no-such-view") is None
