from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    anthropic_api_key: str = Field(..., description="Anthropic API key")
    claude_model: str = Field(default="claude-sonnet-4-5", description="Claude model identifier")
    max_tokens: int = Field(default=1024, description="Maximum tokens per response")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
