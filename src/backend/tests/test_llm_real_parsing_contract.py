"""Contract tests for paid-only OpenRouter structured-output generation."""

import pytest

from app.core.config import Settings, settings
from app.services.llm import LLMGenerationError, LLMService


class _FakeCompletion:
    def __init__(self, content):
        self.choices = [
            type(
                "Choice",
                (),
                {"message": type("Message", (), {"content": content})()},
            )()
        ]


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
    llm.client = type(
        "Client",
        (),
        {"chat": type("Chat", (), {"completions": completions})()},
    )()
    return llm, completions


def _settings(**overrides):
    values = {
        "DATABASE_URL": "sqlite:///./test.db",
        "JWT_SECRET": "test-secret",
        "OPENROUTER_API_KEY": "test-key",
    }
    values.update(overrides)
    return Settings(**values)


def test_paid_model_succeeds_with_strict_schema(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "google/gemini-2.5-pro")
    llm, completions = _llm_with_fake_client(
        ['{"title": "Nhập môn Trí tuệ nhân tạo"}']
    )

    result = llm.generate_course_title("mẫu nội dung tài liệu")

    assert result.title == "Nhập môn Trí tuệ nhân tạo"
    assert [call["model"] for call in completions.calls] == [
        "google/gemini-2.5-pro"
    ]
    assert completions.calls[0]["extra_body"] == {
        "provider": {"require_parameters": True}
    }
    assert completions.calls[0]["response_format"]["json_schema"]["strict"] is True


def test_invalid_schema_retries_the_same_paid_model(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "google/gemini-2.5-pro")
    llm, completions = _llm_with_fake_client(
        ["{not valid json", '{"title": "Kinh tế học"}']
    )

    result = llm.generate_course_title("mẫu nội dung tài liệu")

    assert result.title == "Kinh tế học"
    assert [call["model"] for call in completions.calls] == [
        "google/gemini-2.5-pro",
        "google/gemini-2.5-pro",
    ]


@pytest.mark.parametrize(
    "responses",
    [
        [RuntimeError("provider down"), RuntimeError("provider still down")],
        [None, None],
        ["{bad", "{still bad"],
    ],
)
def test_paid_model_failures_raise_after_two_attempts(responses):
    llm, completions = _llm_with_fake_client(responses)

    with pytest.raises(LLMGenerationError):
        llm.generate_course_title("mẫu nội dung tài liệu")

    assert len(completions.calls) == 2
    assert len({call["model"] for call in completions.calls}) == 1


def test_production_mode_never_returns_mock_generation():
    llm = LLMService()
    llm._test_mode = False
    llm.client = None

    with pytest.raises(LLMGenerationError):
        llm.generate_course_title("mẫu nội dung tài liệu")


def test_production_client_initialization_failure_is_loud(monkeypatch):
    import openai

    llm = LLMService()
    llm._test_mode = False

    def _raise_on_init(**_kwargs):
        raise RuntimeError("client init failed")

    monkeypatch.setattr(openai, "OpenAI", _raise_on_init)

    with pytest.raises(LLMGenerationError):
        llm._init_client()


def test_ocr_retries_the_same_paid_model_and_preserves_image_payload(monkeypatch):
    monkeypatch.setattr(settings, "OPENROUTER_MODEL", "google/gemini-2.5-pro")
    llm, completions = _llm_with_fake_client(
        [RuntimeError("temporary provider error"), "Nội dung trang PDF"]
    )

    result = llm.ocr_page_image(b"fake-png")

    assert result == "Nội dung trang PDF"
    assert [call["model"] for call in completions.calls] == [
        "google/gemini-2.5-pro",
        "google/gemini-2.5-pro",
    ]
    message_content = completions.calls[0]["messages"][0]["content"]
    assert message_content[1]["type"] == "image_url"
    assert message_content[1]["image_url"]["url"].startswith("data:image/png;base64,")


def test_ocr_returns_empty_after_two_failed_paid_attempts():
    llm, completions = _llm_with_fake_client([None, None])

    assert llm.ocr_page_image(b"fake-png") == ""
    assert len(completions.calls) == 2


def test_openrouter_model_defaults_to_gemini_pro(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)

    configured = _settings()

    assert configured.OPENROUTER_MODEL == "google/gemini-2.5-pro"


@pytest.mark.parametrize(
    "model",
    ["openrouter/" + "free", "vendor/model" + ":free", ""],
)
def test_openrouter_model_rejects_non_paid_values(model):
    with pytest.raises(ValueError):
        _settings(OPENROUTER_MODEL=model)


def test_legacy_model_environment_variables_are_ignored(monkeypatch):
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)
    monkeypatch.setenv("OPENROUTER_" + "FREE_MODEL", "legacy-free")
    monkeypatch.setenv("OPENROUTER_" + "PAID_MODEL", "legacy-paid")

    configured = _settings()

    assert configured.OPENROUTER_MODEL == "google/gemini-2.5-pro"
