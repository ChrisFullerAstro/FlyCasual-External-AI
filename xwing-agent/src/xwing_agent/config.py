"""Application configuration using Pydantic Settings."""
from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 33293
    api_reload: bool = False
    debug: bool = False

    # Anthropic Configuration
    anthropic_api_key: SecretStr = Field(..., description="Anthropic API key")
    anthropic_model: str = "claude-sonnet-4-20250514"
    anthropic_max_tokens: int = 4096

    # LangSmith Configuration
    langchain_tracing_v2: bool = True
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: SecretStr | None = None
    langchain_project: str = "xwing-agent"

    # Storage
    storage_path: Path = Path("./data/games")
    rules_index_path: Path = Path("./data/rules_index")

    # Agent Configuration
    perception_error: float = Field(
        default=0.1,
        ge=0.0,
        le=0.5,
        description="Percentage of error in distance measurements",
    )
    max_tool_iterations: int = 10

    # Logging
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
