"""
Core configuration, paths, and utility functions.
"""
import os
import re
import uuid
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

_CONFIG_FILE = Path(__file__).resolve()
_BACKEND_DIR = _CONFIG_FILE.parents[1]
_SRC_DIR = _CONFIG_FILE.parents[2]
_ROOT_DIR = _CONFIG_FILE.parents[3]
_ENV_CANDIDATES = [
    Path.cwd() / ".env",
    Path.cwd() / "api_key.env",
    _BACKEND_DIR / ".env",
    _BACKEND_DIR / "api_key.env",
    _SRC_DIR / ".env",
    _SRC_DIR / "api_key.env",
    _ROOT_DIR / ".env",
    _ROOT_DIR / "api_key.env",
]

for env_path in _ENV_CANDIDATES:
    if env_path.exists():
        load_dotenv(env_path, override=False)

_GOOGLE_API_KEY = (
    os.getenv("GOOGLE_API_KEY")
    or os.getenv("GEMINI_API_KEY")
    or os.getenv("LLM_API_KEY")
)

if _GOOGLE_API_KEY and not os.getenv("GOOGLE_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = _GOOGLE_API_KEY

# ─── Directory Constants ───────────────────────────────────────────────────────

APP_ENV = os.getenv("APP_ENV", os.getenv("ENVIRONMENT", "development")).strip().lower() or "development"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")

STORAGE_PROVIDER = os.getenv("STORAGE_PROVIDER", "local").strip().lower() or "local"
JOB_QUEUE_PROVIDER = os.getenv("JOB_QUEUE_PROVIDER", "inline").strip().lower() or "inline"
CACHE_PROVIDER = os.getenv("CACHE_PROVIDER", "local").strip().lower() or "local"
DOCUMENT_CACHE_ENABLED = os.getenv("DOCUMENT_CACHE_ENABLED", "true").lower() in {"1", "true", "yes", "on"}

DATA_DIR = os.getenv("DATA_DIR", "data")
CACHE_DIR = os.getenv("LOCAL_CACHE_DIR", "cache")
INDEX_DIR = os.getenv("LOCAL_INDEX_DIR", "indices")
LOCAL_UPLOAD_DIR = os.getenv("LOCAL_UPLOAD_DIR", "uploads")
LOCAL_OUTPUT_DIR = os.getenv("LOCAL_OUTPUT_DIR", "")

UPLOAD_DIR = LOCAL_UPLOAD_DIR
_OUTPUT_BASE = LOCAL_OUTPUT_DIR.strip()


def _output_dir(name: str) -> str:
    return os.path.join(_OUTPUT_BASE, name) if _OUTPUT_BASE else name


QUESTIONS_DIR = _output_dir("questions")
BOOKS_DIR = _output_dir("books")
SLIDES_DIR = _output_dir("slides")
VIDEOS_DIR = _output_dir("videos")
MINDMAPS_DIR = _output_dir("mindmaps")
FLASHCARDS_DIR = _output_dir("flashcards")

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DATA_DIR, 'users.db')}")

for d in [UPLOAD_DIR, DATA_DIR, INDEX_DIR, QUESTIONS_DIR, CACHE_DIR, BOOKS_DIR, SLIDES_DIR, VIDEOS_DIR, MINDMAPS_DIR, FLASHCARDS_DIR]:
    os.makedirs(d, exist_ok=True)

logger.info(
    "Runtime providers: env=%s storage=%s queue=%s cache=%s upload_dir=%s output_base=%s database=%s",
    APP_ENV,
    STORAGE_PROVIDER,
    JOB_QUEUE_PROVIDER,
    CACHE_PROVIDER,
    os.path.abspath(UPLOAD_DIR),
    os.path.abspath(LOCAL_OUTPUT_DIR) if LOCAL_OUTPUT_DIR else "legacy-output-dirs",
    DATABASE_URL.split("@")[-1] if "@" in DATABASE_URL else DATABASE_URL,
)

