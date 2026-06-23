import threading
from pathlib import Path

import pytest

from maya.storage.models import TestCaseAdapter, UITestCase
from maya.storage.test_case_store import TestCaseStore


@pytest.fixture
def store(tmp_path: Path) -> TestCaseStore:
    for status in ("pending", "approved", "archived"):
        (tmp_path / "test_cases" / status).mkdir(parents=True)
    return TestCaseStore(tmp_path)


def make_ui_test_case(test_id: str = "", view_identity: str = "login-page") -> UITestCase:
    return UITestCase(
        id=test_id,
        created_by="exploration_agent",
        view_identity=view_identity,
        locator_confidence=0.95,
        steps=[],
    )


def test_create_writes_to_pending(store: TestCaseStore, tmp_path: Path):
    tc = make_ui_test_case()
    tc_id = store.create(tc)

    path = tmp_path / "test_cases" / "pending" / f"{tc_id}.json"
    assert path.exists()
    assert not list((tmp_path / "test_cases" / "pending").glob("*.tmp"))


def test_get_finds_across_all_statuses(store: TestCaseStore, tmp_path: Path):
    tc = make_ui_test_case()
    tc_id = store.create(tc)

    src = tmp_path / "test_cases" / "pending" / f"{tc_id}.json"
    dst = tmp_path / "test_cases" / "approved" / f"{tc_id}.json"
    src.replace(dst)

    found = store.get(tc_id)
    assert found.id == tc_id


def test_get_missing_raises(store: TestCaseStore):
    with pytest.raises(FileNotFoundError):
        store.get("tc_doesnotexist")


def test_list_returns_only_requested_status(store: TestCaseStore, tmp_path: Path):
    store.create(make_ui_test_case(view_identity="a"))
    store.create(make_ui_test_case(view_identity="b"))

    other = make_ui_test_case(test_id="tc_preexisting", view_identity="c")
    (tmp_path / "test_cases" / "approved" / "tc_preexisting.json").write_text(
        other.model_dump_json()
    )

    pending = store.list("pending")
    approved = store.list("approved")

    assert len(pending) == 2
    assert len(approved) == 1
    assert approved[0].id == "tc_preexisting"


def test_list_unknown_status_raises(store: TestCaseStore):
    with pytest.raises(ValueError):
        store.list("bogus")


def test_full_lifecycle_pending_approved_archived(store: TestCaseStore, tmp_path: Path):
    tc = make_ui_test_case()
    tc_id = store.create(tc)

    assert len(store.list("pending")) == 1
    fetched = store.get(tc_id)
    assert fetched.status == "pending"

    store.move(tc_id, "pending", "approved")
    assert store.list("pending") == []
    approved = store.get(tc_id)
    assert approved.status == "approved"
    assert not (tmp_path / "test_cases" / "pending" / f"{tc_id}.json").exists()

    store.move(tc_id, "approved", "archived")
    assert store.list("approved") == []
    archived = store.get(tc_id)
    assert archived.status == "archived"


def test_move_missing_source_raises(store: TestCaseStore):
    with pytest.raises(FileNotFoundError):
        store.move("tc_doesnotexist", "pending", "approved")


def test_move_same_status_raises(store: TestCaseStore):
    tc_id = store.create(make_ui_test_case())
    with pytest.raises(ValueError):
        store.move(tc_id, "pending", "pending")


def test_concurrent_create_both_succeed(store: TestCaseStore, tmp_path: Path):
    barrier = threading.Barrier(2)
    results: dict[str, str] = {}

    def worker(key: str, view_identity: str) -> None:
        barrier.wait()
        results[key] = store.create(make_ui_test_case(view_identity=view_identity))

    t1 = threading.Thread(target=worker, args=("a", "page-a"))
    t2 = threading.Thread(target=worker, args=("b", "page-b"))
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    pending_dir = tmp_path / "test_cases" / "pending"
    for key in ("a", "b"):
        path = pending_dir / f"{results[key]}.json"
        assert path.exists()
        parsed = TestCaseAdapter.validate_json(path.read_bytes())
        assert isinstance(parsed, UITestCase)
