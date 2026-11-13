import json

import pytest

from src.llm_summarizer import (
    InvalidSummaryError,
    LLMServiceError,
    MissingAPIKeyError,
    summarize_log,
    validate_summary_response,
)


VALID_SUMMARY = {
    "summary": "A package could not be imported.",
    "error_type": "ModuleNotFoundError",
    "severity": "High",
    "root_cause": "The module is unavailable in this environment.",
    "evidence": ["ModuleNotFoundError: No module named 'demo'"],
    "suggested_fix": ["Install the package in the active environment."],
    "recommended_steps": ["Install it.", "Re-run the build."],
    "confidence": "High",
    "needs_investigation": False,
}


def test_validates_structured_json_response():
    assert validate_summary_response(json.dumps(VALID_SUMMARY)) == VALID_SUMMARY


@pytest.mark.parametrize(
    "response",
    [
        "not json",
        [],
        {"summary": "missing fields"},
        {**VALID_SUMMARY, "severity": "Urgent"},
        {**VALID_SUMMARY, "evidence": "not a list"},
        {**VALID_SUMMARY, "needs_investigation": "no"},
    ],
)
def test_rejects_invalid_llm_responses(response):
    with pytest.raises(InvalidSummaryError):
        validate_summary_response(response)


def test_missing_api_key_is_reported(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(MissingAPIKeyError, match="GEMINI_API_KEY is not set"):
        summarize_log("ERROR: build failed")


@pytest.mark.parametrize(
    ("log", "error_type"),
    [
        ("ModuleNotFoundError: No module named 'demo'", "ModuleNotFoundError"),
        ("SyntaxError: invalid syntax", "SyntaxError"),
        ("FAILED tests/test_app.py::test_result", "TestFailure"),
    ],
)
def test_offline_mode_returns_deterministic_structured_summary(log, error_type):
    first = summarize_log(log, offline=True)
    second = summarize_log(log, offline=True)
    assert first == second
    assert first["error_type"] == error_type
    assert first["evidence"]


def test_offline_mode_summarizes_successful_build():
    result = summarize_log("Build succeeded", offline=True)
    assert result["error_type"] == "None"
    assert result["needs_investigation"] is False


def test_empty_log_is_rejected():
    with pytest.raises(ValueError, match="empty"):
        summarize_log(" \n ", offline=True)


def test_gemini_api_failure_is_handled_without_leaking_details(monkeypatch):
    from google import genai

    def fail_client(*args, **kwargs):
        raise RuntimeError("sensitive provider detail")

    monkeypatch.setattr(genai, "Client", fail_client)
    with pytest.raises(LLMServiceError, match="Gemini analysis failed") as error:
        summarize_log("ERROR: build failed", api_key="test-key")
    assert "sensitive provider detail" not in str(error.value)
