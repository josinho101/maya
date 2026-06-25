import json
import os
import uuid

from configs.settings import PATHS

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, PATHS["data"])


def data_path(*parts):
    return os.path.join(DATA_DIR, *parts)


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def load_json(path, default=None):
    if default is None:
        default = {}
    if not os.path.isfile(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path, data):
    ensure_dir(os.path.dirname(path))
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def new_id():
    return uuid.uuid4().hex[:8]
