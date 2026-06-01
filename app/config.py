import os
from typing import List
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    GEMINI_API_KEY: str = Field(default="")
    DATABASE_URL: str = Field(default="")
    ALLOWED_ORIGINS: str = Field(default="")
    GEMINI_MODEL: str = Field(default="gemini-2.5-pro")
    GEMINI_TIMEOUT_SECONDS: int = Field(default=60)
    CACHE_TTL_SECONDS: int = Field(default=86400)

    # Allow loading from a local .env file
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def allowed_origins_list(self) -> List[str]:
        if not self.ALLOWED_ORIGINS:
            return []
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",") if origin.strip()]

    @field_validator("GEMINI_API_KEY")
    @classmethod
    def validate_gemini_api_key(cls, v: str) -> str:
        val = v.strip() if v else ""
        if not val:
            raise ValueError("GEMINI_API_KEY environment variable is missing or empty.")
        return val

    @field_validator("DATABASE_URL")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        val = v.strip() if v else ""
        if not val:
            raise ValueError("DATABASE_URL environment variable is missing or empty.")
        if not (val.startswith("postgresql://") or val.startswith("postgresql+asyncpg://")):
            raise ValueError("DATABASE_URL must be a valid PostgreSQL connection string.")
        # Ensure we always use the asyncpg driver
        if val.startswith("postgresql://"):
            val = val.replace("postgresql://", "postgresql+asyncpg://", 1)
        return val

    @field_validator("ALLOWED_ORIGINS")
    @classmethod
    def validate_allowed_origins(cls, v: str) -> str:
        val = v.strip() if v else ""
        if not val:
            raise ValueError("ALLOWED_ORIGINS environment variable is missing or empty.")
        return val

# Instantiate settings to trigger validation on startup
try:
    settings = Settings()
except Exception as e:
    import sys
    print(f"CRITICAL: Application startup failed due to missing or invalid environment variables.", file=sys.stderr)
    print(f"ERROR DETAILS: {e}", file=sys.stderr)
    sys.exit(1)
