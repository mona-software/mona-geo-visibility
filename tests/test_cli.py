from pathlib import Path

from mona_geo_visibility.cli import build_json_report, main, run_pipeline

EXAMPLE_PATH = Path(__file__).resolve().parent.parent / "examples" / "prompt-set-thiet-ke-website.yaml"


def test_dry_run_full_pipeline_no_key_needed(monkeypatch):
    for var in ("OPENAI_API_KEY", "GEMINI_API_KEY", "ANTHROPIC_API_KEY"):
        monkeypatch.delenv(var, raising=False)

    results, meta = run_pipeline(
        prompt_set_path=str(EXAMPLE_PATH),
        runs=2,
        engines=["openai", "gemini", "anthropic"],
        dry_run=True,
    )

    assert meta["brand_name"] == "Websmith VN"
    assert len(results) > 0
    # dry-run không skip vì thiếu key
    assert all(r.skipped_reason is None for r in results)
    assert all(r.error is None for r in results)


def test_engine_without_key_is_skipped_not_crashed(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    results, meta = run_pipeline(
        prompt_set_path=str(EXAMPLE_PATH),
        runs=1,
        engines=["openai"],
        dry_run=False,
    )

    assert len(results) == meta["prompt_count"]
    assert all(r.skipped_reason == "no API key" for r in results)


def test_build_json_report_shape():
    results, meta = run_pipeline(
        prompt_set_path=str(EXAMPLE_PATH),
        runs=1,
        engines=["openai"],
        dry_run=True,
    )
    report = build_json_report(results, meta)
    assert "engines" in report
    assert "openai" in report["engines"]
    assert "share_of_voice" in report
    assert isinstance(report["share_of_voice"], list)


def test_main_dry_run_json_exits_zero(capsys):
    exit_code = main(["--dry-run", "--json", "--no-save", str(EXAMPLE_PATH)])
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "share_of_voice" in captured.out


def test_main_requires_prompt_set_without_dry_run():
    try:
        main([])
        assert False, "phải thoát bằng lỗi khi không có prompt_set và không --dry-run"
    except SystemExit as exc:
        assert exc.code != 0
