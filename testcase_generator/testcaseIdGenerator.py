import re


class TCIDGenerator:

    @staticmethod
    def next_id(existing_test_cases, api_index, prefix="TC"):
        """
        Returns the next unused tc_id for a given endpoint's test_cases list,
        following the same TC_{api_index:02d}_{n:03d} convention add_ids()
        uses during bulk generation. Used when appending a single test case
        (manual add / scenario job) to an endpoint that already has ids
        assigned, so the new id never collides with an existing one.
        """

        pattern = re.compile(rf"^{prefix}_{api_index:02d}_(\d+)$")

        max_n = 0

        for tc in existing_test_cases:

            match = pattern.match(tc.get("tc_id", ""))

            if match:
                max_n = max(max_n, int(match.group(1)))

        return f"{prefix}_{api_index:02d}_{max_n + 1:03d}"

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
