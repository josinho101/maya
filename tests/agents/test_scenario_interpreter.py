from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from maya.adapters.llm_client import LLMResponse
from maya.agents.scenario_interpreter import ScenarioInterpreter
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.test_case_store import TestCaseStore

from .test_exploration_agent import RecordingBrowserDriver, ScriptedLLMClient, _LOCATOR_ARGS


def _tool_call_response(name: str, arguments: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        text="",
        model="stub-model",
        raw={"message": {"tool_calls": [{"function": {"name": name, "arguments": arguments}}]}},
    )


@pytest.fixture
def test_case_store(tmp_path: Path) -> TestCaseStore:
    for status in ("pending", "approved", "archived"):
        (tmp_path / "test_cases" / status).mkdir(parents=True)
    return TestCaseStore(tmp_path)


@pytest.fixture
def snapshot_engine(tmp_path: Path) -> ViewSnapshotEngine:
    return ViewSnapshotEngine(tmp_path)


def make_interpreter(
    llm: ScriptedLLMClient,
    driver: RecordingBrowserDriver,
    snapshot_engine: ViewSnapshotEngine,
    test_case_store: TestCaseStore,
    scenario_text: str = "a user logs in and clicks the counter button",
) -> ScenarioInterpreter:
    return ScenarioInterpreter(
        llm=llm,
        driver=driver,
        snapshot_engine=snapshot_engine,
        test_case_store=test_case_store,
        project_id="demo-proj",
        env_id="dev",
        scenario_text=scenario_text,
        source_scenario_ref="scenario_sessions/scenario_123.json",
    )


def test_goal_achieved_emits_test_case(test_case_store, snapshot_engine):
    responses = [
        _tool_call_response("click", _LOCATOR_ARGS),
        _tool_call_response("goal_achieved", {"summary": "logged in and clicked the counter"}),
    ]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver()
    interpreter = make_interpreter(llm, driver, snapshot_engine, test_case_store)

    result = interpreter.run(max_steps=5, plateau_steps=5)

    assert result.status == "completed"
    assert result.test_case_id is not None
    test_case = test_case_store.get(result.test_case_id)
    assert test_case.created_by == "scenario_interpreter"
    assert test_case.source_scenario_ref == "scenario_sessions/scenario_123.json"
    assert test_case.status == "pending"
    assert len(test_case.steps) == 1
    assert test_case.steps[0].action == "click"
    assert test_case.tags == ["logged in and clicked the counter"]


def test_report_stuck_returns_reason_without_test_case(test_case_store, snapshot_engine):
    responses = [
        _tool_call_response("report_stuck", {"reason": "no shopping cart exists on this page"}),
    ]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver()
    interpreter = make_interpreter(
        llm, driver, snapshot_engine, test_case_store, scenario_text="add an item to the cart"
    )

    result = interpreter.run(max_steps=5, plateau_steps=5)

    assert result.status == "stuck"
    assert result.reason == "no shopping cart exists on this page"
    assert result.test_case_id is None
    assert test_case_store.list("pending") == []


def test_plateau_triggers_stuck(test_case_store, snapshot_engine):
    responses = [_tool_call_response("click", _LOCATOR_ARGS) for _ in range(10)]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver(change_view_on_click=False)
    interpreter = make_interpreter(llm, driver, snapshot_engine, test_case_store)

    result = interpreter.run(max_steps=10, plateau_steps=2)

    assert result.status == "stuck"
    assert "no progress" in result.reason
    assert test_case_store.list("pending") == []


def test_max_steps_exhausted_triggers_stuck(test_case_store, snapshot_engine):
    responses = [_tool_call_response("click", _LOCATOR_ARGS) for _ in range(10)]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver(change_view_on_click=True)
    interpreter = make_interpreter(llm, driver, snapshot_engine, test_case_store)

    result = interpreter.run(max_steps=3, plateau_steps=100)

    assert result.status == "stuck"
    assert "step budget exhausted" in result.reason
    assert len(llm.calls) == 3
    assert test_case_store.list("pending") == []


def test_unparseable_response_triggers_stuck(test_case_store, snapshot_engine):
    llm = ScriptedLLMClient([LLMResponse(text="not json", model="stub-model")])
    driver = RecordingBrowserDriver()
    interpreter = make_interpreter(llm, driver, snapshot_engine, test_case_store)

    result = interpreter.run(max_steps=5, plateau_steps=5)

    assert result.status == "stuck"
    assert "could not determine" in result.reason
