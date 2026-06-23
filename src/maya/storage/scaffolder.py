"""Creates the on-disk project directory tree per plan.md §3.3."""

from __future__ import annotations

from pathlib import Path

from maya.storage.atomic import atomic_write_json
from maya.storage.models import Environment, Project

_ENV_SUBDIRS = ("view_snapshots", "specs", "runs", "healing_logs")


def scaffold_environment(env_dir: Path, env: Environment) -> None:
    for subdir in _ENV_SUBDIRS:
        (env_dir / subdir).mkdir(parents=True, exist_ok=True)
    atomic_write_json(env_dir / "environment.json", env)


def scaffold_project(
    root_dir: Path, project: Project, environments: dict[str, Environment]
) -> None:
    if set(environments) != set(project.environments):
        raise ValueError(
            f"environments {sorted(environments)} do not match "
            f"project.environments {sorted(project.environments)}"
        )

    root_dir = Path(root_dir)

    for status in ("pending", "approved", "archived"):
        (root_dir / "test_cases" / status).mkdir(parents=True, exist_ok=True)
    (root_dir / "scenario_sessions").mkdir(parents=True, exist_ok=True)
    (root_dir / "uploads").mkdir(parents=True, exist_ok=True)

    atomic_write_json(root_dir / "project.json", project)

    for env_id, env in environments.items():
        scaffold_environment(root_dir / "environments" / env_id, env)
