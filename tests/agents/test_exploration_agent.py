from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from maya.adapters.browser_driver import Locator
from maya.adapters.llm_client import LLMResponse
from maya.agents.exploration_agent import ExplorationAgent, ParsedAction, _parse_action
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.models import AuthConfig
from maya.storage.test_case_store import TestCaseStore


def _tool_call_response(name: str, arguments: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        text="",
        model="stub-model",
        raw={"message": {"tool_calls": [{"function": {"name": name, "arguments": arguments}}]}},
    )


def _text_json_response(name: str, arguments: dict[str, Any]) -> LLMResponse:
    return LLMResponse(
        text=json.dumps({"name": name, "arguments": arguments}), model="stub-model"
    )


class ScriptedLLMClient:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self._responses = list(responses)
        self.calls: list[dict[str, Any]] = []

    def generate(
        self,
        prompt: str,
        images: list[bytes] | None = None,
        tools: list[dict[str, Any]] | None = None,
        task_role: str | None = None,
    ) -> LLMResponse:
        self.calls.append(
            {"prompt": prompt, "images": images, "tools": tools, "task_role": task_role}
        )
        if not self._responses:
            return LLMResponse(text="", model="stub-model")
        return self._responses.pop(0)


class RecordingBrowserDriver:
    """Satisfies `BrowserDriver`. `change_view_on_click=True` makes `current_url()`
    change on every `click()`, so each step gets a distinct `view_identity` —
    used to test the step-budget cutoff without tripping the plateau check."""

    def __init__(
        self,
        ax_tree: str = "",
        url: str = "http://example.test/",
        change_view_on_click: bool = False,
    ) -> None:
        self.ax_tree = ax_tree
        self.url = url
        self._change_view_on_click = change_view_on_click
        self._click_count = 0
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    def navigate(self, url: str) -> None:
        self.calls.append(("navigate", (url,)))
        self.url = url

    def current_url(self) -> str:
        return self.url

    def click(self, locator: Locator) -> None:
        self.calls.append(("click", (locator,)))
        if self._change_view_on_click:
            self._click_count += 1
            self.url = f"http://example.test/{self._click_count}"

    def type(self, locator: Locator, text: str) -> None:
        self.calls.append(("type", (locator, text)))

    def get_ax_tree(self) -> str:
        return self.ax_tree

    def screenshot(self) -> bytes:
        return b"fake-png-bytes"

    def get_dom_html(self) -> str:
        return "<html><body></body></html>"

    def upload_file(self, locator: Locator, file_path: Path) -> None:
        self.calls.append(("upload_file", (locator, file_path)))

    def save_storage_state(self, path: Path) -> None:
        self.calls.append(("save_storage_state", (path,)))

    def load_storage_state(self, path: Path) -> None:
        self.calls.append(("load_storage_state", (path,)))


@pytest.fixture
def test_case_store(tmp_path: Path) -> TestCaseStore:
    for status in ("pending", "approved", "archived"):
        (tmp_path / "test_cases" / status).mkdir(parents=True)
    return TestCaseStore(tmp_path)


@pytest.fixture
def snapshot_engine(tmp_path: Path) -> ViewSnapshotEngine:
    return ViewSnapshotEngine(tmp_path)


def make_agent(
    llm: ScriptedLLMClient,
    driver: RecordingBrowserDriver,
    snapshot_engine: ViewSnapshotEngine,
    test_case_store: TestCaseStore,
    upload_fixtures: list[str] | None = None,
) -> ExplorationAgent:
    return ExplorationAgent(
        llm=llm,
        driver=driver,
        snapshot_engine=snapshot_engine,
        test_case_store=test_case_store,
        project_id="demo-proj",
        env_id="dev",
        upload_fixtures=upload_fixtures,
    )


# --- _parse_action -----------------------------------------------------------------

_LOCATOR_ARGS = {"strategy": "css", "value": "#thing"}


@pytest.mark.parametrize(
    "name,arguments",
    [
        ("click", _LOCATOR_ARGS),
        ("type", {**_LOCATOR_ARGS, "text": "hello"}),
        ("navigate", {"url": "http://example.test/page"}),
        ("upload_file", {**_LOCATOR_ARGS, "fixture_ref": "sample.pdf"}),
        ("finish_flow", {"summary": "done"}),
    ],
)
def test_parse_action_native_tool_call(name: str, arguments: dict[str, Any]):
    action = _parse_action(_tool_call_response(name, arguments))
    assert action == ParsedAction(name=name, arguments=arguments)


def test_parse_action_text_json_fallback():
    response = _text_json_response("click", _LOCATOR_ARGS)
    action = _parse_action(response)
    assert action == ParsedAction(name="click", arguments=_LOCATOR_ARGS)


def test_parse_action_malformed_returns_none():
    response = LLMResponse(text="I think you should click the button.", model="stub-model")
    assert _parse_action(response) is None


