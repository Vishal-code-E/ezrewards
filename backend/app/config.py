# backend/app/config.py

from pydantic import field_validator
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Supabase
    SUPABASE_URL: str
    SUPABASE_JWT_SECRET: str
    SUPABASE_SERVICE_ROLE_KEY: str
    DATABASE_URL: str

    # App
    ENVIRONMENT: str = "development"
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    ANTHROPIC_API_KEY: str

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        """
        Handles both formats from .env:
          CORS_ORIGINS=http://localhost:3000
          CORS_ORIGINS=["http://localhost:3000","https://example.com"]
        """
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            v = v.strip()
            if v.startswith("["):
                import json
                return json.loads(v)
            # Comma-separated plain string
            return [origin.strip() for origin in v.split(",")]
        return v

    class Config:
        env_file = ".env"


settings = Settings()
