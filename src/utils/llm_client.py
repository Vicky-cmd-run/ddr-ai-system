from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from urllib import error, request

from src.utils.logger import get_logger


@dataclass(slots=True)
class LLMResponse:
    content: str
    provider: str
    used_live_model: bool


class LLMClient:
    """
    LLM wrapper for OpenAI Responses API or a local Ollama server.

    OpenAI is used when `LLM_PROVIDER=openai`.
    Ollama is used when `LLM_PROVIDER=ollama`.
    """

    def __init__(
        self,
        model_name: str = "gpt-4o-mini",
        reasoning_effort: str = "medium",
        enabled: bool = True,
    ) -> None:
        self.model_name = model_name
        self.reasoning_effort = reasoning_effort
        self.enabled = enabled
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.api_key = os.getenv("OPENAI_API_KEY", "")  # GitHub safety: credentials must come from the environment, never from committed source code.
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        self.ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
        self.logger = get_logger(self.__class__.__name__)

    def available(self) -> bool:
        if not self.enabled:
            return False
        if self.provider == "ollama":
            return True
        return bool(self.api_key)

    def complete_text(
        self,
        prompt: str,
        fallback: str,
        instructions: str = "",
        model: str | None = None,
        max_output_tokens: int = 2000,
    ) -> LLMResponse:
        if not self.available():
            self.logger.warning("LLM provider is not available; returning fallback text.")
            return LLMResponse(fallback, "offline-fallback", False)

        try:
            if self.provider == "ollama":
                self.logger.info(
                    "Calling Ollama with model %s at %s",
                    model or self.model_name,
                    self.ollama_base_url,
                )
                content = self._create_ollama_response(
                    prompt=prompt,
                    instructions=instructions,
                    model=model,
                    max_output_tokens=max_output_tokens,
                )
                return LLMResponse(content or fallback, "ollama", True)

            payload = self._base_payload(
                prompt=prompt,
                instructions=instructions,
                model=model,
                max_output_tokens=max_output_tokens,
            )
            payload["text"] = {"format": {"type": "text"}}
            # Fix 7: complete_text now performs the real OpenAI request so normalization and DDR composition can use the live model when OPENAI_API_KEY is set.
            self.logger.info("Calling OpenAI Responses API with model %s", payload["model"])
            content = self._create_openai_response(payload)
            return LLMResponse(content or fallback, "openai-responses", True)
        except Exception as exc:
            self.logger.warning("%s text request failed; using fallback text. %s", self.provider, exc)
            return LLMResponse(fallback, "offline-fallback", False)

    def complete_json(
        self,
        prompt: str,
        schema_name: str,
        schema: dict[str, Any],
        fallback: dict[str, Any],
        instructions: str = "",
        model: str | None = None,
        max_output_tokens: int = 4000,
    ) -> dict[str, Any]:
        if not self.available():
            self.logger.warning("LLM provider is not available; returning fallback JSON.")
            return fallback

        try:
            if self.provider == "ollama":
                content = self._create_ollama_response(
                    prompt=prompt,
                    instructions=instructions,
                    model=model,
                    max_output_tokens=max_output_tokens,
                )
            else:
                payload = self._base_payload(
                    prompt=prompt,
                    instructions=instructions,
                    model=model,
                    max_output_tokens=max_output_tokens,
                )
                payload["text"] = {
                    "format": {
                        "type": "json_schema",
                        "name": schema_name,
                        "strict": True,
                        "schema": schema,
                    }
                }
                content = self._create_openai_response(payload)
            return json.loads(content)
        except Exception as exc:
            self.logger.warning("%s JSON request failed; using fallback JSON. %s", self.provider, exc)
            return fallback

    def _base_payload(
        self,
        prompt: str,
        instructions: str,
        model: str | None,
        max_output_tokens: int,
    ) -> dict[str, Any]:
        chosen_model = model or self.model_name
        payload: dict[str, Any] = {
            "model": chosen_model,
            "instructions": instructions,
            "input": prompt,
            "max_output_tokens": max_output_tokens,
            "store": False,
        }
        if self.reasoning_effort and (
            chosen_model.startswith("gpt-5") or chosen_model.startswith("o")
        ):
            payload["reasoning"] = {"effort": self.reasoning_effort}
        return payload

    def _create_openai_response(self, payload: dict[str, Any]) -> str:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            response = client.responses.create(**payload)
            output_text = getattr(response, "output_text", "")
            if output_text:
                return output_text
            if hasattr(response, "model_dump_json"):
                return self._extract_output_text(json.loads(response.model_dump_json()))
        except ImportError:
            pass

        req = request.Request(
            f"{self.base_url}/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=120) as handle:
                body = json.loads(handle.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API error: {detail}") from exc

        return self._extract_output_text(body)

    def _create_ollama_response(
        self,
        prompt: str,
        instructions: str,
        model: str | None,
        max_output_tokens: int,
    ) -> str:
        chosen_model = model or self.model_name
        payload = {
            "model": chosen_model,
            "prompt": prompt,
            "system": instructions,
            "stream": False,
            "options": {
                "num_predict": max_output_tokens,
            },
        }
        req = request.Request(
            f"{self.ollama_base_url}/api/generate",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=240) as handle:
                body = json.loads(handle.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"Ollama API error: {detail}") from exc
        except error.URLError as exc:
            raise RuntimeError(
                "Could not reach Ollama. Start it with `ollama serve` and confirm the model is pulled."
            ) from exc

        response_text = body.get("response", "")
        if not response_text:
            raise RuntimeError("Ollama returned an empty response.")
        return response_text.strip()

    def _extract_output_text(self, body: dict[str, Any]) -> str:
        if isinstance(body.get("output_text"), str) and body["output_text"]:
            return body["output_text"]

        chunks: list[str] = []
        for item in body.get("output", []):
            for content in item.get("content", []):
                if content.get("type") == "output_text":
                    chunks.append(content.get("text", ""))
        return "\n".join(chunk for chunk in chunks if chunk).strip()
