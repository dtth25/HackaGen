"""Two-stage book pipeline tests: blueprint -> chapters -> assembled book -> gated PDF."""
import json
import os
import re

from unittest.mock import MagicMock

from langchain_core.documents import Document
from langchain_core.runnables import RunnableLambda

from backend.core import config as core_config
from backend.services import resource_gen


LONG_TECH = (
    "Về mặt kỹ thuật, thuật toán lan truyền ngược tính đạo hàm của hàm mất mát theo từng trọng số "
    "bằng quy tắc chuỗi, đi ngược từ lớp đầu ra về lớp đầu vào. Mỗi nơ-ron lưu giá trị kích hoạt "
    "trong lượt truyền xuôi để tái sử dụng khi tính gradient, giúp độ phức tạp chỉ tuyến tính theo số cạnh. "
    "Điều kiện áp dụng là mọi hàm kích hoạt phải khả vi hoặc khả vi từng khúc như ReLU."
)

BLUEPRINT = {
    "course_title": "Nhập môn Mạng nơ-ron và Học sâu",
    "course_level": "university",
    "audience": "sinh viên",
    "prerequisites": ["Đại số tuyến tính cơ bản"],
    "learning_outcomes": ["Giải thích được cơ chế lan truyền ngược"],
    "course_units": [
        {
            "unit_id": f"unit_0{u}",
            "title": title,
            "big_idea": "Học từ dữ liệu bằng cách tối ưu hàm mất mát.",
            "why_it_matters": "Nền tảng của mọi hệ thống học sâu hiện đại.",
            "key_concepts": ["Gradient descent", "Hàm kích hoạt"],
            "definitions": [{"term": "Gradient descent", "definition": "Thuật toán tối ưu cập nhật trọng số theo đạo hàm."}],
            "formulas": [{"name": "Cập nhật trọng số", "formula": "w = w - lr * dL/dw", "meaning": "lr là tốc độ học"}],
            "examples": ["Phân loại ảnh chữ số viết tay"],
            "common_misconceptions": [{"mistake": "Tốc độ học càng lớn càng tốt", "correction": "Quá lớn làm phân kỳ."}],
            "worked_examples": [{"title": "Một bước gradient", "problem": "Tính bước cập nhật", "outline": "Đạo hàm nhân lr"}],
            "practice_problems": [{"difficulty": "easy", "question": "Nêu vai trò của tốc độ học."}],
            "source_chunk_ids": [f"chunk_{u * 3 - 2}", f"chunk_{u * 3 - 1}", f"chunk_{u * 3}"],
        }
        for u, title in [
            (1, "Nền tảng mạng nơ-ron nhân tạo"),
            (2, "Lan truyền ngược và tối ưu hóa"),
            (3, "Huấn luyện và đánh giá mô hình"),
        ]
    ],
    "glossary": [{"term": "Epoch", "definition": "Một lượt duyệt toàn bộ tập huấn luyện."}],
    "assessment_plan": [{"stage": "Sau đơn vị 1", "method": "Quiz ngắn", "focus": "Khái niệm gradient"}],
    "source_chunk_ids": ["chunk_1", "chunk_2"],
}


