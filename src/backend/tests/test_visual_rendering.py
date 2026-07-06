import json
import os
import zipfile

from langchain_core.documents import Document

from backend.services import resource_gen
from backend.services.resource_gen import ResourceGenerator


def _generator() -> ResourceGenerator:
    generator = object.__new__(ResourceGenerator)
    generator.course_id = "visualtest"
    return generator


SIX_SCENE_SLIDES = [
    {
        "title": "MEX trên cây",
        "content": "- Đường đi P(i,j)\n- MEX(S) trên tập đỉnh",
        "image_suggestion": "tree diagram with highlighted path",
    },
    {
        "title": "Knapsack query",
        "content": "- Trọng lượng W_i, giá trị V_i\n- Truy vấn L_j, R_j, C_j",
        "image_suggestion": "bag items capacity query",
    },
    {
        "title": "Grid board",
        "content": "- Bàn cờ N x M\n- Bảng con 2x2 được highlight",
        "image_suggestion": "grid board visual",
    },
    {
        "title": "Counting modulo",
        "content": "- sum(Ai * xi) <= M\n- Kết quả mod 10^9 + 7",
        "image_suggestion": "formula modulo combinatorics",
    },
    {
        "title": "Lesson map",
        "content": "- Tree/MEX\n- Knapsack\n- Grid\n- Modulo",
        "image_suggestion": "mind map recap",
    },
    {
        "title": "Tổng kết",
        "content": "- Đọc ràng buộc\n- Chọn thuật toán\n- Kiểm tra ví dụ",
        "image_suggestion": "summary recap icons",
    },
]


def test_math_text_is_rendered_as_typographic_notation():
    generator = _generator()

    rendered = generator._format_math_text(
        r"A_i, x_i, W_i, V_i, C_j, P(i,j), MEX(S), O(n log n), \sum A_i x_i \le M, sum(Ai * xi) <= M, 10^9 + 7"
    )

    assert "Aᵢ" in rendered
    assert "xᵢ" in rendered
    assert "Wᵢ" in rendered
    assert "Vᵢ" in rendered
    assert "Cⱼ" in rendered
    assert "P(i, j)" in rendered
    assert "MEX(S)" in rendered
    assert "O(n log n)" in rendered
    assert "Σ Aᵢ × xᵢ ≤ M" in rendered
    assert "Σ(Aᵢ × xᵢ) ≤ M" in rendered
    assert "10⁹ + 7" in rendered


def test_visual_type_inference_covers_lesson_concepts():
    generator = _generator()

    assert generator._infer_visual_type(SIX_SCENE_SLIDES[0]) == "tree_mex"
    assert generator._infer_visual_type(SIX_SCENE_SLIDES[1]) == "knapsack"
    assert generator._infer_visual_type(SIX_SCENE_SLIDES[2]) == "grid"
    assert generator._infer_visual_type(SIX_SCENE_SLIDES[3]) == "counting_modulo"
    assert generator._infer_visual_type(SIX_SCENE_SLIDES[4]) == "lesson_map"
    assert generator._infer_visual_type(SIX_SCENE_SLIDES[5]) == "summary"
    assert generator._infer_visual_type({"title": "Pseudocode", "content": "for i in range(n)"}) == "code"
    assert generator._infer_visual_type({"title": "Đồ thị", "content": "BFS trên node và edge"}) == "graph"
    assert generator._infer_visual_type({"title": "Quy hoạch động", "content": "dp state và transition"}) == "dp"


