"""Fail early on invalid configuration; never load future services here."""
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="GOV_", env_file=ROOT / ".env", env_file_encoding="utf-8",
        extra="forbid",
    )
    app_name: str = Field(default="Government Policy Assistant", min_length=1, max_length=100)
    environment: Literal["development", "test"] = "development"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("cors_origins")
    @classmethod
    def local_origins_only(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("At least one explicit local origin is required")
        for origin in origins:
            parsed = urlsplit(origin)
            if (parsed.scheme != "http" or parsed.hostname not in {"localhost", "127.0.0.1"}
                    or parsed.username or parsed.password or parsed.path or parsed.query
                    or parsed.fragment or parsed.port is None):
                raise ValueError("CORS origins must be loopback HTTP origins with explicit ports")
        return list(dict.fromkeys(origins))
