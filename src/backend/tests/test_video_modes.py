from fastapi.testclient import TestClient
from langchain_core.documents import Document
from backend import main
from backend.main import app
from backend.services.resource_gen import ResourceGenerator


class DummyVectorStore:
    def __init__(self, docs):
        self.docs = docs

    def as_retriever(self, search_kwargs=None):
        return self

    def invoke(self, query: str):
        return self.docs


def create_mock_resource_gen(course_id: str, num_docs: int = 5) -> ResourceGenerator:
    docs = [
        Document(
            page_content=f"=== BẮT ĐẦU DỮ LIỆU TRUY XUẤT ===\n[MÃ ĐỊNH DANH TRANG: {i+1}]\nKhái niệm quan trọng {i+1} về Trí tuệ nhân tạo và học máy.\n=== KẾT THÚC DỮ LIỆU TRANG {i+1} ===",
            metadata={"source": "test.pdf", "page": i+1, "chunk_id": f"chunk_{i+1}"}
        )
        for i in range(num_docs)
    ]
    class MockRAGChains:
        def __init__(self, cid, vs):
            self.course_id = cid
            self.vectorstore = vs
    gen = ResourceGenerator(MockRAGChains(course_id, DummyVectorStore(docs)))
    return gen


def test_generate_vid_sixty_second():
    gen = create_mock_resource_gen("test_vid_60s", num_docs=4)
    res = gen.generate_vid(topic="AI Basics", video_mode="sixty_second", render_mp4=False)
    vid = res.get("vid", {})
    assert vid.get("video_mode") == "sixty_second"
    assert "subtitles_srt" in vid
    assert "-->" in vid["subtitles_srt"]
    assert len(vid.get("scenes", [])) >= 1
    assert "quality_report" in vid


def test_generate_vid_playlist_by_chapter():
    gen = create_mock_resource_gen("test_vid_playlist", num_docs=8)
    res = gen.generate_vid(topic="Khóa học AI", video_mode="playlist_by_chapter")
    vid = res.get("vid", {})
    assert vid.get("video_mode") == "playlist_by_chapter"
    assert vid.get("status") == "planned"
    assert isinstance(vid.get("videos"), list)
    assert len(vid["videos"]) >= 1
    assert vid["videos"][0]["status"] == "planned"


def test_large_pdf_recommendation():
    gen = create_mock_resource_gen("test_large_pdf", num_docs=20)
    res = gen.generate_vid(topic="tổng quan", video_mode="three_minute")
    vid = res.get("vid", {})
    assert vid.get("status") == "recommendation"
    assert "Tài liệu này có nhiều chương/chủ đề" in vid.get("message", "")
    assert isinstance(vid.get("options"), list)


def test_video_quality_rules_rejection():
    gen = create_mock_resource_gen("test_quality_rules", num_docs=3)
    # Test formatting directly with problematic titles
    scenes = [
        {"title": "Ý chính", "voiceover": "Đây là ý chính", "duration_seconds": 15, "source_chunk_ids": []}
    ]
    formatted = gen._format_storyboard_schema(
        scenes=scenes,
        video_title="Test Video",
        video_mode="three_minute",
        target_user="student",
        duration_sec=30,
        docs=gen.vectorstore.docs
    )
    # The generic "Ý chính" title must never survive formatting.
    assert "Ý chính" not in formatted["scenes"][0]["title"]
    # Normalization re-grounds the scene from real document points, so this input
    # legitimately passes the gate afterwards. Gate-level rejection of scenes that
    # stay ungrounded is covered by test_scene_level_rejection_rules.
    assert formatted["scenes"][0]["source_chunk_ids"]
    assert formatted["quality_report"]["is_ready_to_render"]


def test_sixty_second_scene_cap():
    gen = create_mock_resource_gen("test_vid_60s_cap", num_docs=10)
    res = gen.generate_vid(topic="AI Basics", video_mode="sixty_second", render_mp4=False)
    vid = res.get("vid", {})
    assert vid.get("video_mode") == "sixty_second"
    assert 1 <= len(vid.get("scenes", [])) <= 5
    assert vid.get("estimated_duration_seconds", 0) > 0
    assert vid.get("video_title")
    assert vid.get("transcript")


def test_ten_minute_mode_supported():
    gen = create_mock_resource_gen("test_vid_10m", num_docs=10)
    res = gen.generate_vid(topic="Machine Learning", video_mode="ten_minute", render_mp4=False)
    vid = res.get("vid", {})
    assert vid.get("video_mode") == "ten_minute"
    assert len(vid.get("scenes", [])) <= 16
    # Every scene must carry duration and grounding metadata per storyboard schema.
    for sc in vid.get("scenes", []):
        assert sc.get("duration_seconds", 0) > 0
        assert "source_chunk_ids" in sc


