import subprocess
from pathlib import Path

import pytest

from maya.startup_checks import check_secure_config_not_tracked


def _init_repo(repo_dir: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo_dir, check=True)


@pytest.fixture
def repo_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    _init_repo(tmp_path)
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_check_returns_true_when_untracked(repo_dir: Path):
    secure_dir = repo_dir / "framework-data" / "config" / "secure"
    secure_dir.mkdir(parents=True)
    (secure_dir / "acme.secure.json").write_text("{}")

    assert check_secure_config_not_tracked(secure_dir) is True


def test_check_returns_false_when_tracked(repo_dir: Path):
    secure_dir = repo_dir / "framework-data" / "config" / "secure"
    secure_dir.mkdir(parents=True)
    secret_file = secure_dir / "acme.secure.json"
    secret_file.write_text("{}")
    subprocess.run(["git", "add", "-f", str(secret_file)], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "oops"], cwd=repo_dir, check=True, capture_output=True)

    assert check_secure_config_not_tracked(secure_dir) is False


def test_check_handles_non_git_directory_gracefully(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.chdir(tmp_path)
    secure_dir = tmp_path / "framework-data" / "config" / "secure"
    secure_dir.mkdir(parents=True)

    assert check_secure_config_not_tracked(secure_dir) is True
