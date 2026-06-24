"""`run_exploration`: F5-070 entry point wiring Project/Environment (F3) and the
`ui` package's resolved credentials into a fresh `ExplorationAgent` run. Later
epics (F12's scheduler, F13's REST trigger) call into this function directly —
keep its signature stable."""

from __future__ import annotations

from pathlib import Path

from maya.adapters.ollama_adapter import OllamaAdapter
from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.agents.exploration_agent import ExplorationAgent
from maya.config import load_global_config
from maya.managers.project_manager import ProjectManager
from maya.managers.secrets_store import SecretsStore
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.storage.models import AuthConfig
from maya.storage.test_case_store import TestCaseStore


def run_exploration(root_dir: Path, project_id: str, environment_id: str) -> list[str]:
    root_dir = Path(root_dir)

    project_manager = ProjectManager(root_dir)
    project = project_manager.get_project(project_id)
    resolved_package = project_manager.get_resolved_package(project_id, environment_id, "ui")

    base_url = resolved_package["base_url"]
    auth_data = resolved_package.get("auth")
    auth = AuthConfig.model_validate(auth_data) if auth_data else None
    upload_fixtures = resolved_package.get("upload_fixtures", [])

    env_dir = root_dir / "projects" / project_id / "environments" / environment_id
    session_path = env_dir / "storage_state.json"

    global_config = load_global_config(root_dir / "global_config.json")
    llm = OllamaAdapter(global_config)

    project_dir = root_dir / "projects" / project_id
    test_case_store = TestCaseStore(project_dir)
    snapshot_engine = ViewSnapshotEngine(root_dir)

    has_session = session_path.exists()
    driver = PlaywrightAdapter(storage_state=session_path if has_session else None)
    try:
        agent = ExplorationAgent(
            llm=llm,
            driver=driver,
            snapshot_engine=snapshot_engine,
            test_case_store=test_case_store,
            project_id=project_id,
            env_id=environment_id,
            upload_fixtures=upload_fixtures,
        )

        if not has_session:
            if auth is not None and auth.strategy == "form_login":
                secrets = SecretsStore(root_dir)
                username = secrets.get(project_id, environment_id, "username")
                password = secrets.get(project_id, environment_id, "password")
                agent.login(base_url, auth, username, password, session_path)
            else:
                driver.navigate(base_url)

        return agent.run(
            max_steps=project.exploration.max_steps,
            plateau_steps=project.exploration.plateau_steps,
        )
    finally:
        driver.close()
