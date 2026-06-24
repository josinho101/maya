"""`RunOrchestrator.run`: F7-060 entry point loading a project's approved UI test
cases and replaying them via `ExecutionEngine`, aggregating into one `RunSummary`
written to `run_summary.json` (F1-040's persisted shape). F8-040 later adds the
diff-gate branching on top of this same method; F13-010 calls it from the async
REST trigger — keep its signature stable."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from maya.adapters.playwright_adapter import PlaywrightAdapter
from maya.engines.execution_engine import ExecutionEngine
from maya.managers.project_manager import ProjectManager
from maya.storage.atomic import atomic_write_json
from maya.storage.models import RunResultEntry, RunSummary
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

        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        run_id = f"run_{timestamp}_{uuid4().hex}"
        run_dir = project_dir / "environments" / environment_id / "runs" / run_id
        screenshots_dir = run_dir / "screenshots"

        results: list[RunResultEntry] = []
        driver = PlaywrightAdapter()
        try:
            engine = ExecutionEngine(driver, screenshots_dir)
            for tc in approved:
                # Each test case starts from the package's base view so one test
                # case's end state can't bleed into the next (e.g. a counter
                # incremented by an earlier test case).
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

        summary = RunSummary(
            run_id=run_id,
            environment_id=environment_id,
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
