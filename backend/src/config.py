"""Application configuration using Pydantic Settings.

Loads configuration from environment variables with validation.
"""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─────────────────────────────────────────────────────────────
    # Database
    # ─────────────────────────────────────────────────────────────
    database_url: Annotated[
        str,
        Field(description="PostgreSQL connection string with asyncpg driver"),
    ]

    # ─────────────────────────────────────────────────────────────
    # Google Cloud Platform
    # ─────────────────────────────────────────────────────────────
    gcp_project_id: Annotated[
        str,
        Field(description="Google Cloud project ID"),
    ]
    ga4_property_id: Annotated[
        str,
        Field(description="Google Analytics 4 property ID"),
    ]
    google_application_credentials: Annotated[
        str,
        Field(
            default="/app/secrets/gcp-sa-key.json",
            description="Path to GCP service account JSON",
        ),
    ]

    # ─────────────────────────────────────────────────────────────
    # Vertex AI
    # ─────────────────────────────────────────────────────────────
    vertex_ai_location: Annotated[
        str,
        Field(default="global", description="Vertex AI region - global for Gemini 3"),
    ]
    embedding_model: Annotated[
        str,
        Field(default="text-embedding-004", description="Embedding model name"),
    ]

    # ─────────────────────────────────────────────────────────────
    # Gemini
    # ─────────────────────────────────────────────────────────────
    gemini_model: Annotated[
        str,
        Field(default="gemini-3-pro-preview", description="Gemini 3 Pro - most advanced reasoning model"),
    ]
    use_genai_sdk: Annotated[
        bool,
        Field(default=False, description="Use new google-genai SDK instead of vertexai (experimental)"),
    ]

    # ─────────────────────────────────────────────────────────────
    # Google Custom Search (for web search)
    # ─────────────────────────────────────────────────────────────
    google_search_api_key: Annotated[
        str | None,
        Field(default=None, description="Google Custom Search API key"),
    ]
    google_search_engine_id: Annotated[
        str | None,
        Field(default=None, description="Google Custom Search Engine ID (cx)"),
    ]

    # ─────────────────────────────────────────────────────────────
    # Google Ads
    # ─────────────────────────────────────────────────────────────
    google_ads_customer_id: Annotated[
        str | None,
        Field(default=None, description="Default Google Ads customer ID"),
    ]
    google_ads_developer_token: Annotated[
        str | None,
        Field(default=None, description="Google Ads API developer token"),
    ]
    google_ads_client_id: Annotated[
        str | None,
        Field(default=None, description="Google Ads OAuth client ID"),
    ]
    google_ads_client_secret: Annotated[
        str | None,
        Field(default=None, description="Google Ads OAuth client secret"),
    ]
    google_ads_refresh_token: Annotated[
        str | None,
        Field(default=None, description="Google Ads OAuth refresh token"),
    ]
    google_ads_login_customer_id: Annotated[
        str | None,
        Field(default=None, description="Google Ads MCC login customer ID (optional)"),
    ]
    google_ads_client_accounts: Annotated[
        str | None,
        Field(default=None, description="Comma-separated list of Google Ads client account IDs to export"),
    ]
    google_ads_config_path: Annotated[
        str | None,
        Field(default=None, description="Path to google-ads.yaml config file"),
    ]

    # ─────────────────────────────────────────────────────────────
    # API Security
    # ─────────────────────────────────────────────────────────────
    api_secret_key: Annotated[
        str,
        Field(min_length=32, description="Secret key for API security"),
    ]
    allowed_origins: Annotated[
        str,
        Field(
            default="https://ai.scram2k.com",
            description="Comma-separated list of allowed CORS origins",
        ),
    ]

    # ─────────────────────────────────────────────────────────────
    # Application
    # ─────────────────────────────────────────────────────────────
    environment: Annotated[
        str,
        Field(default="production", description="Environment name"),
    ]
    log_level: Annotated[
        str,
        Field(default="INFO", description="Logging level"),
    ]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        """Ensure origins string is properly formatted."""
        if isinstance(v, str):
            return v.strip()
        return v

    @property
    def cors_origins(self) -> list[str]:
        """Parse allowed origins into a list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment.lower() == "production"

    @property
    def ads_client_account_list(self) -> list[str]:
        """Parse Google Ads client accounts into a list."""
        if not self.google_ads_client_accounts:
            return []
        return [acc.strip() for acc in self.google_ads_client_accounts.split(",") if acc.strip()]


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Settings: Application configuration
    """
    return Settings()
