import argparse

from Parser.Utils.file_services import FileService
from Parser.Utils.source_loader import SourceLoader
from Parser.swagger.swagger_parser import SwaggerParser
from configs.settings import PATHS

from Utils.logger import logger


class RestDocumentParser:

    def parse(self, input):

        # Load input document (html/yml)
        source_data = SourceLoader.load(input)

        # find project name
        projectName = source_data.get("info", {}).get("title", "Unknown Project")
        if not projectName:
            raise ValueError("Project name is missing or empty in the parsed output.")
        projectName = projectName.replace(" ", "_").lower()
        projectPath = f"{PATHS['output']}/{projectName}"
        parsedJson = f"{projectPath}/{PATHS['parsed_api_filename']}"

        # load existing parsed json of the project 
        existing_data = FileService.load_existing_output(parsedJson)

        existing_api_map = {
            api["api_sha256"]: api for api in existing_data.get("apis", [])
        }

        #parse the input to json
        parser = SwaggerParser(source_data, existing_api_map)

        final_output = parser.parse()

        FileService.save_output(parsedJson, final_output)

        logger.info(f"Parsed json saved to {parsedJson}")

        return projectPath, parsedJson
