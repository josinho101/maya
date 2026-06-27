import json
from pathlib import Path


class PromptBuilder:

    PROMPT_DIR = Path(__file__).resolve().parent.parent / "prompts"

    @classmethod
    def load_prompt(cls, prompt_name):

        prompt_file = cls.PROMPT_DIR / prompt_name

        if not prompt_file.exists():

            raise FileNotFoundError(f"Prompt file not found: {prompt_file}")

        return prompt_file.read_text(encoding="utf-8")

    @staticmethod
    def render(template, variables):

        for key, value in variables.items():

            if not isinstance(value, str):
                value = str(value)

            template = template.replace(f"{{{{{key}}}}}", value)

        return template

    @classmethod
    def build_prompt(cls, api, category=None):
        """
        category=None builds the default single-call prompt (all test case
        categories + lifecycle tagging in one response). A given category
        ("positive" | "negative" | "boundary" | "required_field") builds a
        smaller, category-scoped prompt instead - used as a fallback when
        the single-call prompt keeps getting truncated for an endpoint with
        a large schema (see TestcaseGenerator._generate_by_category).
        """

        if category is None:
            template = cls.load_prompt("test_case_generation.md")
        else:
            category_template = cls.load_prompt(f"categories/{category}.md")
            shared_rules = cls.load_prompt("_shared_rules.md")
            template = (
                f"{category_template}\n\n{shared_rules}\n\nAPI DETAILS:\n\n{{{{API_DETAILS}}}}"
            )

        variables = {"API_DETAILS": json.dumps(api["api_details"], indent=2)}

        return cls.render(template, variables)

    @classmethod
    def build_scenario_prompt(cls, api, scenario_text):
        """
        Single-test-case prompt for the "generate from scenario" feature -
        same _shared_rules.md contract as a category-scoped bulk-generation
        call, but grounded in a human-written scenario description instead of
        an LLM-chosen category.
        """

        scenario_template = cls.load_prompt("from_scenario.md")
        shared_rules = cls.load_prompt("_shared_rules.md")
        template = (
            f"{scenario_template}\n\n{shared_rules}\n\nAPI DETAILS:\n\n{{{{API_DETAILS}}}}"
        )

        variables = {
            "API_DETAILS": json.dumps(api["api_details"], indent=2),
            "USER_SCENARIO": scenario_text,
        }

        return cls.render(template, variables)

    @classmethod
    def build_steps_prompt(cls, test_case, endpoint, method):
        """
        Prompt for the "generate Gherkin-style test steps" phase - takes an
        already fully-detailed test case (scenario, params, request/response)
        and asks the model only to narrate it as Given/When/Then/And lines,
        not to design or modify any of the test case's actual content.
        """

        template = cls.load_prompt("generate_test_steps.md")

        test_case_payload = {
            "endpoint": endpoint,
            "method": method,
            **{
                k: test_case.get(k, {})
                for k in (
                    "test_scenario", "path_params", "query_params",
                    "headers", "request_data", "files", "expected_response",
                )
            },
        }

        variables = {"TEST_CASE": json.dumps(test_case_payload, indent=2)}

        return cls.render(template, variables)
