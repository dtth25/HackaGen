"""Tests for pdf_book.py (zero coverage before this) and the video_render.py concat-clips
stream-copy → re-encode fallback (zero coverage despite its docstring calling out that it
guards against "the exact failure mode that broke the earlier Vid attempt")."""

import os

import pytest

from app.schemas.generator_output import BookChapter, BookOutput, BookSection
from app.services import video_render
from app.services.pdf_book import build_book_pdf
from app.services.video_render import (
    FORMAT_SPECS,
    VideoRenderError,
    _estimate_spoken_duration,
    concat_clips,
    format_guidance,
)


def _sample_book() -> BookOutput:
    return BookOutput(
        title="Giáo trình Kiểm thử",
        summary="Tóm tắt ngắn gọn nội dung khóa học để kiểm thử PDF.",
        preface="Lời nói đầu cho tài liệu kiểm thử.",
        chapters=[
            BookChapter(
                chapter_title="Chương mở đầu",
                introduction="Giới thiệu chương.",
                objectives=["Hiểu khái niệm cơ bản.", "Áp dụng vào bài tập."],
                sections=[
                    BookSection(title="Phần 1", content="Nội dung phần 1.\n\nĐoạn thứ hai."),
                ],
                key_points=["Điểm cốt lõi 1."],
                review_questions=["Câu hỏi ôn tập 1?"],
            ),
        ],
    )


def test_build_book_pdf_writes_valid_pdf(tmp_path):
    """Smoke test: building a Book PDF from realistic content must not crash and must
    produce a real PDF file (magic bytes + non-trivial size), not an empty/corrupt stub."""
    out_path = str(tmp_path / "book.pdf")
    build_book_pdf(out_path, _sample_book())

    assert os.path.exists(out_path)
    with open(out_path, "rb") as f:
        header = f.read(5)
    assert header == b"%PDF-"
    assert os.path.getsize(out_path) > 1000


def test_concat_clips_stream_copy_succeeds(monkeypatch, tmp_path):
    """Happy path: stream-copy concat succeeds on the first try, no re-encode fallback."""
    calls = []

    def fake_run_ffmpeg(cmd):
        calls.append(cmd)

    monkeypatch.setattr(video_render, "_get_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(video_render, "_run_ffmpeg", fake_run_ffmpeg)

    out_path = str(tmp_path / "out.mp4")
    concat_clips(["a.mp4", "b.mp4"], out_path)

    assert len(calls) == 1
    assert "copy" in calls[0]
    assert not os.path.exists(out_path + ".concat.txt")


def test_concat_clips_falls_back_to_reencode_on_stream_copy_mismatch(monkeypatch, tmp_path):
    """Regression guard for the exact bug the docstring calls out: when clips don't share
    identical encode params, the fast stream-copy concat fails — concat_clips must catch
    that and retry with a full re-encode instead of raising."""
    calls = []

    def fake_run_ffmpeg(cmd):
        calls.append(cmd)
        if "copy" in cmd:
            raise VideoRenderError("ffmpeg lỗi: Non-monotonous DTS in output stream")

    monkeypatch.setattr(video_render, "_get_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(video_render, "_run_ffmpeg", fake_run_ffmpeg)

    out_path = str(tmp_path / "out.mp4")
    concat_clips(["a.mp4", "b.mp4"], out_path)  # must not raise

    assert len(calls) == 2
    assert "copy" in calls[0]
    assert "libx264" in calls[1]
    assert not os.path.exists(out_path + ".concat.txt")


def test_concat_clips_reencode_also_fails_raises(monkeypatch, tmp_path):
    """If both stream-copy and re-encode fail, the real error must propagate — no silent
    swallow, matching this file's stance elsewhere on VideoRenderError."""

    def fake_run_ffmpeg(cmd):
        raise VideoRenderError("ffmpeg lỗi thật")

    monkeypatch.setattr(video_render, "_get_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(video_render, "_run_ffmpeg", fake_run_ffmpeg)

    out_path = str(tmp_path / "out.mp4")
    with pytest.raises(VideoRenderError):
        concat_clips(["a.mp4", "b.mp4"], out_path)


def test_format_pacing_rates_and_guidance_are_explicit():
    assert FORMAT_SPECS["standard"]["tts_rate"] == "+0%"
    assert FORMAT_SPECS["overview"]["tts_rate"] == "+4%"
    assert FORMAT_SPECS["shorts"]["tts_rate"] == "+12%"
    assert "Nhịp nhanh" in format_guidance("shorts")
    text = "một hai ba bốn năm sáu"
    assert _estimate_spoken_duration(text, "+12%") < _estimate_spoken_duration(text, "+0%")
