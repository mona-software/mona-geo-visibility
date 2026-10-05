# mona-geo-visibility

A command-line tool that measures how often a brand is mentioned in answers from OpenAI (ChatGPT), Google Gemini and Anthropic Claude to a set of customer-style questions.

[![test](https://github.com/mona-software/mona-geo-visibility/actions/workflows/test.yml/badge.svg)](https://github.com/mona-software/mona-geo-visibility/actions/workflows/test.yml) [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

You write a prompt set (brand, aliases, competitors, questions); the tool sends each question to each enabled engine several times and reports how often and where the brand appears. Report labels are in Vietnamese, and the bundled example prompt set is in Vietnamese, but prompt sets can be in any language.

Metrics:

- **Visibility**: share of prompts where the brand is mentioned in at least one run, out of the prompts that ran without errors.
- **Average position**: when the answer is a list and the brand appears in an item, the mean 1-based index of that item.
- **Share of voice**: total runs mentioning the brand compared with runs mentioning each declared competitor.
- **Competitor candidates**: capitalized names found near words such as "công ty", "dịch vụ", "nhà cung cấp". This is a heuristic and is reported separately from share of voice.
- **Citations**: source URLs from Gemini `groundingMetadata`, when present. The request does not enable Search grounding, and the OpenAI and Anthropic callers return no citations, so this list is usually empty.

## Install

Requires Python 3.10+. The only runtime dependency is `pyyaml`.

```bash
git clone https://github.com/mona-software/mona-geo-visibility
cd mona-geo-visibility
pip install -e .
```

## Quick start (no API keys)

`--dry-run` runs the whole pipeline against bundled simulated responses, with no network access:

```bash
mona-geo-visibility --dry-run --no-save examples/prompt-set-thiet-ke-website.yaml
```

```
GEO visibility report — brand: Websmith VN
(chế độ --dry-run: dữ liệu giả lập, không gọi API thật)
Số prompt: 12 · số lần chạy/prompt: 3

ChatGPT (OpenAI): visibility 12/12 prompt (100.0%), vị trí TB 2.0
Gemini (Google): visibility 12/12 prompt (100.0%), vị trí TB 3.0
Claude (Anthropic): visibility 12/12 prompt (100.0%), vị trí TB 2.0

Share of Voice (tổng số lần được nhắc, * = brand đo):
  1.WebCraft Saigon (108) · 2.Websmith VN* (84) · 3.PixelNest (72) · 4.DigitalHive (48)
```

These numbers come from fixed fixture data. "Websmith VN" and the competitors are fictional names.

## Prompt set format

A YAML or JSON file. See [`examples/prompt-set-thiet-ke-website.yaml`](examples/prompt-set-thiet-ke-website.yaml) for a full example.

```yaml
brand:
  name: "Your Brand"
  aliases:            # optional: abbreviations and variants
    - "YB"

competitors:          # optional: declared names are used for share of voice
  - "Competitor A"
  - "Competitor B"

prompts:
  - id: "p1"          # optional, generated if omitted
    text: "Which companies in Vietnam build e-commerce websites?"
  - text: "Another question, without an id"
```

Write prompts the way a customer would type them into a chat, not as short search keywords.

## Usage

```bash
mona-geo-visibility <prompt-set.yaml> [options]
```

| Option | Description | Default |
| --- | --- | --- |
| `--runs N` | Runs per prompt per engine | `3` |
| `--engines LIST` | Comma-separated engines to enable | `openai,gemini,anthropic` |
| `--model-openai`, `--model-gemini`, `--model-anthropic` | Override the model per engine | see below |
| `--json` | Print a JSON report | off |
| `--results-dir DIR` | Directory for raw run logs | `results/` |
| `--no-save` | Do not write raw logs | off |
| `--dry-run` | Use bundled fixtures instead of calling APIs | off |

Default models (defined in `src/mona_geo_visibility/engines.py`): `gpt-4o-mini`, `gemini-1.5-flash`, `claude-3-5-haiku-20241022`.

Unless `--no-save` is set, each run writes `results/run-<UTC timestamp>.json` containing the metadata and, for every call, the prompt ID, engine, run index, brand mention and position, competitors found, citations, errors and the full response text.

`--json` prints `meta`, per-engine `engines` summaries (`visibility_score`, `prompts_with_mention`, `total_prompts`, `average_position`, `competitor_mentions`, `errors`), `share_of_voice`, `competitor_candidates` and `citations`.

## Configuration

The tool calls each provider's REST API directly with `urllib`; no provider SDK is required. Set the key for each engine you want to use:

```bash
export OPENAI_API_KEY="..."
export GEMINI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

An engine without a key is reported as `skipped (no API key)` and the other engines still run. API errors are recorded per prompt and excluded from the visibility denominator.

## Project layout

```
src/mona_geo_visibility/
├── cli.py         # pipeline: load prompt set → call engines → analyze → report
├── engines.py     # OpenAI / Gemini / Anthropic REST calls via urllib
├── analyze.py     # brand mentions, list position, competitors, visibility, share of voice
├── promptset.py   # load and validate YAML/JSON prompt sets
└── fixtures/      # simulated responses for --dry-run
```

## Development

```bash
pip install -e ".[dev]"
pytest
```

Tests run offline and need no API keys.

## Limitations

- Model answers vary between calls and over time; use several `--runs` and repeat measurements rather than relying on one run.
- Competitor candidates are a heuristic and can include false positives or miss names.
- The tool measures mentions; it does not change them.

## License

MIT, see [LICENSE](LICENSE).

**`mona-geo-visibility` is a product of MONA Software, a member of The MONA Group.**
