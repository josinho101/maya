"""`run_scenario`: F10-010's entry point wiring a free-text scenario submission
into a fresh `ScenarioInterpreter` run, mirroring `run_exploration`'s adapter
wiring exactly. Persists a `ScenarioSession` immediately on submission and
updates it in place as interpretation progresses — see
features/11-scenario-interpreter.md F10-010."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from maya.adapters.ollama_adapter import OllamaAdapter
from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.agents.agent_actions import login
from maya.agents.scenario_interpreter import ScenarioInterpreter
from maya.config import load_global_config
from maya.managers.project_manager import ProjectManager
from maya.managers.secrets_store import SecretsStore
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.models import AuthConfig, ScenarioSession
from maya.storage.scenario_session_store import ScenarioSessionStore
from maya.storage.test_case_store import TestCaseStore


def run_scenario(
    root_dir: Path, project_id: str, environment_id: str, scenario_text: str
) -> ScenarioSession:
    root_dir = Path(root_dir)

    project_manager = ProjectManager(root_dir)
    project = project_manager.get_project(project_id)
    resolved_package = project_manager.get_resolved_package(project_id, environment_id, "ui")

    base_url = resolved_package["base_url"]
    auth_data = resolved_package.get("auth")
    auth = AuthConfig.model_validate(auth_data) if auth_data else None
    upload_fixtures = resolved_package.get("upload_fixtures", [])

    project_dir = root_dir / "projects" / project_id
    session_store = ScenarioSessionStore(project_dir)
    session = session_store.create(
        project_id=project_id, environment_id=environment_id, text=scenario_text
    )

    env_dir = project_dir / "environments" / environment_id
    session_path = env_dir / "storage_state.json"

    global_config = load_global_config(root_dir / "global_config.json")
    llm = OllamaAdapter(global_config)

    test_case_store = TestCaseStore(project_dir)
    snapshot_engine = ViewSnapshotEngine(root_dir)

    has_session = session_path.exists()
    driver = PlaywrightAdapter(storage_state=session_path if has_session else None)
    try:
        session = session_store.update(session.id, status="in_progress")

        interpreter = ScenarioInterpreter(
            llm=llm,
            driver=driver,
            snapshot_engine=snapshot_engine,
            test_case_store=test_case_store,
            project_id=project_id,
            env_id=environment_id,
            scenario_text=scenario_text,
            source_scenario_ref=session_store.ref_path(session.id),
            upload_fixtures=upload_fixtures,
        )

        if not has_session:
            if auth is not None and auth.strategy == "form_login":
                secrets = SecretsStore(root_dir)
                username = secrets.get(project_id, environment_id, "username")
                password = secrets.get(project_id, environment_id, "password")
                login(driver, base_url, auth, username, password, session_path)
            else:
                driver.navigate(base_url)

        result = interpreter.run(
            max_steps=project.exploration.max_steps,
            plateau_steps=project.exploration.plateau_steps,
        )
    finally:
        driver.close()

    if result.status == "completed":
        return session_store.update(
            session.id,
            status="completed",
            completed_at=datetime.now(UTC),
            resulting_test_case_id=result.test_case_id,
        )
    return session_store.update(
        session.id,
        status="stuck",
        completed_at=datetime.now(UTC),
        blocked_at=result.blocked_at,
        stuck_reason=result.reason,
    )
