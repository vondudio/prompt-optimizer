"""Configuration loading for Prompt Optimizer."""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class AzureConfig:
    """Azure OpenAI connection settings."""
    endpoint: str
    api_key: str
    deployment: str
    api_version: str = "2024-10-21"


@dataclass
class AppConfig:
    """Application-level preferences."""
    default_mode: str = "interactive"
    history_db_path: str = "prompt_history.db"
    max_follow_up_questions: int = 5
    scoring_enabled: bool = True


@dataclass
class Config:
    """Top-level configuration container."""
    azure: AzureConfig
    app: AppConfig = field(default_factory=AppConfig)


def load_config(env_path: str | None = None, config_path: str | None = None) -> Config:
    """Load configuration from .env and config.json files.

    Args:
        env_path: Path to .env file. Defaults to .env in cwd.
        config_path: Path to config.json. Defaults to config.json in cwd.

    Returns:
        Populated Config object.

    Raises:
        ValueError: If required Azure credentials are missing.
    """
    load_dotenv(env_path)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    if not endpoint or not api_key:
        raise ValueError(
            "Missing Azure OpenAI credentials. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in your .env file. "
            "See .env.example for reference."
        )

    azure = AzureConfig(
        endpoint=endpoint,
        api_key=api_key,
        deployment=deployment,
        api_version=api_version,
    )

    app = AppConfig()
    config_file = Path(config_path or "config.json")
    if config_file.exists():
        with open(config_file) as f:
            data = json.load(f)
        app = AppConfig(
            default_mode=data.get("default_mode", app.default_mode),
            history_db_path=data.get("history_db_path", app.history_db_path),
            max_follow_up_questions=data.get("max_follow_up_questions", app.max_follow_up_questions),
            scoring_enabled=data.get("scoring_enabled", app.scoring_enabled),
        )

    return Config(azure=azure, app=app)
