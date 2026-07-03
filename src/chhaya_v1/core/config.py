"""
Configuration Loader for Chhaya.
Loads configuration from YAML and environment variables using Pydantic Settings.
"""

import os
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMConfig(BaseModel):
    default_provider: str = "ollama"
    tier_14b_model: str = "llama3:14b"
    tier_7b_model: str = "llama3:7b"


class StorageConfig(BaseModel):
    backend: str = "sqlite"
    database_url: str = "sqlite:///./chhaya.db"


class MemoryConfig(BaseModel):
    vector_store: str = "chroma"
    path: str = "./chroma_db"


class WorkspaceConfig(BaseModel):
    base_path: str = "./workspaces"


class ExternalAgentsConfig(BaseModel):
    jules_url: str = "https://api.jules.ai/v1/tasks"
    jules_api_key: Optional[str] = None


class LoggingConfig(BaseModel):
    level: str = "INFO"


class ChhayaSettings(BaseSettings):
    """
    Main application settings.
    Prioritizes Env Vars -> Config File -> Defaults.
    """
    model_config = SettingsConfigDict(env_prefix="CHHAYA_", env_file=".env", env_nested_delimiter="__")

    config_path: str = Field(default="./config/config.yaml", description="Path to the YAML config file")

    # These will be populated from YAML or Env Vars (e.g. CHHAYA_LLM__DEFAULT_PROVIDER)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    memory: MemoryConfig = Field(default_factory=MemoryConfig)
    workspace: WorkspaceConfig = Field(default_factory=WorkspaceConfig)
    external_agents: ExternalAgentsConfig = Field(default_factory=ExternalAgentsConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    # Global overrides via purely Env Vars
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL", validation_alias="OLLAMA_BASE_URL")
    jules_api_key: Optional[str] = Field(default=None, alias="JULES_API_KEY", validation_alias="JULES_API_KEY")


def load_config(config_path: str | None = None) -> ChhayaSettings:
    """
    Loads the configuration by combining default values, YAML file contents,
    and Environment Variable overrides.
    """
    env_settings = ChhayaSettings()
    actual_config_path = config_path or env_settings.config_path

    yaml_data: dict[str, Any] = {}
    if Path(actual_config_path).exists():
        with open(actual_config_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f) or {}

    class ChhayaSettingsWithYaml(ChhayaSettings):
        @classmethod
        def settings_customise_sources(
            cls,
            settings_cls,
            init_settings,
            env_settings,
            dotenv_settings,
            file_secret_settings,
        ):
            # Return sources in priority order: env > dotenv > init (yaml) > file_secret
            return (
                env_settings,
                dotenv_settings,
                init_settings,
                file_secret_settings,
            )

    settings = ChhayaSettingsWithYaml(**yaml_data)

    if config_path:
        settings.config_path = config_path

    # Map the root level alias directly if provided
    if settings.jules_api_key:
        settings.external_agents.jules_api_key = settings.jules_api_key

    return settings

# A global instance that can be imported and used throughout the application
settings = load_config()
