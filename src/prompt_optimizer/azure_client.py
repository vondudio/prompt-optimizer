"""Azure OpenAI client wrapper with error handling and retry logic."""

import json
from typing import Any

from openai import AzureOpenAI, APIConnectionError, RateLimitError, APIStatusError
from rich.console import Console

from prompt_optimizer.config import AzureConfig

console = Console(stderr=True)

# Retry settings
MAX_RETRIES = 3


class AzureClient:
    """Wrapper around the Azure OpenAI SDK."""

    def __init__(self, config: AzureConfig):
        self._client = AzureOpenAI(
            azure_endpoint=config.endpoint,
            api_key=config.api_key,
            api_version=config.api_version,
            max_retries=MAX_RETRIES,
            timeout=60.0,
        )
        self._deployment = config.deployment

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> str:
        """Send a chat completion request and return the assistant's reply.

        Args:
            messages: List of {"role": ..., "content": ...} dicts.
            temperature: Sampling temperature.
            max_tokens: Maximum tokens in the response.
            json_mode: If True, request JSON structured output.

        Returns:
            The assistant's response text.
        """
        kwargs: dict[str, Any] = {
            "model": self._deployment,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = self._client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""
        except RateLimitError:
            console.print("[yellow]Rate limited by Azure OpenAI. Retrying...[/yellow]")
            raise
        except APIConnectionError:
            console.print("[red]Cannot connect to Azure OpenAI endpoint.[/red]")
            raise
        except APIStatusError as e:
            console.print(f"[red]Azure OpenAI error: {e.status_code} — {e.message}[/red]")
            raise

    def chat_json(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.4,
        max_tokens: int = 2048,
    ) -> dict:
        """Send a chat request and parse the response as JSON.

        Args:
            messages: Chat messages.
            temperature: Sampling temperature (lower for structured output).
            max_tokens: Maximum tokens.

        Returns:
            Parsed JSON dict from the response.
        """
        raw = self.chat(messages, temperature=temperature, max_tokens=max_tokens, json_mode=True)
        return json.loads(raw)
