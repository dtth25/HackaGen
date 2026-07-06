"""
Shared Context Cleaner, Chunk Classifier, and Quality Gate for AI Course Generator.
Eliminates debug/RAG markers, TOC noise, dot leaders, broken spacing, and classifies chunks.
"""
import re
from typing import Any, Dict, List, Optional, Tuple

VIETNAMESE_SPACING_FIXES = {
    "vềPython": "về Python",
    "Trí tuệNhân": "Trí tuệ Nhân",
    "dữliệu": "dữ liệu",
    "sửdụng": "sử dụng",
    "từmột": "từ một",
    "ngônngữ": "ngôn ngữ",
    "dựán": "dự án",
    "khôngcó": "không có",
    "biến thểchính": "biến thể chính",
    "tham sốkhác": "tham số khác",
    "Ví dụmã": "Ví dụ mã",
    "ĐộChính": "Độ Chính",
    "DựĐoán": "Dự Đoán",
    "Siêu Tham Số": "Siêu tham số",
    "mat- plotlib": "matplotlib",
    "Ví ụd": "Ví dụ",
    "ếkt ợhp": "kết hợp",
    "ạTo": "Tạo",
}

BAD_ARTIFACT_PATTERNS = [
    r"===\s*BẮT ĐẦU DỮ LIỆU TRUY XUẤT.*?===",
    r"===\s*KẾT THÚC DỮ LIỆU.*?===",
    r"\[MÃ ĐỊNH DANH TRANG:\s*\d+\]",
    r"\bNỘI DUNG:\s*",
    r"\bMã định danh trang\s+\d+\s+nội dung\b",
    r"(?:\.\s*){3,}",  # dot leaders like . . . . .
]

BROKEN_HEADINGS = {"contents", "table of contents", "mục lục", "ý chính", "ghi nhớ ý chính"}

# Banned template phrases must never reach user-facing output, even embedded
# mid-sentence (BROKEN_HEADINGS only drops whole lines). Ordered longest-first.
BANNED_PHRASE_REPLACEMENTS = [
    ("Ghi nhớ ý chính", "Ghi nhớ nội dung trọng tâm"),
    ("ghi nhớ ý chính", "ghi nhớ nội dung trọng tâm"),
    ("Ý chính", "Nội dung trọng tâm"),
    ("ý chính", "nội dung trọng tâm"),
]


def scrub_banned_phrases(text: Any) -> str:
    """Replace banned template phrases with neutral wording in public text."""
    value = str(text or "")
    for banned, replacement in BANNED_PHRASE_REPLACEMENTS:
        value = value.replace(banned, replacement)
    return value


