from fastapi import APIRouter
from ..config import get_settings
import os

router = APIRouter()

@router.get("/debug/settings")
async def debug_settings():
    """Debug endpoint to check what settings are loaded"""
    settings = get_settings()
    
    return {
        "aoai_endpoint": settings.aoai_endpoint,
        "aoai_key": settings.aoai_key[:8] + "*" * (len(settings.aoai_key) - 12) + settings.aoai_key[-4:] if settings.aoai_key else None,
        "aoai_deployment": settings.aoai_deployment,
        "aoai_api_version": settings.aoai_api_version,
        "environment_vars": {
            "AZURE_OPENAI_ENDPOINT": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "AZURE_OPENAI_API_KEY": os.getenv("AZURE_OPENAI_API_KEY", "")[:8] + "*" * (len(os.getenv("AZURE_OPENAI_API_KEY", "")) - 12) + os.getenv("AZURE_OPENAI_API_KEY", "")[-4:] if os.getenv("AZURE_OPENAI_API_KEY") else None,
            "AZURE_OPENAI_DEPLOYMENT": os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            "AZURE_OPENAI_API_VERSION": os.getenv("AZURE_OPENAI_API_VERSION"),
        }
    }
