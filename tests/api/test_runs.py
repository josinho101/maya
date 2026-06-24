from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maya.api.main import app
from maya.managers.project_manager import ProjectManager
from maya.storage.models import LocatorTarget, UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app.state.project_manager = ProjectManager(tmp_path)
    return TestClient(app)


def _create_project_with_dev_environment(client: TestClient, demo_app_url: str) -> str:
    project_resp = client.post("/api/v1/projects", json={"name": "Run Trigger Project", "test_types": ["ui"]})
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]

    env_resp = client.post(f"/api/v1/projects/{project_id}/environments", json={"tag": "dev"})
    assert env_resp.status_code == 201

    package_resp = client.put(
        f"/api/v1/projects/{project_id}/environments/dev/packages/ui",
        json={"base_url": demo_app_url},
    )
    assert package_resp.status_code == 200

    return project_id


def _seed_approved_counter_test_case(tmp_path: Path, project_id: str) -> str:
    store = TestCaseStore(tmp_path / "projects" / project_id)
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
def test_trigger_run_and_get_run_round_trip(client: TestClient, tmp_path: Path, demo_app_url: str):
    project_id = _create_project_with_dev_environment(client, demo_app_url)
    test_case_id = _seed_approved_counter_test_case(tmp_path, project_id)

    trigger_resp = client.post(f"/api/v1/projects/{project_id}/runs", params={"environment": "dev"})
    assert trigger_resp.status_code == 200
    triggered_summary = trigger_resp.json()
    assert triggered_summary["environment_id"] == "dev"
    assert [r["test_case_id"] for r in triggered_summary["results"]] == [test_case_id]
    assert triggered_summary["results"][0]["status"] == "pass"

    get_resp = client.get(f"/api/v1/runs/{triggered_summary['run_id']}")
    assert get_resp.status_code == 200
    assert get_resp.json() == triggered_summary


def test_get_unknown_run_404s(client: TestClient):
    resp = client.get("/api/v1/runs/run_does_not_exist")
    assert resp.status_code == 404
