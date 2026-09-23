"""Gọi thẳng REST API công khai của 3 hãng bằng urllib (stdlib) — không phụ
thuộc SDK riêng (openai / google-generativeai / anthropic) để giữ repo nhẹ.

Mỗi hàm `call_*` nhận 1 prompt (str) + model (str) + key (str) và trả về
EngineResponse: text trả lời (đã rút gọn), citations (nếu API có trả), hoặc
error nếu gọi thất bại. KHÔNG hàm nào raise ra ngoài cho lỗi mạng/API — mọi
lỗi được bắt và đóng gói vào EngineResponse.error để cli.py xử lý tiếp
(skip engine đó, chạy tiếp các engine còn lại).
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass, field

DEFAULT_TIMEOUT = 60

# Model mặc định: RẺ/NHANH, không hard-code model đắt tiền. Override được qua
# flag CLI hoặc config.
DEFAULT_MODEL_OPENAI = "gpt-4o-mini"
DEFAULT_MODEL_GEMINI = "gemini-1.5-flash"
DEFAULT_MODEL_ANTHROPIC = "claude-3-5-haiku-20241022"

ENV_KEY_OPENAI = "OPENAI_API_KEY"
ENV_KEY_GEMINI = "GEMINI_API_KEY"
ENV_KEY_ANTHROPIC = "ANTHROPIC_API_KEY"


@dataclass
class EngineResponse:
    engine: str
    model: str
    text: str = ""
    citations: list[str] = field(default_factory=list)
    error: str | None = None
    skipped_reason: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and self.skipped_reason is None


def _post_json(url: str, headers: dict, payload: dict, timeout: int = DEFAULT_TIMEOUT) -> dict:
    """POST JSON bằng urllib, trả về dict đã parse. Raise lại lỗi gốc để
    caller tự bắt và ghi vào EngineResponse.error."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8")
    return json.loads(body)


def _describe_http_error(exc: urllib.error.HTTPError) -> str:
    try:
        body = exc.read().decode("utf-8", errors="replace")
    except Exception:
        body = ""
    return f"HTTP {exc.code}: {body[:500]}"


# ---------------------------------------------------------------------------
# OpenAI — Chat Completions API
# https://platform.openai.com/docs/api-reference/chat/create
# ---------------------------------------------------------------------------

def call_openai(prompt: str, model: str = DEFAULT_MODEL_OPENAI, api_key: str | None = None,
                 timeout: int = DEFAULT_TIMEOUT) -> EngineResponse:
    key = api_key or os.environ.get(ENV_KEY_OPENAI)
    if not key:
        return EngineResponse(engine="openai", model=model, skipped_reason="no API key")

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        data = _post_json(url, headers, payload, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return EngineResponse(engine="openai", model=model, error=_describe_http_error(exc))
    except urllib.error.URLError as exc:
        return EngineResponse(engine="openai", model=model, error=f"network error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001 — muốn bắt mọi lỗi bất ngờ, không crash pipeline
        return EngineResponse(engine="openai", model=model, error=f"unexpected error: {exc}")

    try:
        text = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return EngineResponse(engine="openai", model=model, error=f"unexpected response shape: {data}")

    # Chat Completions API chuẩn không trả citation/grounding — để rỗng.
    return EngineResponse(engine="openai", model=model, text=text, citations=[])


# ---------------------------------------------------------------------------
# Google Gemini — generateContent API
# https://ai.google.dev/api/generate-content
# ---------------------------------------------------------------------------

def call_gemini(prompt: str, model: str = DEFAULT_MODEL_GEMINI, api_key: str | None = None,
                 timeout: int = DEFAULT_TIMEOUT) -> EngineResponse:
    key = api_key or os.environ.get(ENV_KEY_GEMINI)
    if not key:
        return EngineResponse(engine="gemini", model=model, skipped_reason="no API key")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    headers = {"Content-Type": "application/json"}
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
    }

    try:
        data = _post_json(url, headers, payload, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return EngineResponse(engine="gemini", model=model, error=_describe_http_error(exc))
    except urllib.error.URLError as exc:
        return EngineResponse(engine="gemini", model=model, error=f"network error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        return EngineResponse(engine="gemini", model=model, error=f"unexpected error: {exc}")

    try:
        candidate = data["candidates"][0]
        parts = candidate["content"]["parts"]
        text = "".join(p.get("text", "") for p in parts)
    except (KeyError, IndexError, TypeError):
        return EngineResponse(engine="gemini", model=model, error=f"unexpected response shape: {data}")

    # groundingMetadata chỉ xuất hiện khi bật Google Search grounding — optional.
    citations: list[str] = []
    try:
        grounding = candidate.get("groundingMetadata", {})
        chunks = grounding.get("groundingChunks", [])
        for chunk in chunks:
            uri = chunk.get("web", {}).get("uri")
            if uri:
                citations.append(uri)
    except Exception:  # noqa: BLE001 — citation là optional, lỗi ở đây không được làm fail cả response
        pass

    return EngineResponse(engine="gemini", model=model, text=text, citations=citations)


# ---------------------------------------------------------------------------
# Anthropic — Messages API
# https://docs.anthropic.com/en/api/messages
# ---------------------------------------------------------------------------

def call_anthropic(prompt: str, model: str = DEFAULT_MODEL_ANTHROPIC, api_key: str | None = None,
                    timeout: int = DEFAULT_TIMEOUT) -> EngineResponse:
    key = api_key or os.environ.get(ENV_KEY_ANTHROPIC)
    if not key:
        return EngineResponse(engine="anthropic", model=model, skipped_reason="no API key")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }

    try:
        data = _post_json(url, headers, payload, timeout=timeout)
    except urllib.error.HTTPError as exc:
        return EngineResponse(engine="anthropic", model=model, error=_describe_http_error(exc))
    except urllib.error.URLError as exc:
        return EngineResponse(engine="anthropic", model=model, error=f"network error: {exc.reason}")
    except Exception as exc:  # noqa: BLE001
        return EngineResponse(engine="anthropic", model=model, error=f"unexpected error: {exc}")

    try:
        blocks = data["content"]
        text = "".join(b.get("text", "") for b in blocks if b.get("type") == "text")
    except (KeyError, TypeError):
        return EngineResponse(engine="anthropic", model=model, error=f"unexpected response shape: {data}")

    # Messages API chuẩn (không bật web search tool) không trả citation.
    return EngineResponse(engine="anthropic", model=model, text=text, citations=[])


ENV_KEY_BY_ENGINE = {
    "openai": ENV_KEY_OPENAI,
    "gemini": ENV_KEY_GEMINI,
    "anthropic": ENV_KEY_ANTHROPIC,
}


def has_api_key(engine: str) -> bool:
    """Kiểm tra biến môi trường tương ứng có được set không — dùng để quyết
    định skip cả engine trước khi tốn lượt gọi API nào (tránh gọi API thật
    chỉ để "dò" xem có key hay không)."""
    env_var = ENV_KEY_BY_ENGINE.get(engine)
    if not env_var:
        return False
    return bool(os.environ.get(env_var))


ENGINE_CALLERS = {
    "openai": call_openai,
    "gemini": call_gemini,
    "anthropic": call_anthropic,
}

DEFAULT_MODELS = {
    "openai": DEFAULT_MODEL_OPENAI,
    "gemini": DEFAULT_MODEL_GEMINI,
    "anthropic": DEFAULT_MODEL_ANTHROPIC,
}
