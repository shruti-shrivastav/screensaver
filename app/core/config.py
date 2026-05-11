from __future__ import annotations
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    PORT: int = 9090

    # Auth
    JWT_SECRET: str = "change_me"
    ACCESS_TOKEN_TTL: int = 28800   # 8 hours
    REFRESH_TOKEN_TTL: int = 604800  # 7 days

    # Gemini
    GEMINI_API_KEY: str = ""

    # Cloudflare tunnel (empty = disabled)
    CF_TUNNEL_NAME: str = ""

    # Ngrok tunnel url (empty = disabled)
    NGROK_URL: str = ""

    # Capture config
    DISPLAY_OUTPUT: str = "screen"
    FRAME_PATH: str = "/tmp/capture.jpg"

    # Solver
    SOLVER_MAX_TURNS: int = 5

    # Storage
    DATA_DIR: str = "data"

    @property
    def sessions_dir(self) -> str:
        return os.path.join(self.DATA_DIR, "sessions")

    @property
    def htpasswd_path(self) -> str:
        return os.path.join(self.DATA_DIR, ".htpasswd.json")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenience singleton
settings: Settings = get_settings()
