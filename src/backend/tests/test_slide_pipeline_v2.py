"""Lecture-deck slide pipeline tests: schema, structure enforcement, 85 gate, PPTX export."""
import json
import os
import zipfile

from unittest.mock import MagicMock

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from backend.services import resource_gen


NOTES = (
    "Trong slide này, giảng viên bắt đầu bằng bối cảnh thực tế: vì sao mô hình cần học từ dữ liệu thay vì "
    "lập trình luật cứng. Sau đó diễn giải từng bullet: định nghĩa gradient descent, vai trò của tốc độ học, "
    "và điều kiện hội tụ. Đưa ví dụ phân loại ảnh chữ số để minh họa: mỗi epoch, mất mát giảm dần khi trọng số "
    "được cập nhật ngược hướng gradient. Nhấn mạnh sai lầm phổ biến là chọn tốc độ học quá lớn khiến mất mát "
    "dao động hoặc phân kỳ. Kết thúc bằng câu hỏi chuyển tiếp: điều gì xảy ra nếu gradient bằng không? Điều này "
    "dẫn sang slide tiếp theo về điểm dừng và cực tiểu địa phương trong quá trình tối ưu hóa mô hình học máy."
)


def _deck():
    def content_slide(i, slide_type, title, extra_screen=None):
        screen = {"bullets": [f"Bullet {j} về {title}" for j in range(1, 4)],
                  "formula": "", "code": "", "table": [], "diagram_description": ""}
        if extra_screen:
            screen.update(extra_screen)
        return {
            "slide_index": i,
            "slide_type": slide_type,
            "title": title,
            "key_message": f"Thông điệp cốt lõi của {title}.",
            "screen_content": screen,
            "speaker_notes": NOTES,
            "visual_instruction": {"type": "concept_map", "description": f"Sơ đồ khái niệm cho {title}", "labels": ["A", "B"]},
            "student_prompt": f"Câu hỏi cho lớp về {title}?",
            "source_chunk_ids": [f"chunk_{i}"],
        }

    return {
        "deck_title": "Gradient Descent và Tối ưu hóa Mô hình",
        "subtitle": "Từ trực quan đến công thức",
        "course_level": "university",
        "audience": "Sinh viên đại học",
        "estimated_duration_minutes": 45,
        "learning_outcomes": ["Giải thích được cơ chế gradient descent", "Chọn được tốc độ học phù hợp"],
        "slides": [
            content_slide(1, "motivation", "Vì sao mô hình phải học từ dữ liệu"),
            content_slide(2, "concept", "Trực quan về gradient descent"),
            content_slide(3, "formula_breakdown", "Công thức cập nhật trọng số",
                          {"formula": "w = w - lr * dL/dw"}),
            content_slide(4, "diagram", "Đường đi của gradient trên mặt mất mát",
                          {"diagram_description": "Mặt cong mất mát với các bước đi xuống"}),
            content_slide(5, "worked_example", "Ví dụ: một bước cập nhật với lr = 0.1"),
            content_slide(6, "comparison", "So sánh tốc độ học lớn và nhỏ",
                          {"table": [["Tiêu chí", "lr lớn", "lr nhỏ"], ["Hội tụ", "Dao động", "Chậm mà chắc"]]}),
            content_slide(7, "common_mistake", "Sai lầm: tốc độ học càng lớn càng tốt"),
            content_slide(8, "quick_check", "Kiểm tra nhanh: gradient bằng 0 nghĩa là gì"),
        ],
    }


def _generator(tmp_path, monkeypatch, llm_payload=None):
    docs = [
        Document(
            page_content=(
                f"Noi dung {i}: gradient descent cap nhat trong so nguoc huong dao ham cua ham mat mat. "
                "Toc do hoc dieu khien do dai buoc di va anh huong den su hoi tu cua qua trinh huan luyen."
            ),
            metadata={"chunk_id": f"chunk_{i}", "page": i},
        )
        for i in range(1, 13)
    ]
    vectorstore = MagicMock()
    vectorstore.as_retriever.return_value.invoke.return_value = docs

    rag = MagicMock()
    rag.course_id = "slidev2test"
    rag.vectorstore = vectorstore

    payload = llm_payload or _deck()

    def fake_get_llm(temperature=0.1, max_output_tokens=8192, task="default"):
        return RunnableLambda(lambda _p: json.dumps(payload, ensure_ascii=False))

    paths = {
        "slides": os.path.join(str(tmp_path), "slides.json"),
        "slides_pdf": os.path.join(str(tmp_path), "slides.pdf"),
        "slides_pptx": os.path.join(str(tmp_path), "slides.pptx"),
    }
    monkeypatch.setattr(resource_gen, "get_course_path", lambda cid: paths)
    monkeypatch.setattr(resource_gen, "get_llm", fake_get_llm)
    return resource_gen.ResourceGenerator(rag), paths