def _make_chapter(idx: int) -> dict:
    return {
        "chapter_index": idx,
        "title": BLUEPRINT["course_units"][idx - 1]["title"],
        "chapter_overview": "Chương này dạy cơ chế học của mạng nơ-ron từ trực quan đến công thức.",
        "learning_objectives": ["Giải thích cơ chế lan truyền ngược"],
        "prerequisites": ["Đạo hàm cơ bản"],
        "big_picture": "Mọi kỹ thuật sau đều dựa trên việc tối ưu trọng số bằng gradient.",
        "core_concepts": [
            {
                "term": f"Gradient descent (chương {idx})",
                "definition": "Thuật toán tối ưu lặp cập nhật trọng số ngược hướng gradient.",
                "intuition": "Như dò dốc xuống thung lũng trong sương mù: mỗi bước đi theo hướng dốc nhất đi xuống.",
                "technical_explanation": LONG_TECH,
                "example": "Với lr=0.1 và dL/dw=0.4, trọng số w=1.0 thành 0.96.",
                "non_example": "Chọn trọng số ngẫu nhiên mỗi vòng không phải gradient descent.",
                "common_mistake": {"mistake": "Tin rằng luôn đạt cực tiểu toàn cục.", "correction": "Chỉ đảm bảo cực tiểu địa phương với hàm không lồi."},
                "formula": "w = w - lr * dL/dw",
                "code": "for epoch in range(n):\n    w -= lr * grad(w)",
                "source_chunk_ids": [f"chunk_{idx * 3 - 2}"],
            },
            {
                "term": f"Hàm kích hoạt (chương {idx})",
                "definition": "Hàm phi tuyến áp dụng lên tổng có trọng số của mỗi nơ-ron.",
                "intuition": "Công tắc mềm quyết định tín hiệu nào được truyền tiếp.",
                "technical_explanation": LONG_TECH,
                "example": "ReLU(x) = max(0, x) cắt phần âm của tín hiệu.",
                "non_example": "Hàm tuyến tính y = 2x: chồng nhiều lớp vẫn tuyến tính.",
                "common_mistake": {"mistake": "Dùng sigmoid cho mạng rất sâu.", "correction": "Sigmoid gây tiêu biến gradient."},
                "formula": "",
                "code": "",
                "source_chunk_ids": [f"chunk_{idx * 3 - 1}"],
            },
        ],
        "worked_examples": [
            {
                "title": "Một bước cập nhật trọng số",
                "problem": "Cho w=1.0, lr=0.1, dL/dw=0.4. Tính w mới.",
                "step_by_step_solution": [
                    "Bước 1: Xác định gradient dL/dw = 0.4.",
                    "Bước 2: Nhân với tốc độ học: 0.1 * 0.4 = 0.04.",
                    "Bước 3: Trừ vào trọng số: w = 1.0 - 0.04 = 0.96.",
                ],
                "why_each_step_matters": "Tách riêng từng phép tính giúp thấy vai trò của mỗi siêu tham số.",
                "common_error": "Cộng thay vì trừ gradient.",
                "source_chunk_ids": [f"chunk_{idx * 3}"],
            }
        ],
        "practice_problems": [
            {"difficulty": "easy", "question": "Tốc độ học điều khiển điều gì?", "hint": "Độ dài bước.", "solution": "Độ lớn mỗi bước cập nhật.", "source_chunk_ids": [f"chunk_{idx * 3 - 2}"]},
            {"difficulty": "medium", "question": "Vì sao cần hàm kích hoạt phi tuyến?", "hint": "Chồng hàm tuyến tính.", "solution": "Nhiều lớp tuyến tính tương đương một lớp.", "source_chunk_ids": [f"chunk_{idx * 3 - 1}"]},
            {"difficulty": "hard", "question": "Vì sao một bước gradient giảm mất mát với lr đủ nhỏ?", "hint": "Taylor bậc nhất.", "solution": "L(w - lr*g) xấp xỉ L(w) - lr*||g||^2 nhỏ hơn L(w) khi g khác 0.", "source_chunk_ids": [f"chunk_{idx * 3}"]},
        ],
        "chapter_summary": "Gradient descent cập nhật trọng số ngược hướng đạo hàm.",
        "active_recall_questions": ["Viết lại công thức cập nhật trọng số từ trí nhớ."],
        "connections_to_other_chapters": ["Chương sau xây các bộ tối ưu nâng cao trên nền gradient descent."],
        "source_chunk_ids": [f"chunk_{idx * 3 - 2}", f"chunk_{idx * 3 - 1}", f"chunk_{idx * 3}"],
    }


