# mona-geo-visibility

CLI Python mã nguồn mở đo **độ hiển thị của một thương hiệu bất kỳ** trong câu trả lời của ba AI chatbot lớn nhất hiện nay — **ChatGPT (OpenAI)**, **Gemini (Google)** và **Claude (Anthropic)** — khi được hỏi những câu hỏi mà khách hàng thật sự gõ vào ô chat.

## GEO là gì và vì sao phải đo?

Trước đây khi cần tìm một công ty làm dịch vụ gì đó, người dùng gõ từ khoá vào Google rồi lướt qua danh sách kết quả tìm kiếm. Ngày càng nhiều người bỏ qua bước đó và hỏi thẳng ChatGPT, Gemini hoặc Claude câu như "công ty nào thiết kế website uy tín tại Việt Nam" — rồi làm theo gợi ý AI đưa ra mà không tự tìm kiếm thêm. AI trả lời bằng cách tổng hợp thông tin nó đã học được và đôi khi cả kết quả tìm kiếm web thời gian thực, sau đó liệt kê ra một số cái tên. Nếu thương hiệu của bạn không nằm trong danh sách đó, bạn coi như vô hình với nhóm khách hàng này — dù website của bạn có thể đang đứng hạng 1 Google.

**GEO (Generative Engine Optimization)** là việc tối ưu để AI generative "biết tới" và "nhắc tên" thương hiệu của bạn khi trả lời khách hàng tiềm năng, tương tự như SEO tối ưu để Google xếp hạng cao. Nhưng muốn tối ưu thì trước tiên phải **đo được hiện trạng**: AI có đang nhắc thương hiệu của bạn không, nhắc ở vị trí nào trong danh sách, và đang nhắc tên đối thủ nào thay vào đó. Đó chính xác là việc công cụ này làm.

Công cụ đo 3 con số cốt lõi:

- **Visibility score** — trong 100 câu hỏi khách thật có thể hỏi AI về mảng dịch vụ của bạn, AI nhắc tên thương hiệu bạn bao nhiêu %.
- **Share of Voice** — so với các đối thủ, AI đang ưu ái nhắc tên ai nhiều nhất.
- **Vị trí trung bình** — khi thương hiệu bạn có được nhắc trong một danh sách, nó thường đứng thứ mấy (thứ 1 tốt hơn thứ 5).

Ngoài ra công cụ còn cố gắng ghi lại **nguồn mà AI trích dẫn** (khi engine có bật tìm kiếm web và trả về thông tin này) — đây chính là manh mối cho biết bạn cần xuất hiện ở đâu trên internet để lọt vào "tầm ngắm" của AI.

## Cài đặt

Yêu cầu Python 3.10 trở lên.

```bash
git clone https://github.com/themonagroup/mona-geo-visibility.git
cd mona-geo-visibility
pip install -e .
```

Lệnh trên cài package và tạo lệnh `mona-geo-visibility` trong PATH. Dependency ngoài stdlib chỉ có `pyyaml` (để đọc file prompt set dạng YAML).

## Thử ngay không cần API key — chế độ `--dry-run`

Công cụ đi kèm sẵn một bộ dữ liệu giả lập (fixture) mô phỏng câu trả lời của cả 3 engine, để bạn xem toàn bộ luồng đo lường + tính điểm hoạt động ra sao mà **không cần internet, không cần bất kỳ API key nào**, và **không tốn một đồng phí API nào**.

```bash
mona-geo-visibility --dry-run --no-save examples/prompt-set-thiet-ke-website.yaml
```

Đây là **output thật** khi chạy lệnh trên (dán nguyên văn, không chỉnh sửa):

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

Con số trong `--dry-run` là dữ liệu giả lập cố định trong repo — chỉ để bạn kiểm tra công cụ chạy đúng, KHÔNG phản ánh hiệu quả GEO thật của bất kỳ thương hiệu nào. Muốn có số thật, bạn cần chạy với API key thật (xem phần dưới).

`"Websmith VN"` trong ví dụ trên là một **thương hiệu bịa hoàn toàn** để minh hoạ, cùng với các "đối thủ mẫu" `WebCraft Saigon`, `PixelNest`, `DigitalHive` — cũng đều là tên tự đặt, không phải công ty thật nào.

## Viết prompt set của riêng bạn

Prompt set là một file YAML (hoặc JSON) do bạn tự viết, khai báo: thương hiệu cần đo, danh sách đối thủ đã biết (không bắt buộc), và danh sách câu hỏi mô phỏng khách thật. Xem file mẫu đầy đủ tại [`examples/prompt-set-thiet-ke-website.yaml`](examples/prompt-set-thiet-ke-website.yaml). Cấu trúc tối thiểu:

