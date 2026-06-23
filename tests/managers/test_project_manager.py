from pathlib import Path

import pytest

from maya.managers.project_manager import (
    ArchivedError,
    EnvironmentAlreadyExistsError,
    EnvironmentNotFoundError,
    EnvironmentTagAlreadyExistsError,
    ProjectAlreadyExistsError,
    ProjectManager,
    ProjectNameAlreadyExistsError,
    ProjectNotFoundError,
)
from maya.managers.slugify import EmptySlugError
from maya.storage.models import ScheduleConfig


def make_manager(tmp_path: Path) -> ProjectManager:
    return ProjectManager(tmp_path)


def test_create_project_writes_project_json(tmp_path: Path):
    manager = make_manager(tmp_path)

    project = manager.create_project(name="Acme Webapp", test_types=["ui"], description="A webapp")

    assert project.id == "acme-webapp"
    project_json = tmp_path / "projects" / "acme-webapp" / "project.json"
    assert project_json.exists()
    reparsed = manager.get_project("acme-webapp")
    assert reparsed == project


def test_create_project_with_unsluggable_name_raises_empty_slug_error(tmp_path: Path):
    manager = make_manager(tmp_path)

    with pytest.raises(EmptySlugError):
        manager.create_project(name="!!!", test_types=["ui"])


def test_create_project_duplicate_name_raises_name_exists_error(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])

    with pytest.raises(ProjectNameAlreadyExistsError):
        manager.create_project(name="Acme Webapp", test_types=["ui"])


def test_create_project_same_slug_different_name_raises_already_exists_error(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])

    with pytest.raises(ProjectAlreadyExistsError):
        manager.create_project(name="Acme-Webapp!", test_types=["ui"])


def test_add_environment_writes_environment_json_with_empty_packages(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])

    env = manager.add_environment("acme-webapp", "Dev")

    assert env.packages == {}
    assert env.label == "Dev"
    env_json = tmp_path / "projects" / "acme-webapp" / "environments" / "dev" / "environment.json"
    assert env_json.exists()
    project = manager.get_project("acme-webapp")
    assert "dev" in project.environments


