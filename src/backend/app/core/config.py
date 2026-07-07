"""Application settings and configuration loaded from environment variables."""

import logging
import sys
from typing import List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


class Settings(BaseSettings):
    """Core application settings with strict startup validation."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Required variables per specifications
    DATABASE_URL: str = Field(
        ..., description="Database connection URL (e.g. sqlite:///./app.db)"
    )
    JWT_SECRET: str = Field(
        ..., description="Secret key for JWT encoding and decoding"
    )
    GEMINI_API_KEY: str = Field(..., description="Google Gemini API key")

    # Optional variables
    ALLOWED_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS allowed origins",
    )
    UPLOAD_DIR: str = Field(
        default="uploads", description="Directory for storing uploaded files"
    )
    JWT_EXPIRE_MINUTES: int = Field(
        default=10080,
        description="JWT expiration time in minutes (default 7 days)",
    )
    AUTH_COOKIE_NAME: str = Field(
        default="agy_session", description="Name of the HttpOnly auth cookie"
    )
    AUTH_COOKIE_SECURE: bool = Field(
        default=False, description="Whether auth cookie requires HTTPS"
    )
    CHROMA_PERSIST_DIR: str = Field(
        default="data/chroma", description="ChromaDB persistent directory"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="ai_course_chunks", description="ChromaDB collection name"
    )


    @field_validator("DATABASE_URL", "JWT_SECRET", "GEMINI_API_KEY", mode="before")
    @classmethod
    def validate_required_not_empty(cls, value: str, info) -> str:
        if value is None or not str(value).strip():
            raise ValueError(
                f"Required environment variable '{info.field_name}' cannot be missing or empty!"
            )
        return str(value).strip()

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def parse_allowed_origins(cls, value: Union[List[str], str]) -> List[str]:
        if isinstance(value, str):
            import json

            try:
                parsed = json.loads(value)
                if isinstance(parsed, list):
                    return [str(item).strip() for item in parsed]
            except Exception:
                return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


try:
    settings = Settings()
    logger.info("Configuration loaded successfully.")
except Exception as e:
    logger.critical(
        "FATAL: Configuration validation failed at startup! Missing or invalid required environment variables."
    )
    logger.critical("Error details: %s", e)
    # Crash on missing required vars per acceptance criteria
    sys.exit(1)
