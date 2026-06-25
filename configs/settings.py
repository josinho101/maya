import os

LLM = {
    "connector": "ollama",
    "host": "http://localhost:11434",
    "model": "qwen3.5:9b",
    "timeout": 2000,        # HTTP request timeout (seconds) for a single Ollama call.
    "temperature": 0.1,     # Lower = more deterministic output. Raise (e.g. 0.3-0.7) only if
                             # you want more varied sample data across regenerations.
    "seed": None,           # None = a new random seed every call (varied sample data per run).
                             # Set a fixed int for reproducible output when debugging one endpoint.
    "num_predict": 12000,   # Max output tokens per LLM call. Raise this if generation logs show
                             # "truncated by output/context limit" for endpoints with large
                             # request/response schemas - each test-case category
                             # (positive/negative/boundary/required-field) adds to this total in
                             # the default single-call generation mode.
    "num_ctx": 24576,       # Max input+output context window (tokens). Must stay >= num_predict
                             # plus the size of the rendered prompt (rules + API_DETAILS). Raise
                             # together with num_predict if prompts for large schemas overflow.
    "max_retries": 2,       # Retries on truncation/malformed JSON before giving up (single-call
                             # mode) or, if the failure was specifically a token-limit truncation,
                             # before falling back to per-category generation - see
                             # TestcaseGenerator._generate_by_category in testcase_generator.py.
}


FRAMEWORK_DATA_DIR = "framework_data"

PATHS = {
    "data": os.path.join(FRAMEWORK_DATA_DIR, "data"),
    "output": os.path.join(FRAMEWORK_DATA_DIR, "output"),
    "execution_results": os.path.join(FRAMEWORK_DATA_DIR, "execution_results"),
    "logs": os.path.join(FRAMEWORK_DATA_DIR, "logs"),
    "parsed_api_filename": "parsed_api.json",
    "testcase_filename": "generated_testcases.json",
}


# User accounts — add new entries here to create users.
# role must be "admin" (full access) or "user" (read-only).
USERS = [
    {"username": "admin", "password": "admin123", "role": "admin"},
    {"username": "viewer", "password": "viewer123", "role": "user"},
]

JWT = {
    "secret_key": "change-me-in-production",
    "algorithm": "HS256",
    "expiry_hours": 24,
}

LOGGING = {
    "level": "INFO",
    "rotation": "both",      # "size" (RotatingFileHandler), "time" (TimedRotatingFileHandler),
                              # or "both" (rotate on whichever condition hits first)
    "max_bytes": 1 * 1024 * 1024,   # rotate once a file exceeds this size; used when rotation
                                     # is "size" or "both". Lowered from 5MB so low-volume logs
                                     # (e.g. llm.log) still rotate instead of growing for days.
    "backup_count": 5,       # number of rotated files to keep before the oldest is deleted
    "when": "midnight",      # time-based rollover unit; used when rotation is "time" or "both".
                              # one of: "S" (seconds), "M" (minutes), "H" (hours), "D" (days),
                              # "W0"-"W6" (weekly, 0=Monday), or "midnight" (roll over daily at midnight)
    "interval": 1,           # number of `when` units between rollovers (e.g. when="H", interval=4
                              # = every 4 hours). Ignored for "midnight" and "W0"-"W6", which always
                              # roll over once per day / once per week respectively.
}