def _fake_generator(tmp_path, monkeypatch):
    docs = [
        Document(
            page_content=(
                f"Chuong {i}: Mang no-ron nhan tao va thuat toan lan truyen nguoc. "
                f"Dinh nghia khai niem so {i}: gradient descent cap nhat trong so theo dao ham. "
                "Vi du minh hoa: phan loai anh chu so viet tay voi ham mat mat cross-entropy."
            ),
            metadata={"chunk_id": f"chunk_{i}", "page": i},
        )
        for i in range(1, 13)
    ]
    vectorstore = MagicMock()
    vectorstore.as_retriever.return_value.invoke.return_value = docs

    rag = MagicMock()
    rag.course_id = "bookv2test"
    rag.vectorstore = vectorstore

    call_state = {"chapter": 0}

    def fake_get_llm(temperature=0.1, max_output_tokens=8192, task="default"):
        def respond(_prompt_value):
            if task == "course":
                return json.dumps(BLUEPRINT, ensure_ascii=False)
            call_state["chapter"] += 1
            return json.dumps(_make_chapter(min(call_state["chapter"], 3)), ensure_ascii=False)

        return RunnableLambda(respond)

    paths = {
        "book": os.path.join(str(tmp_path), "book.json"),
        "book_pdf": os.path.join(str(tmp_path), "book.pdf"),
        "vector_meta": os.path.join(str(tmp_path), "meta.json"),
    }
    monkeypatch.setattr(resource_gen, "get_course_path", lambda cid: paths)
    monkeypatch.setattr(resource_gen, "get_llm", fake_get_llm)
    monkeypatch.setattr(core_config, "BOOKS_DIR", str(tmp_path))
    return resource_gen.ResourceGenerator(rag), paths


def test_two_stage_book_pipeline_produces_rigorous_grounded_book(tmp_path, monkeypatch):
    generator, paths = _fake_generator(tmp_path, monkeypatch)
    book = generator.generate_book(user_prompt="", target_audience="sinh viên")["book"]

    assert book["title"] == "Nhập môn Mạng nơ-ron và Học sâu"
    assert len(book["chapters"]) == 3
    for chapter in book["chapters"]:
        assert chapter["core_concepts"]
        assert all(c["intuition"] and c["technical_explanation"] for c in chapter["core_concepts"])
        assert chapter["worked_examples"][0]["step_by_step_solution"]
        assert {"easy", "medium", "hard"} <= {p["difficulty"] for p in chapter["practice_problems"]}
        assert chapter["source_chunk_ids"] and all(i.startswith("chunk_") for i in chapter["source_chunk_ids"])
        assert chapter["lessons"], "back-compat lessons must be derived from core concepts"
        assert chapter["active_recall_questions"] and chapter["big_picture"]

    assert book["how_to_use"] and book["course_roadmap"] and book["problem_set"]
    assert book["glossary"] and book["review_plan"]["one_hour"]
    assert book["quality_report"]["score"] >= 85
    assert book["quality_report"]["is_university_ready"] is True
    assert book["generation_status"]["status"] == "full"

    dump = json.dumps(book, ensure_ascii=False)
    for banned in ["Ý chính", "Ghi nhớ ý chính", "BẮT ĐẦU DỮ LIỆU", "MÃ ĐỊNH DANH TRANG", "Contents"]:
        assert banned not in dump
    assert not re.search(r"(?:\.\s*){4,}", dump)

    assert os.path.getsize(paths["book_pdf"]) > 50_000
    assert os.path.exists(os.path.join(str(tmp_path), "bookv2test", "blueprint.json"))

    import fitz

    with fitz.open(paths["book_pdf"]) as pdf:
        assert len(pdf) >= 5  # cover + TOC + body pages


def test_shallow_book_fails_85_gate(tmp_path, monkeypatch):
    generator, _ = _fake_generator(tmp_path, monkeypatch)
    shallow = {
        "title": "Sách",
        "chapters": [
            {
                "chapter_index": 1,
                "title": "Chương 1",
                "core_concepts": [
                    {"term": "X", "definition": "ngắn", "intuition": "", "technical_explanation": "",
                     "example": "", "non_example": "", "common_mistake": {}, "source_chunk_ids": []}
                ],
                "worked_examples": [],
                "practice_problems": [],
                "lessons": [],
            }
        ],
    }
    gate = generator._evaluate_quality_gate(shallow, "book")
    assert gate["is_university_ready"] is False
    assert gate["score"] < 85
    assert gate["warnings"]
