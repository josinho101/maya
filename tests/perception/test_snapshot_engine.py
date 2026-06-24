from __future__ import annotations

import pytest

from maya.adapters.browser_driver import Locator
from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.models import ViewSnapshotRecord


def _make_driver() -> PlaywrightAdapter:
    try:
        return PlaywrightAdapter(headless=True)
    except Exception as exc:  # noqa: BLE001 - environment-dependent (browser not installed)
        pytest.skip(f"Playwright browser not available: {exc}")


@pytest.mark.integration
def test_capture_writes_view_snapshot_record(demo_app_url, tmp_path):
    engine = ViewSnapshotEngine(tmp_path)
    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)
        record = engine.capture(driver, project_id="demo-proj", env_id="dev")
    finally:
        driver.close()

    assert record.view_identity
    view_dir = tmp_path / "projects" / "demo-proj" / "environments" / "dev" / "view_snapshots"
    json_files = list(view_dir.glob("*/*.json"))
    assert len(json_files) == 1
    loaded = ViewSnapshotRecord.model_validate_json(json_files[0].read_text())
    assert loaded.view_identity == record.view_identity


@pytest.mark.integration
def test_capture_is_stable_across_unchanged_captures(demo_app_url, tmp_path):
    engine = ViewSnapshotEngine(tmp_path)
    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)
        first = engine.capture(driver, project_id="demo-proj", env_id="dev")
        second = engine.capture(driver, project_id="demo-proj", env_id="dev")
    finally:
        driver.close()

    assert first.view_identity == second.view_identity
    view_dir = tmp_path / "projects" / "demo-proj" / "environments" / "dev" / "view_snapshots"
    json_files = list(view_dir.glob("*/*.json"))
    assert len(json_files) == 2
    assert len({f.parent for f in json_files}) == 1


@pytest.mark.integration
def test_capture_differs_for_structurally_distinct_view(demo_app_url, tmp_path):
    engine = ViewSnapshotEngine(tmp_path)
    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)
        baseline = engine.capture(driver, project_id="demo-proj", env_id="dev")

        driver.click(Locator(strategy="test_id", value="reveal-panel-button"))
        revealed = engine.capture(driver, project_id="demo-proj", env_id="dev")
    finally:
        driver.close()

    assert baseline.view_identity != revealed.view_identity
    view_dir = tmp_path / "projects" / "demo-proj" / "environments" / "dev" / "view_snapshots"
    assert len(list(view_dir.glob("*"))) == 2
