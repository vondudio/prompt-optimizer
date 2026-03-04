"""Tests for the config module."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from prompt_optimizer.config import load_config, AppConfig


def test_load_config_azure_backend_missing_creds_raises():
    """Should raise ValueError when Azure backend selected but creds missing."""
    with patch.dict(os.environ, {}, clear=True):
        with pytest.raises(ValueError, match="Missing Azure OpenAI credentials"):
            load_config(env_path="/nonexistent/.env", config_path="/nonexistent/config.json")


def test_load_config_local_backend_no_azure_creds():
    """Should succeed with local backend even without Azure credentials."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config_path.write_text(json.dumps({"backend": "local"}))

        with patch.dict(os.environ, {}, clear=True):
            cfg = load_config(env_path="/nonexistent/.env", config_path=str(config_path))

    assert cfg.app.backend == "local"
    assert cfg.azure is None


def test_load_config_env_var_overrides():
    """Env vars should override config.json for backend and local_model."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "config.json"
        config_path.write_text(json.dumps({"backend": "azure"}))

        env = {
            "PROMPT_OPT_BACKEND": "local",
            "PROMPT_OPT_LOCAL_MODEL": "my-custom-model",
        }
        with patch.dict(os.environ, env, clear=True):
            cfg = load_config(env_path="/nonexistent/.env", config_path=str(config_path))

    assert cfg.app.backend == "local"
    assert cfg.app.local_model == "my-custom-model"


def test_app_config_defaults():
    """AppConfig should have sensible defaults."""
    app = AppConfig()
    assert app.backend == "azure"
    assert app.local_model == "phi-4-mini-reasoning"
    assert app.max_follow_up_questions == 5
