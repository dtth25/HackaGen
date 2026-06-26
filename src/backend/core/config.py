"""
Core configuration, paths, and utility functions.
"""
import os
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
import re
import uuid
import hashlib
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_community.chat_models import ChatOpenAI
from langchain_community.embeddings import OpenAIEmbeddings

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

UPLOAD_DIR = "uploads"
INDEX_DIR = "indices"
QUESTIONS_DIR = "questions"
CACHE_DIR = "cache"
BOOKS_DIR = "books"
SLIDES_DIR = "slides"
VIDEOS_DIR = "videos"

for d in [UPLOAD_DIR, INDEX_DIR, QUESTIONS_DIR, CACHE_DIR, BOOKS_DIR, SLIDES_DIR, VIDEOS_DIR]:
    os.makedirs(d, exist_ok=True)

# ─── Vector DB Configuration ───────────────────────────────────────────────────
# Vector DB: FAISS (disk-based, no Docker).

# ─── Model Configuration ───────────────────────────────────────────────────────

DEFAULT_MAX_CACHED_COURSES = int(os.getenv("MAX_CACHED_COURSES", "20"))
BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "60"))
RETRY_DELAY = int(os.getenv("EMBEDDING_BATCH_DELAY", "2"))
MAX_RETRY_DELAY = int(os.getenv("EMBEDDING_MAX_RETRY_DELAY", "60"))


def _normalize_embedding_model(model_name: Optional[str]) -> str:
    """Normalize embedding model name."""
    return (model_name or "baai/bge-m3").strip()


EMBEDDING_MODEL = _normalize_embedding_model(os.getenv("EMBEDDING_MODEL"))
LLM_MODEL = os.getenv("LLM_MODEL", "minimaxai/minimax-m2.7")

# ─── Path Helpers ──────────────────────────────────────────────────────────────

def generate_course_id() -> str:
    """Generate a short unique course ID."""
    return uuid.uuid4().hex[:12]


def get_course_path(course_id: str) -> Dict[str, str]:
    """Get all file paths for a course."""
    return {
        "faiss_meta": os.path.join(INDEX_DIR, f"faiss_{course_id}.json"),
        "questions": os.path.join(QUESTIONS_DIR, f"course_{course_id}_questions.json"),
        "questions_pdf": os.path.join(QUESTIONS_DIR, f"course_{course_id}_quiz.pdf"),
        "meta": os.path.join(QUESTIONS_DIR, f"course_{course_id}_meta.json"),
        "book": os.path.join(BOOKS_DIR, f"course_{course_id}_book.json"),
        "book_pdf": os.path.join(BOOKS_DIR, f"course_{course_id}_book.pdf"),
        "slides": os.path.join(SLIDES_DIR, f"course_{course_id}_slides.json"),
        "slides_pdf": os.path.join(SLIDES_DIR, f"course_{course_id}_slides.pdf"),
        "videos": os.path.join(VIDEOS_DIR, f"course_{course_id}"),
    }


# ─── Embedding / LLM Factory ──────────────────────────────────────────────────

from langchain_core.embeddings import Embeddings
from openai import OpenAI

class NvidiaEmbeddings(Embeddings):
    """Custom wrapper for NVIDIA NIM Embeddings to avoid client-side tokenization issues."""
    def __init__(self, model: str, api_key: str, base_url: str):
        self.model = model
        max_retries = int(os.getenv("LLM_MAX_RETRIES", "8"))
        self.client = OpenAI(api_key=api_key, base_url=base_url, max_retries=max_retries)

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        response = self.client.embeddings.create(
            input=texts,
            model=self.model
        )
        return [data.embedding for data in response.data]

    def embed_query(self, text: str) -> List[float]:
        response = self.client.embeddings.create(
            input=[text],
            model=self.model
        )
        return response.data[0].embedding


def get_embeddings() -> Embeddings:
    """Get NVIDIA NIM embeddings instance."""
    api_key = _require_nvidia_api_key()
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    return NvidiaEmbeddings(
        model=EMBEDDING_MODEL,
        api_key=api_key,
        base_url=base_url
    )


def get_llm(temperature: float = 0.1, max_output_tokens: int = 8192) -> ChatOpenAI:
    """Get NVIDIA NIM LLM instance."""
    api_key = _require_nvidia_api_key()
    base_url = os.getenv("NVIDIA_BASE_URL", "https://integrate.api.nvidia.com/v1")
    max_retries = int(os.getenv("LLM_MAX_RETRIES", "8"))
    return ChatOpenAI(
        model=LLM_MODEL,
        openai_api_key=api_key,
        openai_api_base=base_url,
        temperature=temperature,
        max_tokens=max_output_tokens,
        max_retries=max_retries,
    )