# --- step() / run() -----------------------------------------------------------------


def test_step_returns_false_on_unparseable_response(test_case_store, snapshot_engine):
    llm = ScriptedLLMClient([LLMResponse(text="not json", model="stub-model")])
    driver = RecordingBrowserDriver()
    agent = make_agent(llm, driver, snapshot_engine, test_case_store)

    assert agent.step() is False


def test_run_stops_at_max_steps(test_case_store, snapshot_engine):
    responses = [_tool_call_response("click", _LOCATOR_ARGS) for _ in range(10)]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver(change_view_on_click=True)
    agent = make_agent(llm, driver, snapshot_engine, test_case_store)

    agent.run(max_steps=3, plateau_steps=100)

    assert len(llm.calls) == 3


def test_run_stops_early_on_plateau(test_case_store, snapshot_engine):
    responses = [_tool_call_response("click", _LOCATOR_ARGS) for _ in range(10)]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver(change_view_on_click=False)
    agent = make_agent(llm, driver, snapshot_engine, test_case_store)

    agent.run(max_steps=10, plateau_steps=2)

    # 1 step establishes the seen view_identity, then 2 more identical steps
    # before the plateau counter trips the cutoff.
    assert len(llm.calls) == 3


def test_finish_flow_flushes_test_case(test_case_store, snapshot_engine):
    responses = [
        _tool_call_response("click", _LOCATOR_ARGS),
        _tool_call_response("finish_flow", {"summary": "completed the login flow"}),
    ]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver()
    agent = make_agent(llm, driver, snapshot_engine, test_case_store)

    created_ids = agent.run(max_steps=5, plateau_steps=5)

    assert len(created_ids) == 1
    test_case = test_case_store.get(created_ids[0])
    assert test_case.status == "pending"
    assert test_case.created_by == "exploration_agent"
    assert test_case.view_identity
    assert len(test_case.steps) == 1
    assert test_case.steps[0].action == "click"
    assert test_case.tags == ["completed the login flow"]


def test_upload_file_with_unresolved_fixture_is_recorded_but_not_executed(
    test_case_store, snapshot_engine
):
    responses = [
        _tool_call_response(
            "upload_file", {**_LOCATOR_ARGS, "fixture_ref": "missing-fixture.pdf"}
        ),
        _tool_call_response("finish_flow", {}),
    ]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver()
    agent = make_agent(llm, driver, snapshot_engine, test_case_store, upload_fixtures=[])

    created_ids = agent.run(max_steps=5, plateau_steps=5)

    assert not any(call[0] == "upload_file" for call in driver.calls)
    test_case = test_case_store.get(created_ids[0])
    assert test_case.steps[0].action == "upload_file"
    assert test_case.steps[0].fixture_ref == "missing-fixture.pdf"


def test_upload_file_with_resolved_fixture_is_executed(
    tmp_path, test_case_store, snapshot_engine
):
    fixture_path = tmp_path / "sample.pdf"
    fixture_path.write_bytes(b"%PDF-1.4")

    responses = [
        _tool_call_response(
            "upload_file", {**_LOCATOR_ARGS, "fixture_ref": str(fixture_path)}
        ),
        _tool_call_response("finish_flow", {}),
    ]
    llm = ScriptedLLMClient(responses)
    driver = RecordingBrowserDriver()
    agent = make_agent(
        llm, driver, snapshot_engine, test_case_store, upload_fixtures=[str(fixture_path)]
    )

    agent.run(max_steps=5, plateau_steps=5)

    upload_calls = [call for call in driver.calls if call[0] == "upload_file"]
    assert len(upload_calls) == 1
    assert upload_calls[0][1][1] == fixture_path


# --- login() -------------------------------------------------------------------------


def test_login_dispatches_type_type_click_and_saves_state(
    tmp_path, test_case_store, snapshot_engine
):
    llm = ScriptedLLMClient([])
    driver = RecordingBrowserDriver()
    agent = make_agent(llm, driver, snapshot_engine, test_case_store)

    auth = AuthConfig(
        strategy="form_login",
        secure_ref="demo-proj.dev",
        username_field=Locator(strategy="css", value="#username"),
        password_field=Locator(strategy="css", value="#password"),
        submit_button=Locator(strategy="test_id", value="login-button"),
    )
    session_path = tmp_path / "storage_state.json"

    agent.login(
        base_url="http://example.test/",
        auth=auth,
        username="alice",
        password="s3cret",
        session_path=session_path,
    )

    assert driver.calls == [
        ("navigate", ("http://example.test/",)),
        ("type", (auth.username_field, "alice")),
        ("type", (auth.password_field, "s3cret")),
        ("click", (auth.submit_button,)),
        ("save_storage_state", (session_path,)),
    ]
