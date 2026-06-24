"""`ScenarioInterpreter`: F10's goal-directed sibling to F5's `ExplorationAgent` —
same perceive (AX-tree + screenshot) -> LLM -> act loop shape (composed via
`agent_actions.py`), but steered at a free-text scenario instead of open-ended
exploration, and terminating in either a completed `UITestCase` or a
structured "stuck" report instead of just stopping on a step/plateau budget.
Per plan.md §5.b and features/11-scenario-interpreter.md (F10-020/030/040).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from maya.adapters.browser_driver import BrowserDriver
from maya.adapters.llm_client import LLMClient
from maya.agents.agent_actions import execute_action, perceive
from maya.agents.exploration_agent import ParsedAction, _parse_action
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.models import UIStep, UITestCase
from maya.storage.test_case_store import TestCaseStore

logger = logging.getLogger("maya.agents.scenario_interpreter")

_PROMPT_TEMPLATE_PATH = Path(__file__).parent / "prompts" / "scenario.txt"

_TASK_ROLE = "ui_explore_heal"

_DEFAULT_MAX_STEPS = 30
_DEFAULT_PLATEAU_STEPS = 5

_TERMINAL_ACTIONS = ("goal_achieved", "report_stuck")


def _render_prompt(ax_tree: str, scenario: str, steps: list[UIStep]) -> str:
    template = _PROMPT_TEMPLATE_PATH.read_text()
    history = _render_history(steps)
    return template.format(ax_tree=ax_tree, scenario=scenario, history=history)


def _render_history(steps: list[UIStep]) -> str:
    if not steps:
        return "(none yet)"
    lines = []
    for i, step in enumerate(steps, start=1):
        if step.target is not None:
            detail = f"{step.target.strategy}={step.target.value!r}"
        else:
            detail = repr(step.input) if step.input is not None else ""
        lines.append(f"{i}. {step.action} {detail}".rstrip())
    return "\n".join(lines)


@dataclass
class ScenarioResult:
    status: Literal["completed", "stuck"]
    test_case_id: str | None = None
    blocked_at: str | None = None
    reason: str | None = None


class ScenarioInterpreter:
    def __init__(
        self,
        llm: LLMClient,
        driver: BrowserDriver,
        snapshot_engine: ViewSnapshotEngine,
        test_case_store: TestCaseStore,
        project_id: str,
        env_id: str,
        scenario_text: str,
        source_scenario_ref: str,
        upload_fixtures: list[str] | None = None,
    ) -> None:
        self._llm = llm
        self._driver = driver
        self._snapshot_engine = snapshot_engine
        self._test_case_store = test_case_store
        self._project_id = project_id
        self._env_id = env_id
        self._scenario_text = scenario_text
        self._source_scenario_ref = source_scenario_ref
        self._upload_fixtures = set(upload_fixtures or [])

        self._steps: list[UIStep] = []
        self._flow_view_identity: str | None = None
        self._last_view_identity: str | None = None

    def step(self) -> ParsedAction | None:
        """Perceive, prompt the LLM for one action toward the scenario goal,
        and execute it unless it's a terminal action (`goal_achieved`/
        `report_stuck`), which the caller interprets itself. Returns `None`
        if no valid action could be parsed or executed."""
        ax_tree, screenshot, view_identity = perceive(
            self._driver, self._snapshot_engine, self._project_id, self._env_id
        )
        self._last_view_identity = view_identity
        if self._flow_view_identity is None:
            self._flow_view_identity = view_identity

        prompt = _render_prompt(ax_tree, self._scenario_text, self._steps)
        # Same constraint as ExplorationAgent.step(): never pass tools= here,
        # qwen2.5vl rejects it outright — the prompt's JSON-object format is
        # the only contract this loop relies on.
        response = self._llm.generate(prompt, images=[screenshot], task_role=_TASK_ROLE)
        action = _parse_action(response)
        if action is None:
            logger.warning("scenario interpreter could not parse an action from LLM response")
            return None

        if action.name in _TERMINAL_ACTIONS:
            return action

        try:
            self._steps.append(execute_action(self._driver, action, self._upload_fixtures))
        except Exception:
            logger.warning(
                "scenario interpreter failed to execute action %r", action.name, exc_info=True
            )
            return None
        return action

    def run(self, max_steps: int | None = None, plateau_steps: int | None = None) -> ScenarioResult:
        """Loops `step()` until the scenario is completed (`goal_achieved`),
        explicitly reported stuck (`report_stuck`), stalls (no new
        `view_identity` for `plateau_steps` consecutive steps), an action
        can't be parsed/executed, or `max_steps` is exhausted — every path
        except completion returns a `stuck` result rather than silently
        producing nothing."""
        max_steps = max_steps if max_steps is not None else _DEFAULT_MAX_STEPS
        plateau_steps = plateau_steps if plateau_steps is not None else _DEFAULT_PLATEAU_STEPS

        seen: set[str] = set()
        plateau_count = 0
        for _ in range(max_steps):
            action = self.step()
            if action is None:
                return self._stuck("could not determine or execute a next action")
            if action.name == "goal_achieved":
                return self._completed(action.arguments.get("summary"))
            if action.name == "report_stuck":
                reason = action.arguments.get("reason") or "the model reported being stuck"
                return self._stuck(reason)

            identity = self._last_view_identity
            if identity in seen:
                plateau_count += 1
                if plateau_count >= plateau_steps:
                    return self._stuck(f"no progress for {plateau_steps} consecutive steps")
            else:
                seen.add(identity)
                plateau_count = 0

        return self._stuck("step budget exhausted before completing the scenario")

    def _completed(self, summary: str | None) -> ScenarioResult:
        test_case = UITestCase(
            created_by="scenario_interpreter",
            source_scenario_ref=self._source_scenario_ref,
            view_identity=self._flow_view_identity or self._last_view_identity or "",
            locator_confidence=1.0,
            steps=self._steps,
            tags=[summary] if summary else [],
        )
        test_case_id = self._test_case_store.create(test_case)
        return ScenarioResult(status="completed", test_case_id=test_case_id)

    def _stuck(self, reason: str) -> ScenarioResult:
        return ScenarioResult(
            status="stuck", blocked_at=self._last_view_identity, reason=reason
        )
