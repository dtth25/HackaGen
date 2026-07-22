"""Coverage for the OCR provider abstraction (services/ocr.py) — provider selection by
config, and that fail-soft behavior (empty string on any failure) holds for both providers.
PaddleOCR's real engine is never constructed here (it needs a ~180MB model download and
20+ seconds per call) — only its interface contract is exercised, via monkeypatching."""

import app.services.ocr as ocr_module
from app.services.ocr import (
    OpenRouterOCRProvider,
    PaddleOCRProvider,
    get_ocr_provider,
)


def setup_function():
    ocr_module._reset_provider_for_tests()


def teardown_function():
    ocr_module._reset_provider_for_tests()


def test_get_ocr_provider_defaults_to_openrouter(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "OCR_PROVIDER", "openrouter")
    provider = get_ocr_provider()
    assert isinstance(provider, OpenRouterOCRProvider)


def test_get_ocr_provider_selects_paddleocr(monkeypatch):
    from app.core.config import settings

    monkeypatch.setattr(settings, "OCR_PROVIDER", "paddleocr")
    provider = get_ocr_provider()
    assert isinstance(provider, PaddleOCRProvider)


def test_get_ocr_provider_is_a_singleton_per_process():
    a = get_ocr_provider()
    b = get_ocr_provider()
    assert a is b


def test_openrouter_provider_recognize_delegates_to_llm_service(monkeypatch):
    calls = []

    class _FakeLLMService:
        def ocr_page_image(self, image_bytes):
            calls.append(image_bytes)
            return "  recognized text  "

    monkeypatch.setattr("app.services.llm.LLMService", _FakeLLMService)
    result = OpenRouterOCRProvider().recognize(b"fake-png-bytes")

    assert result == "  recognized text  "
    assert calls == [b"fake-png-bytes"]


def test_openrouter_provider_recognize_returns_empty_string_on_none():
    class _FakeLLMService:
        def ocr_page_image(self, image_bytes):
            return None

    import app.services.llm as llm_module
    original = llm_module.LLMService
    llm_module.LLMService = _FakeLLMService
    try:
        result = OpenRouterOCRProvider().recognize(b"x")
    finally:
        llm_module.LLMService = original

    assert result == ""


def test_paddleocr_provider_recognize_joins_rec_texts(monkeypatch):
    class _FakeResult(dict):
        pass

    class _FakeEngine:
        def predict(self, array):
            return [_FakeResult(rec_texts=["dòng một", "dòng hai"])]

    provider = PaddleOCRProvider()
    monkeypatch.setattr(provider, "_get_engine", lambda: _FakeEngine())

    # A real 2x2 pixel PNG (via Pillow) so cv2.imdecode succeeds without needing a real page render.
    tiny_png = (
        b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x02\x00\x00\x00\x02\x08\x02\x00\x00\x00"
        b"\xfd\xd4\x9as\x00\x00\x00\x13IDATx\x9cc\xfc\xff\xff?\x03\x03\x03\x13\x03\x18\x00\x00$\x06"
        b"\x03\x01]\xa2N\x88\x00\x00\x00\x00IEND\xaeB`\x82"
    )
    result = provider.recognize(tiny_png)

    assert result == "dòng một\ndòng hai"


def test_paddleocr_provider_recognize_returns_empty_string_on_any_failure(monkeypatch):
    provider = PaddleOCRProvider()

    def _boom():
        raise RuntimeError("model load failed")

    monkeypatch.setattr(provider, "_get_engine", _boom)
    result = provider.recognize(b"not-a-real-png")

    assert result == ""


def test_paddleocr_provider_recognize_returns_empty_string_on_undecodable_bytes(monkeypatch):
    provider = PaddleOCRProvider()
    monkeypatch.setattr(provider, "_get_engine", lambda: (_ for _ in ()).throw(AssertionError("engine should not be built for undecodable input")))

    result = provider.recognize(b"not a real image at all")

    assert result == ""
