from pathlib import Path

import pytest

from mona_geo_visibility.promptset import PromptSetError, load_prompt_set

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "examples" / "prompt-set-thiet-ke-website.yaml"


def test_load_example_prompt_set():
    pset = load_prompt_set(EXAMPLE_PATH)
    assert pset.brand_name == "Websmith VN"
    assert "Websmith" in pset.brand_aliases
    assert len(pset.prompts) >= 10
    assert "WebCraft Saigon" in pset.competitors


def test_load_missing_file_raises():
    with pytest.raises(PromptSetError):
        load_prompt_set("/path/khong/ton/tai.yaml")


def test_load_prompt_set_missing_brand(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("prompts:\n  - text: 'câu hỏi bất kỳ'\n", encoding="utf-8")
    with pytest.raises(PromptSetError):
        load_prompt_set(bad_file)


def test_load_prompt_set_missing_prompts(tmp_path):
    bad_file = tmp_path / "bad.yaml"
    bad_file.write_text("brand:\n  name: 'Test Brand'\n", encoding="utf-8")
    with pytest.raises(PromptSetError):
        load_prompt_set(bad_file)


def test_load_prompt_set_string_style_prompts(tmp_path):
    f = tmp_path / "ok.yaml"
    f.write_text(
        "brand:\n  name: 'Test Brand'\nprompts:\n  - 'câu hỏi 1'\n  - 'câu hỏi 2'\n",
        encoding="utf-8",
    )
    pset = load_prompt_set(f)
    assert len(pset.prompts) == 2
    assert pset.prompts[0].id == "p1"
