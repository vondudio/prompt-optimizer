"""Local LLM client using Foundry Local (on-device inference via NPU/GPU/CPU)."""

import json
import re
from typing import Any

from rich.console import Console

console = Console(stderr=True)


def _extract_json_from_text(text: str) -> dict[str, Any] | None:
    """Extract a JSON object from text that may contain markdown fences or other wrapping.

    Handles:
    - Complete code fences: ```json ... ```
    - Unclosed code fences (truncated responses): ```json ...
    - Raw JSON object embedded in prose
    """
    # Strip markdown code fence wrapper if present (closed or unclosed)
    fence_match = re.search(r"```(?:json)?\s*\n?([\s\S]*?)(?:\n?\s*```|$)", text)
    if fence_match:
        content = fence_match.group(1).strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

    # Find the first { and try to parse a JSON object from there
    idx = text.find("{")
    if idx != -1:
        # Try progressively shorter substrings from the last } backwards
        candidate = text[idx:]
        last_brace = candidate.rfind("}")
        if last_brace != -1:
            try:
                return json.loads(candidate[: last_brace + 1])
            except json.JSONDecodeError:
                pass
        # Try the whole remainder (in case it ends with })
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

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

        self._manager = FoundryLocalManager(model)

        # The API model ID differs from the catalog alias
        self._model = self._manager.get_model_info(model).id
        endpoint = self._manager.endpoint
        console.print(f"[dim]Foundry Local ready — model ID: {self._model}[/dim]")

        from openai import OpenAI
        self._client = OpenAI(
            base_url=endpoint,
            api_key=self._manager.api_key,
        )

    # Higher default max_tokens for local models — smaller models are more verbose
    _DEFAULT_MAX_TOKENS = 4096

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion to the local Foundry model."""
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
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
        max_tokens: int = _DEFAULT_MAX_TOKENS,
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

        # Step 2: Try extracting from markdown fences or raw text
        extracted = _extract_json_from_text(raw)
        if extracted is not None:
            return extracted

        # Step 3: Retry with stronger JSON instruction and compact output request
        retry_messages = [
            {
                "role": "system",
                "content": (
                    "You MUST return ONLY valid JSON. No markdown, no explanation, "
                    "no code fences. Output a single JSON object and nothing else. "
                    "Keep string values short and concise to avoid truncation."
                ),
            },
            *messages,
        ]
        raw_retry = self.chat(retry_messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)

        try:
            return json.loads(raw_retry)
        except json.JSONDecodeError:
            pass

        extracted_retry = _extract_json_from_text(raw_retry)
        if extracted_retry is not None:
            return extracted_retry

        # Step 4: Give up
        raise ValueError(
            f"Failed to parse JSON from local model response after retry. "
            f"Raw response (truncated): {raw_retry[:500]}"
        )
