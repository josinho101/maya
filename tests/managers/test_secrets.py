from pathlib import Path

import pytest

from maya.managers.project_manager import ProjectManager
from maya.managers.secrets_store import SecretNotFoundError, SecretsStore, resolve_placeholder


def test_set_then_get_roundtrip(tmp_path: Path):
    store = SecretsStore(tmp_path)

    store.set("acme-webapp", "staging", "api_key", "sk-fake-123")

    assert store.get("acme-webapp", "staging", "api_key") == "sk-fake-123"


def test_get_missing_key_raises(tmp_path: Path):
    store = SecretsStore(tmp_path)

    with pytest.raises(SecretNotFoundError):
        store.get("acme-webapp", "staging", "api_key")


def test_secure_file_lives_under_gitignored_path(tmp_path: Path):
    store = SecretsStore(tmp_path)

    store.set("acme-webapp", "staging", "api_key", "sk-fake-123")

    assert (tmp_path / "config" / "secure" / "acme-webapp.secure.json").exists()


def test_resolve_placeholder_substitutes_value():
    class StubSecrets:
        def get(self, project_id: str, env_id: str, key: str) -> str:
            assert (project_id, env_id, key) == ("acme", "staging", "api_key")
            return "sk-fake-123"

    result = resolve_placeholder("${secure.acme.staging.api_key}", StubSecrets())

    assert result == "sk-fake-123"


def test_resolve_placeholder_passthrough_on_no_match():
    class StubSecrets:
        def get(self, project_id: str, env_id: str, key: str) -> str:
            raise AssertionError("should not be called")

    result = resolve_placeholder("https://staging.acme.com", StubSecrets())

    assert result == "https://staging.acme.com"


def test_get_resolved_package_resolves_without_mutating_disk(tmp_path: Path):
    manager = ProjectManager(tmp_path)
    secrets = SecretsStore(tmp_path)
    secrets.set("acme-webapp", "staging", "api_key", "sk-fake-123")

    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "staging")
    manager.update_package(
        "acme-webapp",
        "staging",
        "ui",
        base_url="https://staging.acme.com",
        env_vars={"API_KEY": "${secure.acme-webapp.staging.api_key}"},
    )

    resolved = manager.get_resolved_package("acme-webapp", "staging", "ui")
    assert resolved["env_vars"]["API_KEY"] == "sk-fake-123"

    raw = manager.get_environment("acme-webapp", "staging")
    assert raw.packages["ui"].env_vars["API_KEY"] == "${secure.acme-webapp.staging.api_key}"
