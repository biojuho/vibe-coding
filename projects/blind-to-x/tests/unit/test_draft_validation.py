import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.draft_validation import DraftValidationMixin  # noqa: E402


class Parser(DraftValidationMixin):
    pass


def test_parse_response_strips_thinking_and_maps_json_payload():
    parser = Parser()
    response = textwrap.dedent(
        """\
        <thinking>do not expose this chain of thought</thinking>
        ```json
        {
          "twitter": "public draft",
          "reply": "source reply",
          "creator_take": "operator summary",
          "image_prompt": "json image prompt"
        }
        ```
        """
    )

    drafts, image_prompt = parser._parse_response(response, ["twitter"], "test-provider")

    assert drafts["_provider_used"] == "test-provider"
    assert drafts["twitter"] == "public draft"
    assert drafts["reply_text"] == "source reply"
    assert drafts["creator_take"] == "operator summary"
    assert image_prompt == "json image prompt"
    assert "thinking" not in drafts["twitter"]


def test_parse_response_thread_keeps_twitter_compatibility_and_auxiliary_tags():
    parser = Parser()
    response = textwrap.dedent(
        """\
        <twitter_thread>1/2 first post
        2/2 second post</twitter_thread>
        <twitter>single tweet should not replace thread</twitter>
        <reply>reply body</reply>
        <regulation_check>safe</regulation_check>
        <creator_take>creator note</creator_take>
        <image_prompt>tag image prompt</image_prompt>
        """
    )

    drafts, image_prompt = parser._parse_response(response, ["twitter"], "test-provider")

    assert drafts["twitter_thread"].startswith("1/2 first post")
    assert drafts["twitter"] == drafts["twitter_thread"]
    assert drafts["reply_text"] == "reply body"
    assert drafts["_regulation_check"] == "safe"
    assert drafts["creator_take"] == "creator note"
    assert image_prompt == "tag image prompt"


def test_parse_response_twitter_fallback_removes_image_prompt_tag():
    parser = Parser()
    response = "Plain fallback draft\n<image_prompt>fallback image prompt</image_prompt>"

    drafts, image_prompt = parser._parse_response(response, ["twitter"], "test-provider")

    assert drafts["twitter"] == "Plain fallback draft"
    assert drafts["reply_text"] == ""
    assert image_prompt == "fallback image prompt"


def test_parse_response_single_requested_format_uses_plain_text_fallback():
    parser = Parser()

    drafts, image_prompt = parser._parse_response("Plain threads draft", ["threads"], "test-provider")

    assert drafts["threads"] == "Plain threads draft"
    assert image_prompt is None


def test_extract_json_payload_with_curly_brace_in_value():
    """DV-BAL001: JSON 값에 중괄호 포함 시 balanced-brace 스캔이 올바른 키 추출.

    이전 코드의 비-greedy 정규식은 첫 번째 닫는 중괄호에서 멈춰
    {"twitter": "연봉 {3.5%} 못 버팀"} 같은 응답에서 JSONDecodeError 후 빈 dict 반환.
    balanced-brace 스캔으로 교체 후 올바르게 파싱돼야 한다.
    """
    parser = Parser()
    # Inline JSON — no fenced block, contains curly brace inside value
    response = '{"twitter": "연봉 {3.5%} 를 기대했지만 현실은 달랐다"}'
    payload = parser._extract_json_payload(response)
    assert "twitter" in payload
    assert "{3.5%}" in payload["twitter"]


def test_extract_json_payload_nested_object_returns_outermost():
    """DV-BAL002: 깊이 있는 중첩 JSON에서도 outermost 객체 반환."""
    parser = Parser()
    response = '{"twitter": "text", "meta": {"score": 8}}'
    payload = parser._extract_json_payload(response)
    assert "twitter" in payload
    assert payload["twitter"] == "text"
