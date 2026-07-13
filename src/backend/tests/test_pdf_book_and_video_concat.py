"""Tests for pdf_book.py (zero coverage before this) and the video_render.py concat-clips
stream-copy → re-encode fallback (zero coverage despite its docstring calling out that it
guards against "the exact failure mode that broke the earlier Vid attempt")."""

import os

import pytest
from pydantic import ValidationError

from app.schemas.generator_output import (
    BookChapter,
    BookOutput,
    BookSection,
    VidDiagram,
    VidDiagramItem,
    VidOutput,
    VidScene,
)
from app.core.config import settings
from app.services.generator import Generator
from app.services import video_render
from app.services.pdf_book import build_book_pdf
from app.services.vector_store import Document
from app.services.video_render import (
    FORMAT_SPECS,
    VideoRenderError,
    _estimate_spoken_duration,
    assemble_video,
    concat_clips,
    concat_clips_xfade,
    format_guidance,
    render_scene_layers,
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


def test_concat_clips_xfade_falls_back_without_clipping_audio(monkeypatch, tmp_path):
    calls = []

    def fake_run_ffmpeg(cmd):
        calls.append(cmd)
        if "xfade=transition=fade" in " ".join(cmd):
            raise VideoRenderError("filtergraph unavailable")

    monkeypatch.setattr(video_render, "_get_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr(video_render, "_run_ffmpeg", fake_run_ffmpeg)

    concat_clips_xfade(["a.mp4", "b.mp4"], [2.0, 2.0], str(tmp_path / "out.mp4"))

    xfade_command = " ".join(calls[0])
    assert "xfade=transition=fade:duration=0.50" in xfade_command
    assert "tpad=stop_mode=clone:stop_duration=0.50" in xfade_command
    assert "concat=n=2:v=0:a=1" in xfade_command
    assert "copy" in calls[1]


def _sample_vid() -> VidOutput:
    return VidOutput(
        title="Video kiểm thử chuyển cảnh",
        total_duration_seconds=0,
        scenes=[
            VidScene(
                scene_number=1,
                title="Câu hỏi mở đầu",
                on_screen_text="Một ý quan trọng",
                key_points=["Điểm thứ nhất", "Điểm thứ hai"],
                narration="Đây là câu dẫn ngắn cho cảnh đầu tiên.",
            ),
            VidScene(
                scene_number=2,
                title="Lời giải thích",
                on_screen_text="Kết nối ý chính",
                key_points=["Kết luận rõ ràng"],
                diagram=VidDiagram(
                    type="flow",
                    items=[
                        VidDiagramItem(label="Dữ liệu", detail="Đầu vào"),
                        VidDiagramItem(label="Phân tích", detail="Xử lý"),
                        VidDiagramItem(label="Kết quả", detail="Ứng dụng"),
                    ],
                ),
                narration="Cảnh thứ hai khép lại mạch giải thích một cách ngắn gọn.",
            ),
        ],
    )


@pytest.mark.parametrize("diagram_type", ["comparison", "flow", "timeline"])
def test_pillow_renders_each_supported_video_diagram(diagram_type, tmp_path):
    scene = VidScene(
        scene_number=1,
        title="Sơ đồ trọng tâm",
        on_screen_text="Nhìn mối liên hệ",
        key_points=["Bullet này phải ẩn"],
        diagram=VidDiagram(
            type=diagram_type,
            title="Mạch kiến thức",
            items=[
                VidDiagramItem(label="Bước một", detail="Khởi đầu"),
                VidDiagramItem(label="Bước hai", detail="Phát triển"),
                VidDiagramItem(label="Bước ba", detail="Kết quả"),
            ],
        ),
        narration="Lời đọc giải thích ba bước của mạch kiến thức này.",
    )
    base_path = str(tmp_path / f"{diagram_type}.png")
    layers = render_scene_layers(scene, 1, 1, 720, 1280, base_path, fmt="shorts")

    from PIL import Image

    assert not any("bullet" in path for path, _ in layers)
    image = Image.open(base_path)
    diagram_region = image.crop((72, 410, 648, 1075))
    assert len(diagram_region.getcolors(maxcolors=1_000_000)) > 4


def test_video_diagram_schema_rejects_unknown_layout():
    with pytest.raises(ValidationError):
        VidDiagram.model_validate({"type": "pyramid", "items": [{"label": "A"}, {"label": "B"}]})


def _fixture_pdf(path: str) -> None:
    import fitz

    document = fitz.open()
    page = document.new_page(width=360, height=480)
    page.insert_text((48, 72), "Trang tai lieu nguon", fontsize=20)
    page.insert_text((48, 118), "Noi dung duoc dung lam visual card.", fontsize=13)
    document.save(path)
    document.close()


def test_document_card_renders_pdf_page_and_silently_falls_back(tmp_path):
    from PIL import Image

    pdf_path = str(tmp_path / "source.pdf")
    _fixture_pdf(pdf_path)
    scene = VidScene(
        scene_number=2,
        title="Trang tai lieu",
        on_screen_text="Nguon tham chieu",
        key_points=["Bullet phai an"],
        narration="Loi doc ngan cho trang tai lieu nguon.",
    )
    base_path = str(tmp_path / "document-card.png")
    layers = render_scene_layers(
        scene,
        2,
        4,
        1280,
        720,
        base_path,
        document_visual={"pdf_path": pdf_path, "page": 1, "side": "left"},
    )

    assert not any("bullet" in path for path, _ in layers)
    image = Image.open(base_path)
    card_pixels = image.crop((80, 110, 640, 620)).get_flattened_data()
    assert sum(pixel[0] > 200 and pixel[1] > 200 and pixel[2] > 200 for pixel in card_pixels) > 500

    fallback_layers = render_scene_layers(
        scene,
        2,
        4,
        1280,
        720,
        str(tmp_path / "missing-card.png"),
        document_visual={"pdf_path": str(tmp_path / "missing.pdf"), "page": 1, "side": "left"},
    )
    assert any("bullet" in path for path, _ in fallback_layers)


def test_generator_builds_grounded_document_visual_map(tmp_path, monkeypatch):
    course_id = "visual-map-course"
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    course_dir = tmp_path / course_id
    course_dir.mkdir()
    pdf_path = course_dir / "1700000000_source.pdf"
    _fixture_pdf(str(pdf_path))

    class ChunkStore:
        def get_course_chunks(self, requested_course_id, chunk_ids):
            assert requested_course_id == course_id
            assert chunk_ids == ["chunk_1", "chunk_2"]
            return [
                Document(content="one", metadata={"chunk_id": "chunk_1", "source_file": "source.pdf", "page": 1}),
                Document(content="two", metadata={"chunk_id": "chunk_2", "source_file": "source.pdf", "page": 1}),
            ]

    vid = VidOutput(
        title="Map visual",
        total_duration_seconds=0,
        scenes=[
            VidScene(scene_number=1, title="Mo dau", narration="Loi doc dau tien du dai.", source_chunk_ids=["chunk_1"]),
            VidScene(scene_number=2, title="Giua mot", narration="Loi doc thu hai du dai.", source_chunk_ids=["chunk_1"]),
            VidScene(scene_number=3, title="Giua hai", narration="Loi doc thu ba du dai.", source_chunk_ids=["chunk_2"]),
            VidScene(scene_number=4, title="Ket", narration="Loi doc ket thuc du dai.", source_chunk_ids=["chunk_2"]),
        ],
    )
    visual_map = Generator(ChunkStore(), llm=None)._build_scene_visual_map(course_id, vid)

    assert list(visual_map) == [2]
    assert visual_map[2]["pdf_path"] == str(pdf_path)
    assert visual_map[2]["page"] == 1
    assert visual_map[2]["side"] == "left"


def test_motion_layers_and_xfade_render_with_silence(tmp_path):
    """The no-network pytest path still renders layered scenes, xfade, and audio tails."""
    from PIL import Image

    base_path = str(tmp_path / "scene_base.png")
    layers = render_scene_layers(_sample_vid().scenes[0], 1, 2, 320, 180, base_path)
    assert os.path.exists(base_path)
    assert [delay for _, delay in layers] == [0.3, 0.9, 1.5, 2.4]
    assert Image.open(base_path).mode == "RGB"
    assert all(Image.open(path).mode == "RGBA" for path, _ in layers)

    artifact_dir = str(tmp_path / "artifact")
    os.makedirs(artifact_dir)
    source_pdf = str(tmp_path / "video-source.pdf")
    _fixture_pdf(source_pdf)
    output = _sample_vid()
    mp4_path = assemble_video(
        output,
        "shorts",
        "female",
        artifact_dir,
        scene_visual_map={1: {"pdf_path": source_pdf, "page": 1, "side": "left"}},
    )

    assert os.path.exists(mp4_path)
    assert os.path.getsize(mp4_path) > 1000
    assert output.total_duration_seconds >= 2
    rendered_duration = video_render._probe_duration(mp4_path)
    assert rendered_duration >= output.total_duration_seconds - 0.5
    assert rendered_duration <= output.total_duration_seconds + 1.0
    assert not os.path.exists(os.path.join(artifact_dir, "_vid_scenes"))


def test_format_pacing_rates_and_guidance_are_explicit():
    assert FORMAT_SPECS["standard"]["tts_rate"] == "+0%"
    assert FORMAT_SPECS["overview"]["tts_rate"] == "+4%"
    assert FORMAT_SPECS["shorts"]["tts_rate"] == "+12%"
    assert "Nhịp nhanh" in format_guidance("shorts")
    text = "một hai ba bốn năm sáu"
    assert _estimate_spoken_duration(text, "+12%") < _estimate_spoken_duration(text, "+0%")
