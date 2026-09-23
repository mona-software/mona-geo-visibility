"""Đọc file prompt-set (YAML hoặc JSON) do người dùng tự viết.

Schema mong đợi:

    brand:
      name: "Websmith VN"
      aliases: ["Websmith", "Web Smith VN"]
    competitors:            # optional
      - "WebCraft Saigon"
      - "PixelNest"
    prompts:
      - id: "p1"             # optional, tự sinh nếu thiếu
        text: "công ty nào thiết kế website chuyên nghiệp tại Việt Nam"
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class PromptItem:
    id: str
    text: str


@dataclass
class PromptSet:
    brand_name: str
    brand_aliases: list[str] = field(default_factory=list)
    competitors: list[str] = field(default_factory=list)
    prompts: list[PromptItem] = field(default_factory=list)


class PromptSetError(ValueError):
    pass


def load_prompt_set(path: str | Path) -> PromptSet:
    p = Path(path)
    if not p.exists():
        raise PromptSetError(f"Không tìm thấy file prompt set: {p}")

    raw_text = p.read_text(encoding="utf-8")
    if p.suffix.lower() == ".json":
        data = json.loads(raw_text)
    else:
        data = yaml.safe_load(raw_text)

    if not isinstance(data, dict):
        raise PromptSetError("File prompt set phải là 1 object (mapping) ở cấp cao nhất")

    brand = data.get("brand")
    if not brand or not isinstance(brand, dict) or not brand.get("name"):
        raise PromptSetError("Thiếu 'brand.name' trong file prompt set")

    brand_name = str(brand["name"]).strip()
    brand_aliases = [str(a).strip() for a in brand.get("aliases", []) if str(a).strip()]

    competitors = [str(c).strip() for c in data.get("competitors", []) if str(c).strip()]

    prompts_raw = data.get("prompts")
    if not prompts_raw or not isinstance(prompts_raw, list):
        raise PromptSetError("Thiếu danh sách 'prompts' (list) trong file prompt set")

    prompts: list[PromptItem] = []
    for idx, item in enumerate(prompts_raw, start=1):
        if isinstance(item, str):
            text = item.strip()
            pid = f"p{idx}"
        elif isinstance(item, dict):
            text = str(item.get("text", "")).strip()
            pid = str(item.get("id") or f"p{idx}")
        else:
            raise PromptSetError(f"Prompt thứ {idx} không hợp lệ: {item!r}")

        if not text:
            raise PromptSetError(f"Prompt thứ {idx} thiếu 'text'")
        prompts.append(PromptItem(id=pid, text=text))

    if not prompts:
        raise PromptSetError("Danh sách 'prompts' rỗng")

    return PromptSet(
        brand_name=brand_name,
        brand_aliases=brand_aliases,
        competitors=competitors,
        prompts=prompts,
    )