def test_export_slides_pptx_renders_six_scene_lesson(monkeypatch, tmp_path):
    generator = _generator()
    paths = {
        "slides": os.path.join(tmp_path, "slides.json"),
        "slides_pptx": os.path.join(tmp_path, "slides.pptx"),
    }
    monkeypatch.setattr(resource_gen, "get_course_path", lambda course_id: paths)

    with open(paths["slides"], "w", encoding="utf-8") as f:
        json.dump(SIX_SCENE_SLIDES, f, ensure_ascii=False)

    pptx_path = generator.export_slides_pptx()

    assert os.path.getsize(pptx_path) > 20_000
    with zipfile.ZipFile(pptx_path) as archive:
        slide_xml = archive.read("ppt/slides/slide4.xml").decode("utf-8")
    assert "10⁹ + 7" in slide_xml
    assert "Σ" in slide_xml


def test_render_scene_images_for_six_scene_lesson(tmp_path):
    generator = _generator()
    scenes = [
        {
            "title": slide["title"],
            "visual_text": slide["content"],
            "image_suggestion": slide["image_suggestion"],
            "voiceover": slide["content"],
        }
        for slide in SIX_SCENE_SLIDES
    ]

    for index, scene in enumerate(scenes, 1):
        path = os.path.join(tmp_path, f"scene_{index}.png")
        generator._render_scene_image(scene, index, path)
        assert os.path.getsize(path) > 8_000


def test_context_cleaner_removes_toc_and_preserves_source_chunk_ids():
    generator = _generator()
    docs = [
        Document(page_content="Contents 7.9 LLM Agents . . . . . . . . . . 118", metadata={"chunk_id": 1}),
        Document(
            page_content="Trí tuệNhân tạo sửdụng dữliệu để xây dựng mô hình dự đoán và hỗ trợ ra quyết định.",
            metadata={"chunk_id": 2},
        ),
        Document(page_content="118 119 120 . . . . . .", metadata={"chunk_id": 3}),
    ]

    context = generator._clean_docs_context(docs)

    assert "Contents" not in context
    assert ". . ." not in context
    assert "Trí tuệ Nhân" in context
    assert "sử dụng dữ liệu" in context
    assert "source_chunk_id: chunk_2" in context


def test_video_concat_uses_local_scene_filenames(monkeypatch, tmp_path):
    generator = _generator()
    paths = {"videos": os.path.join(tmp_path, "course_visualtest")}
    monkeypatch.setattr(resource_gen, "get_course_path", lambda course_id: paths)
    monkeypatch.setattr(generator, "_render_scene_image", lambda scene, index, path: open(path, "wb").write(b"png"))
    monkeypatch.setattr(generator, "_synthesize_voiceover", lambda text, path: open(path, "wb").write(b"mp3-data" * 20))

    def fake_clip(ffmpeg, image_path, audio_path, clip_path, seconds):
        with open(clip_path, "wb") as f:
            f.write(b"mp4-data")

    def fake_ffmpeg(command, cwd=None):
        assert cwd and cwd.endswith("assets")
        concat_path = os.path.join(cwd, "concat.txt")
        with open(concat_path, "r", encoding="utf-8") as f:
            content = f.read()
        assert "file 'scene_01.mp4'" in content
        assert "file 'scene_02.mp4'" in content
        assert "course_visualtest/assets/course_visualtest" not in content
        with open(os.path.join(cwd, "..", "final.mp4"), "wb") as f:
            f.write(b"final")

    monkeypatch.setattr(generator, "_render_scene_clip", fake_clip)
    monkeypatch.setattr(generator, "_run_ffmpeg", fake_ffmpeg)

    metadata = generator._render_vid(
        [
            {"title": "Cảnh 1", "visual_text": "- A", "voiceover": "Nội dung A", "source_chunk_ids": ["chunk_1"]},
            {"title": "Cảnh 2", "visual_text": "- B", "voiceover": "Nội dung B", "source_chunk_ids": ["chunk_2"]},
        ],
        duration_minutes=1,
    )

    assert metadata["status"] == "ready"
    assert "subtitles_srt" in metadata
    assert "debug_log" in metadata
    assert os.path.exists(os.path.join(paths["videos"], "vid.mp4"))
    assert os.path.exists(os.path.join(paths["videos"], "subtitles.srt"))
    assert os.path.exists(os.path.join(paths["videos"], "assets", "concat.txt"))


