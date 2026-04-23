"""LLM client protocol and base interface."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM client backends."""

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str: ...

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> dict: ...