# ─── Cache Configuration ──────────────────────────────────────────────────────

HASH_CACHE_PATH = os.path.join(CACHE_DIR, "file_cache.json")

# Vector DB provider configuration. Chroma is the mandatory local/dev provider for the hackathon demo.
VECTOR_DB_PROVIDER = os.getenv("VECTOR_DB_PROVIDER", "chroma").strip().lower() or "chroma"
FUTURE_VECTOR_DB_PROVIDERS = {"milvus", "qdrant", "pgvector"}
if VECTOR_DB_PROVIDER in {"simple_dev_only", "faiss"}:
    logger.warning(
        "VECTOR_DB_PROVIDER=%s is not a supported local/dev demo provider. Using mandatory Chroma.",
        VECTOR_DB_PROVIDER,
    )
    VECTOR_DB_PROVIDER = "chroma"
elif VECTOR_DB_PROVIDER not in {"chroma", *FUTURE_VECTOR_DB_PROVIDERS}:
    logger.warning("Unknown VECTOR_DB_PROVIDER=%s. Falling back to mandatory Chroma.", VECTOR_DB_PROVIDER)
    VECTOR_DB_PROVIDER = "chroma"

CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIR", os.path.join(DATA_DIR, "chroma"))
CHROMA_COLLECTION_NAME = os.getenv("CHROMA_COLLECTION_NAME", "ai_course_chunks")
SIMPLE_VECTOR_DIR = os.getenv("SIMPLE_VECTOR_DIR", os.path.join(DATA_DIR, "simple_vectors"))

MILVUS_HOST = os.getenv("MILVUS_HOST", "localhost")
MILVUS_PORT = int(os.getenv("MILVUS_PORT", "19530"))
MILVUS_COLLECTION_NAME = os.getenv("MILVUS_COLLECTION_NAME", "ai_course_chunks")

os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
logger.info("Vector DB provider: %s", VECTOR_DB_PROVIDER)
if VECTOR_DB_PROVIDER == "chroma":
    logger.info(
        "Chroma Vector DB: persist_dir=%s collection=%s",
        os.path.abspath(CHROMA_PERSIST_DIR),
        CHROMA_COLLECTION_NAME,
    )
elif VECTOR_DB_PROVIDER in FUTURE_VECTOR_DB_PROVIDERS:
    logger.warning(
        "VECTOR_DB_PROVIDER=%s is reserved for future production use and is not implemented for local/dev. "
        "Use VECTOR_DB_PROVIDER=chroma for the hackathon demo.",
        VECTOR_DB_PROVIDER,
    )

# ─── Model Configuration ───────────────────────────────────────────────────────

DEFAULT_MAX_CACHED_COURSES = int(os.getenv("MAX_CACHED_COURSES", "20"))
DOCUMENT_CHUNK_SIZE = int(os.getenv("DOCUMENT_CHUNK_SIZE", "1800"))
DOCUMENT_CHUNK_OVERLAP = int(os.getenv("DOCUMENT_CHUNK_OVERLAP", "120"))
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "64"))
EMBEDDING_BATCH_DELAY = float(os.getenv("EMBEDDING_BATCH_DELAY", "0"))
EMBEDDING_MAX_RETRIES = int(os.getenv("EMBEDDING_MAX_RETRIES", "3"))
MAX_RETRY_DELAY = float(os.getenv("EMBEDDING_MAX_RETRY_DELAY", "60"))
EMBEDDING_REQUESTS_PER_MINUTE = int(os.getenv("EMBEDDING_REQUESTS_PER_MINUTE", "72"))
EMBEDDING_CACHE_DIR = os.getenv(
    "EMBEDDING_CACHE_DIR",
    os.path.join(CACHE_DIR, "chunk_embeddings"),
)
BATCH_SIZE = EMBEDDING_BATCH_SIZE
RETRY_DELAY = EMBEDDING_BATCH_DELAY

