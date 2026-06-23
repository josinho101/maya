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

    archive_env_resp = client.post("/api/v1/projects/acme-webapp/environments/staging/archive")
    assert archive_env_resp.status_code == 200
    assert archive_env_resp.json()["archived"] is True

    reget_env_resp = client.get("/api/v1/projects/acme-webapp/environments/staging")
    assert reget_env_resp.json()["archived"] is True

    delete_env_resp = client.delete("/api/v1/projects/acme-webapp/environments/staging")
    assert delete_env_resp.status_code == 204

    reget_env_resp_2 = client.get("/api/v1/projects/acme-webapp/environments/staging")
    assert reget_env_resp_2.status_code == 404

    delete_project_resp = client.delete("/api/v1/projects/acme-webapp")
    assert delete_project_resp.status_code == 204

    final_list_resp = client.get("/api/v1/projects")
    assert final_list_resp.json() == []

    reget_project_resp = client.get("/api/v1/projects/acme-webapp")
    assert reget_project_resp.status_code == 404


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


def test_archive_already_archived_project_returns_409(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    client.post("/api/v1/projects/acme/archive")
    response = client.post("/api/v1/projects/acme/archive")
    assert response.status_code == 409


def test_delete_project_removes_it_from_disk(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})

    response = client.delete("/api/v1/projects/acme")
    assert response.status_code == 204

    assert client.get("/api/v1/projects/acme").status_code == 404


def test_list_environments_returns_environments_for_project(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    client.post("/api/v1/projects/acme/environments", json={"tag": "dev"})
    client.post("/api/v1/projects/acme/environments", json={"tag": "staging"})

    response = client.get("/api/v1/projects/acme/environments")
    assert response.status_code == 200
    assert {e["id"] for e in response.json()} == {"dev", "staging"}


def test_sample_environment_json_contains_manifest(client: TestClient):
    response = client.get("/api/v1/projects/environments/sample-json")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/json"

    import json

    manifest = json.loads(response.content)
    assert manifest["tag"] == "staging"
    assert "base_url" in manifest


def test_parse_environment_json_returns_manifest_fields(client: TestClient):
    body = b'{"tag": "prod", "base_url": "https://prod.acme.com", "is_destructive_safe": false}'

    response = client.post(
        "/api/v1/projects/environments/parse-json",
        files={"file": ("environment.json", body, "application/json")},
    )
    assert response.status_code == 200
    assert response.json()["tag"] == "prod"
    assert response.json()["base_url"] == "https://prod.acme.com"


def test_parse_environment_json_with_invalid_json_returns_400(client: TestClient):
    response = client.post(
        "/api/v1/projects/environments/parse-json",
        files={"file": ("environment.json", b"not json", "application/json")},
    )
    assert response.status_code == 400


def test_update_environment_round_trip(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    client.post("/api/v1/projects/acme/environments", json={"tag": "dev"})

    response = client.put(
        "/api/v1/projects/acme/environments/dev",
        json={"label": "Development", "schedule": {"cron": "0 0 * * *"}, "is_destructive_safe": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "Development"
    assert body["schedule"]["cron"] == "0 0 * * *"
    assert body["is_destructive_safe"] is True

    # id stays the same even though label changed
    get_resp = client.get("/api/v1/projects/acme/environments/dev")
    assert get_resp.status_code == 200
    assert get_resp.json()["label"] == "Development"


def test_update_environment_to_taken_label_returns_409(client: TestClient):
    client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["ui"]})
    client.post("/api/v1/projects/acme/environments", json={"tag": "dev"})
    client.post("/api/v1/projects/acme/environments", json={"tag": "staging"})

    response = client.put(
        "/api/v1/projects/acme/environments/dev", json={"label": "staging"}
    )
    assert response.status_code == 409


def test_create_project_with_unsluggable_name_returns_422(client: TestClient):
    response = client.post("/api/v1/projects", json={"name": "!!!", "test_types": ["ui"]})
    assert response.status_code == 422


def test_create_project_with_invalid_test_type_returns_422(client: TestClient):
    response = client.post("/api/v1/projects", json={"name": "Acme", "test_types": ["bogus"]})
    assert response.status_code == 422
