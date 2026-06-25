import json
import os

from configs.settings import PATHS


class TestCaseStorage:

    @staticmethod
    def delete(output_dir):
        file_path = os.path.join(output_dir, PATHS["testcase_filename"])
        if os.path.isfile(file_path):
            os.remove(file_path)

    @staticmethod
    def remove_endpoints(file_path, endpoints_to_remove):
        keys = {(item["endpoint"], item["method"].upper()) for item in endpoints_to_remove}
        with open(file_path, "r") as f:
            data = json.load(f)
        data["results"] = [
            r for r in data.get("results", [])
            if (r.get("endpoint"), r.get("method", "").upper()) not in keys
        ]
        with open(file_path, "w") as f:
            json.dump(data, f, indent=2)

    # OUTPUT_DIR = "generated_testcases"

    @staticmethod
    def save(output_dir, test_cases):

        os.makedirs(output_dir, exist_ok=True)

        file_path = os.path.join(output_dir, PATHS["testcase_filename"])

        with open(file_path, "w") as file:

            json.dump(test_cases, file, indent=2)

        return file_path

    @staticmethod
    def load(output_dir, file_name):

        file_path = os.path.join(output_dir, file_name)

        with open(file_path, "r") as file:

            return json.load(file)

    @staticmethod
    def get_existing_testcases(project_dir):

        file_path = os.path.join(project_dir, PATHS["testcase_filename"])

        if os.path.isfile(file_path):
            return file_path

        return None
