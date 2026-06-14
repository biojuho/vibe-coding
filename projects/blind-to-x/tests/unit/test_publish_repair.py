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