```yaml
brand:
  name: "Tên thương hiệu của bạn"
  aliases:            # optional — tên viết tắt/biến thể
    - "Tên viết tắt"

competitors:          # optional — khai báo trước giúp so khớp chính xác hơn
  - "Đối thủ A"
  - "Đối thủ B"

prompts:
  - id: "p1"           # optional, tự sinh nếu bỏ trống
    text: "công ty nào làm X uy tín tại Việt Nam"
  - text: "câu hỏi khác, không cần khai id"
```

Nguyên tắc viết prompt quan trọng nhất: **viết như một khách hàng thật đang gõ vào ô chat**, không viết từ khoá SEO ngắn gọn. "Nên chọn đơn vị nào làm website bán hàng cho shop của tôi" là một prompt tốt; "thiết kế website giá rẻ" thì không — vì không ai hỏi AI như vậy.

Nếu bạn không khai `competitors`, công cụ vẫn cố gắng đoán các cái tên xuất hiện trong câu trả lời bằng một heuristic đơn giản (tìm cụm "Tên Viết Hoa" đứng gần các từ như "công ty", "dịch vụ", "nhà cung cấp"). Đây **chỉ là gợi ý best-effort**, không chính xác tuyệt đối — công cụ luôn tách riêng phần này ("ứng viên đối thủ gợi ý") khỏi Share of Voice chính thức, vì SOV chỉ tính trên các tên bạn đã khai báo chắc chắn.

## Chạy thật với API key

Công cụ gọi thẳng REST API chính thức của từng hãng bằng `urllib` (thư viện chuẩn Python) — không ép cài SDK riêng của OpenAI/Google/Anthropic. Đặt biến môi trường tương ứng với engine bạn muốn bật:

```bash
export OPENAI_API_KEY="..."       # https://platform.openai.com/api-keys
export GEMINI_API_KEY="..."       # https://aistudio.google.com/apikey
export ANTHROPIC_API_KEY="..."    # https://console.anthropic.com/settings/keys
```

Sau đó chạy:

```bash
mona-geo-visibility examples/prompt-set-thiet-ke-website.yaml
```

Engine nào thiếu key sẽ tự động bị bỏ qua (báo "skipped: no API key" trong output), các engine còn lại vẫn chạy bình thường — công cụ không bao giờ dừng cả chương trình chỉ vì thiếu 1 key, và không bao giờ bịa ra kết quả cho engine bị skip.

### Các flag hữu ích

| Flag | Ý nghĩa | Mặc định |
|---|---|---|
| `--runs N` | Số lần chạy mỗi prompt trên mỗi engine (câu trả lời AI dao động giữa các lần gọi, nên cần chạy lặp lại để lấy tỷ lệ) | `3` |
| `--engines openai,gemini` | Chỉ bật một số engine thay vì cả 3 | `openai,gemini,anthropic` |
| `--model-openai`, `--model-gemini`, `--model-anthropic` | Override model dùng cho từng engine | model rẻ/nhanh của mỗi hãng — xem `engines.py` |
| `--json` | In báo cáo dạng JSON thay vì bảng text (tiện để pipe sang script khác) | tắt |
| `--results-dir DIR` | Thư mục ghi log thô từng lần gọi | `results/` |
| `--no-save` | Không ghi log thô ra đĩa | tắt |
| `--dry-run` | Chạy với fixture giả lập, không gọi API | tắt |

Model mặc định của mỗi hãng được chọn theo tiêu chí **rẻ và nhanh** (ví dụ `gpt-4o-mini`, `gemini-1.5-flash`, `claude-3-5-haiku-20241022`) vì công cụ này thường phải gọi hàng chục đến hàng trăm lần cho một lượt đo đầy đủ (số prompt × số engine × số lần lặp). Bạn hoàn toàn override được sang model mạnh hơn qua flag nếu cần độ chính xác cao hơn, đổi lại chi phí API cao hơn.

Mỗi lần chạy, công cụ ghi lại toàn bộ log thô (từng câu hỏi, từng câu trả lời đầy đủ, thời gian gọi) vào một file JSON trong thư mục `results/` — đây là bằng chứng bạn có thể lưu lại để so sánh qua từng tháng, hoặc dùng làm tài liệu chứng minh khi trình bày với khách hàng/sếp.

## Cấu trúc mã nguồn

