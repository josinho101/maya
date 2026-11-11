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

            # test_user_assignments are baked into the saved file at generation
            # time. If users were added after generation, backfill missing env
            # assignments so the auth header is injected correctly.
            if env_id and test_users:
                default_user_id = test_users[0]["id"]
                for endpoint_result in generated_test_cases.get("results", []):
                    if not endpoint_result.get("requires_auth"):
                        continue
                    for tc in endpoint_result.get("test_cases", []):
                        if tc.get("auth_override"):
                            continue
                        assignments = tc.get("test_user_assignments") or {}
                        if not assignments.get(env_id):
                            tc["test_user_assignments"] = {**assignments, env_id: default_user_id}

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
