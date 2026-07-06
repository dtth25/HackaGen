"""Builds the natural-language instruction block injected into every generation
prompt (Book, Slides, Mindmap, Quiz, Flashcards, Summary, Video) so the same
document produces different output depending on the user's Learning Profile.

Kept as a pure function (no ResourceGenerator dependency) so it's trivial to unit
test and so every generator call site is forced to explicitly pass its result into
the prompt payload — the previous `learning_mode` field silently no-op'd in 3 of 6
generators because there was no single, verifiable injection point like this one.
"""

from typing import Any, Optional

DIFFICULTY_LABELS_VI = {
    "beginner": "Mới bắt đầu (giải thích từ số 0, tránh biệt ngữ)",
    "intermediate": "Trung cấp (đã có nền tảng cơ bản)",
    "university": "Chuẩn đại học (chuyên sâu, học thuật)",
    "advanced": "Nâng cao (chuyên gia, giả định người đọc đã vững kiến thức nền)",
}

LEARNING_GOAL_LABELS_VI = {
    "understand": "Hiểu bản chất khái niệm",
    "exam": "Ôn thi, đạt điểm cao",
    "teach": "Chuẩn bị để giảng dạy lại cho người khác",
    "revise": "Ôn tập lại kiến thức đã học",
    "apply": "Áp dụng vào thực hành/dự án thực tế",
    "onboard": "Onboarding nhanh cho công việc/vai trò mới",
    "research": "Nghiên cứu chuyên sâu, phản biện học thuật",
}

OUTPUT_STYLE_LABELS_VI = {
    "high_yield": "High-yield: chỉ giữ điểm trọng tâm nhất, súc tích tối đa",
    "detailed": "Chi tiết: giải thích đầy đủ, có chiều sâu",
    "visual": "Trực quan: ưu tiên sơ đồ, bảng so sánh, hình dung",
    "practice_based": "Thiên về thực hành: nhiều ví dụ áp dụng, bài tập, mini-project",
    "academic": "Học thuật: chuẩn mực, chặt chẽ, trích dẫn rõ ràng",
    "simple": "Đơn giản: ngôn ngữ đời thường, ví von dễ hiểu",
}

LANGUAGE_STYLE_INSTRUCTIONS = {
    "vietnamese_simple": "Viết bằng tiếng Việt đơn giản, câu ngắn, tránh thuật ngữ khó.",
    "vietnamese_academic": "Viết bằng tiếng Việt học thuật, chuẩn mực sư phạm đại học.",
    "english": "Write in clear academic English.",
    "bilingual_vi_en": "Viết song ngữ: nội dung chính bằng tiếng Việt, giữ thuật ngữ chuyên ngành tiếng Anh trong ngoặc.",
}

TIME_BUDGET_LABELS_VI = {
    "10_min": "10 phút (cực kỳ cô đọng, chỉ những điểm bắt buộc phải biết)",
    "30_min": "30 phút (cô đọng, đủ dùng để ôn nhanh)",
    "1_hour": "1 giờ (đầy đủ nhưng vẫn tập trung, không lan man)",
    "multi_day": "Nhiều ngày (đầy đủ chiều sâu, có thể học trải dài nhiều buổi)",
}

