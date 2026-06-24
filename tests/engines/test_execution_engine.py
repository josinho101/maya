from __future__ import annotations

from pathlib import Path

import pytest

from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.engines.execution_engine import ExecutionEngine
from maya.storage.models import LocatorTarget, UIStep, UITestCase


def _make_driver() -> PlaywrightAdapter:
    try:
        return PlaywrightAdapter(headless=True)
    except Exception as exc:  # noqa: BLE001 - environment-dependent (browser not installed)
        pytest.skip(f"Playwright browser not available: {exc}")


def _counter_test_case(locator_value: str) -> UITestCase:
    return UITestCase(
        id="tc_counter",
        created_by="human",
        view_identity="demo-home",
        locator_confidence=1.0,
        steps=[
            UIStep(
                action="click",
                target=LocatorTarget(strategy="test_id", value=locator_value),
                assertion={"type": "contains", "value": "Count: 1"},
            )
        ],
    )


@pytest.mark.integration
def test_run_test_case_passes_and_records_timing(demo_app_url, tmp_path: Path):
    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)
        engine = ExecutionEngine(driver, tmp_path / "screenshots")
        result = engine.run_test_case(_counter_test_case("counter-button"))
    finally:
        driver.close()

    assert result.status == "pass"
    assert result.execution_time_ms > 0
    assert result.screenshot_refs == []
    assert result.failure_reason is None


@pytest.mark.integration
def test_run_test_case_fails_cleanly_on_broken_locator(demo_app_url, tmp_path: Path):
    driver = _make_driver()
    screenshots_dir = tmp_path / "screenshots"
    try:
        driver.navigate(demo_app_url)
        engine = ExecutionEngine(driver, screenshots_dir)
        result = engine.run_test_case(_counter_test_case("does-not-exist"))
    finally:
        driver.close()

    assert result.status == "fail"
    assert result.failure_reason is not None
    assert len(result.screenshot_refs) == 1
    assert (screenshots_dir / result.screenshot_refs[0]).exists()