def test_video_renderer_alias_and_manim_template_selection():
    generator = _generator()

    assert generator._normalize_video_renderer("simple_slides") == "simple_templates"
    assert generator._normalize_video_renderer("simple_templates") == "simple_templates"
    assert generator._normalize_video_renderer("manim") == "manim"
    assert generator._normalize_video_renderer("unknown") == "manim"

    assert generator._select_manim_template({"title": "F1-score, precision và recall"}) == "confusion_matrix_scene"
    assert generator._select_manim_template({"title": "Gradient descent trên loss curve"}) == "gradient_descent_curve_scene"
    assert generator._select_manim_template({"title": "Neural network layers và backprop"}) == "neural_network_scene"
    assert generator._select_manim_template({"title": "Clustering bằng k-means"}) == "clustering_scene"
    assert generator._select_manim_template({"title": "Pandas DataFrame table"}) == "dataframe_table_scene"
    assert generator._select_manim_template({"visual_template": "flow_diagram"}) == "flow_diagram_scene"


def test_study_pack_is_derived_from_book_plan():
    generator = _generator()
    book = {
        "title": "Study Guide AI",
        "chapters": [
            {
                "title": "Python cho AI",
                "overview": "Chương này giới thiệu Python trong quy trình AI.",
                "chapter_summary": "Python giúp xử lý dữ liệu và xây dựng mô hình AI.",
                "lessons": [
                    {
                        "title": "Biến và vòng lặp",
                        "core_idea": "Biến lưu trạng thái, vòng lặp giúp xử lý dữ liệu lặp lại.",
                        "key_concepts": [
                            {"term": "Biến", "definition": "Tên đại diện cho một giá trị trong chương trình."}
                        ],
                        "source_chunk_ids": ["chunk_1"],
                    }
                ],
            }
        ],
        "glossary": [{"term": "AI", "definition": "Hệ thống mô phỏng năng lực trí tuệ.", "source_chunk_ids": ["chunk_2"]}],
    }

    study_pack = generator._build_study_pack_from_book(book, {"score": 92, "is_university_ready": True})

    assert study_pack["main_output"] == "study_guide_pdf"
    assert study_pack["study_guide"]["chapters"] == 1
    # build_mindmap_from_book stores parent/child links as ID-string references into the
    # flat `nodes` list (matching MINDMAP_GENERATION_PROMPT / generate_fallback_shallow_mindmap),
    # not embedded nested objects — resolve the chapter node and its lesson child by id.
    mindmap_nodes_by_id = {n["id"]: n for n in study_pack["mindmap"]["nodes"]}
    chapter_node = next(n for n in study_pack["mindmap"]["nodes"] if n["type"] == "chapter")
    assert chapter_node["title"] == "Python cho AI"
    lesson_id = chapter_node["children"][0]
    assert mindmap_nodes_by_id[lesson_id]["title"] == "Biến và vòng lặp"
    assert study_pack["high_yield_summary"][0]["summary"]
    assert any(card["front"] == "Biến" for card in study_pack["flashcards"])
    assert "chunk_1" in study_pack["source_chunk_ids"]


def test_manim_script_uses_safe_template_dispatch_only():
    generator = _generator()

    script = generator._build_manim_script(
        "gradient_descent_curve_scene",
        {
            "title": "Gradient descent",
            "screen_text": ["Điểm di chuyển xuống đường loss"],
            "visual_data": {"steps": ["Khởi tạo", "Tính gradient", "Cập nhật"]},
        },
        seconds=18,
    )

    assert "SCENE_DATA = json.loads" in script
    assert "dispatch = {" in script
    assert "gradient_descent_curve_scene" in script
    assert "exec(" not in script
    assert "eval(" not in script
    assert "subprocess" not in script