def normalize_vietnamese_spacing(text: Any) -> str:
    """Normalize broken Vietnamese word spacing."""
    if not text:
        return ""
    value = str(text)
    for broken, fixed in VIETNAMESE_SPACING_FIXES.items():
        value = value.replace(broken, fixed)
    # Fix glued lowercase followed by uppercase character (e.g., họcTập -> học Tập)
    value = re.sub(r"([a-zà-ỹ])([A-ZĐ])", r"\1 \2", value)
    value = re.sub(r"([.!?])([A-ZĐ])", r"\1 \2", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def clean_text_markers(text: Any, drop_broken_headings: bool = True) -> str:
    """Remove debug markers, dot leaders, TOC dots, and repeated header/footer noise."""
    if not text:
        return ""
    value = str(text)
    for pattern in BAD_ARTIFACT_PATTERNS:
        value = re.sub(pattern, " ", value, flags=re.IGNORECASE | re.DOTALL)
    
    value = re.sub(r"\b(page|source|chunk_id)\s*:\s*[^,\n]+", " ", value, flags=re.IGNORECASE)

    lines = []
    for raw_line in value.replace("\r", "").split("\n"):
        line = raw_line.strip()
        if not line:
            continue
        lower = line.lower()
        if drop_broken_headings and lower in BROKEN_HEADINGS:
            continue
        # Drop lines that are purely page numbers or dot leaders
        if re.fullmatch(r"[\d\s.\-–—•/()]+", line):
            continue
        # Drop TOC line like "Chương 1 . . . . . . 12" or "1.1 Introduction .... 5"
        if re.search(r"(?:\.\s*){3,}", line):
            continue
        lines.append(line)
    
    cleaned = "\n".join(lines)
    return normalize_vietnamese_spacing(cleaned)


def classify_chunk(text: str, chunk_id: str = "", page: Any = None) -> Dict[str, Any]:
    """
    Classify chunk into one of:
    toc | body | definition | example | formula | table | code | exercise | summary | heading | noisy
    """
    cleaned = clean_text_markers(text)
    if not cleaned or len(cleaned) < 25:
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "noisy",
            "quality_score": 10,
            "use_for_generation": False,
            "reason": "Too short or empty after cleaning",
        }

    lower = cleaned.lower()
    
    # Check TOC & Index (must be checked BEFORE code/exercise/definition to prevent false positives)
    raw_text = str(text or "")
    raw_lower = raw_text.lower()
    raw_lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
    lines_ending_in_digits = sum(1 for ln in raw_lines if re.search(r"\b\d{1,4}\s*$", ln))
    section_number_lines = sum(1 for ln in raw_lines if re.match(r"^(?:\d+\.)+\d*\s+\w+", ln))

    if (
        re.search(r"(?:\.\s*){3,}|\.\.\.|\…", raw_text)
        or "table of contents" in raw_lower
        or "mục lục" in raw_lower
        or (("contents" in raw_lower or "index" in raw_lower or "danh mục" in raw_lower) and (lines_ending_in_digits >= 2 or section_number_lines >= 2 or len(re.findall(r"\b\d{1,4}\b", raw_lower)) >= 3))
        or (len(raw_lines) >= 3 and (lines_ending_in_digits >= 3 or section_number_lines >= 3))
    ):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "toc",
            "quality_score": 15,
            "use_for_generation": False,
            "reason": "Table of contents / dot leaders / numbered list structure detected",
        }

    words = cleaned.split()
    standalone_numbers = sum(1 for w in words if re.fullmatch(r"\d{1,4}", w))
    if len(words) >= 6 and standalone_numbers / len(words) > 0.20:
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "toc",
            "quality_score": 15,
            "use_for_generation": False,
            "reason": "Index-style line: mostly section numbers/page numbers",
        }

    # Check noisy (mostly digits/symbols)
    symbol_count = len(re.findall(r"[^A-Za-zÀ-ỹ0-9\s]", cleaned))
    if symbol_count / max(len(cleaned), 1) > 0.45:
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "noisy",
            "quality_score": 20,
            "use_for_generation": False,
            "reason": "High symbol/punctuation ratio",
        }

    # Code
    if re.search(r"\b(def|class|import|function|return|const|let|var|int|void|if\s*\(|for\s*\()\b", cleaned) or "```" in text:
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "code",
            "quality_score": 95,
            "use_for_generation": True,
            "reason": "Code snippet or syntax detected",
        }

    # Formula
    if re.search(r"(\b[EFPQW]\s*\([\w,\s]+\)|\b\w+\s*=\s*[\w\d\+\-\*/\^]+|\\\w+|[≤≥≠×Σ∫])", cleaned):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "formula",
            "quality_score": 90,
            "use_for_generation": True,
            "reason": "Mathematical formula or typographic notation",
        }

    # Table
    if cleaned.count("|") >= 3 or re.search(r"(?:\t.{1,30}){2,}", text):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "table",
            "quality_score": 85,
            "use_for_generation": True,
            "reason": "Table data or multi-column layout",
        }

    # Definition
    if re.search(r"\b(định nghĩa|khái niệm|được gọi là|là gì|is defined as|refer to)\b", lower):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "definition",
            "quality_score": 95,
            "use_for_generation": True,
            "reason": "Core definition or academic concept",
        }

    # Example
    if re.search(r"\b(ví dụ|minh họa|chẳng hạn|giả sử|example|for instance)\b", lower):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "example",
            "quality_score": 90,
            "use_for_generation": True,
            "reason": "Practical example or illustration",
        }

    # Exercise
    if re.search(r"\b(bài tập|câu hỏi|hãy tính|luyện tập|exercise|question|quiz)\b", lower):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "exercise",
            "quality_score": 85,
            "use_for_generation": True,
            "reason": "Practice question or exercise",
        }

    # Summary
    if re.search(r"\b(tóm lại|tổng kết|kết luận|nhìn chung|summary|recap|conclusion)\b", lower):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "summary",
            "quality_score": 90,
            "use_for_generation": True,
            "reason": "Summary or concluding recap",
        }

    # Heading (short standalone title/section line, not a full sentence)
    line_count = len([ln for ln in cleaned.splitlines() if ln.strip()])
    word_count = len(cleaned.split())
    if line_count <= 1 and 2 <= word_count <= 12 and cleaned.count(".") == 0 and not re.search(r"[!?]\s*$", cleaned):
        return {
            "chunk_id": chunk_id,
            "page": page,
            "chunk_type": "heading",
            "quality_score": 60,
            "use_for_generation": False,
            "reason": "Short standalone heading or section title",
        }

    # Default Body
    return {
        "chunk_id": chunk_id,
        "page": page,
        "chunk_type": "body",
        "quality_score": 85,
        "use_for_generation": True,
        "reason": "Standard instructional body text",
    }