# Mode behavior bullets from the product spec — the core differentiator per role_mode.
ROLE_MODE_BEHAVIOR_VI = {
    "student": (
        "Vai trò SINH VIÊN: viết sách học súc tích, dễ theo dõi; luôn kèm ví dụ minh họa cụ thể; "
        "thiết kế nội dung hỗ trợ active recall (câu hỏi tự kiểm tra không nhìn tài liệu)."
    ),
    "exam_prep": (
        "Vai trò ÔN THI: ưu tiên các điểm high-yield (khả năng ra đề cao); chỉ rõ các \"bẫy\" hoặc lỗi sai "
        "thường gặp trong đề thi; thêm câu hỏi thi thử (mock questions); tối ưu cho ôn tập nhanh, không lan man."
    ),
    "teacher": (
        "Vai trò GIẢNG VIÊN: nêu rõ mục tiêu bài giảng (lesson objectives) đo lường được; đề xuất hoạt động "
        "lớp học (activities) và câu hỏi thảo luận (discussion); thêm bài tập về nhà (homework); "
        "kèm rubric chấm điểm rõ tiêu chí."
    ),
    "self_learner": (
        "Vai trò NGƯỜI TỰ HỌC: giải thích đơn giản, dùng ví von/analogy đời thường dễ hình dung; "
        "trình bày theo lộ trình từng bước (step-by-step path) rõ ràng, không giả định kiến thức nền."
    ),
    "developer": (
        "Vai trò LẬP TRÌNH/THỰC HÀNH: nếu tài liệu có code, đi từng bước code walkthrough; nêu cách triển khai "
        "(implementation) thực tế; chỉ ra lỗi thường gặp và cách debug; đề xuất mini-project để thực hành áp dụng."
    ),
    "enterprise_trainer": (
        "Vai trò ĐÀO TẠO NỘI BỘ: tóm tắt dạng quy trình chuẩn (SOP summary) rõ các bước; cung cấp checklist "
        "để nhân sự tự kiểm tra; nếu có phần quiz, thiết kế theo hướng compliance quiz (kiểm tra tuân thủ quy trình)."
    ),
    "researcher": (
        "Vai trò NGHIÊN CỨU/CHUYÊN SÂU: nêu rõ định nghĩa (definitions) chính xác; phương pháp (methods) được "
        "dùng; các giả định (assumptions) và giới hạn (limitations) của tài liệu; đề xuất câu hỏi mở "
        "(open questions) cho hướng nghiên cứu tiếp theo."
    ),
}


def build_profile_directives(profile: Optional[dict[str, Any]]) -> str:
    """Return a Vietnamese instruction block to inject into a generation prompt.

    Returns "" when no profile is set (e.g. anonymous/legacy calls), so every
    prompt's `{profile_directives}` placeholder degrades gracefully to a no-op.
    """
    if not profile:
        return ""

    role_mode = str(profile.get("role_mode") or "student")
    difficulty_level = str(profile.get("difficulty_level") or "university")
    learning_goal = str(profile.get("learning_goal") or "understand")
    preferred_output_style = str(profile.get("preferred_output_style") or "detailed")
    language_style = str(profile.get("language_style") or "vietnamese_academic")
    time_budget = str(profile.get("time_budget") or "1_hour")

    lines = ["[HỒ SƠ HỌC TẬP CỦA NGƯỜI DÙNG — BẮT BUỘC TUÂN THEO]"]
    behavior = ROLE_MODE_BEHAVIOR_VI.get(role_mode)
    if behavior:
        lines.append(f"- {behavior}")
    lines.append(f"- Mức độ: {DIFFICULTY_LABELS_VI.get(difficulty_level, difficulty_level)}.")
    lines.append(f"- Mục tiêu học tập: {LEARNING_GOAL_LABELS_VI.get(learning_goal, learning_goal)}.")
    lines.append(f"- Phong cách đầu ra: {OUTPUT_STYLE_LABELS_VI.get(preferred_output_style, preferred_output_style)}.")
    lines.append(f"- Ngân sách thời gian: {TIME_BUDGET_LABELS_VI.get(time_budget, time_budget)}.")
    lang_instr = LANGUAGE_STYLE_INSTRUCTIONS.get(language_style)
    if lang_instr:
        lines.append(f"- Ngôn ngữ: {lang_instr}")

    if profile.get("include_examples") is False:
        lines.append("- KHÔNG cần thêm ví dụ minh họa chi tiết trừ khi thực sự cần thiết để hiểu khái niệm.")
    if profile.get("include_common_mistakes") is False:
        lines.append("- KHÔNG cần phần \"sai lầm thường gặp\"/misconception riêng, tập trung vào nội dung chính.")

    return "\n".join(lines)
