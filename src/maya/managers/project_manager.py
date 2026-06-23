"""CRUD for projects/environments/packages, per plan.md §2.3 and §3.3. Owns composing
the real on-disk layout (`<root_dir>/projects/<project_id>/...`) — callers only ever
deal in project/environment ids, never paths."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Literal

from maya.managers.secrets_store import SecretsStore, resolve_strings
from maya.managers.slugify import slugify
from maya.storage.atomic import atomic_write_json
from maya.storage.models import APIPackage, Environment, Project, ScheduleConfig, UIPackage
from maya.storage.scaffolder import scaffold_environment, scaffold_project

_SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")

_PACKAGE_CLASSES: dict[str, type[UIPackage] | type[APIPackage]] = {
    "ui": UIPackage,
    "api": APIPackage,
}


class ProjectNotFoundError(LookupError):
    pass


class EnvironmentNotFoundError(LookupError):
    pass


class ProjectAlreadyExistsError(ValueError):
    pass


class EnvironmentAlreadyExistsError(ValueError):
    pass


class ProjectNameAlreadyExistsError(ValueError):
    pass


class EnvironmentTagAlreadyExistsError(ValueError):
    pass


class InvalidSlugError(ValueError):
    pass


class ArchivedError(ValueError):
    pass


def _validate_slug(value: str) -> None:
    if not _SLUG_RE.match(value):
        raise InvalidSlugError(
            f"{value!r} is not a valid slug (lowercase alphanumerics/hyphens, "
            "must start and end alphanumeric, max 64 chars)"
        )


class ProjectManager:
    def __init__(self, root_dir: Path) -> None:
        self.root_dir = Path(root_dir)
        self.projects_dir = self.root_dir / "projects"

    def _project_dir(self, project_id: str) -> Path:
        return self.projects_dir / project_id

    def _project_json_path(self, project_id: str) -> Path:
        return self._project_dir(project_id) / "project.json"

    def _env_dir(self, project_id: str, env_id: str) -> Path:
        return self._project_dir(project_id) / "environments" / env_id

    def _env_json_path(self, project_id: str, env_id: str) -> Path:
        return self._env_dir(project_id, env_id) / "environment.json"

    # --- F3-010 / list / get -----------------------------------------------------

    def create_project(
        self,
        name: str,
        test_types: list[Literal["ui", "api"]],
        description: str | None = None,
        default_environment: str = "dev",
        environments: list[str] | None = None,
    ) -> Project:
        project_id = slugify(name)
        _validate_slug(project_id)
        self._check_name_not_taken(name)

        project_dir = self._project_dir(project_id)
        if project_dir.exists():
            raise ProjectAlreadyExistsError(project_id)

        env_ids = environments or []
        for env_id in env_ids:
            _validate_slug(env_id)

        project = Project(
            id=project_id,
            name=name,
            description=description,
            test_types=test_types,
            default_environment=default_environment,
            environments=env_ids,
        )
        envs = {env_id: Environment(id=env_id, label=env_id) for env_id in env_ids}
        scaffold_project(project_dir, project, envs)
        return project

    def _check_name_not_taken(self, name: str, *, exclude_project_id: str | None = None) -> None:
        for project in self.list_projects(include_archived=False):
            if project.id == exclude_project_id:
                continue
            if project.name == name:
                raise ProjectNameAlreadyExistsError(name)

    def list_projects(self, include_archived: bool = False) -> list[Project]:
        if not self.projects_dir.exists():
            return []
        projects = []
        for project_json in sorted(self.projects_dir.glob("*/project.json")):
            project = Project.model_validate_json(project_json.read_bytes())
            if project.archived and not include_archived:
                continue
            projects.append(project)
        return projects

    def get_project(self, project_id: str) -> Project:
        path = self._project_json_path(project_id)
        if not path.exists():
            raise ProjectNotFoundError(project_id)
        return Project.model_validate_json(path.read_bytes())

    def update_project(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        test_types: list[Literal["ui", "api"]] | None = None,
    ) -> Project:
        project = self.get_project(project_id)
        if project.archived:
            raise ArchivedError(project_id)

        if name is not None and name != project.name:
            self._check_name_not_taken(name, exclude_project_id=project_id)

        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if test_types is not None:
            updates["test_types"] = test_types

        project = project.model_copy(update=updates)
        atomic_write_json(self._project_json_path(project_id), project)
        return project

    def delete_project(self, project_id: str) -> Project:
        project = self.get_project(project_id)
        if project.archived:
            raise ArchivedError(project_id)
        project = project.model_copy(update={"archived": True})
        atomic_write_json(self._project_json_path(project_id), project)
        return project

    # --- F3-020 --------------------------------------------------------------

    def add_environment(
        self,
        project_id: str,
        tag: str,
        schedule: ScheduleConfig | None = None,
        is_destructive_safe: bool = False,
    ) -> Environment:
        env_id = slugify(tag)
        _validate_slug(env_id)
        project = self.get_project(project_id)
        self._check_env_tag_not_taken(project, tag)
        if env_id in project.environments:
            raise EnvironmentAlreadyExistsError(env_id)

        env = Environment(
            id=env_id,
            label=tag,
            schedule=schedule,
            is_destructive_safe=is_destructive_safe,
        )
        scaffold_environment(self._env_dir(project_id, env_id), env)

        project = project.model_copy(update={"environments": [*project.environments, env_id]})
        atomic_write_json(self._project_json_path(project_id), project)
        return env

    def _check_env_tag_not_taken(self, project: Project, tag: str) -> None:
        for env_id in project.environments:
            env = self.get_environment(project.id, env_id)
            if env.archived:
                continue
            if env.label == tag:
                raise EnvironmentTagAlreadyExistsError(tag)

    def get_environment(self, project_id: str, env_id: str) -> Environment:
        path = self._env_json_path(project_id, env_id)
        if not path.exists():
            raise EnvironmentNotFoundError(env_id)
        return Environment.model_validate_json(path.read_bytes())

    def delete_environment(self, project_id: str, env_id: str) -> Environment:
        env = self.get_environment(project_id, env_id)
        if env.archived:
            raise ArchivedError(env_id)
        env = env.model_copy(update={"archived": True})
        atomic_write_json(self._env_json_path(project_id, env_id), env)
        return env

    # --- F3-030 ----------------------------------------------------------------

    def update_package(
        self,
        project_id: str,
        env_id: str,
        test_type: Literal["ui", "api"],
        **fields: Any,
    ) -> Environment:
        env = self.get_environment(project_id, env_id)
        package_cls = _PACKAGE_CLASSES[test_type]

        existing = env.packages.get(test_type)
        base_data = existing.model_dump() if existing is not None else {}
        base_data.update(fields)
        package = package_cls.model_validate(base_data)

        env = env.model_copy(update={"packages": {**env.packages, test_type: package}})
        atomic_write_json(self._env_json_path(project_id, env_id), env)
        return env

    # --- F3-070/080 --------------------------------------------------------------

    def get_resolved_package(
        self, project_id: str, env_id: str, test_type: Literal["ui", "api"]
    ) -> dict[str, Any]:
        env = self.get_environment(project_id, env_id)
        package = env.packages[test_type]
        secrets = SecretsStore(self.root_dir)
        return resolve_strings(package.model_dump(), secrets)
