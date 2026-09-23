from mona_geo_visibility.analyze import (
    analyze_response,
    brand_mentioned,
    compute_share_of_voice,
    find_brand_position,
    find_known_competitors,
    guess_competitor_candidates,
    split_into_list_items,
    summarize_engine,
)


def test_brand_mentioned_case_insensitive():
    text = "Tôi nghĩ WEBSMITH VN là lựa chọn tốt cho doanh nghiệp nhỏ."
    assert brand_mentioned(text, "Websmith VN") is True


def test_brand_mentioned_via_alias():
    text = "Websmith là cái tên nhiều người nhắc tới."
    assert brand_mentioned(text, "Websmith VN", aliases=["Websmith"]) is True


def test_brand_not_mentioned():
    text = "WebCraft Saigon và PixelNest là hai lựa chọn phổ biến."
    assert brand_mentioned(text, "Websmith VN", aliases=["Websmith"]) is False


def test_split_into_list_items_numbered():
    text = "Gợi ý cho bạn:\n1. WebCraft Saigon\n2. Websmith VN\n3. PixelNest"
    items = split_into_list_items(text)
    assert items == ["WebCraft Saigon", "Websmith VN", "PixelNest"]


def test_split_into_list_items_no_list_returns_empty():
    text = "Đây chỉ là một đoạn văn bình thường, không có danh sách nào cả."
    assert split_into_list_items(text) == []


def test_find_brand_position_in_list():
    text = "1. WebCraft Saigon\n2. Websmith VN\n3. PixelNest"
    pos = find_brand_position(text, "Websmith VN")
    assert pos == 2


def test_find_brand_position_none_when_not_in_list():
    text = "1. WebCraft Saigon\n2. PixelNest"
    pos = find_brand_position(text, "Websmith VN")
    assert pos is None


def test_find_known_competitors_exact_match():
    text = "WebCraft Saigon và DigitalHive được nhắc nhiều, PixelNest thì ít hơn."
    found = find_known_competitors(text, ["WebCraft Saigon", "PixelNest", "DigitalHive", "KhongCoTrongBai"])
    assert set(found) == {"WebCraft Saigon", "PixelNest", "DigitalHive"}


def test_guess_competitor_candidates_best_effort():
    text = "Bạn có thể tham khảo công ty WebCraft Saigon hoặc dịch vụ PixelNest Studio."
    candidates = guess_competitor_candidates(text, exclude=["Websmith VN"])
    joined = " ".join(candidates)
    assert "WebCraft Saigon" in joined or any("WebCraft" in c for c in candidates)


def test_analyze_response_full():
    text = "1. WebCraft Saigon\n2. Websmith VN\n3. PixelNest"
    result = analyze_response(
        prompt_id="p1",
        engine="openai",
        run_index=0,
        response_text=text,
        brand_name="Websmith VN",
        known_competitors=["WebCraft Saigon", "PixelNest"],
    )
    assert result.brand_mentioned is True
    assert result.brand_position == 2
    assert set(result.competitors_found) == {"WebCraft Saigon", "PixelNest"}


def test_summarize_engine_visibility_score():
    results = [
        analyze_response("p1", "openai", 0, "Websmith VN là lựa chọn tốt.", "Websmith VN"),
        analyze_response("p1", "openai", 1, "Không nhắc gì tới đơn vị nào cả.", "Websmith VN"),
        analyze_response("p2", "openai", 0, "WebCraft Saigon là lựa chọn tốt.", "Websmith VN"),
    ]
    summary = summarize_engine(results, total_prompts=2)
    # p1 có ít nhất 1 lần mention -> tính là "prompt có mention"
    assert summary.prompts_with_mention == 1
    assert summary.visibility_score == 50.0


def test_summarize_engine_with_errors_excludes_from_denominator():
    results = [
        analyze_response("p1", "openai", 0, "Websmith VN xuất hiện.", "Websmith VN"),
    ]
    error_result = analyze_response("p2", "openai", 0, "", "Websmith VN")
    error_result.error = "network error"
    results.append(error_result)

    summary = summarize_engine(results, total_prompts=2)
    assert summary.errors == {"p2": "network error"}
    # mẫu số chỉ tính prompt chạy thành công (2 - 1 lỗi = 1)
    assert summary.visibility_score == 100.0


def test_compute_share_of_voice_ranks_by_mentions():
    results = [
        analyze_response("p1", "openai", 0, "WebCraft Saigon và PixelNest là hai lựa chọn phổ biến.",
                          "Websmith VN", known_competitors=["WebCraft Saigon", "PixelNest"]),
        analyze_response("p2", "openai", 0, "WebCraft Saigon dẫn đầu danh sách.",
                          "Websmith VN", known_competitors=["WebCraft Saigon", "PixelNest"]),
    ]
    sov = compute_share_of_voice(results, "Websmith VN")
    names_in_order = [e.name for e in sov]
    assert names_in_order[0] == "WebCraft Saigon"
    brand_entry = next(e for e in sov if e.is_brand)
    assert brand_entry.mentions == 0
