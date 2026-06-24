from __future__ import annotations

from pathlib import Path

import pytest

from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.engines.execution_engine import ExecutionEngine
from maya.engines.healing_engine import HealingEngine
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.healing_log_store import HealingLogStore
from maya.storage.models import LocatorTarget, UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore


class _RaisingLLM:
    """Stub `LLMClient` that fails the test loudly if the vision tier is ever
    invoked — tiers 1-5 should resolve (or exhaust) without touching the AI queue
    for these single-attempt scenarios (`vision_fallback_after_attempts` default is 2)."""

    def generate(self, prompt, images=None, tools=None, task_role=None):
        raise AssertionError("vision tier should not have been invoked")


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


def _build_healing_engine(root_dir: Path, project_id: str, env_id: str, run_id: str) -> HealingEngine:
    project_dir = root_dir / "projects" / project_id
    return HealingEngine(
        llm=_RaisingLLM(),
        snapshot_engine=ViewSnapshotEngine(root_dir),
        test_case_store=TestCaseStore(project_dir),
        healing_log_store=HealingLogStore(project_dir / "environments" / env_id),
        project_id=project_id,
        env_id=env_id,
        run_id=run_id,
    )


def _seed_baseline_snapshot(root_dir: Path, project_id: str, env_id: str, demo_app_url: str):
    """Captures a `ViewSnapshotRecord` of the unmutated demo page so `HealingEngine`
    can recover the original element's role/name/path_fingerprint when later run
    against a mutated/drastic page — mirrors what a real prior run/exploration pass
    would already have on disk."""
    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)
        record = ViewSnapshotEngine(root_dir).capture(driver, project_id, env_id)
    finally:
        driver.close()
    return record


@pytest.mark.integration
def test_run_test_case_auto_heals_renamed_testid(demo_app_url, demo_app_mutated_url, tmp_path: Path):
    root_dir = tmp_path / "root"
    project_id, env_id, run_id = "proj", "dev", "run_test"

    baseline = _seed_baseline_snapshot(root_dir, project_id, env_id, demo_app_url)

    tc = UITestCase(
        id="tc_counter",
        created_by="human",
        status="approved",
        view_identity=baseline.view_identity,
        locator_confidence=1.0,
        steps=[
            UIStep(
                action="click",
                target=LocatorTarget(strategy="test_id", value="counter-button"),
                assertion={"type": "contains", "value": "Count: 1"},
            )
        ],
    )
    test_case_store = TestCaseStore(root_dir / "projects" / project_id)
    (root_dir / "projects" / project_id / "test_cases" / "approved").mkdir(parents=True, exist_ok=True)
    test_case_store.create(tc)

    healing_engine = _build_healing_engine(root_dir, project_id, env_id, run_id)
    healing_log_store = HealingLogStore(root_dir / "projects" / project_id / "environments" / env_id)

    driver = _make_driver()
    try:
        driver.navigate(demo_app_mutated_url)
        engine = ExecutionEngine(driver, tmp_path / "screenshots", healing_engine=healing_engine)
        result = engine.run_test_case(tc)
    finally:
        driver.close()

    assert result.status == "pass"
    assert result.healed_pass is True
    assert result.healing_event_refs

    entries = healing_log_store.list(tc.id)
    assert len(entries) == 1
    assert entries[0].auto_applied is True
    assert entries[0].applied is not None
    assert entries[0].applied.value == "counter-button-v2"

    healed_tc = test_case_store.get(tc.id)
    assert healed_tc.steps[0].target.value == "counter-button-v2"
    assert healed_tc.status == "approved"


@pytest.mark.integration
def test_run_test_case_low_confidence_flags_needs_review(demo_app_url, demo_app_drastic_url, tmp_path: Path):
    """The counter button is removed entirely (not renamed) — only a weak fuzzy-text
    candidate (an unrelated element) clears the tier floor, so confidence lands well
    below the auto-apply threshold: the step fails and the test case is flagged for
    human review, but the locator itself is left untouched (per plan.md §5.e step 3's
    "below threshold" branch — distinct from the true zero-candidate case)."""
    root_dir = tmp_path / "root"
    project_id, env_id, run_id = "proj", "dev", "run_test"

    baseline = _seed_baseline_snapshot(root_dir, project_id, env_id, demo_app_url)

    tc = UITestCase(
        id="tc_counter",
        created_by="human",
        status="approved",
        view_identity=baseline.view_identity,
        locator_confidence=1.0,
        steps=[
            UIStep(
                action="click",
                target=LocatorTarget(strategy="test_id", value="counter-button"),
                assertion={"type": "contains", "value": "Count: 1"},
            )
        ],
    )
    test_case_store = TestCaseStore(root_dir / "projects" / project_id)
    (root_dir / "projects" / project_id / "test_cases" / "approved").mkdir(parents=True, exist_ok=True)
    test_case_store.create(tc)

    healing_engine = _build_healing_engine(root_dir, project_id, env_id, run_id)
    healing_log_store = HealingLogStore(root_dir / "projects" / project_id / "environments" / env_id)

    driver = _make_driver()
    try:
        driver.navigate(demo_app_drastic_url)
        engine = ExecutionEngine(driver, tmp_path / "screenshots", healing_engine=healing_engine)
        result = engine.run_test_case(tc)
    finally:
        driver.close()

    assert result.status == "fail"
    assert result.healed_pass is False
    assert result.healing_event_refs

    entries = healing_log_store.list(tc.id)
    assert len(entries) == 1
    assert entries[0].auto_applied is False
    assert entries[0].candidates
    assert entries[0].candidates[0].confidence < 0.90

    flagged_tc = test_case_store.get(tc.id)
    assert flagged_tc.status == "needs_review"
    assert flagged_tc.steps[0].target.value == "counter-button"
