"""Local LLM client using Foundry Local (on-device inference via NPU/GPU/CPU)."""

import json
import re
from typing import Any

from rich.console import Console

console = Console(stderr=True)


def _extract_json_from_markdown(text: str) -> dict[str, Any] | None:
    """Try to extract a JSON object from markdown code fences."""
    pattern = r"```(?:json)?\s*\n?(.*?)\n?\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            return None
    return None


class LocalClient:
    """LLM client backed by Foundry Local (OpenAI-compatible local endpoint)."""

    def __init__(self, model: str = "qwen2.5-1.5b-instruct-qnn-npu"):
        try:
            from foundry_local import FoundryLocalManager
        except ImportError:
            raise ImportError(
                "foundry-local-sdk is required for the local backend. "
                "Install it with: pip install prompt-optimizer[local]"
            )

        self._model = model
        console.print(f"[dim]Starting Foundry Local service and loading model '{model}'...[/dim]")

        self._manager = FoundryLocalManager(model)
        endpoint = self._manager.endpoint

        from openai import OpenAI
        self._client = OpenAI(
            base_url=endpoint,
            api_key="foundry-local",
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion to the local Foundry model."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        # JSON mode may not be supported by all local models — try but don't fail
        if json_mode:
            try:
                kwargs["response_format"] = {"type": "json_object"}
                response = self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            except Exception:
                # Fall back without JSON mode
                del kwargs["response_format"]

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Send a chat request and parse the response as JSON.

        Uses a multi-step fallback for robustness with smaller local models:
        1. Try json.loads() on raw response
        2. Try extracting JSON from markdown code fences
        3. Retry with a stronger JSON-only system prompt
        4. Raise a clear error if all fail
        """
        raw = self.chat(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)

        # Step 1: Try direct parse
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            pass

        # Step 2: Try extracting from markdown code fences
        extracted = _extract_json_from_markdown(raw)
        if extracted is not None:
            return extracted

        # Step 3: Retry with stronger JSON instruction
        retry_messages = [
            {
                "role": "system",
                "content": (
                    "You MUST return ONLY valid JSON. No markdown, no explanation, "
                    "no code fences. Output a single JSON object and nothing else."
                ),
            },
            *messages,
        ]
        raw_retry = self.chat(retry_messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)

        try:
            return json.loads(raw_retry)
        except json.JSONDecodeError:
            pass

        extracted_retry = _extract_json_from_markdown(raw_retry)
        if extracted_retry is not None:
            return extracted_retry

        # Step 4: Give up
        raise ValueError(
            f"Failed to parse JSON from local model response after retry. "
            f"Raw response (truncated): {raw_retry[:200]}"
        )
