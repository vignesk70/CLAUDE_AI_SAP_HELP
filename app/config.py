from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    anthropic_api_key: str = Field(..., description="Anthropic API key")
    claude_model: str = Field(default="claude-opus-5", description="Claude model identifier")
    max_tokens: int = Field(default=16000, description="Maximum tokens per response")
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    cors_origins: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
            "http://localhost:3003",
            "http://127.0.0.1:3003",
        ],
        description="Origins allowed to call this API (Nuxt frontend dev server)",
    )

    mongodb_uri: str = Field(
        default="mongodb://localhost:27017/claude_sap_ai",
        description="MongoDB connection string",
    )
    mongodb_database: str = Field(
        default="claude_sap_ai", description="MongoDB database name"
    )
    sap_help_search_url: str = Field(
        default="https://help.sap.com/http.svc/elasticsearch",
        description="SAP Help Portal search endpoint used to seed the help collection",
    )

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
