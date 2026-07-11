"""Application settings and configuration loaded from environment variables."""

import logging
import sys
from pathlib import Path
from typing import List, Union
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger("api")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Single source of truth: the .env at the project root, regardless of the process cwd.
# (config.py -> core -> app -> backend -> src -> project root)
_ROOT_ENV_FILE = str(Path(__file__).resolve().parents[4] / ".env")


class Settings(BaseSettings):
    """Core application settings with strict startup validation."""

    model_config = SettingsConfigDict(
        env_file=_ROOT_ENV_FILE,
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

    # Optional per-feature API keys — each generation feature (Book/Slide/Quiz/Vid) can use
    # its own Gemini key (e.g. to spread usage across separate free-tier quotas). Falls back
    # to GEMINI_API_KEY when left empty.
    GEMINI_BOOK_API_KEY: str = Field(default="", description="Gemini API key for Book generation (falls back to GEMINI_API_KEY)")
    GEMINI_SLIDE_API_KEY: str = Field(default="", description="Gemini API key for Slide generation (falls back to GEMINI_API_KEY)")
    GEMINI_QUIZ_API_KEY: str = Field(default="", description="Gemini API key for Quiz generation (falls back to GEMINI_API_KEY)")
    GEMINI_VID_API_KEY: str = Field(default="", description="Gemini API key for Video generation (falls back to GEMINI_API_KEY)")

    # Optional automatic fallback when Gemini fails/hits quota — Gemini stays the primary
    # (free) provider for every feature; OpenRouter only kicks in as a last resort inside
    # LLMService._call_gemini_strict. Blank = no-op, behavior unchanged.
    OPENROUTER_API_KEY: str = Field(default="", description="OpenRouter API key, used only as a Gemini fallback")
    OPENROUTER_MODEL: str = Field(default="openai/gpt-4o-mini", description="OpenRouter model slug for the fallback")

    # Model routing — mirrors the GEMINI_{FEATURE}_API_KEY pattern above. Each feature
    # falls back to GEMINI_DEFAULT_MODEL when left blank (see LLMService.__init__ and
    # generation.py::get_generator / document_processor.py::_generate_course_title).
    GEMINI_DEFAULT_MODEL: str = Field(default="gemini-2.5-flash", description="Model used when a feature has no override")
    GEMINI_BOOK_MODEL: str = Field(default="", description="Model for Book generation (falls back to GEMINI_DEFAULT_MODEL)")
    GEMINI_SLIDE_MODEL: str = Field(default="", description="Model for Slide generation (falls back to GEMINI_DEFAULT_MODEL)")
    GEMINI_QUIZ_MODEL: str = Field(default="", description="Model for Quiz generation (falls back to GEMINI_DEFAULT_MODEL)")
    GEMINI_VIDEO_MODEL: str = Field(default="", description="Model for Vid generation (falls back to GEMINI_DEFAULT_MODEL)")
    GEMINI_COURSE_MODEL: str = Field(default="", description="Model for course-title generation (falls back to GEMINI_DEFAULT_MODEL)")

    # Optional variables
    ALLOWED_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="CORS allowed origins",
    )
    UPLOAD_DIR: str = Field(
        default="uploads", description="Directory for storing uploaded files"
    )
    OUTPUT_DIR: str = Field(
        default="outputs", description="Directory for storing generated outputs"
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

    # Email verification / password reset — sent via Resend. Left blank by default
    # (unlike GEMINI_API_KEY) so a fresh checkout without Resend set up still boots;
    # attempting to actually send an email with these unset fails loudly at call time
    # instead of crashing the whole app over a feature not yet configured.
    RESEND_API_KEY: str = Field(default="", description="Resend API key for transactional email")
    EMAIL_FROM_ADDRESS: str = Field(
        default="", description="Verified sender, e.g. 'HackaGen <no-reply@yourdomain>'"
    )
    EMAIL_DEV_FALLBACK: bool = Field(
        default=False,
        description=(
            "When true AND RESEND_API_KEY is unset, log OTP codes to the server console "
            "instead of failing — local/dev testing convenience only. Never enable in "
            "production: it lets register/reset-password 'succeed' with nobody actually "
            "receiving the code."
        ),
    )
    EMAIL_OTP_EXPIRE_MINUTES: int = Field(default=10, description="OTP code validity window")
    EMAIL_OTP_MAX_ATTEMPTS: int = Field(default=5, description="Max wrong-code guesses before an OTP is locked")
    EMAIL_OTP_RESEND_COOLDOWN_SECONDS: int = Field(
        default=60, description="Minimum seconds between two OTP sends for the same purpose"
    )

    # Default admin bootstrap — idempotent, runs once at startup if enabled.
    CREATE_DEFAULT_ADMIN: bool = Field(default=False, description="Seed a default admin user at startup")
    ADMIN_EMAIL: str = Field(default="", description="Email for the seeded default admin")
    ADMIN_PASSWORD: str = Field(default="", description="Password for the seeded default admin")
    CHROMA_PERSIST_DIR: str = Field(
        default="data/chroma", description="ChromaDB persistent directory"
    )
    CHROMA_COLLECTION_NAME: str = Field(
        default="ai_course_chunks", description="ChromaDB collection name"
    )

    # Embedding provider — routes chunk/query embedding through Gemini instead of Chroma's
    # default English-centric local model, since content/queries here are Vietnamese.
    EMBEDDING_PROVIDER: str = Field(default="gemini", description="Embedding provider: 'gemini' or 'default' (Chroma's bundled MiniLM)")
    GEMINI_EMBEDDING_MODEL: str = Field(default="gemini-embedding-001", description="Gemini embedding model name")
    EMBEDDING_BATCH_SIZE: int = Field(default=32, description="Chunks per embed_content batch call")
    EMBEDDING_BATCH_DELAY: float = Field(default=0, description="Seconds to sleep between embedding batches")
    EMBEDDING_MAX_RETRIES: int = Field(default=3, description="Max retries per embedding batch on failure")
    EMBEDDING_MAX_RETRY_DELAY: float = Field(default=60, description="Max backoff delay (seconds) between embedding retries")
    EMBEDDING_REQUESTS_PER_MINUTE: int = Field(default=72, description="Client-side rate limit for embedding API calls")
    EMBEDDING_CACHE_DIR: str = Field(default="cache/chunk_embeddings", description="Directory for content-hash embedding cache")

    # Document chunking tuning
    DOCUMENT_CHUNK_SIZE: int = Field(default=1800, description="Target chunk size in characters")
    DOCUMENT_CHUNK_OVERLAP: int = Field(default=120, description="Overlap in characters between consecutive chunks")

    # OCR fallback for scanned PDF pages (rendered page image -> Gemini vision text extraction)
    PDF_ENABLE_OCR: bool = Field(default=True, description="Enable OCR fallback for low-text (scanned) PDF pages")
    PDF_OCR_MAX_PAGES: int = Field(default=12, description="Hard cap on number of pages OCR'd per document")
    PDF_OCR_DPI: int = Field(default=120, description="DPI used when rendering a scanned page to an image for OCR")
    PDF_TEXT_MIN_CHARS_PER_PAGE: int = Field(default=50, description="Below this many extracted chars, a page is considered a scan candidate")
    PDF_SCAN_SAMPLE_PAGES: int = Field(default=12, description="Number of pages sampled to decide whether a document is scanned")


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

    @model_validator(mode="after")
    def validate_admin_bootstrap(self) -> "Settings":
        if self.CREATE_DEFAULT_ADMIN and (not self.ADMIN_EMAIL.strip() or not self.ADMIN_PASSWORD.strip()):
            raise ValueError(
                "CREATE_DEFAULT_ADMIN=true requires ADMIN_EMAIL and ADMIN_PASSWORD to also be set"
            )
        return self


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
