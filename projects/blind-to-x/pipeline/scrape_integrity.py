"""스크레이프 콘텐츠 무결성 분류 (D-033).

스크래퍼가 HTML을 받아 셀렉터로 텍스트를 추출하는 데 '성공'했지만, 그 텍스트가
실제 게시물 본문이 아니라 로그인 월·삭제된 글·봇 차단/캡차 페이지인 경우가 있다.
Blind처럼 콘텐츠를 로그인 뒤로 가두는 사이트에서는 세션 쿠키 만료 시 로그인 월
HTML이 그대로 추출된다. 이런 비-게시물 페이지는 한국어 비율·길이 검사를 통과해
검토 큐를 오염시킨다.

이 모듈은 그런 페이지를 결정론적으로(LLM·네트워크 호출 없이) 감지해 수집 실패로
분류한다. `evaluate_candidate_editorial_fit`(편집 적합도)나 `assess_quality`(스크랩
품질)와 책임이 다르다 — 그것들은 '진짜 게시물'의 품질을 보지만, 이 모듈은 추출한
것이 애초에 게시물이 맞는지를 본다.
"""

from __future__ import annotations

from typing import Any

# 봇 차단·캡차·인프라 차단 페이지 시그니처.
# 직장인 커뮤니티 게시물에는 사실상 등장하지 않으므로 본문 길이와 무관하게 차단한다.
_HARD_SENTINELS: tuple[str, ...] = (
    "비정상적인 접근",
    "자동입력 방지",
    "보안문자를 입력",
    "일시적으로 차단되었",
    "접근이 차단되었",
    "access denied",
    "too many requests",
    "checking your browser",
    "cf-browser-verification",
)

# 로그인 월·삭제/없는 글 시그니처.
# 정상 게시물이 본문에서 인용할 가능성이 (드물게) 있으므로, 본문이
# `min_article_chars` 미만으로 짧을 때만 비-게시물로 판정한다.
_SOFT_SENTINELS: tuple[str, ...] = (
    "로그인이 필요",
    "로그인 후 이용",
    "로그인하고 보기",
    "앱에서 더 보기",
    "앱에서 더 많은",
    "앱에서 전체",
    "앱 다운로드",
    "앱을 다운로드",
    "삭제된 게시물",
    "삭제된 글입니다",
    "존재하지 않는 게시",
    "찾을 수 없는 페이지",
    "페이지를 찾을 수 없",
    "이미 삭제된 게시",
)

# 소프트 시그니처 중 '삭제/없는 글' 계열 — 별도 failure_reason으로 구분 기록.
_DELETED_MARKERS: tuple[str, ...] = ("삭제", "존재하지", "찾을 수 없")

DEFAULT_MIN_ARTICLE_CHARS = 220


def classify_scrape_integrity(
    title: str,
    content: str,
    *,
    min_article_chars: int = DEFAULT_MIN_ARTICLE_CHARS,
) -> dict[str, Any]:
    """추출된 title/content가 실제 게시물인지 분류한다.

    Args:
        title: 추출된 제목.
        content: 추출된 본문.
        min_article_chars: 소프트 시그니처 판정 시 사용할 최소 본문 길이.
            본문이 이보다 짧고 소프트 시그니처가 있으면 비-게시물로 본다.

    Returns:
        dict:
            ``ok`` — True면 정상 게시물로 보임.
            ``category`` — ``"article"`` | ``"blocked"`` | ``"non_article"``.
            ``failure_reason`` — 실패 분류 사유 (ok=True면 None).
            ``matched`` — 매칭된 시그니처 문자열 (ok=True면 None).
    """
    title_s = str(title or "")
    content_s = str(content or "")
    haystack = f"{title_s}\n{content_s}".lower()
    body_len = len(content_s.strip())

    for sentinel in _HARD_SENTINELS:
        if sentinel in haystack:
            return {
                "ok": False,
                "category": "blocked",
                "failure_reason": "scrape_blocked_page",
                "matched": sentinel,
            }

    if body_len < max(0, int(min_article_chars)):
        for sentinel in _SOFT_SENTINELS:
            if sentinel in haystack:
                is_deleted = any(marker in sentinel for marker in _DELETED_MARKERS)
                return {
                    "ok": False,
                    "category": "non_article",
                    "failure_reason": "scrape_deleted_post" if is_deleted else "scrape_login_wall",
                    "matched": sentinel,
                }

    return {"ok": True, "category": "article", "failure_reason": None, "matched": None}
