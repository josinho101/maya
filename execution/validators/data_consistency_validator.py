class DataConsistencyValidator:
    """
    Cross-call validation: compares data returned by an independent follow-up
    call (typically a GET) against the payload that was originally sent to
    create/update the resource, instead of just validating a response
    against its own request.
    """

    @staticmethod
    def compare_fields(source_payload, target_response, validations):

        if not isinstance(source_payload, dict) or not isinstance(target_response, dict):
            return True

        result = True

        for field, value in source_payload.items():

            actual = target_response.get(field)
            passed = actual == value

            validations.append(
                {
                    "check": f"data_consistency:{field}",
                    "expected": value,
                    "actual": actual,
                    "passed": passed,
                }
            )

            if not passed:
                result = False

        return result

    @staticmethod
    def verify_not_found(actual_status_code, validations, expected_not_found_codes=(404,)):

        passed = actual_status_code in expected_not_found_codes

        validations.append(
            {
                "check": "resource_deleted",
                "expected": list(expected_not_found_codes),
                "actual": actual_status_code,
                "passed": passed,
            }
        )

        return passed