def clean_and_filter_chunks(docs: Any, max_docs: int = 24, max_chars: int = 900) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Clean retrieved docs, classify chunks, filter out toc/noisy, and deduplicate.
    Returns (usable_chunks, stats).
    """
    cleaned_chunks: List[Dict[str, Any]] = []
    seen_signatures: set = set()
    noisy_removed = 0
    toc_removed = 0
    classified_list = []

    for idx, doc in enumerate(docs or []):
        raw_text = getattr(doc, "page_content", "") or str(doc)
        metadata = getattr(doc, "metadata", {}) or {}
        raw_id = metadata.get("chunk_id", f"auto_{idx}")
        source_id = str(raw_id) if str(raw_id).startswith("chunk_") else f"chunk_{raw_id}"
        page = metadata.get("page")

        classification = classify_chunk(raw_text, chunk_id=source_id, page=page)
        classified_list.append(classification)

        if not classification["use_for_generation"]:
            if classification["chunk_type"] == "toc":
                toc_removed += 1
            else:
                noisy_removed += 1
            continue

        text = clean_text_markers(raw_text)[:max_chars].strip()
        if not text:
            noisy_removed += 1
            continue

        sig = re.sub(r"\W+", "", text.lower())[:220]
        if sig in seen_signatures:
            noisy_removed += 1
            continue
        seen_signatures.add(sig)

        cleaned_chunks.append({
            "text": text,
            "source_chunk_ids": [source_id],
            "chunk_type": classification["chunk_type"],
            "quality_score": classification["quality_score"],
            "page": page,
        })
        if len(cleaned_chunks) >= max_docs:
            break

    stats = {
        "retrieved_chunks_count": len(docs or []),
        "usable_chunks_count": len(cleaned_chunks),
        "clean_chunks_used": len(cleaned_chunks),
        "noisy_chunks_removed": noisy_removed,
        "toc_chunks_removed": toc_removed,
        "source_chunk_ids": [c["source_chunk_ids"][0] for c in cleaned_chunks],
        "source_chunk_ids_used": [c["source_chunk_ids"][0] for c in cleaned_chunks],
        "classifications": classified_list,
    }
    return cleaned_chunks, stats


def validate_output_artifacts(text: Any, source_chunk_ids: Optional[List[str]] = None) -> Tuple[bool, List[str], List[str]]:
    """
    Validate generated output against bad artifacts and grounding requirements.
    Returns (is_valid, warnings, fixes_needed).
    """
    warnings: List[str] = []
    fixes_needed: List[str] = []
    value = str(text or "")
    
    # Check bad keywords / markers
    bad_markers = [
        ("MÃ ĐỊNH DANH TRANG", "Chứa thẻ gỡ lỗi MÃ ĐỊNH DANH TRANG"),
        ("BẮT ĐẦU DỮ LIỆU", "Chứa thẻ gỡ lỗi BẮT ĐẦU DỮ LIỆU"),
        ("KẾT THÚC DỮ LIỆU", "Chứa thẻ gỡ lỗi KẾT THÚC DỮ LIỆU"),
        ("NỘI DUNG:", "Chứa nhãn NỘI DUNG: thô từ RAG"),
    ]
    for marker, warning_msg in bad_markers:
        if re.search(re.escape(marker), value, flags=re.IGNORECASE):
            warnings.append(warning_msg)
            fixes_needed.append(f"Loại bỏ chuỗi '{marker}' khỏi văn bản")

    # Check broken TOC / dot leaders
    if re.search(r"(?:\.\s*){3,}", value):
        warnings.append("Chứa dòng chấm lửng mục lục (. . .)")
        fixes_needed.append("Dọn dẹp dòng chấm lửng rác")

    # Check broken headings
    for bad_head in ["Ý chính", "Ghi nhớ ý chính"]:
        if re.search(rf"^\s*{re.escape(bad_head)}\s*$", value, flags=re.MULTILINE | re.IGNORECASE):
            warnings.append(f"Chứa tiêu đề rỗng/cụt '{bad_head}'")
            fixes_needed.append(f"Thay thế '{bad_head}' bằng tiêu đề học thuật có ý nghĩa")

    # Check broken Vietnamese spacing
    for broken in VIETNAMESE_SPACING_FIXES.keys():
        if broken in value:
            warnings.append(f"Lỗi dính từ tiếng Việt: '{broken}'")
            fixes_needed.append(f"Chuẩn hóa khoảng cách từ '{broken}' -> '{VIETNAMESE_SPACING_FIXES[broken]}'")

    # Check source grounding
    if not source_chunk_ids or len(source_chunk_ids) == 0:
        warnings.append("Thiếu định danh nguồn (source_chunk_ids)")
        fixes_needed.append("Bổ sung source_chunk_ids để đối chiếu RAG")

    is_valid = len(warnings) == 0
    return is_valid, warnings, fixes_needed
