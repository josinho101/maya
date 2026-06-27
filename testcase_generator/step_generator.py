from testcase_generator.prompt_builder import PromptBuilder
from testcase_generator.response_parser import parse_response
from llm.core.exceptions import LLMResponseError


def generate_steps_for_testcase(llm, test_case, endpoint, method):
    """
    Narrates an already fully-detailed test case as Gherkin-style
    Given/When/Then/And lines, via a dedicated LLM call. Does not change any
    of the test case's existing fields - this only describes them.
    """

    prompt = PromptBuilder.build_steps_prompt(test_case, endpoint, method)

    api = {"api_details": {"endpoint": endpoint, "method": method}}
    response = llm.generate(prompt, api)

    parsed = parse_response(response)

    steps = parsed.get("steps")
    if not isinstance(steps, list) or not all(isinstance(s, str) for s in steps):
        raise LLMResponseError(f"LLM returned no valid 'steps' list for {method} {endpoint}")

    return steps


def generate_steps_for_all(llm, testcases_data, progress_callback=None, stop_check=None):
    """
    Second-phase orchestration: once every test case for a generation already
    exists (testcases_data is the same {"project":..., "results":[...]} shape
    generate_test_cases() returns), walks every test case across every
    endpoint - one at a time, so progress can be tracked per test case - and
    attaches its narrated steps. A failure on one test case doesn't abort the
    rest; it's recorded on that test case via steps_error instead.
    """

    results = testcases_data.get("results", [])
    total = sum(len(r.get("test_cases", [])) for r in results)
    completed = 0

    for result in results:

        endpoint = result.get("endpoint")
        method = result.get("method")

        for tc in result.get("test_cases", []):

            if stop_check is not None and stop_check():
                return testcases_data

            try:
                tc["steps"] = generate_steps_for_testcase(llm, tc, endpoint, method)

            except LLMResponseError as e:
                tc["steps"] = []
                tc["steps_error"] = str(e)

            completed += 1

            if progress_callback:
                progress_callback(completed, total, tc.get("tc_id"))

    return testcases_data