def test_render_vid_uses_manim_for_supported_scene(monkeypatch, tmp_path):
    generator = _generator()
    paths = {"videos": os.path.join(tmp_path, "course_visualtest")}
    monkeypatch.setattr(resource_gen, "get_course_path", lambda course_id: paths)
    monkeypatch.setattr(generator, "_synthesize_voiceover", lambda text, path: open(path, "wb").write(b"mp3-data" * 20))
    monkeypatch.setattr(
        generator,
        "_render_scene_image",
        lambda scene, index, path: (_ for _ in ()).throw(AssertionError("simple renderer should not run")),
    )

    rendered_templates = []

    def fake_manim(manim_path, ffmpeg, scene, index, clip_path, seconds, audio_path, assets_dir):
        rendered_templates.append(scene.get("visual_template"))
        with open(clip_path, "wb") as f:
            f.write(b"manim-mp4-data")
        return True

    def fake_ffmpeg(command, cwd=None):
        assert cwd and cwd.endswith("assets")
        with open(os.path.join(cwd, "..", "final.mp4"), "wb") as f:
            f.write(b"final")

    monkeypatch.setattr(generator, "_render_manim_scene_clip", fake_manim)
    monkeypatch.setattr(generator, "_run_ffmpeg", fake_ffmpeg)

    metadata = generator._render_vid(
        [
            {
                "title": "Gradient descent",
                "visual_template": "gradient_descent_curve_scene",
                "screen_text": ["Loss giảm dần"],
                "voiceover": "Quan sát điểm cập nhật theo hướng giảm loss.",
                "source_chunk_ids": ["chunk_1"],
            }
        ],
        duration_minutes=1,
        renderer="manim",
        manim_path="manim",
    )

    assert rendered_templates == ["gradient_descent_curve_scene"]
    assert metadata["renderer"] == "manim"
    assert metadata["manim_scene_count"] == 1
    assert metadata["simple_scene_count"] == 0
    assert metadata["scenes"][0]["rendered_with"] == "manim"
    assert os.path.exists(os.path.join(paths["videos"], "vid.mp4"))


def test_video_quality_gate_rejects_noisy_static_storyboard():
    generator = _generator()
    storyboard = {
        "videos": [
            {
                "transcript": "Ghi nhớ ý chính và liên hệ với nội dung tài liệu.",
                "subtitles_srt": "1\n00:00:00,000 --> 00:00:05,000\nGhi nhớ ý chính\n",
                "storyboard": [
                    {
                        "title": "Ý chính",
                        "screen_text": ["Contents 7.9 LLM Agents . . . . . . 118"],
                        "voiceover": "Ghi nhớ ý chính và liên hệ với nội dung tài liệu.",
                        "visual_template": "generic",
                        "source_chunk_ids": [],
                    }
                ],
                "quick_quiz": [],
            }
        ]
    }

    quality = generator._evaluate_quality_gate(storyboard, "video")

    assert quality["is_university_ready"] is False
    assert quality["engagement_score"] < 85
    assert quality["visual_score"] < 80
    assert any("Contents" in item or "raw chunks" in item or "rác" in item for item in quality["fixes_needed"] + quality["problems"])


def test_video_scene_normalization_removes_raw_chunk_noise():
    generator = _generator()
    docs = [
        Document(
            page_content="Python trong AI giúp xử lý dữ liệu, huấn luyện mô hình và đánh giá kết quả dự đoán.",
            metadata={"chunk_id": 42},
        )
    ]

    scenes = generator._normalize_scenes(
        [
            {
                "scene_index": 1,
                "scene_type": "concept",
                "title": "Ý chính",
                "screen_text": ["Contents 1 Python . . . . . 12", "dữliệu và mô hình"],
                "voiceover": "Ghi nhớ ý chính và liên hệ với nội dung tài liệu.",
                "visual_template": "concept_card",
                "visual_data": {"definition": "Contents 1 . . . . 12"},
            }
        ],
        1,
        docs,
    )

    scene_dump = json.dumps(scenes, ensure_ascii=False)
    assert "Contents" not in scene_dump
    assert ". . ." not in scene_dump
    assert "Ghi nhớ ý chính" not in scene_dump
    assert scenes[0]["source_chunk_ids"] == ["chunk_42"]
    assert scenes[0]["visual_template"] == "concept_card"


