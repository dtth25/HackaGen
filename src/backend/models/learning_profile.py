"""Learning Profile model: lets different users get different tailored outputs
(Book, Slides, Mindmap, Quiz, Flashcards, Summary, Video) from the same document.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel

RoleMode = Literal[
    "student", "teacher", "self_learner", "exam_prep",
    "enterprise_trainer", "researcher", "developer",
]
DifficultyLevel = Literal["beginner", "intermediate", "university", "advanced"]
LearningGoal = Literal["understand", "exam", "teach", "revise", "apply", "onboard", "research"]
OutputStyle = Literal["high_yield", "detailed", "visual", "practice_based", "academic", "simple"]
LanguageStyle = Literal["vietnamese_simple", "vietnamese_academic", "english", "bilingual_vi_en"]
TimeBudget = Literal["10_min", "30_min", "1_hour", "multi_day"]

ROLE_MODES: tuple[RoleMode, ...] = (
    "student", "teacher", "self_learner", "exam_prep",
    "enterprise_trainer", "researcher", "developer",
)

# Vietnamese labels for onboarding/settings UI, per the product spec.
ROLE_MODE_LABELS_VI: dict[RoleMode, str] = {
    "student": "Sinh viên",
    "exam_prep": "Ôn thi",
    "teacher": "Giảng viên",
    "self_learner": "Người tự học",
    "developer": "Lập trình / thực hành",
    "enterprise_trainer": "Đào tạo nội bộ",
    "researcher": "Nghiên cứu / chuyên sâu",
}

ROLE_MODE_DESCRIPTIONS_VI: dict[RoleMode, str] = {
    "student": "Sách học súc tích, ví dụ minh họa, ôn tập chủ động (active recall).",
    "exam_prep": "Điểm high-yield, các bẫy thường gặp, câu hỏi thi thử, ôn nhanh.",
    "teacher": "Mục tiêu bài giảng, hoạt động lớp học, thảo luận, bài tập về nhà, rubric chấm điểm.",
    "self_learner": "Giải thích đơn giản, ví von dễ hiểu, lộ trình từng bước.",
    "developer": "Đọc hiểu code, cách triển khai, debug, mini-project thực hành.",
    "enterprise_trainer": "Tóm tắt quy trình (SOP), checklist, quiz tuân thủ (compliance).",
    "researcher": "Định nghĩa, phương pháp, giả định, giới hạn, câu hỏi mở.",
}


class LearningProfile(BaseModel):
    """Per-user personalization profile applied to every generator."""

    role_mode: RoleMode = "student"
    difficulty_level: DifficultyLevel = "university"
    learning_goal: LearningGoal = "understand"
    preferred_output_style: OutputStyle = "detailed"
    language_style: LanguageStyle = "vietnamese_academic"
    time_budget: TimeBudget = "1_hour"
    include_examples: bool = True
    include_quiz: bool = True
    include_flashcards: bool = True
    include_mindmap: bool = True
    include_common_mistakes: bool = True


# Sensible per-role defaults for every OTHER field, so picking a role_mode alone
# (e.g. in onboarding) already produces meaningfully different output — the user
# is never required to hand-tune all 6 dimensions themselves.
ROLE_MODE_DEFAULTS: dict[RoleMode, dict[str, Any]] = {
    "student": {
        "difficulty_level": "university",
        "learning_goal": "understand",
        "preferred_output_style": "detailed",
        "time_budget": "1_hour",
        "include_examples": True,
        "include_common_mistakes": True,
    },
    "exam_prep": {
        "difficulty_level": "university",
        "learning_goal": "exam",
        "preferred_output_style": "high_yield",
        "time_budget": "30_min",
        "include_examples": False,
        "include_common_mistakes": True,
    },
    "teacher": {
        "difficulty_level": "advanced",
        "learning_goal": "teach",
        "preferred_output_style": "academic",
        "time_budget": "multi_day",
        "include_examples": True,
        "include_common_mistakes": True,
    },
    "self_learner": {
        "difficulty_level": "beginner",
        "learning_goal": "understand",
        "preferred_output_style": "simple",
        "time_budget": "1_hour",
        "include_examples": True,
        "include_common_mistakes": True,
    },
    "developer": {
        "difficulty_level": "intermediate",
        "learning_goal": "apply",
        "preferred_output_style": "practice_based",
        "time_budget": "1_hour",
        "include_examples": True,
        "include_common_mistakes": True,
    },
    "enterprise_trainer": {
        "difficulty_level": "intermediate",
        "learning_goal": "onboard",
        "preferred_output_style": "practice_based",
        "time_budget": "30_min",
        "include_examples": True,
        "include_common_mistakes": False,
    },
    "researcher": {
        "difficulty_level": "advanced",
        "learning_goal": "research",
        "preferred_output_style": "academic",
        "time_budget": "multi_day",
        "include_examples": False,
        "include_common_mistakes": False,
    },
}


class LearningProfileUpdateRequest(BaseModel):
    """PUT /me/learning-profile body — every field but role_mode is optional so an
    unset field falls back to that role's curated default instead of a generic one.
    """

    role_mode: RoleMode = "student"
    difficulty_level: Optional[DifficultyLevel] = None
    learning_goal: Optional[LearningGoal] = None
    preferred_output_style: Optional[OutputStyle] = None
    language_style: Optional[LanguageStyle] = None
    time_budget: Optional[TimeBudget] = None
    include_examples: Optional[bool] = None
    include_quiz: Optional[bool] = None
    include_flashcards: Optional[bool] = None
    include_mindmap: Optional[bool] = None
    include_common_mistakes: Optional[bool] = None


def resolve_profile_for_role(role_mode: RoleMode, overrides: Optional[dict[str, Any]] = None) -> LearningProfile:
    """Build a full profile from a role_mode's defaults, with explicit overrides applied on top."""
    base: dict[str, Any] = {"role_mode": role_mode, **ROLE_MODE_DEFAULTS.get(role_mode, {})}
    if overrides:
        base.update({k: v for k, v in overrides.items() if v is not None})
    return LearningProfile(**base)
