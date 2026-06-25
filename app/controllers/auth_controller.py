import datetime

import jwt

from app.controllers import BadRequest
from configs import settings
from Utils.logger import logger


def login(username: str, password: str) -> dict:
    user = next((u for u in settings.USERS if u["username"] == username), None)
    if not user or user["password"] != password:
        logger.warning("Failed login attempt for username=%s", username)
        raise BadRequest("Invalid username or password")

    payload = {
        "username": user["username"],
        "role": user["role"],
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=settings.JWT["expiry_hours"]),
    }
    token = jwt.encode(payload, settings.JWT["secret_key"], algorithm=settings.JWT["algorithm"])
    logger.info("Successful login username=%s role=%s", user["username"], user["role"])
    return {"token": token, "username": user["username"], "role": user["role"]}
