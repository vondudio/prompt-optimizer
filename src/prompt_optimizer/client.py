"""LLM client protocol — the abstraction all backends implement."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class LLMClient(Protocol):
    """Protocol for LLM backend clients.

    Both AzureClient and LocalClient implement this interface.
    Downstream code (analyzer, questioner, optimizer) depends on this protocol only.
    """

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion and return the assistant's reply text."""
        ...

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """Send a chat completion and parse the response as JSON."""
        ...
