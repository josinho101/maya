from execution.validators.common_validator import CommonValidator


class PatchValidator(CommonValidator):

    def validate(self, request_data, response_json, status_code, expected):

        validations = []

        overall = True

        # expected = test_case["expected_response"]

        overall &= self.validate_status_code(
            expected["status_code"], status_code, validations
        )

        # request_data = test_case["request_data"]
        request_data = request_data or {}
        response_json = response_json or {}

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

        return {"passed": bool(overall), "validation_details": validations}