os.makedirs(EMBEDDING_CACHE_DIR, exist_ok=True)


def _normalize_embedding_model(model_name: Optional[str]) -> str:
    """Normalize Gemini embedding model names for LangChain batch embeddings."""
    model = (model_name or "models/embedding-001").strip()
    if model in {"gemini-embedding-2", "models/gemini-embedding-2"}:
        logger.warning(
            "EMBEDDING_MODEL=%s is not compatible with current LangChain batch "
            "embedding flow. Falling back to models/embedding-001.",
            model,
        )
        return "models/embedding-001"
    if not model.startswith("models/"):
        model = f"models/{model}"
    return model


EMBEDDING_MODEL = _normalize_embedding_model(
    os.getenv("GEMINI_EMBEDDING_MODEL") or os.getenv("EMBEDDING_MODEL")
)
LLM_MODEL = os.getenv("GEMINI_FAST_MODEL") or os.getenv("LLM_MODEL", "gemini-2.5-flash")


SAFE_DEFAULT_MODEL = "gemini-2.5-flash"

MODEL_TASK_ENV_MAP = {
    "book": "GEMINI_BOOK_MODEL",
    "slide": "GEMINI_SLIDE_MODEL",
    "slides": "GEMINI_SLIDE_MODEL",
    "video": "GEMINI_VIDEO_MODEL",
    "vid": "GEMINI_VIDEO_MODEL",
    "quality": "GEMINI_QUALITY_MODEL",
    "evaluation": "GEMINI_QUALITY_MODEL",
    "course": "GEMINI_COURSE_MODEL",
    "mindmap": "GEMINI_MINDMAP_MODEL",
    "quiz": "GEMINI_QUIZ_MODEL",
    "flashcard": "GEMINI_FLASHCARD_MODEL",
    "flashcards": "GEMINI_FLASHCARD_MODEL",
    "summary": "GEMINI_SUMMARY_MODEL",
    "high_yield": "GEMINI_SUMMARY_MODEL",
    "fast": "GEMINI_FAST_MODEL",
    "helper": "GEMINI_FAST_MODEL",
}


def get_model_name(task: str = "default") -> str:
    """Get the appropriate Gemini model for the given generation task.

    Fallback chain: task-specific env var -> GEMINI_DEFAULT_MODEL ->
    GEMINI_FAST_MODEL -> SAFE_DEFAULT_MODEL (logged as a warning, since it
    means no routing env var was configured at all).
    """
    fast_fallback = (os.getenv("GEMINI_FAST_MODEL") or os.getenv("LLM_MODEL") or "").strip()
    default_fallback = (os.getenv("GEMINI_DEFAULT_MODEL") or "").strip()

    env_var = MODEL_TASK_ENV_MAP.get(task.lower().strip())
    if env_var:
        val = os.getenv(env_var)
        if val and val.strip():
            return val.strip()

    if default_fallback:
        return default_fallback
    if fast_fallback:
        return fast_fallback

    logger.warning(
        "[ModelRouting] No model configured for task '%s' (no task env var, "
        "GEMINI_DEFAULT_MODEL, or GEMINI_FAST_MODEL set). Falling back to safe "
        "default '%s'.",
        task,
        SAFE_DEFAULT_MODEL,
    )
    return SAFE_DEFAULT_MODEL


def generate_course_id() -> str:
    """Generate a short unique course ID."""
    return uuid.uuid4().hex[:12]


