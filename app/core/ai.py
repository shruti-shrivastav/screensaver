from __future__ import annotations
from functools import lru_cache
from google import genai
from app.core.config import settings


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    """Return a cached Gemini client. No Vertex AI — plain API key auth."""
    if not settings.GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Add it to your .env file."
        )
    return genai.Client(api_key=settings.GEMINI_API_KEY)
