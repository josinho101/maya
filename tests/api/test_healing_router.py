from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maya.api.main import app
from maya.managers.project_manager import ProjectManager
from maya.storage.healing_log_store import HealingLogStore
from maya.storage.models import HealingCandidate, HealingEventLogEntry, LocatorTarget, UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app.state.project_manager = ProjectManager(tmp_path)
    return TestClient(app)


def _seed_flagged_test_case(tmp_path: Path, project_id: str, env_id: str) -> tuple[str, HealingEventLogEntry]:
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
    store.update(test_case_id, status="needs_review")

    env_dir = tmp_path / "projects" / project_id / "environments" / env_id
    healing_log_store = HealingLogStore(env_dir)
    entry = HealingEventLogEntry(
        heal_id="heal_abc123",
        run_id="run_1",
        step_id="0",
        failure_type="locator_not_found",
        original_locator={"strategy": "test_id", "value": "counter-button"},
        candidates=[
            HealingCandidate(
                strategy="test_id", value="counter-button-v2", confidence=0.5,
                signal_breakdown={"attribute": 0.6},
            )
        ],
        auto_applied=False,
    )
    healing_log_store.append(test_case_id, entry)
    return test_case_id, entry


def _create_project_with_dev_environment(client: TestClient) -> str:
    project_resp = client.post("/api/v1/projects", json={"name": "Healing Router Project", "test_types": ["ui"]})
    assert project_resp.status_code == 201
    project_id = project_resp.json()["id"]
    env_resp = client.post(f"/api/v1/projects/{project_id}/environments", json={"tag": "dev"})
    assert env_resp.status_code == 201
    return project_id


def test_get_healing_log_round_trips(client: TestClient, tmp_path: Path):
    project_id = _create_project_with_dev_environment(client)
    test_case_id, entry = _seed_flagged_test_case(tmp_path, project_id, "dev")

    resp = client.get(f"/api/v1/projects/{project_id}/test-cases/{test_case_id}/healing-log")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["heal_id"] == "heal_abc123"
    assert body[0]["resolution"] is None


def test_get_healing_log_unknown_test_case_returns_empty(client: TestClient):
    project_id = _create_project_with_dev_environment(client)
    resp = client.get(f"/api/v1/projects/{project_id}/test-cases/tc_does_not_exist/healing-log")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_healing_log_unknown_project_404s(client: TestClient):
    resp = client.get("/api/v1/projects/does-not-exist/test-cases/tc_x/healing-log")
    assert resp.status_code == 404


def test_resolve_accept_patches_locator_and_clears_review(client: TestClient, tmp_path: Path):
    project_id = _create_project_with_dev_environment(client)
    test_case_id, entry = _seed_flagged_test_case(tmp_path, project_id, "dev")

    resp = client.post(f"/api/v1/healing/{entry.heal_id}/resolve", json={"action": "accept"})
    assert resp.status_code == 200
    assert resp.json()["resolution"] == "accepted"

    store = TestCaseStore(tmp_path / "projects" / project_id)
    updated = store.get(test_case_id)
    assert updated.status == "approved"
    assert updated.steps[0].target.value == "counter-button-v2"
    assert updated.locator_confidence == 0.5


def test_resolve_reject_clears_review_without_changing_locator(client: TestClient, tmp_path: Path):
    project_id = _create_project_with_dev_environment(client)
    test_case_id, entry = _seed_flagged_test_case(tmp_path, project_id, "dev")

    resp = client.post(f"/api/v1/healing/{entry.heal_id}/resolve", json={"action": "reject"})
    assert resp.status_code == 200
    assert resp.json()["resolution"] == "rejected"

    store = TestCaseStore(tmp_path / "projects" / project_id)
    updated = store.get(test_case_id)
    assert updated.status == "approved"
    assert updated.steps[0].target.value == "counter-button"


def test_resolve_unknown_heal_id_404s(client: TestClient):
    resp = client.post("/api/v1/healing/heal_does_not_exist/resolve", json={"action": "accept"})
    assert resp.status_code == 404


def test_get_screenshot_unknown_run_404s(client: TestClient):
    resp = client.get("/api/v1/runs/run_does_not_exist/screenshots/x.png")
    assert resp.status_code == 404


def test_get_screenshot_rejects_path_traversal(client: TestClient):
    resp = client.get("/api/v1/runs/run_x/screenshots/..%2F..%2Fetc%2Fpasswd")
    assert resp.status_code in (404, 422)
