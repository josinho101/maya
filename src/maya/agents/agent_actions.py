"""Perceive/act primitives shared between `ExplorationAgent` (F5) and
`ScenarioInterpreter` (F10) — both run the same perceive -> LLM -> act loop
shape over click/type/navigate/upload_file, just with different prompts and
stop conditions. Action parsing (`ParsedAction`/`_parse_action`) stays in
`exploration_agent.py`, where existing tests already import it from.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from maya.adapters.browser_driver import BrowserDriver, Locator
from maya.storage.models import AuthConfig, UIStep

if TYPE_CHECKING:
    from maya.agents.exploration_agent import ParsedAction
    from maya.perception.snapshot_engine import ViewSnapshotEngine

logger = logging.getLogger("maya.agents.actions")


def perceive(
    driver: BrowserDriver,
    snapshot_engine: ViewSnapshotEngine,
    project_id: str,
    env_id: str,
) -> tuple[str, bytes, str]:
    """Returns `(ax_tree, screenshot, view_identity)` for the current page."""
    ax_tree = driver.get_ax_tree()
    screenshot = driver.screenshot()
    record = snapshot_engine.capture(driver, project_id, env_id)
    return ax_tree, screenshot, record.view_identity


def execute_action(
    driver: BrowserDriver, action: ParsedAction, upload_fixtures: set[str]
) -> UIStep:
    """Dispatches one of click/type/navigate/upload_file against `driver`,
    returning the `UIStep` record for the caller to append to the in-progress
    flow. Raises `ValueError` for any other action name — callers handle
    agent-specific terminal actions (`finish_flow`, `goal_achieved`,
    `report_stuck`, ...) before calling this."""
    args = action.arguments
    if action.name == "click":
        locator = Locator(strategy=args["strategy"], value=args["value"])
        driver.click(locator)
        return UIStep(action="click", target=locator)
    elif action.name == "type":
        locator = Locator(strategy=args["strategy"], value=args["value"])
        text = args["text"]
        driver.type(locator, text)
        return UIStep(action="type", target=locator, input=text)
    elif action.name == "navigate":
        url = args["url"]
        driver.navigate(url)
        return UIStep(action="navigate", input=url)
    elif action.name == "upload_file":
        locator = Locator(strategy=args["strategy"], value=args["value"])
        fixture_ref = args["fixture_ref"]
        if fixture_ref in upload_fixtures and Path(fixture_ref).is_file():
            driver.upload_file(locator, Path(fixture_ref))
        else:
            logger.warning(
                "agent recorded an upload_file step with unresolved "
                "fixture_ref=%r; not executing the upload (fixture-library "
                "resolution is out of scope for F5)",
                fixture_ref,
            )
        return UIStep(action="upload_file", target=locator, fixture_ref=fixture_ref)
    else:
        raise ValueError(f"unknown action {action.name!r}")


def login(
    driver: BrowserDriver,
    base_url: str,
    auth: AuthConfig,
    username: str,
    password: str,
    session_path: Path,
) -> None:
    driver.navigate(base_url)
    if auth.username_field is not None:
        driver.type(auth.username_field, username)
    if auth.password_field is not None:
        driver.type(auth.password_field, password)
    if auth.submit_button is not None:
        driver.click(auth.submit_button)
    driver.save_storage_state(session_path)
