import json
import copy

from Parser.swagger.schema_parser import SchemaParser
from Parser.swagger.parameter_parser import ParameterParser
from Parser.swagger.response_parser import ResponseParser
from Parser.Utils.hash_services import HashService
from Utils.logger import logger


class SwaggerParser:

    def __init__(self, source_data, existing_api_map=None):

        self.source_data = source_data

        self.existing_api_map = existing_api_map or {}

        self.schema_parser = SchemaParser(source_data)

        self.parameter_parser = ParameterParser(source_data)

        self.response_parser = ResponseParser(source_data)

        with open("Parser/template.json", "r") as file:
            self.template = json.load(file)

    def parse(self):

        project_name = self.source_data.get("info", {}).get("title", "Unknown Project")

        base_url = ""

        if "host" in self.source_data:

            scheme = self.source_data.get("schemes", ["https"])[0]

            host = self.source_data.get("host", "")

            base_path = self.source_data.get("basePath", "")

            base_url = f"{scheme}://{host}{base_path}"

        elif "servers" in self.source_data:

            servers = self.source_data.get("servers", [])

            if servers:

                base_url = servers[0].get("url", "")

        apis = []

        paths = self.source_data.get("paths", {})

        HTTP_METHODS = {
            "get",
            "post",
            "put",
            "patch",
            "delete",
            "head",
            "options",
            "trace",
        }

        for endpoint, methods in paths.items():

            path_level_parameters = methods.get("parameters", [])

            for http_method, details in methods.items():

                #
                # Skip non-operation keys such as:
                # parameters, summary, description, servers
                #
                if http_method.lower() not in HTTP_METHODS:
                    continue

                api_sha = HashService.generate_api_sha(
                    endpoint=endpoint, method=http_method.upper(), details=details
                )

                if api_sha in self.existing_api_map:

                    logger.info(
                        f"Parsing skipping for existing API: "
                        f"{http_method.upper()} {endpoint}"
                    )

                    existing_api = copy.deepcopy(self.existing_api_map[api_sha])

                    existing_api["existing"] = True

                    apis.append(existing_api)

                    continue

                operation_parameters = details.get("parameters", [])

                parameters = path_level_parameters + operation_parameters

                parsed_parameters, request_body_schema = (
                    self.parameter_parser.parse_parameters(parameters)
                )

                openapi_request_body = self.parameter_parser.parse_request_body(details)

                if openapi_request_body:

                    request_body_schema = openapi_request_body

                responses = details.get("responses", {})

                response_schema = self.response_parser.parse_response_schema(responses)

                response_descriptions = {}

                for status_code, response in responses.items():

                    response_descriptions[status_code] = response.get("description", "")

                feature_name = (
                    details.get("summary")
                    or details.get("operationId")
                    or f"{http_method.upper()} {endpoint}"
                )

                consumes = details.get("consumes", ["application/json"])

                headers = {"Content-Type": consumes[0]}

                if "requestBody" in details:

                    request_body = details.get("requestBody", {})

                    content = request_body.get("content", {})

                    if content:

                        headers["Content-Type"] = list(content.keys())[0]

                api_object = copy.deepcopy(self.template["apis"][0])

                api_object["api_sha256"] = api_sha

                api_object["feature"] = feature_name

                api_object["requirements"]["description"] = details.get(
                    "description", ""
                )

                api_object["requirements"]["acceptance_criteria"] = (
                    self.parameter_parser.generate_acceptance_criteria(
                        parsed_parameters, request_body_schema
                    )
                )

                api_object["api_details"]["endpoint"] = endpoint

                api_object["api_details"]["method"] = http_method.upper()

                api_object["api_details"]["headers"] = headers

                api_object["api_details"]["parameters"] = parsed_parameters

                api_object["api_details"]["request_schema"] = request_body_schema

                api_object["api_details"]["response_schema"] = response_schema

                api_object["api_details"][
                    "response_descriptions"
                ] = response_descriptions

                api_object["existing"] = False

                apis.append(api_object)
        
        METHOD_ORDER = {
            "GET": 1,
            "POST": 2,
            "PUT": 3,
            "PATCH": 4,
            "DELETE": 5,
        }


        def endpoint_sort_key(endpoint):
            return (
                endpoint.count("/"),      # path depth first
                endpoint.count("{"),      # static routes before parameterized routes
                endpoint.lower(),         # alphabetical order
            )


        apis.sort(
            key=lambda api: (
                *endpoint_sort_key(api["api_details"]["endpoint"]),
                METHOD_ORDER.get(api["api_details"]["method"], 999),
            )
        )
        # #
        # # Sort APIs
        # #
        # METHOD_ORDER = {
        #     "GET": 1,
        #     "POST": 2,
        #     "PUT": 3,
        #     "PATCH": 4,
        #     "DELETE": 5,
        # }

        # apis.sort(
        #     key=lambda api: (
        #         api["api_details"]["endpoint"].replace("{", "zzz"),
        #         METHOD_ORDER.get(api["api_details"]["method"], 999),
        #     )
        # )

        #
        # Create final output
        #
        output = copy.deepcopy(self.template)

        output["project"]["name"] = project_name

        output["project"]["base_url"] = base_url

        output["apis"] = apis

        return output


    # def parse(self):

    #     project_name = self.source_data.get("info", {}).get("title", "Unknown Project")

    #     base_url = ""

    #     if "host" in self.source_data:

    #         scheme = self.source_data.get("schemes", ["https"])[0]

    #         host = self.source_data.get("host", "")

    #         base_path = self.source_data.get("basePath", "")

    #         base_url = f"{scheme}://{host}{base_path}"

    #     elif "servers" in self.source_data:

    #         servers = self.source_data.get("servers", [])

    #         if servers:

    #             base_url = servers[0].get("url", "")

    #     apis = []

    #     paths = self.source_data.get("paths", {})

    #     for endpoint, methods in paths.items():

    #         for http_method, details in methods.items():

    #             api_sha = HashService.generate_api_sha(
    #                 endpoint=endpoint,
    #                 method=http_method.upper(),
    #                 details=details
    #             )

    #             if api_sha in self.existing_api_map:

    #                 logger.info(
    #                     f"Parsing skipping for existing API: "
    #                     f"{http_method.upper()} {endpoint}"
    #                 )

    #                 existing_api = copy.deepcopy(
    #                     self.existing_api_map[api_sha]
    #                 )

    #                 existing_api["existing"] = True

    #                 apis.append(existing_api)

    #                 continue

    #             parameters = details.get("parameters", [])

    #             parsed_parameters, request_body_schema = (
    #                 self.parameter_parser.parse_parameters(
    #                     parameters
    #                 )
    #             )

    #             openapi_request_body = (
    #                 self.parameter_parser.parse_request_body(
    #                     details
    #                 )
    #             )

    #             if openapi_request_body:

    #                 request_body_schema = (
    #                     openapi_request_body
    #                 )

    #             responses = details.get("responses", {})

    #             response_schema = (
    #                 self.response_parser.parse_response_schema(
    #                     responses
    #                 )
    #             )

    #             response_descriptions = {}

    #             for status_code, response in responses.items():

    #                 response_descriptions[
    #                     status_code
    #                 ] = response.get(
    #                     "description",
    #                     ""
    #                 )

    #             feature_name = (
    #                 details.get("summary")
    #                 or details.get("operationId")
    #                 or f"{http_method.upper()} {endpoint}"
    #             )

    #             consumes = details.get(
    #                 "consumes",
    #                 ["application/json"]
    #             )

    #             headers = {
    #                 "Content-Type": consumes[0]
    #             }

    #             if "requestBody" in details:

    #                 request_body = details.get(
    #                     "requestBody",
    #                     {}
    #                 )

    #                 content = request_body.get(
    #                     "content",
    #                     {}
    #                 )

    #                 if content:

    #                     headers["Content-Type"] = (
    #                         list(content.keys())[0]
    #                     )

    #             api_object = copy.deepcopy(
    #                 self.template["apis"][0]
    #             )

    #             api_object["api_sha256"] = api_sha

    #             api_object["feature"] = feature_name

    #             api_object["requirements"][
    #                 "description"
    #             ] = details.get(
    #                 "description",
    #                 ""
    #             )

    #             api_object["requirements"][
    #                 "acceptance_criteria"
    #             ] = (
    #                 self.parameter_parser.generate_acceptance_criteria(
    #                     parsed_parameters,
    #                     request_body_schema
    #                 )
    #             )

    #             api_object["api_details"][
    #                 "endpoint"
    #             ] = endpoint

    #             api_object["api_details"][
    #                 "method"
    #             ] = http_method.upper()

    #             api_object["api_details"][
    #                 "headers"
    #             ] = headers

    #             api_object["api_details"][
    #                 "parameters"
    #             ] = parsed_parameters

    #             api_object["api_details"][
    #                 "request_schema"
    #             ] = request_body_schema

    #             api_object["api_details"][
    #                 "response_schema"
    #             ] = response_schema

    #             api_object["api_details"][
    #                 "response_descriptions"
    #             ] = response_descriptions

    #             api_object["existing"] = False

    #             apis.append(api_object)

    #     #
    #     # Sort APIs
    #     #
    #     METHOD_ORDER = {
    #         "GET": 1,
    #         "POST": 2,
    #         "PUT": 3,
    #         "PATCH": 4,
    #         "DELETE": 5,
    #     }

    #     apis.sort(
    #         key=lambda api: (
    #             api["api_details"]["endpoint"].replace(
    #                 "{",
    #                 "zzz"
    #             ),
    #             METHOD_ORDER.get(
    #                 api["api_details"]["method"],
    #                 999
    #             ),
    #         )
    #     )

    #     #
    #     # Create final output
    #     #
    #     output = copy.deepcopy(self.template)

    #     output["project"]["name"] = project_name

    #     output["project"]["base_url"] = base_url

    #     output["apis"] = apis

    #     return output        

    