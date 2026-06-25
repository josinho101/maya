class LLMConnectionError(Exception):
    """Raised when LLM provider connection fails."""


class LLMResponseError(Exception):
    """Raised when invalid response is received."""


class LLMTruncationError(LLMResponseError):
    """Raised when the LLM output was cut off by the output/context token limit."""
