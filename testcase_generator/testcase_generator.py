import os
import json

from testcase_generator.prompt_builder import PromptBuilder
from testcase_generator.response_parser import parse_response
from testcase_generator.testcaseIdGenerator import TCIDGenerator
from llm.core.exceptions import LLMResponseError, LLMTruncationError
from configs.settings import LLM
from Utils.logger import logger
from Utils.resource_group import (
    group_by_resource,
    find_lifecycle_test_cases,
    find_verification_test_cases,
    find_single_resource_entry,
)

CATEGORIES = ("positive", "negative", "boundary", "required_field")


class TestcaseGenerator:

    def __init__(self, llm):
        self.llm = llm

    def generate_test_cases(
        self,
        parsed_input_file,
        existing_testcases_file=None,
        endpoints_to_regenerate=None,
        progress_callback=None,
        stop_check=None,
    ):
        with open(parsed_input_file, "r") as f:
            api_input = json.load(f)

        project = api_input["project"]
        apis = api_input["apis"]
        total = len(apis)

        final_results = []

        # Build a set of (endpoint, method) pairs that must be force-regenerated.
        # When endpoints_to_regenerate is None the caller passes existing_testcases_file=None
        # (regenerate all), so this set is irrelevant in that case.
        force_regen_keys = set()
        if endpoints_to_regenerate is not None:
            for item in endpoints_to_regenerate:
                force_regen_keys.add((item["endpoint"], item["method"].upper()))

        # Load existing test cases
        existing_tc_map = {}
        if existing_testcases_file:
            with open(existing_testcases_file, "r") as f:
                existing_data = json.load(f)
                for result in existing_data.get("results", []):
                    key = (result.get("endpoint"), result.get("method", "").upper())
                    for tc in result.get("test_cases", []):
                        tc.setdefault("lifecycle_role", "independent")
                        # Legacy file written before source/needs_review existed,
                        # or a previously-approved test case being reused as-is -
                        # either way it doesn't need a fresh review pass.
                        tc.setdefault("source", "system")
                        tc.setdefault("needs_review", False)
                    existing_tc_map[key] = result

        for api_index, api in enumerate(apis, start=1):

            if stop_check is not None and stop_check():
                logger.info(
                    f"Generation stopped by request after {api_index - 1}/{total} endpoints."
                )
                break

            endpoint = api.get("api_details", {}).get("endpoint", "")
            method = api.get("api_details", {}).get("method", "").upper()
            requires_auth = api.get("api_details", {}).get("requires_auth", False)
            auth_schemes = api.get("auth_schemes", [])
            key = (endpoint, method)

            try:
                # --------------------------------------------------
                # Reuse existing test cases if available and not forced to regenerate
                # --------------------------------------------------
                force = key in force_regen_keys
                if existing_testcases_file and not force:
                    if key in existing_tc_map:
                        logger.info(f"Using existing test cases for {method} {endpoint}")
                        existing_entry = existing_tc_map[key]
                        existing_entry["requires_auth"] = requires_auth
                        existing_entry["auth_schemes"] = auth_schemes
                        final_results.append(existing_entry)
                        if progress_callback:
                            progress_callback(api_index, total, endpoint, method)
                        continue

                    logger.info(
                        f"No existing test cases found for {method} {endpoint}. "
                        f"Generating new test cases."
                    )

                # --------------------------------------------------
                # Generate new test cases (retry on truncation/malformed JSON)
                # --------------------------------------------------
                prompt = PromptBuilder.build_prompt(api)

                parsed_response = self._generate_with_retry(prompt, api, endpoint, method)

                parsed_response = TCIDGenerator.add_ids(parsed_response, api_index)

                self._replace_test_data_files(parsed_response)

                for tc in parsed_response.get("test_cases", []):
                    tc["source"] = "system"
                    tc["needs_review"] = True

                parsed_response["requires_auth"] = requires_auth
                parsed_response["auth_schemes"] = auth_schemes

                final_results.append(parsed_response)

            except Exception as e:

                final_results.append(
                    {
                        "endpoint": endpoint,
                        "method": method,
                        "test_cases": [],
                        "error": str(e),
                        "requires_auth": requires_auth,
                        "auth_schemes": auth_schemes,
                    }
                )

            if progress_callback:
                progress_callback(api_index, total, endpoint, method)

        self._diversify_update_payloads(final_results)

        self._backfill_missing_lifecycle_roles(final_results)

        self._add_lifecycle_verification_test_cases(final_results)

        return {"project": project, "results": final_results}

    def _generate_with_retry(self, prompt, api, endpoint, method, allow_category_fallback=True):
        """
        Calls the LLM and parses its response, retrying on truncation
        (output/context token limit hit) or malformed JSON output before
        giving up. Connection errors are not retried here - they bubble up
        immediately to the caller.

        If every retry of the single-call prompt is exhausted and the last
        failure was specifically a token-limit truncation (not malformed
        JSON), falls back to generating each test case category in its own
        smaller call (see _generate_by_category) instead of dropping the
        endpoint's test cases entirely.
        """

        max_retries = LLM.get("max_retries", 2)

        last_error = None

        for attempt in range(1, max_retries + 2):

            try:
                response = self.llm.generate(prompt, api)

                return parse_response(response)

            except LLMResponseError as e:

                last_error = e

                logger.warning(
                    f"Attempt {attempt} for {method} {endpoint} failed: {e}. "
                    f"{'Retrying...' if attempt <= max_retries else 'Giving up.'}"
                )

        if allow_category_fallback and isinstance(last_error, LLMTruncationError):

            logger.warning(
                f"Single-call generation for {method} {endpoint} kept hitting the "
                f"output/context token limit; falling back to per-category generation."
            )

            return self._generate_by_category(api, endpoint, method)

        raise last_error

    def _generate_by_category(self, api, endpoint, method):
        """
        Generates each test case category (positive/negative/boundary/
        required_field) in its own smaller LLM call and merges the results.
        Used as a fallback when the combined single-call prompt's output
        keeps exceeding the token limit for an endpoint with a large schema.
        A failure in one category doesn't drop the others.
        """

        merged_test_cases = []
        any_success = False

        for category in CATEGORIES:

            prompt = PromptBuilder.build_prompt(api, category=category)

            try:
                partial = self._generate_with_retry(
                    prompt, api, endpoint, method, allow_category_fallback=False
                )
                merged_test_cases.extend(partial.get("test_cases", []))
                any_success = True

            except LLMResponseError as e:
                logger.error(
                    f"Category '{category}' generation failed for {method} {endpoint}: {e}"
                )

        if not any_success:
            raise LLMResponseError(
                f"All category fallback generations failed for {method} {endpoint}"
            )

        return {"endpoint": endpoint, "method": method, "test_cases": merged_test_cases}

    def _diversify_update_payloads(self, final_results):
        """
        The "create" and "update" lifecycle-tagged test cases for the same
        resource are generated by two separate, isolated LLM calls that
        don't see each other's output (testcase_generator.py calls the LLM
        once per endpoint, with a prompt containing only that endpoint's
        api_details). They can coincidentally land on identical sample
        data, which makes the read-after-update verification meaningless -
        it would pass even if the update were a silent no-op. Force at
        least one field to differ wherever the model produced identical
        payloads. This can only be done here, after every endpoint has
        been generated, since it's the first point where both payloads are
        available together.
        """

        for resource_key, group_entries in group_by_resource(final_results).items():

            lifecycle_map = find_lifecycle_test_cases(group_entries)

            create = lifecycle_map.get("create")
            update = lifecycle_map.get("update")

            if not create or not update:
                continue

            create_data = create[1].get("request_data", {})
            update_data = update[1].get("request_data", {})

            if not isinstance(create_data, dict) or not isinstance(update_data, dict):
                continue

            overlapping_fields = [
                field
                for field in update_data
                if field in create_data and update_data[field] == create_data[field]
            ]

            if not overlapping_fields or len(overlapping_fields) < len(update_data):
                continue  # at least one field already differs - update is meaningful as-is

            for field in overlapping_fields:

                new_value = self._distinct_value(update_data[field])

                if new_value != update_data[field]:
                    update_data[field] = new_value
                    logger.info(
                        f"Diversified update payload for resource '{resource_key}': "
                        f"field '{field}' changed so read-after-update verification is meaningful."
                    )
                    break
            else:
                logger.warning(
                    f"Could not diversify update payload for resource '{resource_key}' - "
                    f"no eligible scalar field found; read-after-update verification may be "
                    f"inconclusive."
                )

    _BACKFILL_ROLE_METHODS = (
        ("read", ("GET",)),
        ("update", ("PUT", "PATCH")),
        ("delete", ("DELETE",)),
    )

    def _backfill_missing_lifecycle_roles(self, final_results):
        """
        The LLM is instructed (prompts/test_case_generation.md) to tag the
        single positive GET/PUT/PATCH/DELETE-by-id test case for a resource
        as "read"/"update"/"delete", but it doesn't always comply - it can
        leave that test case tagged "independent". Since
        _add_lifecycle_verification_test_cases() requires both "create" and
        "read" to be present before it'll generate any verification test
        cases, a single missed "read" tag silently drops verify_create/
        verify_update/verify_delete entirely, even when "update"/"delete"
        were tagged correctly.

        For resource groups that have a "create" role, this deterministically
        assigns any missing "read"/"update"/"delete" role to that endpoint's
        first independent, 2xx test case - the endpoint and status code
        unambiguously identify the correct test case, so no LLM judgment is
        needed. Idempotent: once a role is assigned, find_lifecycle_test_cases
        finds it on the next run and this is a no-op for that group.
        """

        for key, group_entries in group_by_resource(final_results).items():

            lifecycle_map = find_lifecycle_test_cases(group_entries)

            if "create" not in lifecycle_map:
                continue

            for role, methods in self._BACKFILL_ROLE_METHODS:

                if role in lifecycle_map:
                    continue

                for method in methods:

                    entry = find_single_resource_entry(group_entries, key, method)

                    if not entry:
                        continue

                    for tc in entry.get("test_cases", []):

                        if tc.get("lifecycle_role") != "independent":
                            continue

                        status_code = tc.get("expected_response", {}).get("status_code")

                        if isinstance(status_code, int) and 200 <= status_code < 300:
                            tc["lifecycle_role"] = role
                            logger.info(
                                f"Auto-corrected lifecycle_role for {tc.get('tc_id')} "
                                f"({entry.get('method')} {entry.get('endpoint')}) to "
                                f"'{role}' - LLM left it as 'independent'."
                            )
                            break
                    else:
                        continue

                    break

    def _add_lifecycle_verification_test_cases(self, final_results):
        """
        For every resource group that has both "create" and "read"
        lifecycle-tagged test cases, persists the CRUD-consistency checks
        the execution engine performs (re-fetch after create/update,
        confirm 404 after delete) as real test cases on that read
        endpoint's test_cases list, tagged
        "verify_create"/"verify_update"/"verify_delete". Without this,
        execution/lifecycle_executor.py used to fabricate these checks in
        memory at run time, so they showed up in execution results but had
        no matching entry in the generated test case catalog - this makes
        the catalog and the execution count agree. "create" is required
        for all three roles because every verification needs the id of the
        resource that "create" produced - without it there's nothing to
        re-fetch. Idempotent: re-running generation with reused (not
        force-regenerated) endpoints won't duplicate verification entries
        that are already present.
        """

        for group_entries in group_by_resource(final_results).values():

            lifecycle_map = find_lifecycle_test_cases(group_entries)

            read = lifecycle_map.get("read")

            if not read or "create" not in lifecycle_map:
                continue

            read_entry, read_tc = read

            existing_roles = find_verification_test_cases(group_entries)

            if "verify_create" not in existing_roles:
                read_entry["test_cases"].append(
                    self._build_verification_test_case(
                        read_tc, "verify_create", "VERIFY_READ_AFTER_CREATE",
                        "Verify created resource is retrievable and matches submitted data",
                    )
                )

            if "update" in lifecycle_map and "verify_update" not in existing_roles:
                read_entry["test_cases"].append(
                    self._build_verification_test_case(
                        read_tc, "verify_update", "VERIFY_READ_AFTER_UPDATE",
                        "Verify updated resource reflects the new data",
                    )
                )

            if "delete" in lifecycle_map and "verify_delete" not in existing_roles:
                read_entry["test_cases"].append(
                    self._build_verification_test_case(
                        read_tc, "verify_delete", "VERIFY_READ_AFTER_DELETE",
                        "Verify resource no longer exists after DELETE",
                        expected_response={"status_code": 404, "required_fields": [], "field_types": {}},
                    )
                )

    @staticmethod
    def _build_verification_test_case(read_tc, lifecycle_role, tc_id_suffix, scenario, expected_response=None):

        return {
            "tc_id": f"{read_tc['tc_id']}_{tc_id_suffix}",
            "test_scenario": scenario,
            "lifecycle_role": lifecycle_role,
            "source": "system",
            "needs_review": True,
            "path_params": dict(read_tc.get("path_params", {})),
            "query_params": dict(read_tc.get("query_params", {})),
            "headers": dict(read_tc.get("headers", {})),
            "request_data": {},
            "files": {},
            "expected_response": (
                expected_response
                if expected_response is not None
                else json.loads(json.dumps(read_tc.get("expected_response", {})))
            ),
        }

    @staticmethod
    def _distinct_value(value):

        if isinstance(value, bool):
            return not value

        if isinstance(value, str):
            return value if value.endswith(" (Updated)") else f"{value} (Updated)"

        if isinstance(value, int):
            return value + 1

        if isinstance(value, float):
            return value + 1.0

        return value

    @staticmethod
    def _replace_test_data_files(parsed_response):
        """
        Replace fake/generated filenames from LLM
        with actual files from test_data folder.
        """

        VALID_FILE = os.path.abspath(os.path.join("test_data", "image.jpg"))

        INVALID_FILE = os.path.abspath(os.path.join("test_data", "invalidimage.txt"))

        test_cases = parsed_response.get("test_cases", [])

        for tc in test_cases:

            scenario = tc.get("test_scenario", "").lower()

            is_negative = any(
                word in scenario
                for word in [
                    "invalid",
                    "unsupported",
                    "wrong format",
                    "negative",
                    "gif",
                    "bmp",
                    "exe",
                    "text file",
                ]
            )

            replacement_file = INVALID_FILE if is_negative else VALID_FILE

            TestcaseGenerator._replace_file_recursively(tc, replacement_file)

    @staticmethod
    def _replace_file_recursively(data, replacement_file):
        """
        Recursively search testcase JSON
        and replace any fake filenames.
        """

        FILE_EXTENSIONS = [
            ".jpg",
            ".jpeg",
            ".png",
            ".gif",
            ".bmp",
            ".txt",
            ".pdf",
            ".exe",
        ]

        if isinstance(data, dict):

            for key, value in data.items():

                if isinstance(value, str):

                    lower_value = value.lower()

                    if any(ext in lower_value for ext in FILE_EXTENSIONS):

                        data[key] = replacement_file

                elif isinstance(value, (dict, list)):

                    TestcaseGenerator._replace_file_recursively(value, replacement_file)

        elif isinstance(data, list):

            for item in data:

                TestcaseGenerator._replace_file_recursively(item, replacement_file)
