import json

from execution.api_executor import APIExecutor
from execution.auth_manager import AuthManager
from storage.testcase_storage import TestCaseStorage
from storage.execution_storage import ExecutionStorage


class ExecutionRunner:

    @staticmethod
    def execute(project_path, input_file, base_url_override=None, environment_name=None,
                env_id=None, auth_config=None, test_users=None):

        with open(input_file, "r") as f:
            generated_test_cases = json.load(f)

            if base_url_override:
                generated_test_cases["project"]["base_url"] = base_url_override

            users_by_id = {u["id"]: u for u in (test_users or [])}
            auth_manager = AuthManager(auth_config or {}, users_by_id)

            try:
                execution_results = APIExecutor.execute(
                    project=generated_test_cases["project"],
                    results=generated_test_cases["results"],
                    auth_manager=auth_manager,
                    env_id=env_id,
                )
            finally:
                auth_manager.clear()

            report_path = ExecutionStorage.save(
                project_path,
                execution_results,
                environment_name=environment_name or "",
                environment_url=base_url_override or generated_test_cases["project"].get("base_url", ""),
                project_name=generated_test_cases["project"].get("name", ""),
            )

            return report_path
