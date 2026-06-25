# class Validator:

#     @staticmethod
#     def validate(response, expected):

#         validation_details = []

#         expected_status = expected.get("status_code")

#         actual_status = response.get("status_code")
#         body = response.get("body")


#         # ----------------------------
#         # 1. STATUS CODE VALIDATION
#         # ----------------------------
#         if expected_status is not None:
#             validation_details.append({
#                 "check": "status_code",
#                 "expected": expected_status,
#                 "actual": actual_status,
#                 "passed": expected_status == actual_status
#             })

#         # ----------------------------
#         # 2. NORMALIZE BODY TYPE
#         # ----------------------------
#         if body is None:
#             return validation_details

#         # ----------------------------
#         # 3. LIST RESPONSE HANDLING
#         # ----------------------------
#         if isinstance(body, list):

#             for field in expected.get("required_fields", []):
#                 exists = all(isinstance(item, dict) and field in item for item in body)

#                 validation_details.append({
#                     "check": f"field_exists:{field}",
#                     "passed": exists
#                 })

#             for field, expected_type in expected.get("field_types", {}).items():

#                 type_ok = True

#                 for item in body:
#                     if not isinstance(item, dict):
#                         type_ok = False
#                         break

#                     value = item.get(field)

#                     if value is None:
#                         type_ok = False
#                         break

#                     if expected_type == "string" and not isinstance(value, str):
#                         type_ok = False
#                         break

#                 validation_details.append({
#                     "check": f"type:{field}",
#                     "expected": expected_type,
#                     "actual": type(body[0].get(field)).__name__ if body and isinstance(body[0], dict) else "NoneType",
#                     "passed": type_ok
#                 })

#         # ----------------------------
#         # 4. DICT RESPONSE HANDLING
#         # ----------------------------
#         elif isinstance(body, dict):

#             for field in expected.get("required_fields", []):

#                 validation_details.append({
#                     "check": f"field_exists:{field}",
#                     "passed": field in body
#                 })

#             for field, expected_type in expected.get("field_types", {}).items():

#                 value = body.get(field)

#                 validation_details.append({
#                     "check": f"type:{field}",
#                     "expected": expected_type,
#                     "actual": type(value).__name__ if value is not None else "NoneType",
#                     "passed": isinstance(value, str if expected_type == "string" else object)
#                 })


#         return validation_details
