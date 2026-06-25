import requests
import time
from execution.validator_factory import ValidatorFactory
from execution.resource_context import ResourceContext
from Utils.resource_group import group_by_resource
from Utils.logger import logger


class APIExecutor:

    @staticmethod
    def send_request(method, url, headers=None, query_params=None, json_body=None):
        """
        Low-level HTTP call shared by normal test-case execution and the
        framework-synthesized lifecycle verification calls.

        Returns: (response, response_json, execution_time_ms)
        """

        start_time = time.perf_counter()

        response = requests.request(
            method=method,
            url=url,
            params=query_params or {},
            json=json_body,
            headers=headers or {},
        )

        execution_time_ms = round((time.perf_counter() - start_time) * 1000, 2)

        try:
            response_json = response.json()
        except ValueError:
            response_json = {}

        return response, response_json, execution_time_ms

    @staticmethod
    def execute_test_case(base_url, endpoint, method, tc, resource_key, path_param_overrides=None):
        """
        Executes a single generated test case against resource_key's
        ResourceContext scope.

        Returns: (result_dict, response_json, status_code)
        """

        validator = ValidatorFactory.get_validator(method)

        resolved_path_params = ResourceContext.resolve(resource_key, tc.get("path_params", {}))
        resolved_query_params = ResourceContext.resolve(resource_key, tc.get("query_params", {}))
        resolved_request_data = ResourceContext.resolve(resource_key, tc.get("request_data", {}))

        if path_param_overrides:
            resolved_path_params = {**resolved_path_params, **path_param_overrides}

        url = base_url + endpoint

        for k, v in resolved_path_params.items():
            url = url.replace("{" + k + "}", str(v))

        headers = tc.get("headers", {})

        logger.info(f"Executing testcase {tc['tc_id']} {tc['test_scenario']}")

        response, response_json, execution_time_ms = APIExecutor.send_request(
            method=method,
            url=url,
            headers=headers,
            query_params=resolved_query_params,
            json_body=resolved_request_data,
        )

        if method.upper() == "POST" and response.status_code in [200, 201]:
            ResourceContext.store(resource_key, response_json)

        validation_result = validator.validate(
            request_data=resolved_request_data,
            response_json=response_json,
            status_code=response.status_code,
            expected=tc["expected_response"],
        )

        result = {
            "tc_id": tc["tc_id"],
            "test_scenario": tc["test_scenario"],
            "lifecycle_role": tc.get("lifecycle_role", "independent"),
            "status": ("PASS" if validation_result["passed"] else "FAIL"),
            "expected_status_code": tc["expected_response"]["status_code"],
            "actual_status_code": response.status_code,
            "execution_time_ms": execution_time_ms,
            "request": {
                "method": method,
                "url": url,
                "query_params": resolved_query_params,
                "headers": headers,
                "request_data": resolved_request_data,
                "path_params": resolved_path_params,
            },
            "response_body": response.text,
            "validation_details": validation_result["validation_details"],
        }

        return result, response_json, response.status_code

    @staticmethod
    def execute(project, results):

        from execution.lifecycle_executor import LifecycleExecutor

        base_url = project["base_url"]

        all_results = []

        groups = group_by_resource(results)

        for resource_key, group_entries in groups.items():

            logger.info(f"Executing resource group '{resource_key}'")

            all_results.extend(LifecycleExecutor.run(base_url, resource_key, group_entries))

        return all_results
