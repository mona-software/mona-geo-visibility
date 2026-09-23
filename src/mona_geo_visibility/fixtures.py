"""Nạp fixture cho chế độ --dry-run: trả về câu trả lời giả lập theo vòng
xoay (round-robin) cho mỗi (engine, run_index) mà không gọi mạng."""

from __future__ import annotations

import json
from importlib import resources

from .engines import EngineResponse

_FIXTURE_FILENAME = "dry_run_responses.json"


def load_fixture_data() -> dict:
    with resources.files(__package__).joinpath("fixtures", _FIXTURE_FILENAME).open(
        "r", encoding="utf-8"
    ) as f:
        return json.load(f)


def fake_call(engine: str, run_index: int, model: str = "dry-run") -> EngineResponse:
    """Trả về 1 EngineResponse giả lập cho engine + lần chạy run_index (0-based).
    Xoay vòng qua danh sách fixture để mỗi lần chạy có câu trả lời khác nhau
    một chút, mô phỏng output AI dao động giữa các lần gọi."""
    data = load_fixture_data()
    engine_responses = data.get("default", {}).get(engine)
    if not engine_responses:
        return EngineResponse(engine=engine, model=model, error=f"no dry-run fixture for engine '{engine}'")

    text = engine_responses[run_index % len(engine_responses)]
    return EngineResponse(engine=engine, model=model, text=text, citations=[])