```
src/mona_geo_visibility/
├── cli.py         # điều phối pipeline: đọc prompt set → gọi engine → phân tích → in báo cáo
├── engines.py      # gọi REST API của OpenAI / Gemini / Anthropic bằng urllib
├── analyze.py      # nhận diện brand mention, vị trí trong list, đối thủ, tính visibility/SOV
├── promptset.py    # đọc & validate file prompt set YAML/JSON
└── fixtures/       # dữ liệu giả lập dùng cho --dry-run
```

## Chạy test

```bash
pip install -e ".[dev]"
pytest
```

Toàn bộ test chạy được **không cần internet và không cần API key thật** (dùng dry-run/mock), phù hợp để chạy trong CI.

## Giới hạn cần biết

- Heuristic đoán tên đối thủ khi không khai báo trước là **best-effort**, có thể bắt nhầm hoặc bỏ sót — luôn tự soát lại trước khi dùng làm số liệu chính thức.
- Việc AI có nhắc tên thương hiệu hay không phụ thuộc vào rất nhiều yếu tố ngoài tầm kiểm soát của công cụ này (bản cập nhật model, có bật tìm kiếm web hay không, ngữ cảnh phiên chat...) — nên đo lặp lại nhiều lần (`--runs`) và đo định kỳ hàng tháng thay vì tin vào một lần chạy duy nhất.
- Đây là công cụ đo — không tự động "sửa" GEO cho bạn. Việc cải thiện visibility (xuất hiện nhiều hơn ở nguồn AI hay trích dẫn, được nhắc tên nhiều hơn trên các bài viết/danh mục uy tín...) là bước tiếp theo, nằm ngoài phạm vi công cụ này.

---

# English

## What this is

`mona-geo-visibility` is an open-source Python CLI that measures how visible a brand is in the answers of the three dominant AI chatbots — **ChatGPT (OpenAI)**, **Gemini (Google)**, and **Claude (Anthropic)** — when asked natural, customer-style questions about a service or product category.

This is **GEO (Generative Engine Optimization)**: as more people ask AI chatbots directly instead of searching Google, being mentioned by name in the AI's answer becomes as valuable as ranking #1 on a search results page. Before you can optimize for it, you need to measure your current state — that's what this tool does.

It computes:

- **Visibility score** — the % of customer-style prompts where the AI mentions your brand.
- **Share of Voice** — how your brand's mention count compares to known competitors.
- **Average position** — when your brand appears in a list, what rank it typically gets.
- A best-effort collection of **cited sources** (when an engine returns grounding/citation metadata), which points to where you need to build presence online.

## Install

Requires Python 3.10+.

```bash
git clone https://github.com/themonagroup/mona-geo-visibility.git
cd mona-geo-visibility
pip install -e .
```

The only non-stdlib dependency is `pyyaml` (for reading YAML prompt sets).

## Try it with zero setup — `--dry-run`

```bash
mona-geo-visibility --dry-run --no-save examples/prompt-set-thiet-ke-website.yaml
```

This runs the full pipeline against a bundled fixture of simulated AI responses — no internet, no API key, no cost. See the real output pasted in the Vietnamese section above (it is the same command, same output).

## Write your own prompt set

A prompt set is a YAML or JSON file you write yourself, declaring the brand to measure, optional known competitors, and a list of natural customer-style questions. See [`examples/prompt-set-thiet-ke-website.yaml`](examples/prompt-set-thiet-ke-website.yaml) for a full annotated example (Vietnamese-language example; the schema itself is language-agnostic).

## Run for real

Set the environment variable(s) for the engines you want to enable:

```bash
export OPENAI_API_KEY="..."
export GEMINI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
```

```bash
mona-geo-visibility your-prompt-set.yaml
```

Any engine missing its key is skipped with a clear message; the others keep running. The tool never crashes the whole run over one missing key, and never fabricates a result for a skipped engine.

Run `mona-geo-visibility --help` for the full flag reference (`--runs`, `--engines`, `--model-*`, `--json`, `--results-dir`, `--no-save`, `--dry-run`).

## Tests

```bash
pip install -e ".[dev]"
pytest
```

All tests run offline (dry-run/mocked), suitable for CI.

## Limitations

- The no-competitors-declared heuristic for guessing competitor names is best-effort and can misfire — always sanity-check it.
- AI answers are non-deterministic; run multiple `--runs` and re-measure periodically rather than trusting a single run.
- This tool measures GEO visibility; it does not fix it for you.

---
Từ MONA — https://mona.media · Các repo khác: https://github.com/themonagroup · Hub mã nguồn mở: https://mona.media/mona-open/
