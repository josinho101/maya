"""`ExplorationAgent`: perceive (AX-tree + screenshot) -> LLM tool-calling -> act,
per plan.md S2.3 and features/06-autonomous-ui-exploration-agent.md (F5-010/020/040/050).
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from maya.adapters.browser_driver import BrowserDriver, Locator
from maya.adapters.llm_client import LLMClient, LLMResponse
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.models import AuthConfig, UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore

logger = logging.getLogger("maya.agents.exploration")

_PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "exploration.txt"

_TASK_ROLE = "ui_explore_heal"

_DEFAULT_MAX_STEPS = 30
_DEFAULT_PLATEAU_STEPS = 5

_LOCATOR_PROPERTIES: dict[str, Any] = {
    "strategy": {
        "type": "string",
        "enum": ["test_id", "role", "text", "label", "css", "xpath"],
    },
    "value": {"type": "string"},
}

EXPLORATION_TOOLS: list[dict[str, Any]] = [
    # Ollama function-calling schema for the 5 available actions. Kept as a typed
    # reference even though `step()` never sends this to `generate(tools=...)` —
    # see the comment there for why.
    {
        "type": "function",
        "function": {
            "name": "click",
            "description": "Click on an element identified by a locator.",
            "parameters": {
                "type": "object",
                "properties": dict(_LOCATOR_PROPERTIES),
                "required": ["strategy", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "type",
            "description": "Type text into an input element identified by a locator.",
            "parameters": {
                "type": "object",
                "properties": {**_LOCATOR_PROPERTIES, "text": {"type": "string"}},
                "required": ["strategy", "value", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "navigate",
            "description": "Navigate to an absolute URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "upload_file",
            "description": (
                "Set a file-input element's selected file to a fixture reference."
            ),
            "parameters": {
                "type": "object",
                "properties": {**_LOCATOR_PROPERTIES, "fixture_ref": {"type": "string"}},
                "required": ["strategy", "value", "fixture_ref"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "finish_flow",
            "description": "Signal that one coherent flow has been completed.",
            "parameters": {
                "type": "object",
                "properties": {"summary": {"type": "string"}},
                "required": [],
            },
        },
    },
]

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


@dataclass
class ParsedAction:
    name: str
    arguments: dict[str, Any] = field(default_factory=dict)


def _parse_action(response: LLMResponse) -> ParsedAction | None:
    """Native Ollama `tool_calls` first (plan.md S1.1); falls back to a bare
    `{"name": ..., "arguments": {...}}` JSON object in `response.text` since
    vision models aren't guaranteed to emit the native tool-calling shape."""
    message = response.raw.get("message", {}) if isinstance(response.raw, dict) else {}
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        function = tool_calls[0].get("function", {})
        name = function.get("name")
        arguments = function.get("arguments") or {}
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError:
                return None
        if not name or not isinstance(arguments, dict):
            return None
        return ParsedAction(name=name, arguments=arguments)

    match = _JSON_OBJECT_RE.search(response.text or "")
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    name = payload.get("name")
    arguments = payload.get("arguments") or {}
    if not name or not isinstance(arguments, dict):
        return None
    return ParsedAction(name=name, arguments=arguments)


def _render_prompt(ax_tree: str) -> str:
    template = _PROMPT_TEMPLATE_PATH.read_text()
    return template.format(ax_tree=ax_tree)


