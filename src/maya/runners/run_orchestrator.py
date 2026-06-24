"""`RunOrchestrator.run`: F7-060 entry point loading a project's approved UI test
cases and replaying them via `ExecutionEngine`, aggregating into one `RunSummary`
written to `run_summary.json` (F1-040's persisted shape). F8-040 adds the diff-gate
branching on top of this same method (per view: reuse on none/cosmetic, reuse +
healing-ready flag on structural-minor, scoped re-exploration on structural-major);
F13-010 calls it from the async REST trigger — keep its signature stable."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.engines.execution_engine import ExecutionEngine
from maya.managers.project_manager import ProjectManager
from maya.perception.snapshot_engine import ViewSnapshotEngine
from maya.runners.exploration_runner import run_exploration
from maya.storage.atomic import atomic_write_json
from maya.storage.models import RunResultEntry, RunSummary, Severity, UITestCase
from maya.storage.test_case_store import TestCaseStore


class RunOrchestrator:
    def __init__(self, root_dir: Path) -> None:
        self._root_dir = Path(root_dir)
        self._project_manager = ProjectManager(self._root_dir)

    def run(self, project_id: str, environment_id: str) -> RunSummary:
        resolved_package = self._project_manager.get_resolved_package(
            project_id, environment_id, "ui"
        )
        base_url = resolved_package["base_url"]

        project_dir = self._project_manager.project_dir(project_id)
        test_case_store = TestCaseStore(project_dir)
        approved = [tc for tc in test_case_store.list("approved") if tc.protocol == "ui"]

        by_view: dict[str, list[UITestCase]] = defaultdict(list)
        for tc in approved:
            by_view[tc.view_identity].append(tc)

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        run_id = f"run_{timestamp}_{uuid4().hex}"
        run_dir = project_dir / "environments" / environment_id / "runs" / run_id
        screenshots_dir = run_dir / "screenshots"

        snapshot_engine = ViewSnapshotEngine(self._root_dir)
        decisions: dict[str, Any] = {}
        results: list[RunResultEntry] = []

        for view_identity, view_test_cases in by_view.items():
            driver = PlaywrightAdapter()
            try:
                # Each test case starts from the package's base view so one test
                # case's end state can't bleed into the next (e.g. a counter
                # incremented by an earlier test case). The diff gate also reaches
                # the view to check this way — per-view navigation beyond base_url
                # isn't built yet, so every group's capture happens at base_url.
                driver.navigate(base_url)
                # Load "previous" before capturing "current" — capture() persists
                # immediately, and would otherwise become its own "previous" lookup.
                previous = snapshot_engine.load_latest(
                    project_id, environment_id, view_identity
                )
                current = snapshot_engine.capture(driver, project_id, environment_id)
                severity = (
                    Severity.NONE
                    if previous is None
                    else snapshot_engine.diff(current, previous)
                )

                if severity != Severity.STRUCTURAL_MAJOR:
                    decisions[view_identity] = {"severity": severity, "action": "reuse"}
                    if severity == Severity.STRUCTURAL_MINOR:
                        decisions[view_identity]["healing_ready"] = True

                    engine = ExecutionEngine(driver, screenshots_dir)
                    for tc in view_test_cases:
                        driver.navigate(base_url)
                        result = engine.run_test_case(tc)
                        results.append(
                            RunResultEntry(
                                test_case_id=result.test_case_id,
                                status=result.status,
                                execution_time_ms=result.execution_time_ms,
                                screenshot_refs=result.screenshot_refs,
                            )
                        )
            finally:
                driver.close()

            if severity == Severity.STRUCTURAL_MAJOR:
                # run_exploration() opens its own Playwright session — the
                # orchestrator's driver above must already be closed (Playwright's
                # sync API can't run two sessions in the same thread at once).
                new_test_case_ids = run_exploration(
                    self._root_dir,
                    project_id,
                    environment_id,
                    view_identity=view_identity,
                )
                decisions[view_identity] = {
                    "severity": severity,
                    "action": "re-explore",
                    "new_test_case_ids": new_test_case_ids,
                }

        summary = RunSummary(
            run_id=run_id,
            environment_id=environment_id,
            decision=decisions,
            total_job_time_ms=sum(r.execution_time_ms for r in results),
            results=results,
            summary={
                "pass": sum(1 for r in results if r.status == "pass"),
                "fail": sum(1 for r in results if r.status == "fail"),
            },
        )

        run_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_json(run_dir / "run_summary.json", summary)
        return summary