def test_fallback_video_scenes_are_dynamic_and_grounded():
    generator = _generator()
    docs = [
        Document(
            page_content=(
                "Trí tuệ Nhân tạo sử dụng dữ liệu để học quy luật, dự đoán kết quả và hỗ trợ ra quyết định "
                "trong các bài toán thực tế như phân loại ảnh, dự đoán giá và phân tích văn bản."
            ),
            metadata={"chunk_id": 11},
        ),
        Document(
            page_content=(
                "Python hữu ích cho AI vì có thư viện xử lý dữ liệu, huấn luyện mô hình và trực quan hóa kết quả. "
                "Người học cần hiểu biến, hàm, vòng lặp và cách kiểm tra lỗi thường gặp."
            ),
            metadata={"chunk_id": 12},
        ),
    ]

    scenes = generator._build_fallback_scenes(docs, 6)
    templates = {scene["visual_template"] for scene in scenes}

    # Anti-padding rule: a 2-chunk document yields 2 honest scenes, never 6
    # near-identical ones (repeated voiceover would fail the video quality gate).
    assert len(scenes) == 2
    assert len(templates) == 2
    voiceovers = [scene["voiceover"] for scene in scenes]
    assert len(voiceovers) == len(set(voiceovers))
    assert all(scene["source_chunk_ids"] for scene in scenes)
    assert "Ý chính" not in json.dumps(scenes, ensure_ascii=False)


def test_book_pdf_elements_includes_all_academic_sections():
    generator = _generator()
    book_data = {
        "title": "Cơ sở Trí tuệ Nhân tạo",
        "subtitle": "Giáo trình đại học",
        "audience": "Sinh viên CNTT",
        "estimated_duration": "20 giờ",
        "table_of_contents": [
            {
                "chapter_index": 1,
                "chapter_title": "Nhập môn AI",
                "lessons": [{"lesson_index": 1, "lesson_title": "Khái niệm và ứng dụng"}]
            }
        ],
        "chapters": [
            {
                "chapter_index": 1,
                "title": "Chương 1: Nhập môn AI",
                "overview": "Chương này giới thiệu nền tảng cơ bản về AI.",
                "learning_outcomes": ["Giải thích được định nghĩa AI."],
                "lessons": [
                    {
                        "lesson_index": 1,
                        "title": "Bài 1.1: Khái niệm và ứng dụng",
                        "duration": "30 phút",
                        "core_idea": "AI giúp máy tính học từ dữ liệu.",
                        "why_it_matters": "Quan trọng trong tự động hóa.",
                        "learning_objectives": ["Hiểu cơ chế học máy."],
                        "explanation": "Giải thích chi tiết === BẮT ĐẦU DỮ LIỆU TRUY XUẤT === không được xuất hiện.",
                        "must_know_points": ["Cần có dữ liệu tốt."],
                        "key_concepts": [{"term": "Machine Learning", "definition": "Học máy từ dữ liệu"}],
                        "example": "Ví dụ phân loại thư rác.",
                        "common_misunderstanding": {"mistake": "AI thay thế hoàn toàn con người", "correction": "AI là công cụ hỗ trợ"},
                        "practice_activity": "Tìm 3 ứng dụng AI thực tế.",
                        "quick_check": [{"question": "AI là gì?", "answer": "Hệ thống học từ dữ liệu", "explanation": "Theo định nghĩa chuẩn"}]
                    }
                ],
                "chapter_summary": "Tóm tắt chương 1."
            }
        ],
        "glossary": [
            {"term": "Machine Learning", "definition": "Học máy từ dữ liệu", "related_chapter": 1}
        ],
        "review_plan": {
            "ten_minute": ["Ôn tập điểm trọng tâm"],
            "thirty_minute": ["Làm câu hỏi tự kiểm tra"],
            "one_hour": ["Làm bài tập lớn"]
        }
    }

    elements = generator._book_pdf_elements(book_data)
    rendered_text = "\n".join([t for t, s in elements])

    assert "Ý tưởng cốt lõi (Core Idea):" in rendered_text
    assert "Tại sao quan trọng (Why It Matters):" in rendered_text
    assert "Sai lầm phổ biến & Cách hiểu đúng:" in rendered_text
    assert "Thuật ngữ & Khái niệm (Glossary)" in rendered_text
    assert "Kế hoạch ôn tập (Review Plan)" in rendered_text
    assert "BẮT ĐẦU DỮ LIỆU TRUY XUẤT" not in rendered_text