def test_add_environment_duplicate_tag_raises(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")

    with pytest.raises(EnvironmentTagAlreadyExistsError):
        manager.add_environment("acme-webapp", "dev")


def test_add_environment_rejects_duplicate_tag_within_project(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "Staging")

    with pytest.raises(EnvironmentTagAlreadyExistsError):
        manager.add_environment("acme-webapp", "Staging")


def test_add_environment_same_slug_different_tag_raises_already_exists_error(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "Staging")

    with pytest.raises(EnvironmentAlreadyExistsError):
        manager.add_environment("acme-webapp", "Staging!")


def test_add_environment_allows_same_tag_across_different_projects(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.create_project(name="Other App", test_types=["ui"])

    manager.add_environment("acme-webapp", "Staging")
    env = manager.add_environment("other-app", "Staging")

    assert env.label == "Staging"


def test_update_package_merges_and_revalidates_ui_fields(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "staging")

    manager.update_package(
        "acme-webapp", "staging", "ui", base_url="https://staging.acme.com", instructions=None
    )
    env = manager.update_package(
        "acme-webapp", "staging", "ui", env_vars={"FEATURE_FLAG_X": "true"}
    )

    ui = env.packages["ui"]
    assert ui.base_url == "https://staging.acme.com"
    assert ui.env_vars == {"FEATURE_FLAG_X": "true"}

    reread = manager.get_environment("acme-webapp", "staging")
    assert reread.packages["ui"].base_url == "https://staging.acme.com"


def test_update_project_changes_name_description_test_types(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])

    updated = manager.update_project(
        "acme-webapp", name="Acme Web App", description="Updated description"
    )

    assert updated.name == "Acme Web App"
    assert updated.description == "Updated description"
    assert manager.get_project("acme-webapp").name == "Acme Web App"


def test_update_project_on_archived_project_raises(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.archive_project("acme-webapp")

    with pytest.raises(ArchivedError):
        manager.update_project("acme-webapp", name="New Name")


def test_update_project_rejects_rename_to_existing_name(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.create_project(name="Other App", test_types=["ui"])

    with pytest.raises(ProjectNameAlreadyExistsError):
        manager.update_project("other-app", name="Acme Webapp")


def test_update_project_allows_rename_to_own_current_name(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])

    updated = manager.update_project("acme-webapp", name="Acme Webapp")

    assert updated.name == "Acme Webapp"


def test_list_projects_filters_archived_by_default_and_include_archived_flag_works(
    tmp_path: Path,
):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.create_project(name="Other App", test_types=["ui"])
    manager.archive_project("other-app")

    active = manager.list_projects()
    assert [p.id for p in active] == ["acme-webapp"]

    everything = manager.list_projects(include_archived=True)
    assert {p.id for p in everything} == {"acme-webapp", "other-app"}


def test_archive_project_sets_archived_true_files_remain(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])

    archived = manager.archive_project("acme-webapp")

    assert archived.archived is True
    project_dir = tmp_path / "projects" / "acme-webapp"
    assert project_dir.is_dir()
    assert (project_dir / "project.json").exists()
    assert manager.get_project("acme-webapp").archived is True


def test_archive_project_already_archived_raises(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.archive_project("acme-webapp")

    with pytest.raises(ArchivedError):
        manager.archive_project("acme-webapp")


def test_delete_project_removes_directory_from_disk(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    project_dir = tmp_path / "projects" / "acme-webapp"
    assert project_dir.is_dir()

    manager.delete_project("acme-webapp")

    assert not project_dir.exists()
    with pytest.raises(ProjectNotFoundError):
        manager.get_project("acme-webapp")


def test_delete_project_missing_raises(tmp_path: Path):
    manager = make_manager(tmp_path)

    with pytest.raises(ProjectNotFoundError):
        manager.delete_project("nope")


def test_archive_environment_sets_archived_true_does_not_remove_from_project_environments_list(
    tmp_path: Path,
):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")

    archived = manager.archive_environment("acme-webapp", "dev")

    assert archived.archived is True
    project = manager.get_project("acme-webapp")
    assert "dev" in project.environments
    env_dir = tmp_path / "projects" / "acme-webapp" / "environments" / "dev"
    assert (env_dir / "environment.json").exists()


def test_delete_environment_removes_directory_and_unlists_it(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")
    env_dir = tmp_path / "projects" / "acme-webapp" / "environments" / "dev"
    assert env_dir.is_dir()

    manager.delete_environment("acme-webapp", "dev")

    assert not env_dir.exists()
    project = manager.get_project("acme-webapp")
    assert "dev" not in project.environments


def test_list_environments_filters_archived_by_default(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")
    manager.add_environment("acme-webapp", "staging")
    manager.archive_environment("acme-webapp", "staging")

    active = manager.list_environments("acme-webapp")
    assert [e.id for e in active] == ["dev"]

    everything = manager.list_environments("acme-webapp", include_archived=True)
    assert {e.id for e in everything} == {"dev", "staging"}


def test_update_environment_changes_label_schedule_and_destructive_safe(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")

    updated = manager.update_environment(
        "acme-webapp",
        "dev",
        label="Development",
        schedule=ScheduleConfig(cron="0 0 * * *"),
        is_destructive_safe=True,
    )

    assert updated.id == "dev"
    assert updated.label == "Development"
    assert updated.schedule.cron == "0 0 * * *"
    assert updated.is_destructive_safe is True
    assert manager.get_environment("acme-webapp", "dev").label == "Development"


def test_update_environment_rename_to_own_current_label_succeeds(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")

    updated = manager.update_environment("acme-webapp", "dev", label="dev")

    assert updated.label == "dev"


def test_update_environment_rename_to_taken_label_raises(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")
    manager.add_environment("acme-webapp", "staging")

    with pytest.raises(EnvironmentTagAlreadyExistsError):
        manager.update_environment("acme-webapp", "dev", label="staging")


def test_update_environment_on_archived_environment_raises(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")
    manager.archive_environment("acme-webapp", "dev")

    with pytest.raises(ArchivedError):
        manager.update_environment("acme-webapp", "dev", label="Development")


def test_get_project_missing_raises():
    manager = ProjectManager(Path("/nonexistent-root"))
    with pytest.raises(ProjectNotFoundError):
        manager.get_project("nope")


def test_get_environment_missing_raises(tmp_path: Path):
    manager = make_manager(tmp_path)
    manager.create_project(name="Acme Webapp", test_types=["ui"])

    with pytest.raises(EnvironmentNotFoundError):
        manager.get_environment("acme-webapp", "nope")


def test_full_create_configure_archive_flow(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")
    manager.add_environment("acme-webapp", "staging")
    manager.update_package("acme-webapp", "dev", "ui", base_url="https://dev.acme.com")

    dev_env = manager.get_environment("acme-webapp", "dev")
    assert dev_env.packages["ui"].base_url == "https://dev.acme.com"

    manager.archive_project("acme-webapp")
    project = manager.get_project("acme-webapp")
    assert project.archived is True
    assert (tmp_path / "projects" / "acme-webapp" / "environments" / "dev").is_dir()
    assert (tmp_path / "projects" / "acme-webapp" / "environments" / "staging").is_dir()


def test_full_create_configure_delete_flow_removes_everything(tmp_path: Path):
    manager = make_manager(tmp_path)

    manager.create_project(name="Acme Webapp", test_types=["ui"])
    manager.add_environment("acme-webapp", "dev")
    manager.add_environment("acme-webapp", "staging")
    manager.update_package("acme-webapp", "dev", "ui", base_url="https://dev.acme.com")

    manager.delete_project("acme-webapp")

    assert not (tmp_path / "projects" / "acme-webapp").exists()
