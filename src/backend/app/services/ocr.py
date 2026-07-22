"""OCR provider abstraction: OpenRouter vision (paid, default) or PaddleOCR (local, free,
CPU-only). Both share the same contract — `recognize(image_bytes) -> str`, best-effort, empty
string on failure — so `document_processor.py::_ocr_page`'s fail-soft convention (OCR failure
is never fatal to document processing) holds regardless of which provider is configured."""

import logging
from typing import Optional, Protocol

logger = logging.getLogger(__name__)


class OCRProvider(Protocol):
    def recognize(self, image_bytes: bytes) -> str:
        """Transcribe the text visible in a page image. Returns '' on any failure —
        callers must never treat OCR failure as fatal."""
        ...


class OpenRouterOCRProvider:
    """Today's default: send the page image to the configured OpenRouter vision model. A
    fresh `LLMService()` per call (matches pre-existing behavior) — cheap, since the client
    itself is lightweight; the actual cost is the per-call API request."""

    def recognize(self, image_bytes: bytes) -> str:
        from app.services.llm import LLMService

        return LLMService().ocr_page_image(image_bytes) or ""


class PaddleOCRProvider:
    """Local, free, CPU-only OCR via PaddleOCR. The underlying engine is expensive to
    construct (model load takes seconds to tens of seconds depending on cache warmth) so it
    is built once per process and reused — never re-instantiate per page.

    `enable_mkldnn=False` is required, not cosmetic: on at least one real CPU (verified
    2026-07-19), paddlepaddle 3.3.1's oneDNN/PIR execution path crashes with
    `NotImplementedError: (Unimplemented) ConvertPirAttribute2RuntimeAttribute...` on the very
    first inference call. Disabling oneDNN avoids that crash entirely at the cost of some CPU
    throughput (measured: ~20-25s per dense CJK page, ~620MB steady-state RSS, no leak across
    repeated calls in one process). This has only been verified against Chinese-script source
    text — Vietnamese/Latin-script accuracy with this same `lang` model is unverified."""

    _engine = None

    def __init__(self, lang: str = "ch"):
        self.lang = lang

    def _get_engine(self):
        if PaddleOCRProvider._engine is None:
            from paddleocr import PaddleOCR

            PaddleOCRProvider._engine = PaddleOCR(
                use_textline_orientation=True, lang=self.lang, enable_mkldnn=False
            )
        return PaddleOCRProvider._engine

    def recognize(self, image_bytes: bytes) -> str:
        try:
            import cv2
            import numpy as np

            array = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
            if array is None:
                return ""
            engine = self._get_engine()
            results = engine.predict(array)
            texts = []
            for result in results:
                rec_texts = result.get("rec_texts", []) if hasattr(result, "get") else getattr(result, "rec_texts", [])
                texts.extend(rec_texts)
            return "\n".join(texts).strip()
        except Exception as e:
            logger.warning(f"PaddleOCR recognition failed: {e}")
            return ""


_provider: Optional[OCRProvider] = None


def get_ocr_provider() -> OCRProvider:
    """Singleton, chosen once per process by OCR_PROVIDER — a PaddleOCR engine is too
    expensive to build per call, and there is no reason to re-check config on every page."""
    global _provider
    if _provider is None:
        from app.core.config import settings

        provider_name = getattr(settings, "OCR_PROVIDER", "openrouter")
        if provider_name == "paddleocr":
            _provider = PaddleOCRProvider()
        else:
            _provider = OpenRouterOCRProvider()
    return _provider


def _reset_provider_for_tests() -> None:
    """Test-only: clear the cached singleton. A test that changes OCR_PROVIDER (or monkeypatches
    PaddleOCRProvider) must call this first, or it'll see whatever a previous test cached."""
    global _provider
    _provider = None
    PaddleOCRProvider._engine = None
