from pathlib import Path

import pytest

from maya.storage.scenario_session_store import (
    ScenarioSessionNotFoundError,
    ScenarioSessionStore,
)


@pytest.fixture
def store(tmp_path: Path) -> ScenarioSessionStore:
    (tmp_path / "scenario_sessions").mkdir(parents=True)
    return ScenarioSessionStore(tmp_path)


def test_create_writes_session_with_text_persisted(store: ScenarioSessionStore, tmp_path: Path):
    session = store.create(
        project_id="demo-proj", environment_id="dev", text="a user logs in and clicks the button"
    )

    assert session.status == "pending_interpretation"
    assert session.text == "a user logs in and clicks the button"
    path = tmp_path / "scenario_sessions" / f"{session.id}.json"
    assert path.exists()
    assert not list((tmp_path / "scenario_sessions").glob("*.tmp"))


def test_get_round_trips(store: ScenarioSessionStore):
    session = store.create(project_id="demo-proj", environment_id="dev", text="do a thing")
    fetched = store.get(session.id)
    assert fetched == session


def test_get_unknown_id_raises(store: ScenarioSessionStore):
    with pytest.raises(ScenarioSessionNotFoundError):
        store.get("scenario_doesnotexist")


def test_update_persists_status_transition(store: ScenarioSessionStore):
    session = store.create(project_id="demo-proj", environment_id="dev", text="do a thing")
    updated = store.update(session.id, status="completed", resulting_test_case_id="tc_abc")

    assert updated.status == "completed"
    assert updated.resulting_test_case_id == "tc_abc"
    assert store.get(session.id) == updated


def test_ref_path_points_at_scenario_sessions_file(store: ScenarioSessionStore):
    session = store.create(project_id="demo-proj", environment_id="dev", text="do a thing")
    assert store.ref_path(session.id) == f"scenario_sessions/{session.id}.json"


def test_create_ids_are_unique_for_rapid_submissions(store: ScenarioSessionStore):
    sessions = [
        store.create(project_id="demo-proj", environment_id="dev", text=f"scenario {i}")
        for i in range(5)
    ]
    assert len({s.id for s in sessions}) == 5
