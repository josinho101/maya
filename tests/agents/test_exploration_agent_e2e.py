from __future__ import annotations

from pathlib import Path

import pytest

from maya.adapters.ollama_adapter import OllamaAdapter
from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.agents.exploration_agent import ExplorationAgent
from maya.config import GlobalConfig
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.test_case_store import TestCaseStore

from ..conftest import OLLAMA_HOST


def _make_driver() -> PlaywrightAdapter:
    try:
        return PlaywrightAdapter(headless=True)
    except Exception as exc:  # noqa: BLE001 - environment-dependent (browser not installed)
        pytest.skip(f"Playwright browser not available: {exc}")


@pytest.mark.integration
def test_exploration_agent_run_against_demo_app(demo_app_url, ollama_models, tmp_path: Path):
    vision_models = [m for m in ollama_models if "vl" in m.lower() or "vision" in m.lower()]
    if not vision_models:
        pytest.skip("no multimodal model installed locally")

    config = GlobalConfig(
        ollama_host=OLLAMA_HOST, model_preferences={"ui_explore_heal": [vision_models[0]]}
    )
    llm = OllamaAdapter(config)

    for status in ("pending", "approved", "archived"):
        (tmp_path / "test_cases" / status).mkdir(parents=True)
    test_case_store = TestCaseStore(tmp_path)
    snapshot_engine = ViewSnapshotEngine(tmp_path)

    driver = _make_driver()
    try:
        driver.navigate(demo_app_url)
        agent = ExplorationAgent(
            llm=llm,
            driver=driver,
            snapshot_engine=snapshot_engine,
            test_case_store=test_case_store,
            project_id="demo-proj",
            env_id="dev",
        )
        agent.run(max_steps=5, plateau_steps=5)
    finally:
        driver.close()

    pending = test_case_store.list("pending")
    assert len(pending) >= 1
    test_case = pending[0]
    assert test_case.view_identity

    target_steps = [step for step in test_case.steps if step.target is not None]
    assert target_steps, "expected at least one step with a locator target"
    assert target_steps[0].target.strategy
    assert target_steps[0].target.value