def test_force_bypasses_large_pdf_recommendation():
    gen = create_mock_resource_gen("test_force", num_docs=20)
    res = gen.generate_vid(topic="tổng quan", video_mode="three_minute", render_mp4=False, force=True)
    vid = res.get("vid", {})
    assert vid.get("status") != "recommendation"
    assert vid.get("video_mode") == "three_minute"


def test_chapter_selection_bypasses_recommendation():
    gen = create_mock_resource_gen("test_chapter_scope", num_docs=20)
    res = gen.generate_vid(topic="tổng quan", video_mode="three_minute", render_mp4=False, chapter_id="Chương 2")
    vid = res.get("vid", {})
    assert vid.get("status") != "recommendation"


def test_scene_level_rejection_rules():
    gen = create_mock_resource_gen("test_scene_rules", num_docs=3)
    videos = [{
        "full_title": "Bài 1",
        "source_chunk_ids": ["chunk_1"],
        "storyboard": [
            {"title": "Cảnh A", "voiceover": "Cùng một lời thuyết minh lặp lại.", "source_chunk_ids": []},
            {"title": "Cảnh B", "voiceover": "Cùng một lời thuyết minh lặp lại.", "source_chunk_ids": ["chunk_2"],
             "screen_text": ["một dòng chữ trên màn hình quá dài vượt quá mười lăm từ cho phép nên phải bị đánh dấu cảnh báo ngay"]},
        ],
    }]
    report = gen._evaluate_quality_gate({"videos": videos}, "video")
    assert not report["is_university_ready"]
    joined = " ".join(report["warnings"])
    assert "source_chunk_ids" in joined
    assert "lặp lại" in joined
    assert "screen_text" in joined


def test_sixty_second_fallback_fits_duration_target():
    gen = create_mock_resource_gen("test_60s_duration_fit", num_docs=10)
    res = gen.generate_vid(topic="AI Basics", video_mode="sixty_second", render_mp4=False)
    vid = res.get("vid", {})
    total = sum(sc.get("duration_seconds", 0) for sc in vid.get("scenes", []))
    assert total == vid.get("estimated_duration_seconds")
    # Rounding can add ~0.5s per scene at most; the 60s target must hold in practice.
    assert total <= 66


def test_fallback_does_not_pad_repeated_scenes():
    # A 2-chunk document must not be inflated into 6-8 near-identical scenes.
    gen = create_mock_resource_gen("test_no_padding", num_docs=2)
    res = gen.generate_vid(topic="AI Basics", video_mode="three_minute", render_mp4=False)
    vid = res.get("vid", {})
    scenes = vid.get("scenes", [])
    assert 1 <= len(scenes) <= 2
    voiceovers = [sc.get("voiceover") for sc in scenes]
    assert len(voiceovers) == len(set(voiceovers))


def test_fallback_playlist_video_is_grounded_and_passes_gate():
    gen = create_mock_resource_gen("test_grounded_fallback", num_docs=8)
    res = gen.generate_vid(topic="Khóa học AI", video_mode="playlist_by_chapter")
    vid = res.get("vid", {})
    videos = vid.get("videos", [])
    assert videos
    # Video-level grounding is aggregated from its scenes' source_chunk_ids.
    assert videos[0].get("source_chunk_ids")
    report = vid.get("quality_report", {})
    assert report.get("score", 0) >= 80, report.get("warnings")


def test_vid_api_endpoints(monkeypatch):
    # These routes now require an authenticated, owning user (see main._verify_course_access).
    monkeypatch.setitem(
        main.app.dependency_overrides,
        main.get_current_user,
        lambda: main.UserInDB(id="test_admin", email="admin@example.com", password_hash="pwd", role="admin", is_active=True),
    )
    client = TestClient(app)
    mock_gen = create_mock_resource_gen("course_test_vid", num_docs=5)

    class MockRAG:
        def get_resource_generator(self):
            return mock_gen

    monkeypatch.setattr("backend.main._get_ready_course", lambda cid: MockRAG())

    # Generate 60s video
    resp = client.post("/api/generate-vid", json={
        "course_id": "course_test_vid",
        "video_mode": "sixty_second",
        "topic": "AI Hook",
        "render_mp4": False
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["vid"]["video_mode"] == "sixty_second"

    # Regenerate scene
    resp2 = client.post("/api/course/course_test_vid/vid/scene/regenerate", json={
        "scene_index": 1,
        "instruction": "Nói rõ hơn về ví dụ"
    })
    assert resp2.status_code == 200

    # Generate playlist and render one
    client.post("/api/generate-vid", json={
        "course_id": "course_test_vid",
        "video_mode": "playlist_by_chapter"
    })
    resp3 = client.post("/api/course/course_test_vid/vid/render", json={
        "video_index": 1
    })
    assert resp3.status_code == 200
