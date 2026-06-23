from pathlib import Path

import pytest

from maya.storage.models import Environment, Project
from maya.storage.scaffolder import scaffold_project


def make_project() -> Project:
    return Project(
        id="acme-webapp",
        test_types=["ui"],
        default_environment="dev",
        environments=["dev", "staging"],
    )


def make_environments() -> dict[str, Environment]:
    return {
        "dev": Environment(id="dev", label="Dev", is_destructive_safe=True),
        "staging": Environment(id="staging", label="Staging", is_destructive_safe=False),
    }


def test_scaffold_creates_full_tree(tmp_path: Path):
    project = make_project()
    environments = make_environments()

    scaffold_project(tmp_path, project, environments)

    for status in ("pending", "approved", "archived"):
        assert (tmp_path / "test_cases" / status).is_dir()
    assert (tmp_path / "scenario_sessions").is_dir()
    assert (tmp_path / "uploads").is_dir()

    for env_id in ("dev", "staging"):
        env_dir = tmp_path / "environments" / env_id
        for subdir in ("view_snapshots", "specs", "runs", "healing_logs"):
            assert (env_dir / subdir).is_dir()
        assert (env_dir / "environment.json").exists()

    assert (tmp_path / "project.json").exists()


def test_scaffold_mismatched_environments_raises(tmp_path: Path):
    project = make_project()
    environments = make_environments()
    del environments["staging"]

    with pytest.raises(ValueError):
        scaffold_project(tmp_path, project, environments)


def test_scaffolded_project_json_reparses(tmp_path: Path):
    project = make_project()
    environments = make_environments()

    scaffold_project(tmp_path, project, environments)

    reparsed = Project.model_validate_json((tmp_path / "project.json").read_text())
    assert reparsed == project


def test_scaffolded_environment_json_reparses(tmp_path: Path):
    project = make_project()
    environments = make_environments()

    scaffold_project(tmp_path, project, environments)

    for env_id, env in environments.items():
        path = tmp_path / "environments" / env_id / "environment.json"
        reparsed = Environment.model_validate_json(path.read_text())
        assert reparsed == env
