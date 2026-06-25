import re

from execution.api_executor import APIExecutor
from execution.validators.common_validator import CommonValidator
from execution.validators.data_consistency_validator import DataConsistencyValidator
from Utils.logger import logger
from Utils.resource_group import find_lifecycle_test_cases, find_verification_test_cases

_PATH_PARAM = re.compile(r"\{([^/]+)\}")


class LifecycleExecutor:
    """
    Orchestrates the CRUD lifecycle for one resource group: create the
    resource, read it back to confirm the data, update it, read it back
    again to confirm the update, delete it, then read it again to confirm
    deletion. Falls back to plain independent execution for groups with no
    "create" lifecycle role, and for every non-lifecycle test case.

    The verify_create/verify_update/verify_delete test cases are persisted
    in the generated test case catalog (see
    testcase_generator.py's _add_lifecycle_verification_test_cases) rather
    than fabricated here, so every catalog entry always produces exactly
    one result row - PASS/FAIL when it actually runs, SKIPPED when its
    prerequisite CRUD step didn't succeed.
    """

    @staticmethod
    def run(base_url, resource_key, group_entries):

        results = []
        executed_tc_ids = set()

        lifecycle_map = find_lifecycle_test_cases(group_entries)
        verification_map = find_verification_test_cases(group_entries)

        create = lifecycle_map.get("create")
        read = lifecycle_map.get("read")
        update = lifecycle_map.get("update")
        delete = lifecycle_map.get("delete")

        resource_id = None
        create_request_data = None
        create_headers = None

        if create:

            entry, tc = create
            executed_tc_ids.add(tc["tc_id"])

            logger.info(f"Executing lifecycle CREATE for resource '{resource_key}'")

            result, response_json, status_code = APIExecutor.execute_test_case(
                base_url, entry["endpoint"], entry["method"], tc, resource_key
            )
            results.append(result)

            if 200 <= status_code < 300:
                resource_id = LifecycleExecutor._extract_resource_id(response_json, lifecycle_map)
                create_request_data = result["request"]["request_data"]
                create_headers = result["request"]["headers"]

                if resource_id is None:
                    logger.warning(
                        f"Could not determine resource id for '{resource_key}' from create "
                        f"response; skipping lifecycle read/update/delete verification."
                    )
            else:
                logger.warning(
                    f"Lifecycle CREATE for '{resource_key}' did not return a success status "
                    f"({status_code}); skipping dependent read/update/delete verification."
                )

        if resource_id is not None:

            if read:

                read_entry, read_tc = read
                executed_tc_ids.add(read_tc["tc_id"])

                overrides = LifecycleExecutor._path_param_overrides(read_entry["endpoint"], resource_id)

                read_result, _, _ = APIExecutor.execute_test_case(
                    base_url, read_entry["endpoint"], read_entry["method"], read_tc, resource_key,
                    path_param_overrides=overrides,
                )
                results.append(read_result)

                verify_create = verification_map.get("verify_create")
                if verify_create:
                    _, verify_create_tc = verify_create
                    executed_tc_ids.add(verify_create_tc["tc_id"])
                    results.append(
                        LifecycleExecutor._run_verification_get(
                            base_url, read_entry, verify_create_tc, resource_id, create_headers,
                            compare_against=create_request_data,
                        )
                    )

            if update:

                entry, tc = update
                executed_tc_ids.add(tc["tc_id"])

                logger.info(f"Executing lifecycle UPDATE for resource '{resource_key}'")

                overrides = LifecycleExecutor._path_param_overrides(entry["endpoint"], resource_id)

                result, _, status_code = APIExecutor.execute_test_case(
                    base_url, entry["endpoint"], entry["method"], tc, resource_key,
                    path_param_overrides=overrides,
                )
                results.append(result)

                verify_update = verification_map.get("verify_update")
                if verify_update and read:

                    read_entry, _ = read
                    _, verify_update_tc = verify_update
                    executed_tc_ids.add(verify_update_tc["tc_id"])

                    if 200 <= status_code < 300:
                        results.append(
                            LifecycleExecutor._run_verification_get(
                                base_url, read_entry, verify_update_tc, resource_id, create_headers,
                                compare_against=result["request"]["request_data"],
                            )
                        )
                    else:
                        results.append(
                            LifecycleExecutor._skipped_result(
                                verify_update_tc,
                                "UPDATE did not return a success status; verification skipped.",
                            )
                        )

            if delete:

                entry, tc = delete
                executed_tc_ids.add(tc["tc_id"])

                logger.info(f"Executing lifecycle DELETE for resource '{resource_key}'")

                overrides = LifecycleExecutor._path_param_overrides(entry["endpoint"], resource_id)

                result, _, status_code = APIExecutor.execute_test_case(
                    base_url, entry["endpoint"], entry["method"], tc, resource_key,
                    path_param_overrides=overrides,
                )
                results.append(result)

                verify_delete = verification_map.get("verify_delete")
                if verify_delete and read:

                    read_entry, _ = read
                    _, verify_delete_tc = verify_delete
                    executed_tc_ids.add(verify_delete_tc["tc_id"])

                    if 200 <= status_code < 300 or status_code == 204:
                        results.append(
                            LifecycleExecutor._run_deleted_check(
                                base_url, read_entry, verify_delete_tc, resource_id, create_headers
                            )
                        )
                    else:
                        results.append(
                            LifecycleExecutor._skipped_result(
                                verify_delete_tc,
                                "DELETE did not return a success status; verification skipped.",
                            )
                        )

        else:

            # CREATE didn't run or didn't succeed - every verify_* test case
            # needs the id it produced, so none of them can run. Emit an
            # explicit SKIPPED row for each instead of silently dropping
            # them, so the result count always matches the catalog count.
            for role in ("verify_create", "verify_update", "verify_delete"):

                verify = verification_map.get(role)

                if verify:
                    _, verify_tc = verify
                    executed_tc_ids.add(verify_tc["tc_id"])
                    results.append(
                        LifecycleExecutor._skipped_result(
                            verify_tc,
                            "CREATE did not succeed, or the created resource id could not be "
                            "determined; verification skipped.",
                        )
                    )

        # Every remaining test case (negative/boundary/required-field cases,
        # plus any lifecycle-tagged ones we couldn't actually chain) runs
        # exactly as before - independent of resource chaining.
        for entry in group_entries:

            endpoint = entry.get("endpoint", "")
            method = entry.get("method", "")

            for tc in entry.get("test_cases", []):

                if tc.get("tc_id") in executed_tc_ids:
                    continue

                result, _, _ = APIExecutor.execute_test_case(
                    base_url, endpoint, method, tc, resource_key
                )
                results.append(result)

        return results

    @staticmethod
    def _path_param_names(endpoint):

        return _PATH_PARAM.findall(endpoint)

    @staticmethod
    def _path_param_overrides(endpoint, resource_id):

        return {name: resource_id for name in LifecycleExecutor._path_param_names(endpoint)}

    @staticmethod
    def _extract_resource_id(response_json, lifecycle_map):

        if not isinstance(response_json, dict):
            return None

        candidate_names = []

        for role in ("read", "update", "delete"):

            entry_tc = lifecycle_map.get(role)

            if entry_tc:
                candidate_names.extend(LifecycleExecutor._path_param_names(entry_tc[0]["endpoint"]))

        lower_map = {k.lower(): v for k, v in response_json.items()}

        for name in candidate_names:

            if name.lower() in lower_map:
                return lower_map[name.lower()]

        return lower_map.get("id")

    @staticmethod
    def _synthesize_get_url(base_url, endpoint_template, resource_id):

        url = base_url + endpoint_template

        for name in LifecycleExecutor._path_param_names(endpoint_template):
            url = url.replace("{" + name + "}", str(resource_id))

        return url

    @staticmethod
    def _skipped_result(verify_tc, reason):

        return {
            "tc_id": verify_tc["tc_id"],
            "test_scenario": verify_tc["test_scenario"],
            "lifecycle_role": verify_tc.get("lifecycle_role"),
            "status": "SKIPPED",
            "skip_reason": reason,
            "expected_status_code": verify_tc.get("expected_response", {}).get("status_code"),
            "actual_status_code": None,
            "execution_time_ms": 0,
            "request": {
                "method": "GET", "url": None, "query_params": {}, "headers": {},
                "request_data": {}, "path_params": {},
            },
            "response_body": "",
            "validation_details": [],
        }

    @staticmethod
    def _run_verification_get(base_url, read_entry, verify_tc, resource_id, headers, compare_against):

        url = LifecycleExecutor._synthesize_get_url(base_url, read_entry["endpoint"], resource_id)

        response, response_json, execution_time_ms = APIExecutor.send_request(
            method="GET", url=url, headers=headers, query_params={}, json_body=None,
        )

        validations = []
        common_validator = CommonValidator()

        status_ok = response.status_code == 200
        validations.append(
            {"check": "status_code", "expected": 200, "actual": response.status_code, "passed": status_ok}
        )
        overall = status_ok

        if status_ok and isinstance(response_json, dict):

            expected = verify_tc.get("expected_response", {})

            overall &= common_validator.validate_required_fields(
                response_json, expected.get("required_fields", []), validations
            )
            overall &= common_validator.validate_field_types(
                response_json, expected.get("field_types", {}), validations
            )

            if compare_against:
                overall &= DataConsistencyValidator.compare_fields(compare_against, response_json, validations)

        return {
            "tc_id": verify_tc["tc_id"],
            "test_scenario": verify_tc["test_scenario"],
            "lifecycle_role": verify_tc.get("lifecycle_role"),
            "status": "PASS" if overall else "FAIL",
            "expected_status_code": 200,
            "actual_status_code": response.status_code,
            "execution_time_ms": execution_time_ms,
            "request": {
                "method": "GET",
                "url": url,
                "query_params": {},
                "headers": headers or {},
                "request_data": {},
                "path_params": {},
            },
            "response_body": response.text,
            "validation_details": validations,
        }

    @staticmethod
    def _run_deleted_check(base_url, read_entry, verify_tc, resource_id, headers):

        url = LifecycleExecutor._synthesize_get_url(base_url, read_entry["endpoint"], resource_id)

        response, _, execution_time_ms = APIExecutor.send_request(
            method="GET", url=url, headers=headers, query_params={}, json_body=None,
        )

        validations = []
        passed = DataConsistencyValidator.verify_not_found(response.status_code, validations)

        return {
            "tc_id": verify_tc["tc_id"],
            "test_scenario": verify_tc["test_scenario"],
            "lifecycle_role": verify_tc.get("lifecycle_role"),
            "status": "PASS" if passed else "FAIL",
            "expected_status_code": 404,
            "actual_status_code": response.status_code,
            "execution_time_ms": execution_time_ms,
            "request": {
                "method": "GET",
                "url": url,
                "query_params": {},
                "headers": headers or {},
                "request_data": {},
                "path_params": {},
            },
            "response_body": response.text,
            "validation_details": validations,
        }
