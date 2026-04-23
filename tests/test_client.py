"""Tests for LLMClient protocol."""

from unittest.mock import MagicMock

from prompt_optimizer.azure_client import AzureClient
from prompt_optimizer.client import LLMClient


def test_azure_client_satisfies_protocol():
    """AzureClient should match the LLMClient protocol."""
    mock = MagicMock(spec=AzureClient)
    assert isinstance(mock, LLMClient)
