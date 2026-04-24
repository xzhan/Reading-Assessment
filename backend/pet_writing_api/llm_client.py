"""OpenAI-compatible JSON client for PET Writing pipeline."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class LLMClientError(Exception):
    """Raised when an LLM call fails or returns invalid content."""


@dataclass
class LLMCallResult:
    provider: str
    model_name: str
    model_version: str | None
    output_payload: dict[str, Any]
    latency_ms: int


def _extract_text_from_message(message: Any) -> str:
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        parts = []
        for item in message:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts)
    return ""


def _extract_json_block(text: str) -> dict[str, Any]:
    candidate = text.strip()
    if candidate.startswith("```"):
        lines = candidate.splitlines()
        if len(lines) >= 3:
            candidate = "\n".join(lines[1:-1]).strip()
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end < start:
            raise LLMClientError("LLM response did not contain valid JSON.")
        try:
            return json.loads(candidate[start : end + 1])
        except json.JSONDecodeError as exc:
            raise LLMClientError("LLM response JSON could not be parsed.") from exc


class OpenAICompatibleLLMClient:
    """Minimal OpenAI-compatible chat completion client."""

    def __init__(
        self,
        api_key: str | None,
        model: str | None,
        base_url: str = "https://api.openai.com/v1",
        timeout_sec: int = 30,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout_sec = timeout_sec

    @classmethod
    def from_env(cls) -> "OpenAICompatibleLLMClient":
        return cls(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_MODEL"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
            timeout_sec=int(os.getenv("PET_WRITING_LLM_TIMEOUT_SEC", "30")),
        )

    def is_enabled(self) -> bool:
        return bool(self.api_key and self.model)

    def complete_json(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        temperature: float = 0.2,
    ) -> LLMCallResult:
        if not self.is_enabled():
            raise LLMClientError("LLM client is not configured.")

        body = json.dumps(
            {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": temperature,
            }
        ).encode("utf-8")
        req = urllib.request.Request(
            url=f"{self.base_url}/chat/completions",
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        start = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise LLMClientError(f"LLM HTTP error {exc.code}: {detail}") from exc
        except urllib.error.URLError as exc:
            raise LLMClientError(f"LLM connection failed: {exc}") from exc
        latency_ms = int((time.perf_counter() - start) * 1000)

        choices = payload.get("choices") or []
        if not choices:
            raise LLMClientError("LLM response did not include choices.")
        message = choices[0].get("message", {}).get("content")
        content = _extract_text_from_message(message)
        parsed = _extract_json_block(content)
        return LLMCallResult(
            provider="openai-compatible",
            model_name=self.model or "unknown",
            model_version=payload.get("model"),
            output_payload=parsed,
            latency_ms=latency_ms,
        )
