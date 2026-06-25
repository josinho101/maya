import json

from execution.api_executor import APIExecutor
from storage.testcase_storage import TestCaseStorage
from storage.execution_storage import ExecutionStorage


class ExecutionRunner:

    @staticmethod
    def execute(project_path, input_file):

        with open(input_file, "r") as f:
            generated_test_cases = json.load(f)

            execution_results = APIExecutor.execute(
                project=generated_test_cases["project"],
                results=generated_test_cases["results"],
            )

            report_path = ExecutionStorage.save(project_path, execution_results)

            return report_path
