"""Tests for config module."""

import json
import os
import tempfile
from unittest.mock import patch

import pytest

from prompt_optimizer.config import load_config, AzureConfig, AppConfig, Config


_BASE_ENV = {
    "AZURE_OPENAI_ENDPOINT": "https://test.openai.azure.com",
    "AZURE_OPENAI_API_KEY": "test-key-123",
    "AZURE_OPENAI_DEPLOYMENT": "gpt-4o",
    "AZURE_OPENAI_API_VERSION": "2024-10-21",
}


class TestLoadConfig:
    @patch.dict(os.environ, _BASE_ENV, clear=False)
    def test_load_config_from_env(self):
        cfg = load_config(env_path=os.devnull)
        assert cfg.azure.endpoint == "https://test.openai.azure.com"
        assert cfg.azure.api_key == "test-key-123"
        assert cfg.azure.deployment == "gpt-4o"
        assert isinstance(cfg, Config)

    @patch.dict(os.environ, {k: v for k, v in _BASE_ENV.items() if k != "AZURE_OPENAI_ENDPOINT"}, clear=True)
    def test_load_config_missing_endpoint_raises(self):
        with pytest.raises(ValueError, match="Missing Azure OpenAI credentials"):
            load_config(env_path=os.devnull)

    @patch.dict(os.environ, {k: v for k, v in _BASE_ENV.items() if k != "AZURE_OPENAI_API_KEY"}, clear=True)
    def test_load_config_missing_api_key_raises(self):
        with pytest.raises(ValueError, match="Missing Azure OpenAI credentials"):
            load_config(env_path=os.devnull)

    @patch.dict(os.environ, _BASE_ENV, clear=False)
    def test_load_config_with_config_json(self):
        data = {"default_mode": "quick", "max_follow_up_questions": 3}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            f.flush()
            cfg = load_config(env_path=os.devnull, config_path=f.name)
        os.unlink(f.name)
        assert cfg.app.default_mode == "quick"
        assert cfg.app.max_follow_up_questions == 3

    @patch.dict(os.environ, _BASE_ENV, clear=False)
    def test_load_config_defaults(self):
        cfg = load_config(env_path=os.devnull)
        assert cfg.azure.deployment == "gpt-4o"
        assert cfg.azure.api_version == "2024-10-21"
        assert cfg.app.default_mode == "interactive"
        assert cfg.app.history_db_path == "prompt_history.db"
        assert cfg.app.scoring_enabled is True
