"""
Generation Readiness Evaluation Service.
Computes per-output readiness and safe fallback recommendations without global overblocking.
"""
from typing import Any, Dict, List
from services.context_cleaner import clean_and_filter_chunks


def evaluate_document_readiness(
    docs: Any,
    document_id: str = "",
    max_docs: int = 32,
    max_chars: int = 900,
) -> Dict[str, Any]:
    """
    Evaluate context quality and determine per-output generation readiness.
    """
    cleaned_chunks, stats = clean_and_filter_chunks(docs, max_docs=max_docs, max_chars=max_chars)

    retrieved_count = stats.get("retrieved_chunks_count", len(docs or []))
    clean_chunks_count = stats.get("usable_chunks_count", len(cleaned_chunks))
    noisy_removed = stats.get("noisy_chunks_removed", 0) + stats.get("toc_chunks_removed", 0)

    extracted_char_count = sum(len(c.get("text", "")) if isinstance(c, dict) else len(getattr(c, "page_content", "") or str(c)) for c in cleaned_chunks)
    
    # Calculate overall quality score
    if retrieved_count == 0 or clean_chunks_count == 0:
        overall_quality_score = 0
    else:
        ratio = clean_chunks_count / max(1, retrieved_count)
        volume_bonus = min(25, int(extracted_char_count / 300))
        overall_quality_score = min(100, int(ratio * 70) + volume_bonus)
        if clean_chunks_count < 2:
            overall_quality_score = min(overall_quality_score, 45)
        elif clean_chunks_count < 4:
            overall_quality_score = min(overall_quality_score, 68)

    warnings: List[str] = []
    recommended_actions: List[str] = []
    safe_outputs_available: List[str] = []

    # Check if scanned / too little raw text
    is_scanned_or_empty = (clean_chunks_count == 0 and retrieved_count > 0) or (extracted_char_count < 300 and clean_chunks_count <= 1)
    if is_scanned_or_empty:
        warnings.append("PDF này có vẻ là bản scan hoặc ảnh, hệ thống chưa đọc được đủ text. Vui lòng bật OCR hoặc tải bản PDF có text rõ hơn.")
        recommended_actions.append("Bật OCR hoặc sử dụng bản PDF có lớp văn bản (text layer) rõ ràng hơn.")
    elif clean_chunks_count < 4:
        warnings.append("PDF này có nội dung đọc được nhưng chưa đủ ngữ cảnh sạch để tạo toàn bộ học liệu. Bạn vẫn có thể tạo bản tóm tắt, outline hoặc bản học trọng tâm.")
        recommended_actions.append("Sử dụng các tính năng tạo tóm tắt, dàn ý (outline) hoặc học trọng tâm để khai thác dữ liệu hiện có.")

    # Determine safe outputs available
    if clean_chunks_count >= 1 or extracted_char_count >= 300:
        safe_outputs_available.extend(["short_summary", "document_outline", "high_yield_notes"])
        if clean_chunks_count >= 2 or extracted_char_count >= 600:
            safe_outputs_available.append("key_terms")

    # Per-output readiness rules
    readiness: Dict[str, Dict[str, str]] = {}

    # 1. Book (needs most structured context)
    if clean_chunks_count >= 8 and overall_quality_score >= 75:
        readiness["book"] = {
            "status": "ready",
            "reason": "Đủ ngữ cảnh sạch để tạo sách học trọn vẹn với các chương bài học chi tiết.",
            "recommended_fallback": "full_book"
        }
    elif clean_chunks_count >= 1 or extracted_char_count >= 300:
        readiness["book"] = {
            "status": "limited",
            "reason": "Ngữ cảnh ở mức trung bình hoặc giới hạn. Có thể tạo sách học trọng tâm rút gọn.",
            "recommended_fallback": "high_yield_study_guide"
        }
    else:
        readiness["book"] = {
            "status": "not_enough_context",
            "reason": "Chưa đủ để tạo sách học đầy đủ. Hệ thống cần nhiều đoạn nội dung liên tục hơn để xây dựng chương, bài học, ví dụ và câu hỏi kiểm tra.",
            "recommended_fallback": "short_summary" if "short_summary" in safe_outputs_available else "cannot_generate"
        }

    # 2. Course
    if clean_chunks_count >= 8 and overall_quality_score >= 75:
        readiness["course"] = {
            "status": "ready",
            "reason": "Đủ cấu trúc và ngữ cảnh để xây dựng toàn bộ lộ trình khóa học.",
            "recommended_fallback": "full_course"
        }
    elif clean_chunks_count >= 1 or extracted_char_count >= 300:
        readiness["course"] = {
            "status": "limited",
            "reason": "Có thể tạo cấu trúc khóa học rút gọn tập trung vào các chủ đề tìm thấy.",
            "recommended_fallback": "high_yield_course"
        }
    else:
        readiness["course"] = {
            "status": "not_enough_context",
            "reason": "Chưa đủ dữ liệu văn bản để phân chia thành lộ trình nhiều chương bài.",
            "recommended_fallback": "short_outline" if "document_outline" in safe_outputs_available else "cannot_generate"
        }

    # 3. Video (needs dynamic scenes and examples)
    if clean_chunks_count >= 5 and overall_quality_score >= 70:
        readiness["video"] = {
            "status": "ready",
            "reason": "Đủ mạch nội dung và ví dụ để trực quan hóa thành video bài giảng hoàn chỉnh.",
            "recommended_fallback": "full_video"
        }
    elif clean_chunks_count >= 3:
        readiness["video"] = {
            "status": "limited",
            "reason": "Mạch văn bản giới hạn, có thể tạo video kịch bản ngắn (short script).",
            "recommended_fallback": "short_60_second_script"
        }
    else:
        readiness["video"] = {
            "status": "not_enough_context",
            "reason": "Chưa đủ để tạo video hoàn chỉnh. Video cần mạch nội dung rõ, ví dụ và các ý có thể trực quan hóa. Bạn có thể tạo script/storyboard ngắn trước.",
            "recommended_fallback": "storyboard_only" if clean_chunks_count >= 1 else "cannot_generate"
        }

    # 4. Quiz (needs enough factual content)
    if clean_chunks_count >= 4 and overall_quality_score >= 65:
        readiness["quiz"] = {
            "status": "ready",
            "reason": "Đủ dữ kiện để tạo bộ câu hỏi kiểm tra đánh giá toàn diện.",
            "recommended_fallback": "full_quiz"
        }
    elif clean_chunks_count >= 2:
        readiness["quiz"] = {
            "status": "limited",
            "reason": "Có đủ thông tin cơ bản để tạo 3-5 câu hỏi ôn tập nhanh.",
            "recommended_fallback": "3_basic_questions"
        }
    else:
        readiness["quiz"] = {
            "status": "not_enough_context",
            "reason": "Chưa đủ dữ kiện để tạo bộ câu hỏi chất lượng. Có thể tạo một vài câu hỏi ôn tập cơ bản nếu bạn muốn.",
            "recommended_fallback": "3_basic_questions" if clean_chunks_count >= 1 else "cannot_generate"
        }

    # 5. Slides
    if clean_chunks_count >= 4 and overall_quality_score >= 65:
        readiness["slides"] = {
            "status": "ready",
            "reason": "Đủ nội dung để tạo bộ slide thuyết trình chuyên nghiệp.",
            "recommended_fallback": "full_deck"
        }
    elif clean_chunks_count >= 2:
        readiness["slides"] = {
            "status": "limited",
            "reason": "Có thể sinh bộ slide tổng quan ngắn (6 slides overview).",
            "recommended_fallback": "short_6_slide_overview"
        }
    else:
        readiness["slides"] = {
            "status": "not_enough_context",
            "reason": "Chưa đủ nội dung chi tiết để phân bổ thành slide thuyết trình.",
            "recommended_fallback": "summary_slides" if clean_chunks_count >= 1 else "cannot_generate"
        }

    # 6. Flashcards (can be generated if terms exist)
    if clean_chunks_count >= 3 or extracted_char_count >= 800:
        readiness["flashcards"] = {
            "status": "ready",
            "reason": "Đủ thuật ngữ và định nghĩa để tạo thẻ ghi nhớ.",
            "recommended_fallback": "full_flashcards"
        }
    elif clean_chunks_count >= 1 or extracted_char_count >= 300:
        readiness["flashcards"] = {
            "status": "limited",
            "reason": "Tìm thấy một số thuật ngữ chính, có thể tạo flashcards cơ bản.",
            "recommended_fallback": "key_terms_only"
        }
    else:
        readiness["flashcards"] = {
            "status": "not_enough_context",
            "reason": "Chưa trích xuất được thuật ngữ hay khái niệm rõ ràng.",
            "recommended_fallback": "cannot_generate"
        }

    # 7. Mindmap (can be shallow if limited context)
    if clean_chunks_count >= 3 and overall_quality_score >= 60:
        readiness["mindmap"] = {
            "status": "ready",
            "reason": "Đủ chủ đề để tạo sơ đồ tư duy nhiều tầng.",
            "recommended_fallback": "full_mindmap"
        }
    elif clean_chunks_count >= 1:
        readiness["mindmap"] = {
            "status": "limited",
            "reason": "Có thể xây dựng sơ đồ khái niệm đơn giản 1-2 tầng.",
            "recommended_fallback": "shallow_concept_map"
        }
    else:
        readiness["mindmap"] = {
            "status": "not_enough_context",
            "reason": "Không đủ thông tin cấu trúc để liên kết sơ đồ.",
            "recommended_fallback": "cannot_generate"
        }

    for k, v in readiness.items():
        if v.get("status") in ("ready", "limited") and k not in safe_outputs_available:
            safe_outputs_available.append(k)

    return {
        "document_id": document_id,
        "overall_quality_score": overall_quality_score,
        "clean_chunks_count": clean_chunks_count,
        "noisy_chunks_removed": noisy_removed,
        "generation_readiness": readiness,
        "safe_outputs_available": safe_outputs_available,
        "warnings": warnings,
        "recommended_actions": recommended_actions,
        "cleaned_docs": cleaned_chunks,
        "stats": stats,
    }
