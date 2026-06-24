from __future__ import annotations

from pathlib import Path

import pytest

from maya.managers.project_manager import ProjectManager
from maya.runners.run_orchestrator import RunOrchestrator
from maya.storage.models import LocatorTarget, UIStep, UITestCase
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