def test_all_generators_return_task_8_quality_metadata():
    generator = _generator()
    quality = generator._evaluate_quality_gate({"title": "Test resource", "source_chunk_ids": ["chunk_1"]}, "book")
    enriched = generator._quality_with_context_stats(quality, {"title": "Test resource", "source_chunk_ids": ["chunk_1"]}, [Document(page_content="Test content for evaluation.")])

    for key in ["is_final", "quality_score", "source_grounding_score", "warnings", "fixes_needed"]:
        assert key in enriched
    assert enriched["is_final"] is True


def test_validate_and_normalize_book_plan_fixes_generic_titles_and_assigns_chunks(tmp_path, monkeypatch):
    from backend.core import config
    monkeypatch.setattr(config, "BOOKS_DIR", str(tmp_path))
    generator = _generator()
    docs = [Document(page_content="Khái niệm Mạng nơ-ron tích chập CNN trong xử lý ảnh.", metadata={"chunk_id": "chunk_cnn", "page": 1})]
    raw_plan = {
        "title": "Chương 1",
        "chapters": [
            {
                "chapter_index": 1,
                "title": "Chương 1",
                "lessons": [{"title": "Bài 1.1"}]
            }
        ]
    }
    validated = generator._validate_and_normalize_book_plan(raw_plan, docs, "Sinh viên CNTT", "normal")
    assert validated["title"] != "Chương 1"
    assert validated["chapters"][0]["title"] != "Chương 1"
    assert validated["chapters"][0]["lessons"][0]["source_chunk_ids"] == ["chunk_cnn"]
    assert os.path.exists(os.path.join(str(tmp_path), generator.course_id, "plan.json"))


def test_validate_book_export_safety_rejects_prohibited_markers_and_generic_chapter_titles():
    import pytest
    generator = _generator()
    bad_marker_book = {
        "title": "Sách AI",
        "chapters": [
            {
                "chapter_index": 1,
                "title": "Khái niệm AI",
                "lessons": [{"title": "Bài 1", "explanation": "Nội dung kèm === BẮT ĐẦU DỮ LIỆU TRUY XUẤT ==="}]
            }
        ]
    }
    with pytest.raises(ValueError, match="prohibited marker"):
        generator._validate_book_export_safety(bad_marker_book)

    generic_chapter_book = {
        "title": "Sách AI",
        "chapters": [
            {
                "chapter_index": 1,
                "title": "Chương 1",
                "lessons": [{"title": "Bài 1", "explanation": "Nội dung hợp lệ"}]
            }
        ]
    }
    with pytest.raises(ValueError, match="blank or generic chapter title"):
        generator._validate_book_export_safety(generic_chapter_book)


