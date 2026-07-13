"""Contract tests for OpenRouter free-first structured output routing."""

import pytest

from app.core.config import settings
from app.services.llm import LLMGenerationError, LLMService


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [type("Choice", (), {"message": type("Message", (), {"content": content})()})()]


class _FakeCompletions:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return _FakeCompletion(response)


def _llm_with_fake_client(responses):
    llm = LLMService()
    completions = _FakeCompletions(responses)
    llm.client = type("Client", (), {"chat": type("Chat", (), {"completions": completions})()})()
    return llm, completions


def test_free_router_succeeds_with_strict_schema(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_FREE_MODEL", "free-test")
    llm, completions = _llm_with_fake_client(['{"title": "Nhập môn Trí tuệ nhân tạo"}'])

    result = llm.generate_course_title("mẫu nội dung tài liệu")

    assert result.title == "Nhập môn Trí tuệ nhân tạo"
    assert [call["model"] for call in completions.calls] == ["free-test"]
    assert completions.calls[0]["extra_body"] == {"provider": {"require_parameters": True}}
    assert completions.calls[0]["response_format"]["json_schema"]["strict"] is True


def test_invalid_free_schema_retries_paid_model(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_FREE_MODEL", "free-test")
    monkeypatch.setattr(settings, "OPENROUTER_PAID_MODEL", "paid-test")
    llm, completions = _llm_with_fake_client(["{not valid json", '{"title": "Kinh tế học"}'])

    result = llm.generate_course_title("mẫu nội dung tài liệu")

    assert result.title == "Kinh tế học"
    assert [call["model"] for call in completions.calls] == ["free-test", "paid-test"]


def test_both_models_fail_raises_generation_error():
    llm, completions = _llm_with_fake_client(["{bad", "{still bad"])

    with pytest.raises(LLMGenerationError):
        llm.generate_course_title("mẫu nội dung tài liệu")

    assert len(completions.calls) == 2
