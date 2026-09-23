"""Phân tích câu trả lời của AI: brand có được nhắc không, vị trí trong danh sách,
đối thủ nào xuất hiện, và tính điểm visibility / share of voice.

Toàn bộ hàm ở đây là pure function (không gọi mạng) để test dễ và tái sử dụng
cho cả nhánh --dry-run lẫn nhánh gọi API thật.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Tách danh sách / listicle trong câu trả lời (để tìm vị trí thứ mấy)
# ---------------------------------------------------------------------------

# Khớp các kiểu đánh số/gạch đầu dòng phổ biến khi AI liệt kê danh sách:
# "1. Tên", "1) Tên", "- Tên", "* Tên", "**1. Tên**"
_LIST_ITEM_RE = re.compile(
    r"^\s*(?:\*\*)?(?:(\d{1,2})[.\):]|[-*•])\s*(?:\*\*)?\s*(.+)$",
    re.MULTILINE,
)


def split_into_list_items(text: str) -> list[str]:
    """Tách văn bản thành các dòng "item" nếu nó có dạng danh sách/listicle.

    Trả về danh sách rỗng nếu văn bản không có cấu trúc danh sách rõ ràng
    (không có dòng nào khớp pattern đánh số/gạch đầu dòng).
    """
    items: list[str] = []
    for match in _LIST_ITEM_RE.finditer(text):
        content = match.group(2).strip()
        if content:
            items.append(content)
    return items


# ---------------------------------------------------------------------------
# So khớp brand / alias trong text (không phân biệt hoa thường)
# ---------------------------------------------------------------------------

def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _name_pattern(name: str) -> re.Pattern:
    """Dựng regex khớp 'nguyên cụm từ' name, không phân biệt hoa thường,
    cho phép biên là khoảng trắng/dấu câu (không bắt buộc \\b vì tên có thể
    chứa ký tự không phải word, ví dụ "Web.Design")."""
    escaped = re.escape(name.strip())
    # thay khoảng trắng đã escape bằng \s+ để khớp cả khi có nhiều khoảng trắng
    escaped = escaped.replace(r"\ ", r"\s+")
    return re.compile(rf"(?<![\w]){escaped}(?![\w])", re.IGNORECASE)


def find_brand_mentions(text: str, brand_name: str, aliases: list[str] | None = None) -> list[str]:
    """Trả về danh sách các biến thể tên (brand_name hoặc alias) thực sự xuất
    hiện trong text. Rỗng nếu không nhắc gì."""
    names = [brand_name] + list(aliases or [])
    found = []
    for name in names:
        if not name:
            continue
        if _name_pattern(name).search(text):
            found.append(name)
    return found


def brand_mentioned(text: str, brand_name: str, aliases: list[str] | None = None) -> bool:
    return bool(find_brand_mentions(text, brand_name, aliases))


def find_brand_position(text: str, brand_name: str, aliases: list[str] | None = None) -> int | None:
    """Nếu câu trả lời có cấu trúc danh sách và brand xuất hiện trong 1 item,
    trả về vị trí (1-based) của item đó. Trả None nếu không phải danh sách
    hoặc brand không nằm trong item nào."""
    items = split_into_list_items(text)
    if not items:
        return None
    names = [brand_name] + list(aliases or [])
    for idx, item in enumerate(items, start=1):
        for name in names:
            if name and _name_pattern(name).search(item):
                return idx
    return None


# ---------------------------------------------------------------------------
# Phát hiện đối thủ
# ---------------------------------------------------------------------------

def find_known_competitors(text: str, competitors: list[str]) -> list[str]:
    """Match chính xác (theo tên đã khai báo trước trong config) — ưu tiên
    dùng cách này khi user đã khai competitors, độ chính xác cao."""
    found = []
    for comp in competitors:
        if comp and _name_pattern(comp).search(text):
            found.append(comp)
    return found


# Các từ khoá tiếng Việt hay đứng trước tên công ty/nhà cung cấp trong câu văn
_COMPANY_CONTEXT_WORDS = (
    r"công ty|dịch vụ|nhà cung cấp|đơn vị|thương hiệu|agency|studio|"
    r"tập đoàn|nền tảng|website|trang"
)

# Cụm "Tên Riêng Viết Hoa" (>=1 từ, mỗi từ bắt đầu bằng chữ hoa, cho phép số/dấu gạch)
_PROPER_NOUN_RE = re.compile(
    r"\b(?:[A-ZÀÁẢÃẠÂẦẤẨẪẬĂẰẮẲẴẶÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]"
    r"[\wÀ-ỹ]*(?:[.\-][\wÀ-ỹ]+)*\s*){1,4}"
)

_CONTEXT_NEAR_RE = re.compile(
    # Từ khoá ngữ cảnh không phân biệt hoa/thường (?i:...), nhưng phần "filler"
    # phía sau PHẢI là chữ thường thật sự — nếu để cả cụm re.IGNORECASE thì
    # [a-z] sẽ khớp luôn cả chữ hoa và nuốt mất tên riêng viết hoa theo sau.
    rf"(?i:{_COMPANY_CONTEXT_WORDS})\s+(?:[a-zàảãạ]+\s+){{0,3}}",
)


def guess_competitor_candidates(text: str, exclude: list[str] | None = None, window: int = 60) -> list[str]:
    """Heuristic BEST-EFFORT: tìm các cụm 'Tên Riêng Viết Hoa' xuất hiện gần
    (trong khoảng `window` ký tự sau) các từ ngữ cảnh như "công ty", "dịch vụ",
    "nhà cung cấp"... Đây KHÔNG phải nhận diện chính xác — chỉ là gợi ý để
    người dùng tự soát lại. Không dùng kết quả này để tính Share of Voice
    một cách tuyệt đối, chỉ dùng làm danh sách ứng viên tham khảo.
    """
    exclude_norm = {_normalize(e) for e in (exclude or [])}
    candidates: dict[str, int] = {}

    for ctx_match in _CONTEXT_NEAR_RE.finditer(text):
        start = ctx_match.end()
        snippet = text[start:start + window]
        noun_match = _PROPER_NOUN_RE.search(snippet)
        if not noun_match:
            continue
        candidate = noun_match.group(0).strip().rstrip(".,;:!?")
        if not candidate or len(candidate) < 2:
            continue
        if _normalize(candidate) in exclude_norm:
            continue
        # loại các từ chung chung hay bị bắt nhầm (đầu câu, viết hoa ngẫu nhiên)
        if _normalize(candidate) in {"tôi", "bạn", "việt nam", "ai", "chatgpt", "gemini", "claude"}:
            continue
        candidates[candidate] = candidates.get(candidate, 0) + 1

    # sắp theo tần suất xuất hiện giảm dần, giữ thứ tự ổn định
    return sorted(candidates, key=lambda k: (-candidates[k], k))


# ---------------------------------------------------------------------------
# Cấu trúc kết quả 1 lần chạy (1 prompt x 1 engine x 1 run)
# ---------------------------------------------------------------------------

@dataclass
class RunResult:
    prompt_id: str
    engine: str
    run_index: int
    response_text: str
    brand_mentioned: bool
    brand_position: int | None
    competitors_found: list[str] = field(default_factory=list)
    competitor_candidates: list[str] = field(default_factory=list)
    citations: list[str] = field(default_factory=list)
    error: str | None = None
    skipped_reason: str | None = None


def analyze_response(
    prompt_id: str,
    engine: str,
    run_index: int,
    response_text: str,
    brand_name: str,
    aliases: list[str] | None = None,
    known_competitors: list[str] | None = None,
    citations: list[str] | None = None,
) -> RunResult:
    """Phân tích 1 câu trả lời thô và trả về RunResult đầy đủ."""
    mentioned = brand_mentioned(response_text, brand_name, aliases)
    position = find_brand_position(response_text, brand_name, aliases) if mentioned else None

    comp_list = known_competitors or []
    found_competitors = find_known_competitors(response_text, comp_list)

    candidates: list[str] = []
    if not comp_list:
        exclude = [brand_name] + list(aliases or [])
        candidates = guess_competitor_candidates(response_text, exclude=exclude)

    return RunResult(
        prompt_id=prompt_id,
        engine=engine,
        run_index=run_index,
        response_text=response_text,
        brand_mentioned=mentioned,
        brand_position=position,
        competitors_found=found_competitors,
        competitor_candidates=candidates,
        citations=list(citations or []),
    )


# ---------------------------------------------------------------------------
# Tính điểm tổng hợp: visibility score, share of voice, vị trí trung bình
# ---------------------------------------------------------------------------

@dataclass
class EngineSummary:
    engine: str
    total_prompts: int = 0
    prompts_with_mention: int = 0
    total_runs: int = 0
    runs_with_mention: int = 0
    positions: list[int] = field(default_factory=list)
    competitor_mentions: dict[str, int] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)  # prompt_id -> lý do skip/error

    @property
    def visibility_score(self) -> float:
        """% số prompt có >=1 lần brand được nhắc, trên tổng số prompt đã chạy
        thành công (không tính prompt bị skip/error vào mẫu số)."""
        attempted = self.total_prompts - len(self.errors)
        if attempted <= 0:
            return 0.0
        return round(100.0 * self.prompts_with_mention / attempted, 2)

    @property
    def average_position(self) -> float | None:
        if not self.positions:
            return None
        return round(sum(self.positions) / len(self.positions), 2)


def summarize_engine(results: list[RunResult], total_prompts: int) -> EngineSummary:
    """Gom danh sách RunResult (của 1 engine) thành EngineSummary."""
    if not results:
        return EngineSummary(engine="unknown", total_prompts=total_prompts)

    engine = results[0].engine
    summary = EngineSummary(engine=engine, total_prompts=total_prompts)

    by_prompt: dict[str, list[RunResult]] = {}
    for r in results:
        by_prompt.setdefault(r.prompt_id, []).append(r)

    for prompt_id, runs in by_prompt.items():
        error_runs = [r for r in runs if r.error or r.skipped_reason]
        ok_runs = [r for r in runs if not (r.error or r.skipped_reason)]
        if ok_runs:
            summary.total_runs += len(ok_runs)
            mention_runs = [r for r in ok_runs if r.brand_mentioned]
            summary.runs_with_mention += len(mention_runs)
            if mention_runs:
                summary.prompts_with_mention += 1
            for r in mention_runs:
                if r.brand_position is not None:
                    summary.positions.append(r.brand_position)
            for r in ok_runs:
                for comp in r.competitors_found:
                    summary.competitor_mentions[comp] = summary.competitor_mentions.get(comp, 0) + 1
        elif error_runs:
            reason = error_runs[0].error or error_runs[0].skipped_reason or "unknown"
            summary.errors[prompt_id] = reason

    return summary


@dataclass
class ShareOfVoiceEntry:
    name: str
    mentions: int
    is_brand: bool = False


def compute_share_of_voice(
    results: list[RunResult],
    brand_name: str,
) -> list[ShareOfVoiceEntry]:
    """So sánh tổng số lần brand được nhắc với từng đối thủ (đã khai báo,
    known_competitors — KHÔNG gộp competitor_candidates suy đoán vào SOV vì
    đó chỉ là gợi ý best-effort, không đủ tin cậy để xếp hạng)."""
    counts: dict[str, int] = {}
    ok_results = [r for r in results if not (r.error or r.skipped_reason)]

    brand_hits = sum(1 for r in ok_results if r.brand_mentioned)
    counts[brand_name] = brand_hits

    for r in ok_results:
        for comp in r.competitors_found:
            counts[comp] = counts.get(comp, 0) + 1

    entries = [
        ShareOfVoiceEntry(name=name, mentions=n, is_brand=(name == brand_name))
        for name, n in counts.items()
    ]
    entries.sort(key=lambda e: (-e.mentions, e.name))
    return entries
