import random
import time
import requests

from llm.core.base_llm import BaseLLM
from configs.settings import LLM

from llm.core.exceptions import LLMConnectionError, LLMResponseError, LLMTruncationError

from Utils.logger import logger, llm_logger


class OllamaLLM(BaseLLM):

    def __init__(
        self,
        host=LLM["host"],
        model=LLM["model"],
        timeout=LLM["timeout"],
        temperature=LLM["temperature"],
        seed=LLM.get("seed"),
        num_predict=LLM["num_predict"],
        num_ctx=LLM["num_ctx"],
    ):

        self.host = host
        self.model = model
        self.timeout = timeout
        self.temperature = temperature
        self.seed = seed
        self.num_predict = num_predict
        self.num_ctx = num_ctx

    def generate(self, prompt: str, api) -> str:

        start = time.perf_counter()

        endpoint = api["api_details"]["endpoint"]
        method = api["api_details"]["method"]

        logger.info("Sending prompt to Ollama model=%s host=%s", self.model, self.host)

        llm_logger.info(
            "LLM REQUEST | model=%s host=%s endpoint='%s' method='%s'\nPROMPT:\n%s",
            self.model, self.host, endpoint, method, prompt,
        )

        url = f"{self.host}/api/generate"

        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "think": False,
            "options": {
                "temperature": self.temperature,
                "seed": self.seed if self.seed is not None else random.randint(0, 2**31 - 1),
                "num_predict": self.num_predict,
                "num_ctx": self.num_ctx,
            },
        }

        try:

            response = requests.post(url, json=payload, timeout=self.timeout)

            response.raise_for_status()

        except requests.exceptions.RequestException as e:

            logger.error("Connection error: %s", e)

            llm_logger.error(
                "LLM REQUEST FAILED | model=%s host=%s endpoint='%s' method='%s' error=%s\nPROMPT:\n%s",
                self.model, self.host, endpoint, method, e, prompt,
            )

            raise LLMConnectionError(f"Ollama connection failed: {e}")

        end = time.perf_counter()
        elapsed = end - start

        logger.info(
            f"Testcase generation for endpoint '{endpoint}' "
            f"method '{method}' completed in {elapsed:.2f} sec"
        )

        try:

            data = response.json()

            generated_response = data.get("response", "")
            done_reason = data.get("done_reason")

            if not generated_response:

                llm_logger.error(
                    "LLM EMPTY RESPONSE | model=%s endpoint='%s' method='%s' duration=%.2fs\nRAW RESPONSE:\n%s",
                    self.model, endpoint, method, elapsed, data,
                )

                raise LLMResponseError(f"Empty response received from Ollama: {data}")

            llm_logger.info(
                "LLM RESPONSE | model=%s endpoint='%s' method='%s' duration=%.2fs done_reason=%s\nRESPONSE:\n%s",
                self.model, endpoint, method, elapsed, done_reason, generated_response,
            )

            if done_reason == "length":

                raise LLMTruncationError(
                    f"Ollama response truncated by output/context limit (done_reason='length') "
                    f"for endpoint '{endpoint}' method '{method}' "
                    f"(num_predict={self.num_predict}, num_ctx={self.num_ctx})"
                )

            return generated_response

        except ValueError:

            llm_logger.error(
                "LLM INVALID JSON RESPONSE | model=%s endpoint='%s' method='%s' duration=%.2fs\nRAW TEXT:\n%s",
                self.model, endpoint, method, elapsed, response.text,
            )

            raise LLMResponseError("Invalid JSON response from Ollama")
