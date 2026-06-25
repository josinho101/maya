from testcase_generator.prompt_builder import PromptBuilder
from testcase_generator.response_parser import parse_response
from testcase_generator.testcase_generator import TestcaseGenerator
from llm.core.exceptions import LLMResponseError


def generate_from_scenario(llm, api, scenario_text):
    """
    Drafts a single test case for one endpoint from a human-written scenario
    description. Mirrors TestcaseGenerator's single-call generation path
    (prompt -> LLM -> parse_response), scoped to one test case instead of a
    full category sweep. Does not assign a tc_id or source/needs_review -
    those are set once, by the caller's save path, so a discarded/cancelled
    draft never consumes an id.
    """

    prompt = PromptBuilder.build_scenario_prompt(api, scenario_text)

    response = llm.generate(prompt, api)

    parsed = parse_response(response)

    test_cases = parsed.get("test_cases", [])
    if not test_cases:
        raise LLMResponseError("LLM returned no test case for the given scenario")

    draft = test_cases[0]

    TestcaseGenerator._replace_test_data_files({"test_cases": [draft]})

    return draft
