"""OpenAI-compatible LLM client with honest failure handling and fallback support."""
import json
import logging
from typing import Dict, Any, Optional, List
from src.config import settings

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related issues."""
    pass


class LLMUnavailableError(LLMError):
    """Raised when LLM API credentials or endpoints are unavailable."""
    pass


class LLMClient:
    """Client for OpenAI-compatible LLM APIs (OpenAI, Ollama, LM Studio, Groq, etc.)."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.base_url = base_url or settings.openai_base_url
        self.api_key = api_key if api_key is not None else settings.openai_api_key
        self.model = model or settings.openai_model
        self._client = None

    def is_available(self) -> bool:
        """Truthfully report whether an API key has been configured."""
        if not self.api_key:
            return False
        cleaned = self.api_key.strip()
        return bool(cleaned and cleaned != "your-api-key-here" and len(cleaned) > 5)

    def _get_client(self):
        if not self.is_available():
            raise LLMUnavailableError(
                "No valid OpenAI-compatible API key provided in OPENAI_API_KEY environment variable. "
                "Configure a valid key in .env or settings to enable live LLM planning."
            )
        if self._client is None:
            try:
                from openai import OpenAI
                self._client = OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=30.0
                )
            except Exception as e:
                raise LLMUnavailableError(f"Failed to initialize OpenAI client: {e}")
        return self._client

    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.0,
        response_format: Optional[Dict[str, str]] = None
    ) -> str:
        """Execute a chat completion against the OpenAI-compatible endpoint."""
        client = self._get_client()
        try:
            kwargs: Dict[str, Any] = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
            }
            if response_format:
                kwargs["response_format"] = response_format

            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise LLMError(f"LLM API call failed: {str(e)}")
