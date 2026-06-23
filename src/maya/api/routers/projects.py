"""REST CRUD for Project/Environment/Package — thin wrappers over ProjectManager,
per plan.md §5.f's run-trigger contract style. Gap-fill identified during planning:
the dashboard has nothing to call without this router."""

from __future__ import annotations

import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, ValidationError

from maya.managers.project_manager import ProjectManager
from maya.storage.models import Environment, EnvironmentImportManifest, Project, ScheduleConfig

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

_SAMPLE_ENVIRONMENT_MANIFEST = {
    "tag": "staging",
    "schedule": {"cron": "0 */6 * * *"},
    "is_destructive_safe": False,
    "base_url": "https://staging.example.com",
    "auth": {"strategy": "none", "secure_ref": ""},
    "env_vars": {"EXAMPLE_KEY": "example-value"},
}


def get_project_manager(request: Request) -> ProjectManager:
    return request.app.state.project_manager


class CreateProjectRequest(BaseModel):
    name: str
    description: str | None = None
    test_types: list[Literal["ui", "api"]]
    default_environment: str = "dev"


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    test_types: list[Literal["ui", "api"]] | None = None


class AddEnvironmentRequest(BaseModel):
    tag: str
    schedule: ScheduleConfig | None = None
    is_destructive_safe: bool = False


class UpdateEnvironmentRequest(BaseModel):
    label: str | None = None
    schedule: ScheduleConfig | None = None
    is_destructive_safe: bool | None = None


class UpdatePackageRequest(BaseModel):
    model_config = {"extra": "allow"}


@router.post("", status_code=201)
def create_project(body: CreateProjectRequest, request: Request) -> Project:
    manager = get_project_manager(request)
    return manager.create_project(
        name=body.name,
        description=body.description,
        test_types=body.test_types,
        default_environment=body.default_environment,
    )


@router.get("")
def list_projects(request: Request) -> list[Project]:
    return get_project_manager(request).list_projects()


@router.get("/{project_id}")
def get_project(project_id: str, request: Request) -> Project:
    return get_project_manager(request).get_project(project_id)


@router.put("/{project_id}")
def update_project(project_id: str, body: UpdateProjectRequest, request: Request) -> Project:
    manager = get_project_manager(request)
    return manager.update_project(
        project_id,
        name=body.name,
        description=body.description,
        test_types=body.test_types,
    )


@router.delete("/{project_id}", status_code=204, response_class=Response)
def delete_project(project_id: str, request: Request) -> None:
    get_project_manager(request).delete_project(project_id)


@router.post("/{project_id}/archive")
def archive_project(project_id: str, request: Request) -> Project:
    return get_project_manager(request).archive_project(project_id)


@router.get("/environments/sample-json")
def download_sample_environment_json() -> Response:
    return Response(
        content=json.dumps(_SAMPLE_ENVIRONMENT_MANIFEST, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=environment-sample.json"},
    )


@router.post("/environments/parse-json")
async def parse_environment_json(file: UploadFile) -> EnvironmentImportManifest:
    content = await file.read()
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise HTTPException(400, "Invalid environment file: not valid JSON") from exc
    try:
        return EnvironmentImportManifest.model_validate(data)
    except ValidationError as exc:
        raise HTTPException(400, f"Invalid environment.json: {exc}") from exc


@router.get("/{project_id}/environments")
def list_environments(project_id: str, request: Request) -> list[Environment]:
    return get_project_manager(request).list_environments(project_id)


@router.post("/{project_id}/environments", status_code=201)
def add_environment(project_id: str, body: AddEnvironmentRequest, request: Request) -> Environment:
    manager = get_project_manager(request)
    return manager.add_environment(
        project_id,
        tag=body.tag,
        schedule=body.schedule,
        is_destructive_safe=body.is_destructive_safe,
    )


@router.get("/{project_id}/environments/{env_id}")
def get_environment(project_id: str, env_id: str, request: Request) -> Environment:
    return get_project_manager(request).get_environment(project_id, env_id)


@router.put("/{project_id}/environments/{env_id}")
def update_environment(
    project_id: str, env_id: str, body: UpdateEnvironmentRequest, request: Request
) -> Environment:
    manager = get_project_manager(request)
    return manager.update_environment(
        project_id,
        env_id,
        label=body.label,
        schedule=body.schedule,
        is_destructive_safe=body.is_destructive_safe,
    )


@router.delete("/{project_id}/environments/{env_id}", status_code=204, response_class=Response)
def delete_environment(project_id: str, env_id: str, request: Request) -> None:
    get_project_manager(request).delete_environment(project_id, env_id)


@router.post("/{project_id}/environments/{env_id}/archive")
def archive_environment(project_id: str, env_id: str, request: Request) -> Environment:
    return get_project_manager(request).archive_environment(project_id, env_id)


@router.put("/{project_id}/environments/{env_id}/packages/{test_type}")
def update_package(
    project_id: str,
    env_id: str,
    test_type: Literal["ui", "api"],
    body: UpdatePackageRequest,
    request: Request,
) -> Environment:
    manager = get_project_manager(request)
    return manager.update_package(project_id, env_id, test_type, **body.model_dump(exclude_unset=True))