def get_course_path(course_id: str) -> Dict[str, str]:
    """Get all file paths for a course."""
    return {
        "faiss_meta": os.path.join(INDEX_DIR, f"faiss_{course_id}.json"),
        "chroma_meta": os.path.join(INDEX_DIR, f"chroma_{course_id}.json"),
        "vector_meta": os.path.join(INDEX_DIR, f"{VECTOR_DB_PROVIDER}_{course_id}.json"),
        "questions": os.path.join(QUESTIONS_DIR, f"course_{course_id}_questions.json"),
        "questions_pdf": os.path.join(QUESTIONS_DIR, f"course_{course_id}_quiz.pdf"),
        "meta": os.path.join(QUESTIONS_DIR, f"course_{course_id}_meta.json"),
        "book": os.path.join(BOOKS_DIR, f"course_{course_id}_book.json"),
        "book_pdf": os.path.join(BOOKS_DIR, f"course_{course_id}_book.pdf"),
        "slides": os.path.join(SLIDES_DIR, f"course_{course_id}_slides.json"),
        "slides_pdf": os.path.join(SLIDES_DIR, f"course_{course_id}_slides.pdf"),
        "slides_pptx": os.path.join(SLIDES_DIR, f"course_{course_id}_slides.pptx"),
        "questions_key_pdf": os.path.join(QUESTIONS_DIR, f"course_{course_id}_answer_key.pdf"),
        "videos": os.path.join(VIDEOS_DIR, f"course_{course_id}"),
        "mindmap": os.path.join(MINDMAPS_DIR, f"course_{course_id}_mindmap.json"),
        "flashcards": os.path.join(FLASHCARDS_DIR, f"course_{course_id}_flashcards.json"),
    }


# ─── Embedding / LLM Factory ──────────────────────────────────────────────────

def get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Get Gemini embeddings instance."""
    api_key = _require_google_api_key()
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL, google_api_key=api_key)


def get_llm(temperature: float = 0.1, max_output_tokens: int = 8192, task: str = "default") -> ChatGoogleGenerativeAI:
    """Get Gemini LLM instance routed by task."""
    api_key = _require_google_api_key()
    model_name = get_model_name(task)
    logger.info("[ModelRouting] Task '%s' -> using model: %s", task, model_name)
    return ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=temperature,
        max_output_tokens=max_output_tokens,
    )


def _require_google_api_key() -> str:
    """Return configured Gemini API key or raise an actionable error."""
    api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY") or _GOOGLE_API_KEY
    if not api_key:
        raise RuntimeError(
            "Missing Gemini API key. Set GOOGLE_API_KEY in your shell or in one of: "
            ".env, api_key.env, src/api_key.env, src/backend/.env. "
            "Legacy aliases GEMINI_API_KEY and LLM_API_KEY are also accepted."
        )
    return api_key


# ─── Utility Functions ─────────────────────────────────────────────────────────

def format_docs(docs: List[Document]) -> str:
    """Format documents for prompt context."""
    return "\n\n".join(doc.page_content for doc in docs)


def extract_json(text: Any) -> str:
    """Extract JSON array/object from LLM text output."""
    text_str = str(text)
    # Remove markdown code fences
    text_str = re.sub(r'```json|```', '', text_str, flags=re.IGNORECASE).strip()
    # Grab the first outermost [...] or {...} block
    match = re.search(r"(\[.*\]|\{.*\})", text_str, re.DOTALL)
    if match:
        return match.group(1).strip()
    return "[]"


def sanitize_filename(name: str) -> str:
    """Convert string to safe filename."""
    import unidecode
    name = unidecode.unidecode(name)
    name = re.sub(r'\s+', '_', name.lower().strip())
    name = re.sub(r'[^\w\s\-]', '', name)
    return name if name else "general_topic"


def get_cache_key(content: str) -> str:
    """Generate MD5 cache key from content."""
    return hashlib.md5(content.encode()).hexdigest()


def sanitize_input(text: str) -> str:
    """Sanitize user input to prevent injection attacks."""
    if not isinstance(text, str):
        return str(text)
    text = "".join(ch for ch in text if ch.isprintable() or ch == "\n")
    text = text.strip()
    return text


def _timestamp() -> str:
    """Get formatted timestamp for logging."""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
