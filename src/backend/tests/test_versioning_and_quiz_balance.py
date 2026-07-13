"""Focused regression coverage for version identities and quiz answer balancing."""

from app.schemas.generator_output import QuizOption, QuizOutput, QuizQuestion
from app.services.generator import _balance_quiz_answers
from app.services.versioning import migrate_legacy_artifact_metadata, version_slug


def _quiz(question_count: int) -> QuizOutput:
    return QuizOutput(
        title="Quiz",
        questions=[
            QuizQuestion(
                question_number=index + 1,
                question_text=f"Câu hỏi {index + 1}",
                options=[QuizOption(key=key, text=f"Đáp án {key}") for key in "ABCD"],
                correct_answer="A",
            )
            for index in range(question_count)
        ],
    )


def test_new_versions_use_unique_uuid_identities_for_identical_options():
    first = version_slug("book", {"detail_level": "Tiêu chuẩn"})
    second = version_slug("book", {"detail_level": "Tiêu chuẩn"})

    assert first != second
    assert len(first) == len(second) == 36


def test_legacy_metadata_cleanup_removes_regeneration_counter():
    metadata = {"study_pack": {"regen_counts": {"book": 2}, "artifacts": {}}}

    migrated, changed = migrate_legacy_artifact_metadata(metadata)

    assert changed is True
    assert "regen_counts" not in migrated["study_pack"]


def test_quiz_answers_are_balanced_and_rekeyed_deterministically():
    balanced = _balance_quiz_answers(_quiz(11), "version-123")
    answers = [question.correct_answer for question in balanced.questions]
    counts = [answers.count(letter) for letter in "ABCD"]

    assert max(counts) - min(counts) <= 1
    assert all(not (answers[index] == answers[index - 1] == answers[index - 2]) for index in range(2, len(answers)))
    assert all([option.key for option in question.options] == list("ABCD") for question in balanced.questions)
    assert all(question.options["ABCD".index(question.correct_answer)].text == "Đáp án A" for question in balanced.questions)
