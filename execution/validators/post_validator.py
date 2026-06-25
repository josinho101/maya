from execution.validators.common_validator import CommonValidator


class PostValidator(CommonValidator):

    def validate(self, request_data, response_json, status_code, expected):

        validations = []
        overall = True

        overall &= self.validate_status_code(
            expected["status_code"], status_code, validations
        )

        if status_code in [200, 201]:

            overall &= self.validate_required_fields(
                response_json, expected["required_fields"], validations
            )

            overall &= self.validate_field_types(
                response_json, expected["field_types"], validations
            )

            # Handle both dict and list request payloads
            if isinstance(request_data, dict):

                for field, value in request_data.items():

                    if field in response_json:

                        passed = response_json[field] == value

                        validations.append(
                            {
                                "check": f"value_match:{field}",
                                "expected": value,
                                "actual": response_json[field],
                                "passed": passed,
                            }
                        )

                        overall &= passed

            elif isinstance(request_data, list):

                # If response is also a list, compare item-by-item
                if isinstance(response_json, list):

                    for req_item, resp_item in zip(request_data, response_json):

                        if not isinstance(req_item, dict) or not isinstance(
                            resp_item, dict
                        ):
                            continue

                        for field, value in req_item.items():

                            if field in resp_item:

                                passed = resp_item[field] == value

                                validations.append(
                                    {
                                        "check": f"value_match:{field}",
                                        "expected": value,
                                        "actual": resp_item[field],
                                        "passed": passed,
                                    }
                                )

                                overall &= passed

                # If request is a single-item list but response is a dict
                elif len(request_data) > 0 and isinstance(request_data[0], dict):

                    for field, value in request_data[0].items():

                        if field in response_json:

                            passed = response_json[field] == value

                            validations.append(
                                {
                                    "check": f"value_match:{field}",
                                    "expected": value,
                                    "actual": response_json[field],
                                    "passed": passed,
                                }
                            )

                            overall &= passed

        return {"passed": bool(overall), "validation_details": validations}


# from execution.validators.common_validator import CommonValidator


# class PostValidator(CommonValidator):

#     def validate(self,request_data,response_json,status_code,expected):

#         validations = []
#         overall = True

#         overall &= self.validate_status_code(expected["status_code"],status_code, validations)

#         if status_code in [200, 201]:

#             overall &= self.validate_required_fields(
#                 response_json,
#                 expected["required_fields"],
#                 validations
#             )

#             overall &= self.validate_field_types(
#                 response_json,
#                 expected["field_types"],
#                 validations
#             )

#             for field, value in request_data.items():

#                 if field in response_json:

#                     passed = response_json[field] == value

#                     validations.append({
#                         "check": f"value_match:{field}",
#                         "expected": value,
#                         "actual": response_json[field],
#                         "passed": passed
#                     })

#                     overall &= passed


#         return {
#             "passed": bool(overall),
#             "validation_details": validations
#         }