class ExplorationAgent:
    def __init__(
        self,
        llm: LLMClient,
        driver: BrowserDriver,
        snapshot_engine: ViewSnapshotEngine,
        test_case_store: TestCaseStore,
        project_id: str,
        env_id: str,
        upload_fixtures: list[str] | None = None,
    ) -> None:
        self._llm = llm
        self._driver = driver
        self._snapshot_engine = snapshot_engine
        self._test_case_store = test_case_store
        self._project_id = project_id
        self._env_id = env_id
        self._upload_fixtures = set(upload_fixtures or [])

        self._steps: list[UIStep] = []
        self._flow_view_identity: str | None = None
        self._last_view_identity: str | None = None
        self._created_test_case_ids: list[str] = []

    def login(
        self,
        base_url: str,
        auth: AuthConfig,
        username: str,
        password: str,
        session_path: Path,
    ) -> None:
        self._driver.navigate(base_url)
        if auth.username_field is not None:
            self._driver.type(auth.username_field, username)
        if auth.password_field is not None:
            self._driver.type(auth.password_field, password)
        if auth.submit_button is not None:
            self._driver.click(auth.submit_button)
        self._driver.save_storage_state(session_path)

    def step(self) -> bool:
        """Perceive, prompt the LLM for one tool call, and execute it. Returns
        False if no valid action could be parsed or executed (caller should
        stop the run)."""
        ax_tree = self._driver.get_ax_tree()
        screenshot = self._driver.screenshot()

        record = self._snapshot_engine.capture(self._driver, self._project_id, self._env_id)
        self._last_view_identity = record.view_identity
        if self._flow_view_identity is None:
            self._flow_view_identity = record.view_identity

        prompt = _render_prompt(ax_tree)
        # `qwen2.5vl` (the only model configured for `ui_explore_heal`) rejects any
        # request that includes `tools` with a 400 ("does not support tools") rather
        # than degrading gracefully — confirmed against a live Ollama instance. So we
        # never pass `tools=` here; the prompt instructs the JSON-object fallback
        # format instead, and `_parse_action` still checks for native `tool_calls`
        # first in case a future task_role is backed by a model that supports them.
        response = self._llm.generate(prompt, images=[screenshot], task_role=_TASK_ROLE)
        action = _parse_action(response)
        if action is None:
            logger.warning("exploration agent could not parse an action from LLM response")
            return False

        if action.name == "finish_flow":
            self._flush(summary=action.arguments.get("summary"))
            return True

        try:
            self._execute(action)
        except Exception:
            logger.warning(
                "exploration agent failed to execute action %r", action.name, exc_info=True
            )
            return False
        return True

    def run(self, max_steps: int | None = None, plateau_steps: int | None = None) -> list[str]:
        """Loops `step()` until `max_steps` is exhausted, no new `view_identity`
        appears for `plateau_steps` consecutive steps, or a step fails. Returns
        the ids of every `UITestCase` written to `pending/`."""
        max_steps = max_steps if max_steps is not None else _DEFAULT_MAX_STEPS
        plateau_steps = plateau_steps if plateau_steps is not None else _DEFAULT_PLATEAU_STEPS

        seen: set[str] = set()
        plateau_count = 0
        for _ in range(max_steps):
            if not self.step():
                break
            identity = self._last_view_identity
            if identity in seen:
                plateau_count += 1
                if plateau_count >= plateau_steps:
                    break
            else:
                seen.add(identity)
                plateau_count = 0

        self._flush()
        return self._created_test_case_ids

    def _execute(self, action: ParsedAction) -> None:
        args = action.arguments
        if action.name == "click":
            locator = Locator(strategy=args["strategy"], value=args["value"])
            self._driver.click(locator)
            self._steps.append(UIStep(action="click", target=locator))
        elif action.name == "type":
            locator = Locator(strategy=args["strategy"], value=args["value"])
            text = args["text"]
            self._driver.type(locator, text)
            self._steps.append(UIStep(action="type", target=locator, input=text))
        elif action.name == "navigate":
            url = args["url"]
            self._driver.navigate(url)
            self._steps.append(UIStep(action="navigate", input=url))
        elif action.name == "upload_file":
            locator = Locator(strategy=args["strategy"], value=args["value"])
            fixture_ref = args["fixture_ref"]
            if fixture_ref in self._upload_fixtures and Path(fixture_ref).is_file():
                self._driver.upload_file(locator, Path(fixture_ref))
            else:
                logger.warning(
                    "exploration agent recorded an upload_file step with unresolved "
                    "fixture_ref=%r; not executing the upload (fixture-library "
                    "resolution is out of scope for F5)",
                    fixture_ref,
                )
            self._steps.append(
                UIStep(action="upload_file", target=locator, fixture_ref=fixture_ref)
            )
        else:
            raise ValueError(f"unknown action {action.name!r}")

    def _flush(self, summary: str | None = None) -> None:
        if not self._steps:
            self._flow_view_identity = None
            return
        test_case = UITestCase(
            created_by="exploration_agent",
            view_identity=self._flow_view_identity or self._last_view_identity or "",
            locator_confidence=1.0,
            steps=self._steps,
            tags=[summary] if summary else [],
        )
        test_case_id = self._test_case_store.create(test_case)
        self._created_test_case_ids.append(test_case_id)
        self._steps = []
        self._flow_view_identity = None
