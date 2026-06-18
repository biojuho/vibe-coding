from pipeline.publish_repair import repair_hold_draft


def test_fixable_string_false_does_not_repair_hold_dict():
    result = repair_hold_draft(
        "Check this https://example.com",
        {
            "action": "HOLD",
            "fixable": "false",
            "reasons": ["external_link_in_body"],
        },
        {},
    )

    assert result.changed is False
    assert result.text == "Check this https://example.com"
    assert result.applied == []


def test_quality_only_hold_is_not_fabricated():
    """Content/structure-quality holds must NOT be patched with templated abstraction.

    The old behavior appended a "참 개인 감정으로 끝낼 일이 아니라 ~의 문제거든요 / 정답은
    상황마다 다를 수 있어도 기준은 남습니다" value-frame — the exact banned anti-pattern,
    identical across posts. It must no longer be produced.
    """
    original = "팀장이 야근을 당연하게 여김"
    result = repair_hold_draft(
        original,
        {"action": "HOLD", "fixable": True, "reasons": ["voice", "ending", "quality_score_below_threshold"]},
        {"killer_sentence": "회복 시간이 사라진다", "universal_value": "기준", "closure": "open"},
    )

    assert result.changed is False
    assert result.applied == []
    assert result.text == original
    assert "기준은 남습니다" not in result.text
    assert "감정으로 끝낼" not in result.text
    assert "아니라" not in result.text


def test_mechanical_fixes_still_apply():
    """URL strip + hashtag limiting (the genuinely mechanical repairs) still work."""
    result = repair_hold_draft(
        "본문 내용 https://example.com/article #a #b #c #d #e",
        {
            "action": "HOLD",
            "fixable": True,
            "reasons": ["external_link_in_body", "hashtag_limit_exceeded"],
        },
        None,
        max_hashtags=3,
    )

    assert result.changed is True
    assert "strip_url" in result.applied
    assert "limit_hashtags" in result.applied
    assert "https://" not in result.text
    assert result.text.count("#") == 3


def test_overlength_hold_trims_preserving_leading_content_without_frame():
    long_draft = "오천만원 연봉 협상 결렬 " * 40  # well over 280 X-weighted chars
    result = repair_hold_draft(
        long_draft,
        {"action": "HOLD", "fixable": True, "reasons": ["x_weighted_length_exceeded"]},
        None,
    )

    assert result.changed is True
    assert "trim_to_x_weighted_limit" in result.applied
    assert result.weighted_length <= 280
    # trims real content from the front, never injects boilerplate
    assert result.text.startswith("오천만원 연봉 협상 결렬")
    assert "기준은 남습니다" not in result.text
