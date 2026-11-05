"""
Live LLM Providers (Gemini & OpenAI)
Provides asynchronous cloud-based LLM inference and structured JSON generation.
Guarantees secret redaction and graceful error boundaries.
"""
import json
import re
from typing import Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from ai_agronomist.config import (
    GEMINI_API_KEY,
    OPENAI_API_KEY,
    LLM_MODEL,
    LLM_REQUEST_TIMEOUT_SECONDS,
    redact_sensitive,
)
from ai_agronomist.providers.llm_base import (
    BaseLLMProvider,
    LLMError,
    LLMAuthenticationError,
    LLMInferenceError,
)

T = TypeVar("T", bound=BaseModel)


class GeminiLLMProvider(BaseLLMProvider):
    """
    Google Gemini REST client via async httpx.
    Supports standard generateContent with optional JSON response schema.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self._api_key = (api_key if api_key is not None else (GEMINI_API_KEY or "")).strip()
        self._model = (model or LLM_MODEL or "gemini-flash-lite-latest").strip()
        self._timeout = timeout_seconds or LLM_REQUEST_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def provider_status(self) -> str:
        return "live" if self.is_live_ready() else "unavailable"

    def is_live_ready(self) -> bool:
        return bool(self._api_key and len(self._api_key) > 5)

    def _get_endpoint(self) -> str:
        model_name = self._model
        if not model_name.startswith("models/"):
            model_name = f"models/{model_name}"
        return f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent"

    def _get_headers(self) -> dict:
        return {
            "Content-Type": "application/json",
            "x-goog-api-key": self._api_key,
        }

    def _handle_error_response(self, res: httpx.Response) -> None:
        raw_text = res.text
        try:
            err_json = res.json()
            err_msg = err_json.get("error", {}).get("message", raw_text)
        except Exception:
            err_msg = raw_text

        sanitized = redact_sensitive(err_msg)

        if res.status_code in (400, 401, 403) and ("api key" in sanitized.lower() or "invalid" in sanitized.lower() or "unauthorized" in sanitized.lower() or "permission" in sanitized.lower()):
            raise LLMAuthenticationError(f"Gemini authentication failed (status {res.status_code}): {sanitized}")
        if res.status_code == 429:
            raise LLMInferenceError(f"Gemini quota exhausted / rate limited (status 429): {sanitized}")
        if res.status_code == 404:
            raise LLMInferenceError(f"Gemini model '{self._model}' not found (status 404): {sanitized}")

        raise LLMInferenceError(f"Gemini API error (status {res.status_code}): {sanitized}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        if not self.is_live_ready():
            raise LLMAuthenticationError(
                "Gemini API key is missing or unconfigured in backend/.env (GEMINI_API_KEY)."
            )

        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(
                    self._get_endpoint(),
                    json=payload,
                    headers=self._get_headers(),
                )
                if res.status_code != 200:
                    self._handle_error_response(res)
                data = res.json()
                usage = data.get("usageMetadata", {})
                if usage:
                    self.last_usage = {
                        "prompt_tokens": usage.get("promptTokenCount"),
                        "completion_tokens": usage.get("candidatesTokenCount"),
                        "total_tokens": usage.get("totalTokenCount"),
                        "model": self._model,
                    }
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                return text.strip()
        except LLMError:
            raise
        except httpx.TimeoutException:
            raise LLMInferenceError(f"Gemini request timed out after {self._timeout}s")
        except Exception as exc:
            sanitized = redact_sensitive(str(exc))
            raise LLMInferenceError(f"Gemini request failed: {sanitized}")

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if not self.is_live_ready():
            raise LLMAuthenticationError(
                "Gemini API key is missing or unconfigured in backend/.env (GEMINI_API_KEY)."
            )

        json_instruction = (
            f"\n\nReturn strictly valid JSON adhering to this JSON Schema:\n"
            f"{json.dumps(schema.model_json_schema())}\n"
            "Do NOT include markdown formatting or backticks around the JSON."
        )
        full_prompt = prompt + json_instruction

        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(
                    self._get_endpoint(),
                    json=payload,
                    headers=self._get_headers(),
                )
                if res.status_code != 200:
                    self._handle_error_response(res)
                data = res.json()
                usage = data.get("usageMetadata", {})
                if usage:
                    self.last_usage = {
                        "prompt_tokens": usage.get("promptTokenCount"),
                        "completion_tokens": usage.get("candidatesTokenCount"),
                        "total_tokens": usage.get("totalTokenCount"),
                        "model": self._model,
                    }
                raw_json = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "")
                )
                # Strip markdown fences if Gemini added them despite responseMimeType
                clean_json = re.sub(r"^```(?:json)?\s*", "", raw_json.strip())
                clean_json = re.sub(r"\s*```$", "", clean_json)
                return schema.model_validate_json(clean_json)
        except LLMError:
            raise
        except httpx.TimeoutException:
            raise LLMInferenceError(f"Gemini structured request timed out after {self._timeout}s")
        except Exception as exc:
            sanitized = redact_sensitive(str(exc))
            raise LLMInferenceError(f"Gemini structured generation failed: {sanitized}")


class OpenAILLMProvider(BaseLLMProvider):
    """
    OpenAI-compatible REST client via async httpx.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
    ):
        self._api_key = (api_key if api_key is not None else (OPENAI_API_KEY or "")).strip()
        self._model = (model or "gpt-4o-mini").strip()
        self._timeout = timeout_seconds or LLM_REQUEST_TIMEOUT_SECONDS

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def provider_status(self) -> str:
        return "live" if self.is_live_ready() else "unavailable"

    def is_live_ready(self) -> bool:
        return bool(self._api_key and len(self._api_key) > 5)

    def _handle_error_response(self, res: httpx.Response) -> None:
        raw_text = res.text
        try:
            err_json = res.json()
            err_msg = err_json.get("error", {}).get("message", raw_text)
        except Exception:
            err_msg = raw_text

        sanitized = redact_sensitive(err_msg)

        if res.status_code == 401:
            raise LLMAuthenticationError(f"OpenAI authentication failed (HTTP 401): {sanitized}")
        if res.status_code == 429:
            raise LLMInferenceError(f"OpenAI rate limit or quota exceeded (HTTP 429): {sanitized}")
        if res.status_code == 404:
            raise LLMInferenceError(f"OpenAI model '{self._model}' not found (HTTP 404): {sanitized}")

        raise LLMInferenceError(f"OpenAI API error (HTTP {res.status_code}): {sanitized}")

    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
    ) -> str:
        if not self.is_live_ready():
            raise LLMAuthenticationError(
                "OpenAI API key is missing or unconfigured in backend/.env (OPENAI_API_KEY)."
            )

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if res.status_code != 200:
                    self._handle_error_response(res)
                data = res.json()
                usage = data.get("usage", {})
                if usage:
                    self.last_usage = {
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                        "model": self._model,
                    }
                text = data["choices"][0]["message"]["content"]
                return text.strip()
        except LLMError:
            raise
        except httpx.TimeoutException:
            raise LLMInferenceError(f"OpenAI request timed out after {self._timeout}s")
        except Exception as exc:
            sanitized = redact_sensitive(str(exc))
            raise LLMInferenceError(f"OpenAI request failed: {sanitized}")

    async def generate_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
    ) -> T:
        if not self.is_live_ready():
            raise LLMAuthenticationError(
                "OpenAI API key is missing or unconfigured in backend/.env (OPENAI_API_KEY)."
            )

        json_instruction = (
            f"\n\nOutput strictly valid JSON matching this schema:\n"
            f"{json.dumps(schema.model_json_schema())}"
        )
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt + json_instruction})

        payload = {
            "model": self._model,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                res = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                )
                if res.status_code != 200:
                    self._handle_error_response(res)
                data = res.json()
                usage = data.get("usage", {})
                if usage:
                    self.last_usage = {
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                        "model": self._model,
                    }
                content = data["choices"][0]["message"]["content"]
                return schema.model_validate_json(content)
        except LLMError:
            raise
        except httpx.TimeoutException:
            raise LLMInferenceError(f"OpenAI structured request timed out after {self._timeout}s")
        except Exception as exc:
            sanitized = redact_sensitive(str(exc))
            raise LLMInferenceError(f"OpenAI structured generation failed: {sanitized}")
