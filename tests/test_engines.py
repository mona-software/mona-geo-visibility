import os

from mona_geo_visibility.engines import call_anthropic, call_gemini, call_openai, has_api_key


def test_call_openai_skipped_without_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    resp = call_openai("prompt bất kỳ", api_key=None)
    assert resp.skipped_reason == "no API key"
    assert resp.error is None
    assert resp.ok is False


def test_call_gemini_skipped_without_key(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    resp = call_gemini("prompt bất kỳ", api_key=None)
    assert resp.skipped_reason == "no API key"


def test_call_anthropic_skipped_without_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resp = call_anthropic("prompt bất kỳ", api_key=None)
    assert resp.skipped_reason == "no API key"


def test_has_api_key_reads_env(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert has_api_key("openai") is False
    monkeypatch.setenv("OPENAI_API_KEY", "fixture-value-not-a-real-key-000")
    assert has_api_key("openai") is True


def test_has_api_key_unknown_engine():
    assert has_api_key("does-not-exist") is False
