from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from maya.api.main import app
from maya.managers.project_manager import ProjectManager


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    app.state.project_manager = ProjectManager(tmp_path)
    return TestClient(app)


def test_full_crud_sequence(client: TestClient):
    create_resp = client.post(
        "/api/v1/projects",
        json={"name": "Acme Webapp", "test_types": ["ui"]},
    )
    assert create_resp.status_code == 201
    assert create_resp.json()["id"] == "acme-webapp"

    list_resp = client.get("/api/v1/projects")
    assert list_resp.status_code == 200
    assert [p["id"] for p in list_resp.json()] == ["acme-webapp"]

    get_resp = client.get("/api/v1/projects/acme-webapp")
    assert get_resp.status_code == 200
    assert get_resp.json()["name"] == "Acme Webapp"

    update_resp = client.put("/api/v1/projects/acme-webapp", json={"name": "Acme Web App"})
    assert update_resp.status_code == 200
    assert update_resp.json()["name"] == "Acme Web App"

    add_env_resp = client.post(
        "/api/v1/projects/acme-webapp/environments", json={"tag": "Staging"}
    )
    assert add_env_resp.status_code == 201
    assert add_env_resp.json()["id"] == "staging"

    get_env_resp = client.get("/api/v1/projects/acme-webapp/environments/staging")
    assert get_env_resp.status_code == 200
    assert get_env_resp.json()["label"] == "Staging"

    update_pkg_resp = client.put(
        "/api/v1/projects/acme-webapp/environments/staging/packages/ui",
        json={"base_url": "https://staging.acme.com"},
    )
    assert update_pkg_resp.status_code == 200
    assert update_pkg_resp.json()["packages"]["ui"]["base_url"] == "https://staging.acme.com"

    delete_env_resp = client.delete("/api/v1/projects/acme-webapp/environments/staging")
    assert delete_env_resp.status_code == 204

    reget_env_resp = client.get("/api/v1/projects/acme-webapp/environments/staging")
    assert reget_env_resp.json()["archived"] is True

    delete_project_resp = client.delete("/api/v1/projects/acme-webapp")
    assert delete_project_resp.status_code == 204

    final_list_resp = client.get("/api/v1/projects")
    assert final_list_resp.json() == []


def test_get_nonexistent_project_returns_404(client: TestClient):
    response = client.get("/api/v1/projects/nope")
    assert response.status_code == 404


def test_put_nonexistent_project_returns_404(client: TestClient):
    response = client.put("/api/v1/projects/nope", json={"name": "X"})
    assert response.status_code == 404


def test_delete_nonexistent_project_returns_404(client: TestClient):
    response = client.delete("/api/v1/projects/nope")
    assert response.status_code == 404


def test_create_duplicate_project_name_returns_409(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    response = client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    assert response.status_code == 409


def test_add_duplicate_environment_tag_returns_409(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    client.post("/api/v1/projects/acme/environments", json={"tag": "dev"})
    response = client.post("/api/v1/projects/acme/environments", json={"tag": "dev"})
    assert response.status_code == 409


def test_delete_already_archived_project_returns_409(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    client.delete("/api/v1/projects/acme")
    response = client.delete("/api/v1/projects/acme")
    assert response.status_code == 409


def test_create_project_with_unsluggable_name_returns_422(client: TestClient):
    response = client.post("/api/v1/projects", json={"name": "!!!", "test_types": ["ui"]})
    assert response.status_code == 422


def test_create_project_with_invalid_test_type_returns_422(client: TestClient):
    response = client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["bogus"]})
    assert response.status_code == 422