def _require_nvidia_api_key() -> str:
    """Return configured NVIDIA API key or raise an actionable error."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        raise RuntimeError(
            "Missing NVIDIA API key. Set NVIDIA_API_KEY in your shell or in .env."
        )
    return api_key


# ─── Utility Functions ─────────────────────────────────────────────────────────

def format_docs(docs: List[Document]) -> str:
    """Format documents for prompt context."""
    return "\n\n".join(doc.page_content for doc in docs)


def repair_json_quotes_and_commas(s: str) -> str:
    """Repair trailing commas and unescaped quotes inside JSON strings."""
    n = len(s)
    out = []
    in_string = False
    stack = []  # Keep track of 'object' or 'array' context
    i = 0
    
    while i < n:
        c = s[i]
        if not in_string:
            if c == '{':
                stack.append('object')
                out.append(c)
                i += 1
            elif c == '}':
                if stack and stack[-1] == 'object':
                    stack.pop()
                out.append(c)
                i += 1
            elif c == '[':
                stack.append('array')
                out.append(c)
                i += 1
            elif c == ']':
                if stack and stack[-1] == 'array':
                    stack.pop()
                out.append(c)
                i += 1
            elif c == '"':
                in_string = True
                out.append(c)
                i += 1
            elif c == ',':
                # Check for trailing comma
                j = i + 1
                while j < n and s[j].isspace():
                    j += 1
                if j < n and s[j] in ('}', ']'):
                    # Trailing comma: skip it
                    i = j
                    continue
                out.append(c)
                i += 1
            else:
                out.append(c)
                i += 1
        else:
            if c == '\\':
                # Escape sequence - append backslash and the next character
                if i + 1 < n:
                    out.append(s[i:i+2])
                    i += 2
                else:
                    out.append(c)
                    i += 1
            elif c == '"':
                # Check if this quote closes the string
                # Find next non-whitespace
                j = i + 1
                while j < n and s[j].isspace():
                    j += 1
                
                is_closing = False
                if j == n:
                    is_closing = True
                elif s[j] in ('}', ']'):
                    is_closing = True
                elif s[j] == ':':
                    is_closing = True
                elif s[j] == ',':
                    # Look ahead after comma
                    k = j + 1
                    while k < n and s[k].isspace():
                        k += 1
                    if k == n or s[k] in ('}', ']'):
                        is_closing = True
                    elif s[k] == '"':
                        # We see a quote after comma.
                        # Is it a key of an object or an element of an array?
                        current_context = stack[-1] if stack else 'object'
                        if current_context == 'array':
                            # In an array, elements are just values, so this is a closing quote
                            is_closing = True
                        else:
                            # In an object, the next string must be a key, so it must be followed by ':'
                            # Let's find the closing quote of this potential key
                            key_close = k + 1
                            found_close = False
                            while key_close < n:
                                if s[key_close] == '\\':
                                    key_close += 2
                                elif s[key_close] == '"':
                                    found_close = True
                                    break
                                else:
                                    key_close += 1
                            
                            if found_close:
                                # Now check if the next non-whitespace character after the closing quote is ':'
                                next_after_key = key_close + 1
                                while next_after_key < n and s[next_after_key].isspace():
                                    next_after_key += 1
                                if next_after_key < n and s[next_after_key] == ':':
                                    is_closing = True
                
                if is_closing:
                    in_string = False
                    out.append(c)
                    i += 1
                else:
                    # Escape the quote
                    out.append('\\"')
                    i += 1
            else:
                out.append(c)
                i += 1
                
    return "".join(out)


def extract_json(text: Any) -> str:
    """Extract JSON array/object from LLM text output."""
    text_str = str(text).strip()
    # Grab the first outermost [...] or {...} block
    match = re.search(r"(\[.*\]|\{.*\})", text_str, re.DOTALL)
    if match:
        extracted = match.group(1).strip()
        
        # 1. Sửa lỗi dấu gạch chéo ngược lẻ trước dấu ngoặc kép đóng (escape quote ngoài ý muốn)
        odd_backslash_pattern = r'(?<!\\)\\(?:\\\\)*"\s*(?=[,}\]])'
        def fix_backslash(m):
            matched = m.group(0)
            quote_idx = matched.find('"')
            backslashes = matched[:quote_idx]
            rest = matched[quote_idx:]
            return backslashes + '\\' + rest
        
        extracted = re.sub(odd_backslash_pattern, fix_backslash, extracted)

        # 2. Sửa lỗi dấu nháy kép chưa được escape và dấu phẩy thừa (trailing comma)
        extracted = repair_json_quotes_and_commas(extracted)

        # 3. Sửa lỗi thoát (escape) ký tự backslash không hợp lệ (ví dụ trong công thức LaTeX \sum, \in)
        # Chỉ coi b, f, n, r, t là ký tự thoát JSON hợp lệ nếu chúng KHÔNG được theo sau bởi tên lệnh LaTeX bắt đầu bằng ký tự đó
        pattern = r'(?<!\\)\\(?!"|\\|/|b(?!eta|ar|egin|oldsymbol|mod)|f(?!rac|orall)|n(?!eq|otin|abla)|r(?!ightarrow|ho|ight)|t(?!o|au|heta|ilde|ext|imes)|u[0-9a-fA-F]{4})'
        return re.sub(pattern, r'\\\\', extracted)
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
