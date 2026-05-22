"""Unit tests for pipeline/scrape_integrity.py — 수집 콘텐츠 무결성 분류 (D-033)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline.scrape_integrity import (
    DEFAULT_MIN_ARTICLE_CHARS,
    classify_scrape_integrity,
)

# 게이트를 통과해야 하는 현실적인 게시물 본문 (220자 이상, 시그니처 없음).
_GENUINE = (
    "팀장이 회의에서 성과급 이야기를 꺼냈는데 다들 표정이 굳었다. "
    "작년보다 적게 나온 사람이 절반이 넘었고, 옆자리 동료는 이직을 알아보겠다고 했다. "
    "결국 회사가 보상으로 잡아두려는 신호가 아니라 떠나라는 신호처럼 느껴졌다는 댓글이 많았다. "
    "어떤 사람은 그래도 올해는 경기가 어려우니 이해한다고 했지만, "
    "대부분은 평가 기준이 매년 바뀌는 게 더 문제라고 지적했다. "
    "한 댓글은 차라리 기준을 공개하고 납득시키는 회사가 부럽다고 적었고, "
    "그 밑으로 비슷한 경험담이 줄줄이 달리며 스레드가 길어졌다."
)


class TestGenuineArticle:
    def test_genuine_long_post_passes(self):
        verdict = classify_scrape_integrity("성과급 후기", _GENUINE)
        assert verdict["ok"] is True
        assert verdict["category"] == "article"
        assert verdict["failure_reason"] is None

    def test_short_genuine_post_without_sentinel_passes(self):
        # 짧아도 시그니처가 없으면 통과 — 길이만으로는 차단하지 않는다.
        verdict = classify_scrape_integrity("점심 메뉴 고민", "오늘 점심 뭐 먹지 다들 추천 좀.")
        assert verdict["ok"] is True

    def test_empty_inputs_do_not_crash(self):
        assert classify_scrape_integrity("", "")["ok"] is True
        assert classify_scrape_integrity(None, None)["ok"] is True  # type: ignore[arg-type]


class TestHardSentinels:
    """봇 차단·캡차 페이지 — 본문 길이와 무관하게 차단."""

    def test_bot_block_page_is_blocked(self):
        verdict = classify_scrape_integrity("", "비정상적인 접근이 감지되어 일시적으로 차단되었습니다.")
        assert verdict["ok"] is False
        assert verdict["category"] == "blocked"
        assert verdict["failure_reason"] == "scrape_blocked_page"

    def test_captcha_page_is_blocked(self):
        verdict = classify_scrape_integrity("보안 확인", "자동입력 방지문자를 입력해 주세요.")
        assert verdict["ok"] is False
        assert verdict["failure_reason"] == "scrape_blocked_page"

    def test_english_access_denied_is_blocked(self):
        verdict = classify_scrape_integrity("", "Access Denied. You do not have permission.")
        assert verdict["ok"] is False
        assert verdict["category"] == "blocked"

    def test_hard_sentinel_blocks_even_with_long_body(self):
        # 본문이 길어도 하드 시그니처가 있으면 차단 (차단 페이지에 잡설이 붙은 경우).
        long_body = "비정상적인 접근이 감지되었습니다. " + ("안내문 " * 80)
        verdict = classify_scrape_integrity("", long_body)
        assert verdict["ok"] is False
        assert verdict["category"] == "blocked"


class TestSoftSentinels:
    """로그인 월·삭제 글 — 본문이 짧을 때만 차단."""

    def test_short_login_wall_is_non_article(self):
        verdict = classify_scrape_integrity("게시물", "로그인이 필요합니다. 앱을 다운로드하세요.")
        assert verdict["ok"] is False
        assert verdict["category"] == "non_article"
        assert verdict["failure_reason"] == "scrape_login_wall"

    def test_short_deleted_post_is_non_article(self):
        verdict = classify_scrape_integrity("", "삭제된 게시물입니다.")
        assert verdict["ok"] is False
        assert verdict["failure_reason"] == "scrape_deleted_post"

    def test_long_post_quoting_soft_sentinel_passes(self):
        # 정상 게시물이 본문에서 '로그인이 필요'를 인용 — 길이가 충분하면 통과.
        verdict = classify_scrape_integrity("회사 보안 정책 토론", _GENUINE + " 사내 시스템은 로그인이 필요하다.")
        assert verdict["ok"] is True
        assert verdict["category"] == "article"

    def test_min_article_chars_is_configurable(self):
        text = "로그인이 필요합니다. " + ("안내 " * 20)  # 약 100자대
        # 기본 임계값(220)에서는 짧다고 보아 차단
        assert classify_scrape_integrity("", text)["ok"] is False
        # 임계값을 매우 낮추면 '충분히 길다'고 보아 통과
        assert classify_scrape_integrity("", text, min_article_chars=10)["ok"] is True

    def test_default_threshold_constant_is_exposed(self):
        assert DEFAULT_MIN_ARTICLE_CHARS == 220
