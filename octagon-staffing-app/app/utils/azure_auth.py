from __future__ import annotations

import logging
import os
from typing import Optional

import structlog
from azure.identity.aio import DefaultAzureCredential


_credential_singleton: Optional[DefaultAzureCredential] = None


def configure_structured_logging(level: str = "INFO") -> None:
    """Configure structlog and stdlib logging for JSON output.

    This format works well with Azure Log Analytics.
    """

    logging.basicConfig(level=getattr(logging, level.upper(), logging.INFO))
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.dict_tracebacks,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.getLevelName(level.upper())),
        cache_logger_on_first_use=True,
    )


async def get_default_credential() -> DefaultAzureCredential:
    """Get a cached async DefaultAzureCredential.

    Uses Managed Identity in Azure, falls back to developer credentials locally.
    """

    global _credential_singleton
    if _credential_singleton is None:
        _credential_singleton = DefaultAzureCredential(exclude_interactive_browser_credential=True)
    return _credential_singleton


async def close_default_credential() -> None:
    """Close the cached credential if open."""

    global _credential_singleton
    if _credential_singleton is not None:
        await _credential_singleton.close()
        _credential_singleton = None


