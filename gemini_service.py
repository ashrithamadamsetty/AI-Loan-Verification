"""Centralized Google Gemini client used by all generative AI features."""

from functools import lru_cache
import json
import logging
from typing import Any

from google import genai
from google.genai import types
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from config import get_settings

logger = logging.getLogger(__name__)


class GeminiConfigurationError(RuntimeError):
    """Raised when Gemini is used without the required local configuration."""


class GeminiService:
    def __init__(self, api_key: str | None = None, model: str | None = None):
        settings = get_settings()
        self.api_key = (api_key or settings.gemini_api_key).strip()
        self.model = model or settings.gemini_model
        self._client: genai.Client | None = None

    @property
    def client(self) -> genai.Client:
        if not self.api_key:
            raise GeminiConfigurationError(
                "GEMINI_API_KEY is not configured. Copy .env.example to .env and add a Gemini API key."
            )
        if self._client is None:
            self._client = genai.Client(api_key=self.api_key)
        return self._client

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        reraise=True,
    )
    def generate_text(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        temperature: float = 0.1,
        max_output_tokens: int = 8192,
    ) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        if not response.text:
            raise RuntimeError("Gemini returned an empty response.")
        return response.text.strip()

    def generate_json(
        self,
        prompt: str,
        *,
        system_instruction: str | None = None,
        response_schema: dict[str, Any] | type | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 8192,
    ) -> Any:
        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=temperature,
            max_output_tokens=max_output_tokens,
            response_mime_type="application/json",
            response_schema=response_schema,
        )
        response = self.client.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config,
        )
        if response.parsed is not None:
            parsed = response.parsed
            return parsed.model_dump() if hasattr(parsed, "model_dump") else parsed
        if not response.text:
            raise RuntimeError("Gemini returned an empty JSON response.")
        return json.loads(self._strip_code_fence(response.text))

    @staticmethod
    def _strip_code_fence(content: str) -> str:
        content = content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines.pop()
            content = "\n".join(lines)
        return content.strip()


@lru_cache(maxsize=1)
def get_gemini_service() -> GeminiService:
    return GeminiService()
