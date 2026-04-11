"""Provider-agnostic LLM client interfaces."""

from dataclasses import dataclass
import json
import os
from typing import Protocol

import httpx


class StructuredLLMClient(Protocol):
    """Protocol for clients that return schema-shaped structured outputs."""

    def generate_structured(
        self,
        operation: str,
        prompt: str,
        required_keys: tuple[str, ...],
    ) -> dict:
        """Return a structured response for an operation."""


@dataclass(frozen=True)
class OpenAICompatibleLLMClient:
    """Minimal OpenAI-compatible chat completions client for structured JSON generation."""

    model: str
    api_key_env: str = "OPENAI_API_KEY"
    api_base: str = "http://localhost:11434/v1"
    http_client: httpx.Client | None = None
    timeout_seconds: float = 300.0

    @property
    def api_key(self) -> str:
        return os.environ.get(self.api_key_env, "ollama")

    @property
    def uses_native_ollama(self) -> bool:
        return (
            ("localhost:11434" in self.api_base or "127.0.0.1:11434" in self.api_base)
            and self.api_key == "ollama"
        )

    @property
    def prompt_profile(self) -> str:
        return "compact" if self.uses_native_ollama else "full"

    def _ollama_base(self) -> str:
        return self.api_base.removesuffix("/v1").rstrip("/")

    def _native_ollama_prompt(self, prompt: str) -> str:
        return (
            "Return only valid JSON. "
            "Do not include commentary, reasoning, markdown, or code fences.\n\n"
            f"{prompt}"
        )

    def _native_ollama_retry_prompt(self, prompt: str, operation: str) -> str:
        if operation == "extract":
            return (
                "Return a shorter JSON response. "
                "Keep only the most durable facts. "
                "Do not exceed 6 entities, 8 claims, and 8 evidence spans. "
                "Return only valid JSON with no commentary, reasoning, markdown, or code fences.\n\n"
                f"{prompt}"
            )
        return self._native_ollama_prompt(prompt)

    def _native_ollama_num_predict(self, operation: str) -> int:
        if operation == "extract":
            return 900
        if operation == "answer":
            return 400
        return 600

    def _generate_via_ollama_native(
        self,
        client: httpx.Client,
        operation: str,
        prompt: str,
        required_keys: tuple[str, ...],
    ) -> dict:
        last_error: Exception | None = None
        prompt_variants = [
            self._native_ollama_prompt(prompt),
            self._native_ollama_retry_prompt(prompt, operation),
        ]
        for current_prompt in prompt_variants:
            try:
                response = client.post(
                    f"{self._ollama_base()}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": current_prompt,
                        "stream": False,
                        "format": "json",
                        "think": False,
                        "options": {
                            "temperature": 0,
                            "num_predict": self._native_ollama_num_predict(operation),
                        },
                    },
                )
                response.raise_for_status()
                body = response.json()
                result = json.loads(body["response"])
                missing = [key for key in required_keys if key not in result]
                if missing:
                    raise ValueError(f"missing required keys: {missing}")
                return result
            except (KeyError, json.JSONDecodeError, ValueError) as exc:
                last_error = exc
                continue
        raise ValueError(f"failed to parse structured response: {last_error}")

    def generate_structured(
        self,
        operation: str,
        prompt: str,
        required_keys: tuple[str, ...],
    ) -> dict:
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a structured data generator. "
                        "Return only valid JSON and satisfy all required keys."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        client = self.http_client or httpx.Client(timeout=self.timeout_seconds)
        close_client = self.http_client is None
        try:
            if self.uses_native_ollama:
                return self._generate_via_ollama_native(
                    client=client,
                    operation=operation,
                    prompt=prompt,
                    required_keys=required_keys,
                )

            last_error: Exception | None = None
            for _ in range(2):
                try:
                    response = client.post(
                        f"{self.api_base}/chat/completions",
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                    response.raise_for_status()
                    body = response.json()
                    content = body["choices"][0]["message"]["content"]
                    result = json.loads(content)
                    missing = [key for key in required_keys if key not in result]
                    if missing:
                        raise ValueError(f"missing required keys: {missing}")
                    return result
                except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
                    last_error = exc
                    continue
            raise ValueError(f"failed to parse structured response: {last_error}")
        finally:
            if close_client:
                client.close()


def render_structured_output(
    client: StructuredLLMClient,
    operation: str,
    prompt: str,
    required_keys: tuple[str, ...],
) -> dict:
    """Use any structured LLM client through the same interface."""
    return client.generate_structured(
        operation=operation,
        prompt=prompt,
        required_keys=required_keys,
    )
