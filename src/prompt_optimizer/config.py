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
    max_follow_up_questions: int = 5
    scoring_enabled: bool = True
    backend: str = "azure"
    local_model: str = "phi-4-mini-reasoning"


@dataclass
class Config:
    """Top-level configuration container."""
    azure: AzureConfig | None
    app: AppConfig = field(default_factory=AppConfig)


def load_config(env_path: str | None = None, config_path: str | None = None) -> Config:
    """Load configuration from .env and config.json files.

    Args:
        env_path: Path to .env file. Defaults to .env in cwd.
        config_path: Path to config.json. Defaults to config.json in cwd.

    Returns:
        Populated Config object.

    Raises:
        ValueError: If required Azure credentials are missing and backend is 'azure'.
    """
    load_dotenv(env_path)

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
    deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-10-21")

    # Read app config first to determine backend
    app = AppConfig()
    config_file = Path(config_path or "config.json")
    if config_file.exists():
        with open(config_file) as f:
            data = json.load(f)
        app = AppConfig(
            default_mode=data.get("default_mode", app.default_mode),
            max_follow_up_questions=data.get("max_follow_up_questions", app.max_follow_up_questions),
            scoring_enabled=data.get("scoring_enabled", app.scoring_enabled),
            backend=data.get("backend", app.backend),
            local_model=data.get("local_model", app.local_model),
        )

    # Override with env vars if set
    app.backend = os.getenv("PROMPT_OPT_BACKEND", app.backend)
    app.local_model = os.getenv("PROMPT_OPT_LOCAL_MODEL", app.local_model)

    # Azure credentials are only required when using the azure backend
    azure: AzureConfig | None = None
    if endpoint and api_key:
        azure = AzureConfig(
            endpoint=endpoint,
            api_key=api_key,
            deployment=deployment,
            api_version=api_version,
        )
    elif app.backend == "azure":
        raise ValueError(
            "Missing Azure OpenAI credentials. "
            "Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY in your .env file, "
            "or use --backend local for Foundry Local. See .env.example for reference."
        )

    return Config(azure=azure, app=app)
