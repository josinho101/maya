from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maya.api.main import app
from maya.managers.project_manager import ProjectManager


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app.state.project_manager = ProjectManager(tmp_path)
    return TestClient(app)


def _create_project_with_dev_environment(client: TestClient, demo_app_url: str) -> str:
    project_resp = client.post(
        "/api/v1/projects", json={"name": "Scenario Submission Project", "test_types": ["ui"]}
    )
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


@pytest.mark.integration
def test_submit_scenario_persists_text_and_round_trips_via_get(
    client: TestClient, tmp_path: Path, demo_app_url: str, ollama_models: list[str]
):
    vision_models = [m for m in ollama_models if "vl" in m.lower() or "vision" in m.lower()]
    if not vision_models:
        pytest.skip("no multimodal model installed locally")
    (tmp_path / "global_config.json").write_text(
        json.dumps({"model_preferences": {"ui_explore_heal": [vision_models[0]]}})
    )

    project_id = _create_project_with_dev_environment(client, demo_app_url)

    submit_resp = client.post(
        f"/api/v1/projects/{project_id}/scenarios",
        json={"text": "a user logs in and clicks the counter button", "environment_id": "dev"},
    )
    assert submit_resp.status_code == 200
    session = submit_resp.json()
    assert session["text"] == "a user logs in and clicks the counter button"
    assert session["status"] in ("completed", "stuck")

    on_disk = json.loads(
        (tmp_path / "projects" / project_id / "scenario_sessions" / f"{session['id']}.json")
        .read_text()
    )
    assert on_disk["text"] == "a user logs in and clicks the counter button"

    get_resp = client.get(f"/api/v1/projects/{project_id}/scenarios/{session['id']}")
    assert get_resp.status_code == 200
    assert get_resp.json() == session


def test_get_unknown_scenario_session_404s(client: TestClient):
    project_resp = client.post(
        "/api/v1/projects", json={"name": "No Scenarios Project", "test_types": ["ui"]}
    )
    project_id = project_resp.json()["id"]

    resp = client.get(f"/api/v1/projects/{project_id}/scenarios/scenario_does_not_exist")
    assert resp.status_code == 404