def test_slide_from_point_generates_professional_schema():
    generator = _generator()
    point = {"text": "Khái niệm Mạng nơ-ron tích chập CNN trong nhận dạng hình ảnh.", "source_chunk_ids": ["chunk_cnn"]}
    slide = generator._slide_from_point(point, 1, {"title": "Cơ chế Mạng CNN"})
    assert slide["slide_index"] == 1
    assert slide["slide_type"] == "concept"
    assert len(slide["bullets"]) >= 3
    assert len(slide["bullets"]) <= 5
    assert isinstance(slide["visual"], dict)
    assert len(slide["speaker_notes"].split()) >= 20


def test_evaluate_quality_gate_penalizes_generic_slide_titles_and_fewer_than_3_bullets():
    generator = _generator()
    bad_deck = {
        "slides": [
            {
                "title": "Ý chính",
                "bullets": ["Một bullet duy nhất"],
                "speaker_notes": "Ngắn",
                "source_chunk_ids": ["chunk_1"],
            }
        ]
    }
    report = generator._evaluate_quality_gate(bad_deck, "slides")
    assert report["score"] < 85
    assert any("generic" in p for p in report["problems"])
    assert any("ít hơn 3 bullet" in p for p in report["problems"])


def test_video_generator_teaching_flow_and_example_card(tmp_path):
    generator = _generator()
    flow_items = [generator._video_flow_item(i, 9) for i in range(9)]
    types = [t for t, _ in flow_items]
    assert "hook" in types
    assert "objective" in types
    assert "concept" in types
    assert "example" in types
    assert "common_mistake" in types
    assert "quiz" in types
    assert "recap" in types

    scene = {
        "visual_template": "example_card",
        "title": "Ví dụ phân loại thư rác",
        "visual_data": {"example_title": "Hệ thống lọc email spam"},
        "screen_text": ["Nhận diện từ khóa spam", "Phân tích địa chỉ gửi", "Đưa ra xác suất spam"],
    }
    image_path = os.path.join(tmp_path, "test_example_card.png")
    generator._render_scene_image(scene, 1, image_path)
    assert os.path.exists(image_path)
    assert os.path.getsize(image_path) > 1000


def test_quiz_generator_exam_pack_and_high_yield_lesson_structure(monkeypatch):
    generator = _generator()
    docs = [
        Document(
            page_content="Thuật ngữ AI là Trí tuệ Nhân tạo. Ứng dụng AI trong học tập giúp phân tích dữ liệu hiệu quả.",
            metadata={"chunk_id": "chunk_1", "page": 1, "source": "doc.pdf"},
        ),
        Document(
            page_content="Machine Learning là máy học, giúp tự động rút ra quy luật từ dữ liệu.",
            metadata={"chunk_id": "chunk_2", "page": 2, "source": "doc.pdf"},
        ),
    ]

    class DummyRetriever:
        def invoke(self, query):
            return docs

    class DummyVectorStore:
        def as_retriever(self, **kwargs):
            return DummyRetriever()

    generator.vectorstore = DummyVectorStore()
    monkeypatch.setattr(generator, "_invoke_chain", lambda *args, **kwargs: '{"questions": [{"question": "AI là gì?", "options": ["A", "B", "C", "D"], "correct": 0, "explanation": "Theo tài liệu"}]}')

    quiz_res = generator.generate_quiz_v2("AI trong học tập", quantity=5, difficulty="exam")
    assert "exam_pack" in quiz_res
    assert quiz_res["exam_pack"] is not None
    assert "short_answer_questions" in quiz_res["exam_pack"]
    assert "flashcards" in quiz_res["exam_pack"]

    # source_chunk_ids must be KEPT (every generated item needs grounding metadata per the
    # product's quality-gate contract); only raw internal keys like chunk_id/page/source are
    # stripped from public payloads.
    sanitized = generator._sanitize_payload(
        {"questions": [{"question": "Q?", "source_chunk_ids": ["chunk_1"], "chunk_id": "chunk_1", "page": 1}]}
    )
    assert sanitized["questions"][0]["source_chunk_ids"] == ["chunk_1"]
    assert "chunk_id" not in sanitized["questions"][0]
    assert "page" not in sanitized["questions"][0]