def test_slide_pipeline_produces_rigorous_deck_with_structure(tmp_path, monkeypatch):
    generator, paths = _generator(tmp_path, monkeypatch)
    result = generator.generate_slides_v2("Gradient Descent", num_slides=10)
    slides = result["slides"]

    types = [s["slide_type"] for s in slides]
    # Structure enforcement adds the missing title/objectives/recap/practice slides.
    assert types[0] == "title"
    assert types[1] == "objectives"
    assert "recap" in types and "practice" in types
    assert "worked_example" in types and "common_mistake" in types and "quick_check" in types

    for slide in slides:
        assert slide["slide_index"] >= 1
        assert "screen_content" in slide and "visual_instruction" in slide
        assert len(slide["bullets"]) <= 5
        assert slide["title"].strip().lower() not in {"ý chính", "nội dung chính", ""}
    content_slides = [s for s in slides if s["slide_type"] not in {"title", "objectives", "recap", "practice"}]
    assert all(s["source_chunk_ids"] for s in content_slides)
    assert all(len(s["speaker_notes"].split()) >= 50 for s in content_slides)

    quality = result["quality_report"]
    assert quality["score"] >= 85, quality
    assert quality["is_university_ready"] is True
    for key in ["academic_depth_score", "visual_quality_score", "teaching_quality_score", "source_grounding_score"]:
        assert key in quality

    dump = json.dumps(slides, ensure_ascii=False)
    for banned in ["Ý chính", "Ghi nhớ ý chính", "Contents", "BẮT ĐẦU DỮ LIỆU"]:
        assert banned not in dump

    # PPTX export: formula box, table, code-free, notes, and slide numbers present.
    pptx_path = generator.export_slides_pptx()
    assert os.path.getsize(pptx_path) > 20_000
    with zipfile.ZipFile(pptx_path) as archive:
        slide_xml_names = [n for n in archive.namelist() if n.startswith("ppt/slides/slide")]
        assert len(slide_xml_names) >= 10
        all_xml = "".join(archive.read(n).decode("utf-8") for n in sorted(slide_xml_names))
        assert "w = w - lr" in all_xml or "dL/dw" in all_xml  # formula rendered
        assert "lr lớn" in all_xml  # comparison table rendered
        assert "/ " not in "" and "2 / " in all_xml  # slide numbers rendered
        notes_names = [n for n in archive.namelist() if n.startswith("ppt/notesSlides/")]
        assert notes_names, "speaker notes must be exported"


def test_slide_gate_rejects_deck_without_notes_or_examples(tmp_path, monkeypatch):
    generator, _ = _generator(tmp_path, monkeypatch)
    bad_deck = {
        "slides": [
            {
                "slide_index": i,
                "slide_type": "concept",
                "title": f"Khái niệm {i}",
                "key_message": "",
                "bullets": ["Một bullet"],
                "speaker_notes": "Quá ngắn.",
                "source_chunk_ids": [],
            }
            for i in range(1, 6)
        ]
    }
    gate = generator._evaluate_quality_gate(bad_deck, "slides")
    assert gate["is_university_ready"] is False
    assert gate["score"] < 85
    assert any("speaker_notes" in w for w in gate["warnings"])
    assert any("source_chunk_ids" in w for w in gate["warnings"])
    assert any("ví dụ" in w for w in gate["warnings"])


def test_limited_context_returns_short_overview_deck_with_warning(tmp_path, monkeypatch):
    generator, _ = _generator(tmp_path, monkeypatch)
    # Only 1 usable chunk -> readiness for slides is not_enough_context.
    thin_docs = [Document(page_content="Noi dung ngan gon ve gradient descent trong hoc may.", metadata={"chunk_id": "chunk_1"})]
    generator.vectorstore.as_retriever.return_value.invoke.return_value = thin_docs

    result = generator.generate_slides_v2("Gradient Descent", num_slides=12)
    assert result["generation_status"]["status"] == "limited"
    assert result["generation_status"]["fallback_used"] == "short_overview_deck"
    assert 5 <= len(result["slides"]) <= 8
