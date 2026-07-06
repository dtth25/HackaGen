from langchain_core.documents import Document

from backend.services.doc_processor import analyze_document_quality


def _pages(texts, scanned=False):
    total = len(texts)
    return [
        Document(page_content=text, metadata={"pdf_total_pages": total, "scanned_pdf": scanned})
        for text in texts
    ]


def test_good_textbook_is_full_readiness():
    docs = _pages(
        [f"Nội dung chương {i} về Trí tuệ nhân tạo và học máy. " * 40 for i in range(1, 21)]
    )
    report = analyze_document_quality("doc_textbook", "textbook.pdf", docs)

    assert report["generation_readiness"] == "full"
    assert report["is_scanned_or_image_based"] is False
    assert report["document_type"] in {"textbook", "mixed_content"}
    assert report["clean_context_score"] >= 75
    assert report["file_name"] == "textbook.pdf"


def test_short_two_page_pdf_is_not_full():
    docs = _pages(["Bài viết ngắn về khái niệm cơ bản trong lập trình. " * 15] * 2)
    report = analyze_document_quality("doc_short", "short.pdf", docs)

    assert report["generation_readiness"] in {"limited", "summary_only"}
    assert report["generation_readiness"] != "full"
    assert report["extracted_char_count"] > 0


def test_toc_heavy_pdf_flags_noise_but_keeps_body():
    toc_text = (
        "Mục lục\nChương 1 . . . . . . . . 5\nChương 2 . . . . . . . . 12\n"
        + ("Nội dung thực tế của chương học rất chi tiết và đầy đủ. " * 30)
    )
    docs = _pages([toc_text] * 5)
    report = analyze_document_quality("doc_toc", "toc.pdf", docs)

    assert report["has_toc_noise"] is True
    assert report["has_dot_leaders"] is True
    # Body content still present, so generation should not be fully blocked.
    assert report["generation_readiness"] != "insufficient"


def test_scanned_pdf_needs_ocr():
    docs = _pages(["ab"], scanned=True)
    report = analyze_document_quality("doc_scan", "scan.pdf", docs)

    assert report["is_scanned_or_image_based"] is True
    assert report["generation_readiness"] == "needs_ocr"
    assert "OCR" in " ".join(report["recommended_actions"])


def test_mixed_noisy_pdf_is_not_insufficient_when_body_exists():
    docs = _pages(
        [
            "1\n2\n3\n" + ("Đoạn nội dung thân bài dài với nhiều thông tin hữu ích cho người học. " * 20)
            for _ in range(4)
        ]
    )
    report = analyze_document_quality("doc_mixed", "mixed.pdf", docs)

    assert report["generation_readiness"] in {"full", "limited", "summary_only"}
    assert report["extracted_char_count"] > 500
