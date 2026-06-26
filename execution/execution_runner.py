import json

from execution.api_executor import APIExecutor
from storage.testcase_storage import TestCaseStorage
from storage.execution_storage import ExecutionStorage


class ExecutionRunner:

    @staticmethod
    def execute(project_path, input_file, base_url_override=None, environment_name=None):

        with open(input_file, "r") as f:
            generated_test_cases = json.load(f)

            if base_url_override:
                generated_test_cases["project"]["base_url"] = base_url_override

            execution_results = APIExecutor.execute(
                project=generated_test_cases["project"],
                results=generated_test_cases["results"],
            )

            report_path = ExecutionStorage.save(
                project_path,
                execution_results,
                environment_name=environment_name or "",
                environment_url=base_url_override or generated_test_cases["project"].get("base_url", ""),
                project_name=generated_test_cases["project"].get("name", ""),
            )

            return report_path
