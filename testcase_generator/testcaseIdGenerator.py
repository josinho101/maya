class TCIDGenerator:

    @staticmethod
    def add_ids(api_response, api_index=1, prefix="TC"):

        updated_test_cases = []

        test_cases = api_response.get("test_cases", [])

        for index, tc in enumerate(test_cases, start=1):

            tc_id = f"{prefix}_{api_index:02d}_{index:03d}"

            updated_tc = {"tc_id": tc_id, **tc}

            updated_test_cases.append(updated_tc)

        api_response["test_cases"] = updated_test_cases

        return api_response
