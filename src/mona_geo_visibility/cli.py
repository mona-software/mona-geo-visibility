"""CLI chính của mona-geo-visibility.

Luồng: đọc prompt set -> với mỗi prompt, gọi từng engine đã bật (--runs lần)
-> phân tích từng câu trả lời -> tổng hợp visibility score + share of voice
-> in báo cáo (text hoặc --json) -> ghi log thô ra results/.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from .analyze import (
    ShareOfVoiceEntry,
    analyze_response,
    compute_share_of_voice,
    summarize_engine,
)
from .engines import DEFAULT_MODELS, ENGINE_CALLERS, has_api_key
from .fixtures import fake_call
from .promptset import PromptSetError, load_prompt_set

ALL_ENGINES = ["openai", "gemini", "anthropic"]

ENGINE_DISPLAY_NAME = {
    "openai": "ChatGPT (OpenAI)",
    "gemini": "Gemini (Google)",
    "anthropic": "Claude (Anthropic)",
}


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="mona-geo-visibility",
        description=(
            "Đo độ hiển thị (visibility) của một thương hiệu trong câu trả lời của "
            "ChatGPT, Gemini và Claude — công cụ GEO (Generative Engine Optimization)."
        ),
    )
    parser.add_argument(
        "prompt_set",
        nargs="?",
        help="Đường dẫn file prompt set (YAML hoặc JSON). Bắt buộc trừ khi dùng --dry-run.",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=3,
        help="Số lần chạy mỗi prompt trên mỗi engine (mặc định 3, vì output AI dao động).",
    )
    parser.add_argument(
        "--engines",
        default=",".join(ALL_ENGINES),
        help=f"Danh sách engine bật, phân tách bằng dấu phẩy. Mặc định: {','.join(ALL_ENGINES)}",
    )
    parser.add_argument("--model-openai", default=None, help="Override model OpenAI (mặc định rẻ/nhanh).")
    parser.add_argument("--model-gemini", default=None, help="Override model Gemini (mặc định rẻ/nhanh).")
    parser.add_argument("--model-anthropic", default=None, help="Override model Anthropic (mặc định rẻ/nhanh).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Chạy toàn bộ pipeline với fixture giả lập, KHÔNG gọi API thật. Không cần key.",
    )
    parser.add_argument(
        "--results-dir",
        default="results",
        help="Thư mục ghi log thô từng lần gọi (mặc định: results/).",
    )
    parser.add_argument("--no-save", action="store_true", help="Không ghi log thô ra results/.")
    parser.add_argument("--json", action="store_true", help="In báo cáo dạng JSON thay vì bảng text.")
    return parser


def resolve_models(args: argparse.Namespace) -> dict[str, str]:
    return {
        "openai": args.model_openai or DEFAULT_MODELS["openai"],
        "gemini": args.model_gemini or DEFAULT_MODELS["gemini"],
        "anthropic": args.model_anthropic or DEFAULT_MODELS["anthropic"],
    }


def run_pipeline(
    prompt_set_path: str,
    runs: int = 3,
    engines: list[str] | None = None,
    models: dict[str, str] | None = None,
    dry_run: bool = False,
) -> tuple[list, dict]:
    """Chạy toàn bộ pipeline, trả về (list[RunResult], meta dict).

    meta chứa: brand_name, brand_aliases, competitors, prompt_count, engines_run.
    Hàm này KHÔNG in gì ra stdout và KHÔNG ghi file — để test dễ và để cli.py
    tách riêng phần "chạy" khỏi phần "trình bày".
    """
    try:
        pset = load_prompt_set(prompt_set_path)
    except PromptSetError as exc:
        print(f"Lỗi prompt set: {exc}", file=sys.stderr)
        sys.exit(1)

    engines = engines or ALL_ENGINES
    models = models or DEFAULT_MODELS

    all_results = []

    for engine in engines:
        caller = ENGINE_CALLERS.get(engine)
        model = models.get(engine, DEFAULT_MODELS.get(engine, "default"))

        # Kiểm tra 1 lần duy nhất xem engine có bị skip (thiếu key) không, để
        # khỏi gọi lặp lại cho từng prompt/run — "no API key" là tình trạng
        # chung của cả engine, không phải của riêng 1 prompt.
        engine_skip_reason: str | None = None
        if not dry_run and caller is None:
            engine_skip_reason = f"unknown engine '{engine}'"
        elif not dry_run and not has_api_key(engine):
            engine_skip_reason = "no API key"

        for prompt in pset.prompts:
            if engine_skip_reason:
                result = analyze_response(
                    prompt_id=prompt.id,
                    engine=engine,
                    run_index=0,
                    response_text="",
                    brand_name=pset.brand_name,
                    aliases=pset.brand_aliases,
                    known_competitors=pset.competitors,
                )
                result.skipped_reason = engine_skip_reason
                all_results.append(result)
                continue

            for run_index in range(runs):
                if dry_run:
                    resp = fake_call(engine, run_index, model=model)
                else:
                    resp = caller(prompt.text, model=model)

                if resp.error:
                    result = analyze_response(
                        prompt_id=prompt.id,
                        engine=engine,
                        run_index=run_index,
                        response_text="",
                        brand_name=pset.brand_name,
                        aliases=pset.brand_aliases,
                        known_competitors=pset.competitors,
                    )
                    result.error = resp.error
                else:
                    result = analyze_response(
                        prompt_id=prompt.id,
                        engine=engine,
                        run_index=run_index,
                        response_text=resp.text,
                        brand_name=pset.brand_name,
                        aliases=pset.brand_aliases,
                        known_competitors=pset.competitors,
                        citations=resp.citations,
                    )

                all_results.append(result)

    meta = {
        "brand_name": pset.brand_name,
        "brand_aliases": pset.brand_aliases,
        "competitors": pset.competitors,
        "prompt_count": len(pset.prompts),
        "engines_run": engines,
        "runs_per_prompt": runs,
        "models": models,
        "dry_run": dry_run,
    }
    return all_results, meta


def save_raw_results(results: list, meta: dict, results_dir: str) -> Path:
    out_dir = Path(results_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_path = out_dir / f"run-{timestamp}.json"

    payload = {
        "meta": meta,
        "results": [
            {
                "prompt_id": r.prompt_id,
                "engine": r.engine,
                "run_index": r.run_index,
                "brand_mentioned": r.brand_mentioned,
                "brand_position": r.brand_position,
                "competitors_found": r.competitors_found,
                "competitor_candidates": r.competitor_candidates,
                "citations": r.citations,
                "error": r.error,
                "skipped_reason": r.skipped_reason,
                "response_text": r.response_text,
            }
            for r in results
        ],
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_path


def format_sov_line(entries: list[ShareOfVoiceEntry]) -> str:
    parts = []
    for i, e in enumerate(entries, start=1):
        marker = f"{e.name}*" if e.is_brand else e.name
        parts.append(f"{i}.{marker} ({e.mentions})")
    return " · ".join(parts)


def print_text_report(results: list, meta: dict) -> None:
    brand = meta["brand_name"]
    print(f"GEO visibility report — brand: {brand}")
    if meta.get("dry_run"):
        print("(chế độ --dry-run: dữ liệu giả lập, không gọi API thật)")
    print(f"Số prompt: {meta['prompt_count']} · số lần chạy/prompt: {meta['runs_per_prompt']}")
    print()

    total_prompts = meta["prompt_count"]

    for engine in meta["engines_run"]:
        engine_results = [r for r in results if r.engine == engine]
        summary = summarize_engine(engine_results, total_prompts=total_prompts)
        display = ENGINE_DISPLAY_NAME.get(engine, engine)

        if summary.errors and summary.total_runs == 0:
            reasons = set(summary.errors.values())
            reason = next(iter(reasons))
            print(f"{display}: skipped ({reason})")
            continue

        pos = f", vị trí TB {summary.average_position}" if summary.average_position else ""
        print(
            f"{display}: visibility {summary.prompts_with_mention}/{total_prompts - len(summary.errors)} "
            f"prompt ({summary.visibility_score}%){pos}"
        )
        if summary.errors:
            print(f"  ⚠ {len(summary.errors)} prompt lỗi/skip: {list(summary.errors.values())[:3]}")

    print()
    sov = compute_share_of_voice(results, brand)
    print("Share of Voice (tổng số lần được nhắc, * = brand đo):")
    print(f"  {format_sov_line(sov)}")

    all_candidates = sorted({c for r in results for c in r.competitor_candidates})
    if all_candidates:
        print()
        print(
            "Ứng viên đối thủ gợi ý (best-effort, CHƯA xác nhận — do không khai "
            "competitors trong prompt set):"
        )
        print(f"  {', '.join(all_candidates[:20])}")

    all_citations = sorted({c for r in results for c in r.citations})
    if all_citations:
        print()
        print("Nguồn trích dẫn AI đã dùng (citation/grounding, nếu engine trả về):")
        for c in all_citations[:20]:
            print(f"  - {c}")


def build_json_report(results: list, meta: dict) -> dict:
    total_prompts = meta["prompt_count"]
    engines_summary = {}
    for engine in meta["engines_run"]:
        engine_results = [r for r in results if r.engine == engine]
        summary = summarize_engine(engine_results, total_prompts=total_prompts)
        engines_summary[engine] = {
            "visibility_score": summary.visibility_score,
            "prompts_with_mention": summary.prompts_with_mention,
            "total_prompts": total_prompts,
            "average_position": summary.average_position,
            "competitor_mentions": summary.competitor_mentions,
            "errors": summary.errors,
        }

    sov = compute_share_of_voice(results, meta["brand_name"])
    return {
        "meta": meta,
        "engines": engines_summary,
        "share_of_voice": [
            {"name": e.name, "mentions": e.mentions, "is_brand": e.is_brand} for e in sov
        ],
        "competitor_candidates": sorted({c for r in results for c in r.competitor_candidates}),
        "citations": sorted({c for r in results for c in r.citations}),
    }


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    if not args.dry_run and not args.prompt_set:
        parser.error("thiếu prompt_set (hoặc dùng --dry-run để chạy thử với fixture)")

    prompt_set_path = args.prompt_set
    if args.dry_run and not prompt_set_path:
        # dùng luôn prompt set mẫu đi kèm repo nếu người dùng không chỉ định
        default_example = Path(__file__).resolve().parent.parent.parent / "examples" / "prompt-set-thiet-ke-website.yaml"
        prompt_set_path = str(default_example)

    engines = [e.strip() for e in args.engines.split(",") if e.strip()]
    models = resolve_models(args)

    results, meta = run_pipeline(
        prompt_set_path=prompt_set_path,
        runs=args.runs,
        engines=engines,
        models=models,
        dry_run=args.dry_run,
    )

    if not args.no_save:
        out_path = save_raw_results(results, meta, args.results_dir)
        if not args.json:
            print(f"(đã ghi log thô: {out_path})")
            print()

    if args.json:
        print(json.dumps(build_json_report(results, meta), ensure_ascii=False, indent=2))
    else:
        print_text_report(results, meta)

    return 0


if __name__ == "__main__":
    sys.exit(main())
