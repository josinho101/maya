"""F8-050: "the first thing to prove" (plan.md §10) — routine runs against an
unchanged view never touch the LLM, and a structurally-mutated view triggers
exactly the scoped re-exploration call, nothing more."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.logging_setup import configure_logging
from maya.managers.project_manager import ProjectManager
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.runners.run_orchestrator import RunOrchestrator
from maya.storage.atomic import atomic_write_json
from maya.storage.models import ExplorationConfig, LocatorTarget, UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore


def _capture_view_identity(url: str, tmp_path: Path) -> str:
    driver = PlaywrightAdapter(headless=True)
    try:
        driver.navigate(url)
        record = ViewSnapshotEngine(tmp_path).capture(driver, "scratch", "scratch")
    finally:
        driver.close()
    return record.view_identity


def _seed_approved_test_case(store: TestCaseStore, view_identity: str) -> str:
    tc = UITestCase(
        created_by="human",
        view_identity=view_identity,
        locator_confidence=1.0,
        steps=[
            UIStep(
                action="click",
                target=LocatorTarget(strategy="test_id", value="counter-button"),
                assertion={"type": "contains", "value": "Count: 1"},
            )
        ],
    )
    test_case_id = store.create(tc)
    store.move(test_case_id, "pending", "approved")
    return test_case_id


def _llm_log_lines(tmp_path: Path) -> list[str]:
    log_path = tmp_path / "logs" / "llm" / "llm.log"
    if not log_path.exists():
        return []
    return log_path.read_text().splitlines()


@pytest.mark.integration
def test_unchanged_run_makes_zero_llm_calls_then_mutation_triggers_scoped_reexploration(
    demo_app_url, demo_app_mutated_url, ollama_models, tmp_path: Path
):
    vision_models = [m for m in ollama_models if "vl" in m.lower() or "vision" in m.lower()]
    if not vision_models:
        pytest.skip("no multimodal model installed locally")

    configure_logging(tmp_path)

    project_manager = ProjectManager(tmp_path)
    project = project_manager.create_project(
        name="LLM Log Idempotency Project", test_types=["ui"], environments=["dev"]
    )
    project = project.model_copy(
        update={"exploration": ExplorationConfig(max_steps=3, plateau_steps=3)}
    )
    atomic_write_json(tmp_path / "projects" / project.id / "project.json", project)
    (tmp_path / "global_config.json").write_text(
        json.dumps({"model_preferences": {"ui_explore_heal": [vision_models[0]]}})
    )

    project_manager.update_package(project.id, "dev", "ui", base_url=demo_app_url)
    view_identity = _capture_view_identity(demo_app_url, tmp_path)
    store = TestCaseStore(project_manager.project_dir(project.id))
    _seed_approved_test_case(store, view_identity)

    orchestrator = RunOrchestrator(tmp_path)

    orchestrator.run(project.id, "dev")
    lines_after_first = len(_llm_log_lines(tmp_path))

    orchestrator.run(project.id, "dev")
    lines_after_second = len(_llm_log_lines(tmp_path))

    assert lines_after_second == lines_after_first == 0

    # Mutate: counter-button's data-testid changes underneath the approved test
    # case — a structural-major change relative to the last two runs' snapshots.
    project_manager.update_package(project.id, "dev", "ui", base_url=demo_app_mutated_url)
    summary = orchestrator.run(project.id, "dev")

    lines_after_mutation = _llm_log_lines(tmp_path)
    new_lines = lines_after_mutation[lines_after_second:]

    assert summary.decision[view_identity]["action"] == "re-explore"
    assert new_lines, "expected the scoped re-exploration call to log at least one LLM call"
    assert all("task_role=ui_explore_heal" in line for line in new_lines)
    # Bounded by the tight exploration budget set above — proves this is the one
    # scoped re-exploration call, not an unrelated full re-exploration sweep.
    assert len(new_lines) <= 3
