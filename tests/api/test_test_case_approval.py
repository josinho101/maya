from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maya.api.main import app
from maya.managers.project_manager import ProjectManager
from maya.storage.atomic import atomic_write_json
from maya.storage.models import APITestCase, UITestCase


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app.state.project_manager = ProjectManager(tmp_path)
    return TestClient(app)


def _seed_pending_ui_test_case(tmp_path: Path, project_id: str, test_id: str, view_identity: str) -> None:
    tc = UITestCase(
        id=test_id,
        created_by="exploration_agent",
        view_identity=view_identity,
        locator_confidence=0.9,
        steps=[{"action": "click", "target": {"strategy": "css", "value": "#submit"}}],
    )
    path = tmp_path / "projects" / project_id / "test_cases" / "pending" / f"{test_id}.json"
    atomic_write_json(path, tc)


def _seed_pending_api_test_case(tmp_path: Path, project_id: str, test_id: str) -> None:
    tc = APITestCase(id=test_id, created_by="api_discovery_agent")
    path = tmp_path / "projects" / project_id / "test_cases" / "pending" / f"{test_id}.json"
    atomic_write_json(path, tc)


def _create_project(client: TestClient) -> str:
    resp = client.post("/api/v1/projects", json={"name": "Acme Webapp", "test_types": ["ui"]})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_list_pending_and_approve(client: TestClient, tmp_path: Path):
    project_id = _create_project(client)
    _seed_pending_ui_test_case(tmp_path, project_id, "tc_approve_me", "login-page")

    list_resp = client.get(f"/api/v1/projects/{project_id}/test-cases?status=pending")
    assert list_resp.status_code == 200
    assert [tc["id"] for tc in list_resp.json()] == ["tc_approve_me"]

    approve_resp = client.post(f"/api/v1/projects/{project_id}/test-cases/tc_approve_me/approve")
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "approved"

    assert client.get(f"/api/v1/projects/{project_id}/test-cases?status=pending").json() == []
    approved = client.get(f"/api/v1/projects/{project_id}/test-cases?status=approved").json()
    assert [tc["id"] for tc in approved] == ["tc_approve_me"]


def test_reject_persists_reason_in_archived(client: TestClient, tmp_path: Path):
    project_id = _create_project(client)
    _seed_pending_ui_test_case(tmp_path, project_id, "tc_reject_me", "checkout-page")

    reject_resp = client.post(
        f"/api/v1/projects/{project_id}/test-cases/tc_reject_me/reject",
        json={"reason": "locator is flaky"},
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["status"] == "archived"
    assert reject_resp.json()["rejection_reason"] == "locator is flaky"

    archived = client.get(f"/api/v1/projects/{project_id}/test-cases?status=archived").json()
    assert archived[0]["rejection_reason"] == "locator is flaky"


def test_patch_steps_persists(client: TestClient, tmp_path: Path):
    project_id = _create_project(client)
    _seed_pending_ui_test_case(tmp_path, project_id, "tc_edit_me", "signup-page")

    patch_resp = client.patch(
        f"/api/v1/projects/{project_id}/test-cases/tc_edit_me",
        json={"steps": [{"action": "click", "target": {"strategy": "css", "value": "#fixed-locator"}}]},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["steps"][0]["target"]["value"] == "#fixed-locator"

    refetched = client.get(f"/api/v1/projects/{project_id}/test-cases?status=pending").json()
    assert refetched[0]["steps"][0]["target"]["value"] == "#fixed-locator"


def test_approve_unknown_id_404s(client: TestClient):
    project_id = _create_project(client)
    resp = client.post(f"/api/v1/projects/{project_id}/test-cases/tc_doesnotexist/approve")
    assert resp.status_code == 404


def test_double_approve_409s(client: TestClient, tmp_path: Path):
    project_id = _create_project(client)
    _seed_pending_ui_test_case(tmp_path, project_id, "tc_twice", "home-page")

    first = client.post(f"/api/v1/projects/{project_id}/test-cases/tc_twice/approve")
    assert first.status_code == 200

    second = client.post(f"/api/v1/projects/{project_id}/test-cases/tc_twice/approve")
    assert second.status_code == 409


def test_patch_api_test_case_422s(client: TestClient, tmp_path: Path):
    project_id = _create_project(client)
    _seed_pending_api_test_case(tmp_path, project_id, "tc_api_stub")

    resp = client.patch(
        f"/api/v1/projects/{project_id}/test-cases/tc_api_stub", json={"steps": []}
    )
    assert resp.status_code == 422


def test_list_filters_by_protocol(client: TestClient, tmp_path: Path):
    project_id = _create_project(client)
    _seed_pending_ui_test_case(tmp_path, project_id, "tc_ui_one", "login-page")
    _seed_pending_api_test_case(tmp_path, project_id, "tc_api_one")

    ui_only = client.get(f"/api/v1/projects/{project_id}/test-cases?status=pending&protocol=ui").json()
    assert [tc["id"] for tc in ui_only] == ["tc_ui_one"]

    api_only = client.get(f"/api/v1/projects/{project_id}/test-cases?status=pending&protocol=api").json()
    assert [tc["id"] for tc in api_only] == ["tc_api_one"]
