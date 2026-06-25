import argparse
import json

from Parser.rest_document_parser import RestDocumentParser

from llm.core.llm_client import LLMClient

from Utils.logger import logger

from testcase_generator.testcase_generator import TestcaseGenerator

from storage.testcase_storage import TestCaseStorage

from execution.execution_runner import ExecutionRunner


def main():

    arg_parser = argparse.ArgumentParser()

    arg_parser.add_argument(
        "--input", required=True, help="Swagger/OpenAPI file path or URL"
    )
    args = arg_parser.parse_args()

    parser = RestDocumentParser()

    project_path, parsed_json = parser.parse(args.input)

    llm = LLMClient.get_llm_client()

    generator = TestcaseGenerator(llm)

    existing_testcases = TestCaseStorage.get_existing_testcases(project_path)

    result = generator.generate_test_cases(parsed_json, existing_testcases)

    saved_file = TestCaseStorage.save(project_path, result)

    logger.info("Test cases saved to: %s", saved_file)

    execution_report_path = ExecutionRunner.execute(project_path, saved_file)

    logger.info("Execution Results:\n%s", json.dumps(execution_report_path, indent=2))
    


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as e:
        #print(f"ERROR: {e}")
        logger.info(f"ERROR: {e}") 
