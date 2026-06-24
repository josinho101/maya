from __future__ import annotations

import json
from pathlib import Path

import pytest

from maya.managers.project_manager import ProjectManager
from maya.runners.exploration_runner import run_exploration
from maya.storage.atomic import atomic_write_json
from maya.storage.models import ExplorationConfig
from maya.storage.test_case_store import TestCaseStore


@pytest.mark.integration
def test_run_exploration_end_to_end_with_no_auth(demo_app_url, ollama_models, tmp_path: Path):
    vision_models = [m for m in ollama_models if "vl" in m.lower() or "vision" in m.lower()]
    if not vision_models:
        pytest.skip("no multimodal model installed locally")

    (tmp_path / "global_config.json").write_text(
        json.dumps({"model_preferences": {"ui_explore_heal": [vision_models[0]]}})
    )

    project_manager = ProjectManager(tmp_path)
    project = project_manager.create_project(
        name="Demo Exploration Project", test_types=["ui"], environments=["dev"]
    )
    project_manager.update_package("demo-exploration-project", "dev", "ui", base_url=demo_app_url)

    # Keep the integration run fast: a handful of steps is enough to prove the
    # whole F1-F5 stack wires together end to end.
    project = project.model_copy(
        update={"exploration": ExplorationConfig(max_steps=5, plateau_steps=5)}
    )
    atomic_write_json(tmp_path / "projects" / project.id / "project.json", project)

    created_ids = run_exploration(tmp_path, project.id, "dev")

    assert created_ids
    test_case_store = TestCaseStore(tmp_path / "projects" / project.id)
    pending = test_case_store.list("pending")
    assert len(pending) == len(created_ids)
    assert all(tc.id in created_ids for tc in pending)
