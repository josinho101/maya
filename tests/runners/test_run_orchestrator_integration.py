from __future__ import annotations

import json
from pathlib import Path

import pytest

from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.managers.project_manager import ProjectManager
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.runners.run_orchestrator import RunOrchestrator
from maya.storage.atomic import atomic_write_json
from maya.storage.models import ExplorationConfig, LocatorTarget, UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore


def _seed_approved_counter_test_case(store: TestCaseStore) -> str:
    tc = UITestCase(
        created_by="human",
        view_identity="demo-home",
        locator_confidence=1.0,
        steps=[
            UIStep(
                action="click",
                target=LocatorTarget(strategy="test_id", value="counter-button"),
                assertion={"type": "contains", "value": "Count: 1"},
            )
        ],
    )
    test_case_id = store.create(tc)
    store.move(test_case_id, "pending", "approved")
    return test_case_id


@pytest.mark.integration
def test_run_orchestrator_aggregates_two_approved_test_cases(demo_app_url, tmp_path: Path):
    project_manager = ProjectManager(tmp_path)
    project = project_manager.create_project(
        name="Demo Run Project", test_types=["ui"], environments=["dev"]
    )
    project_manager.update_package(project.id, "dev", "ui", base_url=demo_app_url)

    store = TestCaseStore(project_manager.project_dir(project.id))
    first_id = _seed_approved_counter_test_case(store)
    second_id = _seed_approved_counter_test_case(store)

    summary = RunOrchestrator(tmp_path).run(project.id, "dev")

    assert {r.test_case_id for r in summary.results} == {first_id, second_id}
    assert all(r.status == "pass" for r in summary.results)
    assert all(r.execution_time_ms > 0 for r in summary.results)
    assert summary.total_job_time_ms == sum(r.execution_time_ms for r in summary.results)
    assert summary.summary == {"pass": 2, "fail": 0}

    run_summary_path = (
        project_manager.project_dir(project.id)
        / "environments"
        / "dev"
        / "runs"
        / summary.run_id
        / "run_summary.json"
    )
    assert run_summary_path.exists()


def _capture_view_identity(url: str, tmp_path: Path) -> str:
    """Real `view_identity` for `url`'s landing view, computed the same way
    `ViewSnapshotEngine` always does — captured into a disposable scratch
    project/env so it doesn't pollute the real project's snapshot history."""
    driver = PlaywrightAdapter(headless=True)
    try:
        driver.navigate(url)
        record = ViewSnapshotEngine(tmp_path).capture(driver, "scratch", "scratch")
    finally:
        driver.close()
    return record.view_identity


def _seed_approved_test_case(store: TestCaseStore, view_identity: str) -> str:
    tc = UITestCase(
        created_by="human",
        view_identity=view_identity,
        locator_confidence=1.0,
        steps=[
            UIStep(
                action="click",
                target=LocatorTarget(strategy="test_id", value="counter-button"),
                assertion={"type": "contains", "value": "Count: 1"},
            )
        ],
    )
    test_case_id = store.create(tc)
    store.move(test_case_id, "pending", "approved")
    return test_case_id


@pytest.mark.integration
def test_run_orchestrator_diff_gate_reuses_unchanged_view(demo_app_url, tmp_path: Path):
    project_manager = ProjectManager(tmp_path)
    project = project_manager.create_project(
        name="Diff Gate Reuse Project", test_types=["ui"], environments=["dev"]
    )
    project_manager.update_package(project.id, "dev", "ui", base_url=demo_app_url)

    view_identity = _capture_view_identity(demo_app_url, tmp_path)
    store = TestCaseStore(project_manager.project_dir(project.id))
    test_case_id = _seed_approved_test_case(store, view_identity)

    orchestrator = RunOrchestrator(tmp_path)
    first = orchestrator.run(project.id, "dev")
    second = orchestrator.run(project.id, "dev")

    for summary in (first, second):
        assert summary.decision[view_identity]["action"] == "reuse"
        assert {r.test_case_id for r in summary.results} == {test_case_id}
        assert all(r.status == "pass" for r in summary.results)


@pytest.mark.integration
def test_run_orchestrator_diff_gate_triggers_scoped_reexploration(
    demo_app_url, demo_app_mutated_url, ollama_models, tmp_path: Path
):
    vision_models = [m for m in ollama_models if "vl" in m.lower() or "vision" in m.lower()]
    if not vision_models:
        pytest.skip("no multimodal model installed locally")

    project_manager = ProjectManager(tmp_path)
    project = project_manager.create_project(
        name="Diff Gate Reexplore Project", test_types=["ui"], environments=["dev"]
    )
    # Tight exploration budget — only the gate's branching is under test here, not
    # exploration coverage/quality.
    project = project.model_copy(
        update={"exploration": ExplorationConfig(max_steps=3, plateau_steps=3)}
    )
    atomic_write_json(tmp_path / "projects" / project.id / "project.json", project)

    (tmp_path / "global_config.json").write_text(
        json.dumps({"model_preferences": {"ui_explore_heal": [vision_models[0]]}})
    )

    # Baseline snapshot taken against the *original* demo page — this becomes
    # "previous" for the gate below. The original and mutated pages compute the
    # same view_identity (same URL shape/landmark structure/heading); only the
    # counter button's data-testid differs between them.
    view_identity = _capture_view_identity(demo_app_url, tmp_path)
    baseline_driver = PlaywrightAdapter(headless=True)
    try:
        baseline_driver.navigate(demo_app_url)
        ViewSnapshotEngine(tmp_path).capture(baseline_driver, project.id, "dev")
    finally:
        baseline_driver.close()

    store = TestCaseStore(project_manager.project_dir(project.id))
    stale_test_case_id = _seed_approved_test_case(store, view_identity)

    # The orchestrator now reaches the *mutated* page — counter-button was renamed,
    # a structural-major change relative to the baseline snapshot just captured.
    project_manager.update_package(project.id, "dev", "ui", base_url=demo_app_mutated_url)

    summary = RunOrchestrator(tmp_path).run(project.id, "dev")

    decision = summary.decision[view_identity]
    assert decision["action"] == "re-explore"
    assert "new_test_case_ids" in decision
    assert stale_test_case_id not in {r.test_case_id for r in summary.results}
