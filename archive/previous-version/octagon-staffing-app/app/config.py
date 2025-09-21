from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Application settings loaded from environment variables.

    In production on Azure Container Apps, these are populated from Key Vault
    via secret references. Local development can use a .env file.
    """
    
    model_config = SettingsConfigDict(
        env_file='../.env',
        env_file_encoding='utf-8',
        extra='ignore'
    )

    environment: Literal["dev", "staging", "prod"] = Field(
        default="dev"
    )

    # Azure Storage (Blob)
    storage_blob_endpoint: str = Field(default="")

    # Azure Document Intelligence
    docintel_endpoint: Optional[str] = Field(default=None)

    # Azure OpenAI
    aoai_endpoint: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('AZURE_OPENAI_ENDPOINT', 'AOAI_ENDPOINT')
    )
    aoai_key: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices('AZURE_OPENAI_API_KEY', 'AOAI_KEY')
    )
    aoai_deployment: str = Field(
        default='text-embedding-3-small',
        validation_alias=AliasChoices('AZURE_OPENAI_DEPLOYMENT', 'AOAI_DEPLOYMENT')
    )
    aoai_api_version: str = Field(
        default='2024-08-01-preview',
        validation_alias=AliasChoices('AZURE_OPENAI_API_VERSION', 'AOAI_API_VERSION')
    )
    

    # Azure AI Search
    search_endpoint: Optional[str] = Field(default=None)
    search_key: Optional[str] = Field(default=None)
    search_index_name: str = Field(default="octagon-sows")

    # Application settings
    cors_allow_origins: str = Field(default="*")
    log_level: str = Field(default="INFO")
    port: int = Field(default=8080)


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Return cached application settings."""
    return AppSettings()


