"""Contract tests for LLMService._call_gemini_strict's REAL parsing/retry path.

Every other test in this suite runs with PYTEST_CURRENT_TEST set, which makes
LLMService._init_client() leave self.client as None — so _call_gemini_strict always
takes the `fallback_fn()` branch and the actual google-genai response parsing
(response.text -> schema_model.model_validate_json), the 2-attempt retry loop, and the
per-attempt exception handling are never exercised by anything else in the suite. A
future google-genai upgrade that changes response shape or GenerateContentConfig
behavior would not be caught by any existing test.

These tests bypass that short-circuit deliberately by setting `.client` on an already-
constructed LLMService to a fake object shaped like the real SDK client, so the real
code path in _call_gemini_strict runs end to end against a controlled fake response.
"""

from app.core.config import settings
from app.services.llm import LLMGenerationError, LLMService
from app.schemas.generator_output import CourseTitleOutput


class _FakeResponse:
    def __init__(self, text):
        self.text = text


class _FakeModels:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def generate_content(self, model, contents, config):
        self.calls.append({"model": model, "contents": contents, "config": config})
        item = self._responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return _FakeResponse(item)


class _FakeClient:
    def __init__(self, responses):
        self.models = _FakeModels(responses)


def _llm_with_fake_client(responses) -> LLMService:
    llm = LLMService()  # PYTEST_CURRENT_TEST keeps this offline (self.client stays None)
    llm.client = _FakeClient(responses)  # bypass the short-circuit for this one instance
    return llm


def test_real_parsing_path_succeeds_on_first_attempt(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    llm = _llm_with_fake_client(['{"title": "Nhập môn Trí tuệ nhân tạo"}'])

    result = llm.generate_course_title("mẫu nội dung tài liệu")

    assert isinstance(result, CourseTitleOutput)
    assert result.title == "Nhập môn Trí tuệ nhân tạo"
    assert len(llm.client.models.calls) == 1
    assert llm.client.models.calls[0]["model"] == llm.model_name


def test_real_parsing_path_retries_on_invalid_json_then_succeeds(monkeypatch):
    """First response is malformed JSON — must retry once (attempts=2 default) and
    succeed with the second, real response rather than falling back or raising."""
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr("app.services.llm.time.sleep", lambda *_: None)
    llm = _llm_with_fake_client(
        ["{not valid json", '{"title": "Kinh tế học đại cương"}']
    )

    result = llm.generate_course_title("mẫu nội dung tài liệu")

    assert result.title == "Kinh tế học đại cương"
    assert len(llm.client.models.calls) == 2


def test_real_parsing_path_exhausts_retries_and_raises(monkeypatch):
    """Both attempts return malformed JSON and OpenRouter isn't configured — must raise
    LLMGenerationError, not silently fall back to a fake/empty title."""
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")
    monkeypatch.setattr("app.services.llm.time.sleep", lambda *_: None)
    llm = _llm_with_fake_client(["{not valid json", "{also not valid"])

    try:
        llm.generate_course_title("mẫu nội dung tài liệu")
        assert False, "expected LLMGenerationError"
    except LLMGenerationError:
        pass

    assert len(llm.client.models.calls) == 2
