from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal, Optional

from pydantic import BaseModel, Field


class AppSettings(BaseModel):
    """Application settings loaded from environment variables.

    In production on Azure Container Apps, these are populated from Key Vault
    via secret references. Local development can use a .env file.
    """

    environment: Literal["dev", "staging", "prod"] = Field(
        default=os.getenv("ENVIRONMENT", "dev")
    )

    # Azure Storage (Blob)
    storage_blob_endpoint: str = Field(
        default_factory=lambda: os.getenv("STORAGE_BLOB_ENDPOINT", "")
    )

    # Azure Document Intelligence
    docintel_endpoint: Optional[str] = Field(default=os.getenv("DOCINTEL_ENDPOINT"))
    docintel_key: Optional[str] = Field(default=os.getenv("DOCINTEL_KEY"))

    # Azure OpenAI
    aoai_endpoint: Optional[str] = Field(default=os.getenv("AZURE_OPENAI_ENDPOINT"))
    aoai_key: Optional[str] = Field(default=os.getenv("AZURE_OPENAI_API_KEY"))
    aoai_deployment: str = Field(default=os.getenv("AZURE_OPENAI_DEPLOYMENT", "text-embedding-3-small"))
    aoai_api_version: str = Field(default=os.getenv("AZURE_OPENAI_API_VERSION", "2024-08-01-preview"))

    # Azure AI Search
    search_endpoint: Optional[str] = Field(default=os.getenv("SEARCH_ENDPOINT"))
    search_key: Optional[str] = Field(default=os.getenv("SEARCH_KEY"))
    search_index_name: str = Field(default=os.getenv("SEARCH_INDEX_NAME", "octagon-sows"))

    # Application settings
    cors_allow_origins: str = Field(default=os.getenv("CORS_ALLOW_ORIGINS", "*"))
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    port: int = Field(default=int(os.getenv("PORT", "8080")))


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""

    return AppSettings()


