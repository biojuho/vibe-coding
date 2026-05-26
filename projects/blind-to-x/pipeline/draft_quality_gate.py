"""Post-LLM 초안 품질 게이트 (Draft Quality Gate).

LLM이 생성한 초안이 플랫폼별 최소 품질 기준을 충족하는지 검증합니다.
검증 실패 시 재생성을 요청하거나 경고를 발생시킵니다.

사용법:
    gate = DraftQualityGate()
    result = gate.validate("twitter", "직장인 연봉 이야기...")
    if not result.passed:
        # 재생성 또는 경고 처리
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from pipeline.draft_contract import iter_publishable_drafts
from pipeline.rules_loader import get_rule_section

logger = logging.getLogger(__name__)

_cliche_cache: list[str] | None = None


def _load_cliche_watchlist() -> list[str]:
    """Load the cliche watchlist with a small local cache."""
    global _cliche_cache
    if _cliche_cache is not None:
        return _cliche_cache
    _cliche_cache = list(get_rule_section("cliche_watchlist", []))
    return _cliche_cache


# ── 플랫폼별 품질 기준 ──────────────────────────────────────────────
PLATFORM_RULES: dict[str, dict[str, Any]] = {
    "twitter": {
        "min_len": 60,
        "max_len": 280,
        "require_cta": False,
        "cta_patterns": [
            r"[?？]",  # 질문으로 끝나는지
            r"(어떻게|어떰|공감|RT|리트윗|생각|의견|댓글|여러분|나만)",
        ],
        "max_hashtags": 3,
        "forbidden_patterns": [
            r"https?://",  # 외부 링크 금지
        ],
        "min_korean_ratio": 0.3,  # 한글 비율 최소
    },
    "threads": {
        "min_len": 80,
        "max_len": 500,
        "require_cta": False,
        "cta_patterns": [
            r"[?？]",
            r"(댓글|저장|공감|여러분|어떻게|어떤|의견|생각)",
        ],
        "max_hashtags": 5,
        "min_hashtags": 0,
        "forbidden_patterns": [],
        "min_korean_ratio": 0.3,
    },
    "naver_blog": {
        "min_len": 1000,
        "max_len": 5000,
        "require_headings": True,
        "min_headings": 2,
        "min_seo_tags": 5,
        "require_cta": False,
        "cta_patterns": [
            r"(이웃|공감|좋아요|구독|댓글|의견|팔로우)",
        ],
        "min_korean_ratio": 0.4,
    },
    "newsletter": {
        "min_len": 300,
        "max_len": 2000,
        "require_cta": False,
        "min_korean_ratio": 0.3,
    },
}


@dataclass
class QualityCheckItem:
    """단일 품질 검사 항목 결과."""

    rule: str
    passed: bool
    detail: str = ""
    severity: str = "warning"  # "warning" | "error" | "info"


@dataclass
class QualityResult:
    """플랫폼별 초안 품질 검증 결과."""

    platform: str
    passed: bool = True
    score: int = 100
    items: list[QualityCheckItem] = field(default_factory=list)
    should_retry: bool = False

    def add(
        self,
        rule: str,
        passed: bool,
        detail: str = "",
        severity: str = "warning",
    ) -> None:
        """검사 항목 추가."""
        item = QualityCheckItem(
            rule=rule,
            passed=passed,
            detail=detail,
            severity=severity,
        )
        self.items.append(item)
        if not passed:
            if severity == "error":
                self.passed = False
                self.score -= 25
                self.should_retry = True
            elif severity == "warning":
                self.score -= 10
        self.score = max(0, self.score)

    def to_dict(self) -> dict[str, Any]:
        return {
            "platform": self.platform,
            "passed": self.passed,
            "score": self.score,
            "should_retry": self.should_retry,
            "items": [
                {
                    "rule": i.rule,
                    "passed": i.passed,
                    "detail": i.detail,
                    "severity": i.severity,
                }
                for i in self.items
            ],
        }

    def summary(self) -> str:
        """한 줄 요약 문자열."""
        icon = "✅" if self.passed else "❌"
        fails = [i for i in self.items if not i.passed]
        fail_str = f" ({len(fails)} issues)" if fails else ""
        return f"{icon} {self.platform}: score={self.score}/100{fail_str}"


def _korean_ratio(text: str) -> float:
    """텍스트 내 한글 문자 비율 계산."""
    if not text:
        return 0.0
    korean_chars = sum(1 for c in text if "\uac00" <= c <= "\ud7a3")
    total_chars = sum(1 for c in text if not c.isspace())
    return korean_chars / total_chars if total_chars > 0 else 0.0


def _count_hashtags(text: str) -> int:
    """해시태그 개수 계산."""
    return len(re.findall(r"#[\w가-힣]+", text))


def _count_headings(text: str) -> int:
    """Markdown 소제목(## 또는 ###) 개수 계산."""
    return len(re.findall(r"^#{2,3}\s+.+", text, re.MULTILINE))


def _has_cta(text: str, patterns: list[str]) -> bool:
    """CTA(Call-to-Action) 패턴이 존재하는지 검사."""
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False


def _has_forbidden(text: str, patterns: list[str]) -> list[str]:
    """금지 패턴 매칭 결과 반환."""
    found = []
    for pattern in patterns:
        matches = re.findall(pattern, text)
        if matches:
            found.append(pattern)
    return found


def _looks_like_error_text(text: str) -> bool:
    lowered = (text or "").lower()
    signals = (
        "error generating drafts",
        "rate limit",
        "too many requests",
        "429",
        "traceback",
        "attributeerror",
        "asyncopenai",
        "sdk error",
        "gemini api error",
        "service unavailable",
    )
    return any(signal in lowered for signal in signals)


def _has_scene_anchor(text: str) -> bool:
    first_sentence = re.split(r"(?<=[.!?\n])\s+|\n+", text.strip(), maxsplit=1)[0]
    if not first_sentence:
        return False
    return bool(
        re.search(r"\d", first_sentence)
        or re.search(r"[\"'“”‘’]", first_sentence)
        or re.search(r"(회의|출근|퇴근|카톡|메신저|면담|복도|회의실|점심|야근|실수령|세전|세후)", first_sentence)
        or re.search(r"(라고|라는 말|했더니|했는데)", first_sentence)
    )


def _has_generic_cta(text: str) -> bool:
    return bool(
        re.search(
            r"(여러분 생각은|어떻게 생각|어떠신가요|여러분은 어떻게|여러분도 그렇게 생각|공감하시나요)\??",
            text,
        )
    )


def _has_cliche_opening(text: str) -> bool:
    first_sentence = re.split(r"(?<=[.!?\n])\s+|\n+", text.strip(), maxsplit=1)[0]
    return bool(
        re.search(
            r"(오늘은 .*이야기해보|많은 .* 고민하고 있|현실적으로|결론적으로|요즘 사람들|한번 생각해봅시다)",
            first_sentence,
        )
    )


# ── P1-A: 인플루언서 어휘 zero-tolerance ──────────────────────────────
# brand_voice yaml 의 "절대 금지" 목록과 동기화. 1회만 등장해도 톤이 깨지므로
# cliche_watchlist (3개 임계) 와 별도로 즉시 실패시킨다.
#
# 의도적으로 제외한 어휘: "지뢰", "시그널" — 일상 어휘(지뢰밭, 매수 시그널)와
# 충돌이 잦아 false positive 가 많다. 3회 이상 누적은 cliche_watchlist 가 잡는다.
_INFLUENCER_VOCAB = (
    "끝판왕",
    "민낯",
    "쓴맛",
    "기절할 뻔",
    "어처구니없",
    "어질어질",
    "한 수 알려",
    "정신 차리고 봐",
    "현실 자각 타임",
    "팩폭",
    "팩폭당",
    "레전드",
)


def _find_influencer_vocab(text: str) -> list[str]:
    """인플루언서 명사화·과장 어휘를 찾아서 매칭된 어휘 리스트를 반환."""
    found: list[str] = []
    for word in _INFLUENCER_VOCAB:
        if word in text:
            found.append(word)
    # 중복 제거 (순서 유지)
    seen: set[str] = set()
    deduped: list[str] = []
    for word in found:
        if word not in seen:
            seen.add(word)
            deduped.append(word)
    return deduped


# ── P1-B: 마무리 여운 (마지막 문장이 CTA/질문으로 끝나지 않아야 함) ──
_CLOSING_CTA_PATTERNS = re.compile(
    r"(댓글로|저장해|공감하면|RT 부탁|리트윗 부탁|구독 부탁|팔로우 부탁|"
    r"좋아요 부탁|한 수 알려|의견 알려|어떻게 생각|어떠신가요|"
    r"공감되시면|아닐까요|아닐까\??$|않을까요|않을까\??$)"
)


def _ends_with_cta_or_question(text: str) -> str | None:
    """마지막 문장이 질문/CTA 로 끝나면 매칭된 사유, 아니면 None."""
    sentences = [s.strip() for s in re.split(r"(?<=[.!?。\n])\s*", text.strip()) if s.strip()]
    if not sentences:
        return None
    last = sentences[-1]
    # 트레일링 구두점 제거
    last_clean = last.rstrip()
    if last_clean.endswith(("?", "？")):
        return "마지막 문장이 질문(?)으로 끝남"
    if _CLOSING_CTA_PATTERNS.search(last_clean):
        return "마지막 문장에 CTA 패턴 포함"
    return None


# ── P1-C: 이모지 카운트 ───────────────────────────────────────────────
# BMP 외(U+1F300~U+1FAFF) + 일부 BMP 심볼 + variation selector 동반 이모지.
# 한글/숫자/구두점은 카운트하지 않음.
_EMOJI_PATTERN = re.compile(
    "["
    "\U0001f300-\U0001f5ff"  # 기호·픽토그램
    "\U0001f600-\U0001f64f"  # 이모티콘
    "\U0001f680-\U0001f6ff"  # 운송·지도
    "\U0001f700-\U0001f77f"
    "\U0001f780-\U0001f7ff"
    "\U0001f800-\U0001f8ff"
    "\U0001f900-\U0001f9ff"  # 추가 기호·픽토그램
    "\U0001fa00-\U0001faff"  # 추가 픽토그램
    "\U00002600-\U000027bf"  # 기타 기호·딩벳
    "]"
)


def _count_emojis(text: str) -> int:
    """이모지(픽토그래프) 개수를 결정론적으로 카운트."""
    return len(_EMOJI_PATTERN.findall(text or ""))


# ── P1-D: 출처 도입 강박 ──────────────────────────────────────────────
_LEAD_DEPENDENCY_PATTERN = re.compile(
    r"(블라인드|뽐뿌|에펨코리아|fmkorea|잡플래닛|jobplanet|커뮤니티|레딧)"
    r"(?:에서|에)\s*"
    r"(?:봤|본\s*(?:글|얘기|이야기)|들었|들은|올라온|올라왔)"
)


def _has_lead_dependency(text: str) -> bool:
    """첫 문장이 '~에서 봤는데/~에 올라온 글인데' 류 도입 강박을 사용하는지."""
    first_sentence = re.split(r"(?<=[.!?\n])\s+|\n+", text.strip(), maxsplit=1)[0]
    if not first_sentence:
        return False
    return bool(_LEAD_DEPENDENCY_PATTERN.search(first_sentence))


# ── Phase 2 (2026-05-26+): creator_take 무색무취 검출 ──────────────────
# 운영자(creator)의 입장이 없는 "요약만 한 글" 을 결정론적으로 검출한다.
#
# 검출 기준은 의도적으로 보수적(conservative) 으로 잡았다 — golden 예시들은
# 의도적으로 짧고 관찰형이라 "판단 어휘 없음 == 무색무취" 라는 단순 규칙은
# 모조리 false-positive 가 난다. 진짜 무색무취는 hedge 가 누적되면서 동시에
# 일반화/양화 어휘("자주", "다양한", "많은") 가 끼어드는 패턴이다.

# 약화/추측/거리두기 어미·표현
_HEDGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"것\s*같"),
    re.compile(r"수도\s*있"),
    re.compile(r"있을\s*수\s*있"),
    re.compile(r"인\s*듯"),
    re.compile(r"라고\s*한다"),
    re.compile(r"라는\s*얘기"),
    re.compile(r"라는\s*말"),
    re.compile(r"보이는\s*듯"),
    re.compile(r"보이는\s*상황"),
    re.compile(r"보이고\s*있다"),
    re.compile(r"^[^\n]*?(아닐까|않을까)(요)?\s*싶", re.MULTILINE),
)

# 일반화/양화 어휘 — 무색무취 요약형 글에 동반 출현
_GENERALIZATION_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(
        r"(자주|다양한|많은\s*사람|여러\s*가지|종종|일부\s*사람|일반적|"
        r"대부분의|보통|흔히)"
    ),
)

# 강한 입장 신호 — 하나라도 있으면 "입장 있음" 으로 판정해 무색무취에서 면제
_STANCE_PATTERNS: tuple[re.Pattern[str], ...] = (
    # 가치 판단 어휘 (구체 평가)
    re.compile(
        r"(다행|안타|씁쓸|웃기|한심|어이없|황당|충격적|기특|놀랍|답답|섬뜩|"
        r"부럽|짠하|미안하|당연|이상하|기막|어처구니없|뻔뻔|치사|기가\s*막|"
        r"무섭|섬뜩하|허무|허탈|짜증|짜릿|짠한|짠함|짠하다)"
    ),
    # 운영자 시점/주관 표현
    re.compile(
        r"(내\s*생각|내\s*느낌|솔직히|개인적으로|보기에는|보기엔|"
        r"내가\s*보기|내가\s*느낀|내\s*기준)"
    ),
    # 강조/단언 부사
    re.compile(
        r"(?:^|[^\w가-힣])(결국|결국엔|진짜|정말|사실|솔직|분명히|"
        r"오히려|역설적|반대로|이게\s*맞|이게\s*아니|아닌|"
        r"안\s*되는|못\s*하는|진심)"
    ),
    # 대조 접속사 (입장 전환 신호)
    re.compile(r"(?:^|\s)(근데|그런데|하지만|반면|반대로)\b"),
    # 강한 종결 어휘 ('이거임', '~이다', '~게 답', '~한 셈')
    re.compile(
        r"(이거임|이게\s*답|이거였|인\s*셈|한\s*셈|"
        r"두\s*번째\s*[가-힣]+|다행이|불가능)"
    ),
    # 직접 의문문(수사적) — 마지막 ? 가 아닌 본문 중간의 ?
    re.compile(r"\?\s*\S"),
    # 1인칭 표현 (저는/나는/내가) — 자기 경험을 곧 입장으로 봄
    re.compile(r"(?:^|\s)(저는|나는|내가|제가|우리는)\b"),
)

# naver_blog 의 <creator_take> 태그 추출
_CREATOR_TAKE_TAG = re.compile(
    r"<creator_take>\s*(.*?)\s*</creator_take>",
    re.IGNORECASE | re.DOTALL,
)


def _extract_creator_take(text: str) -> str | None:
    """<creator_take> 태그 본문을 추출. 태그가 없으면 None."""
    match = _CREATOR_TAKE_TAG.search(text)
    if not match:
        return None
    return match.group(1).strip() or None


def _count_pattern_hits(text: str, patterns: tuple[re.Pattern[str], ...]) -> int:
    """주어진 패턴 묶음에 매칭된 unique 패턴 수를 반환."""
    return sum(1 for pat in patterns if pat.search(text))


def _is_colorless_take(text: str, min_chars: int = 30) -> tuple[bool, str]:
    """무색무취 take 여부를 보수적으로 판정한다.

    무색무취 = 다음 둘 중 하나:
      A. hedge ≥ 2 AND stance == 0 — "거리두기만 누적, 입장 0"
      B. generalization ≥ 1 AND stance == 0 AND length ≥ min_chars
         — "일반화 어휘로 요약만 하고 입장 없음"

    golden 예시(짧고 관찰형, 함축적 입장)는 모두 통과해야 함. 따라서 단순
    "stance == 0" 만으로는 무색무취 판정하지 않는다.

    Returns:
        (is_colorless, 사유). False 면 사유는 빈 문자열.
    """
    if not text or not text.strip():
        return False, ""
    cleaned = text.strip()
    stance_hits = _count_pattern_hits(cleaned, _STANCE_PATTERNS)
    if stance_hits > 0:
        return False, ""
    hedge_hits = _count_pattern_hits(cleaned, _HEDGE_PATTERNS)
    gen_hits = _count_pattern_hits(cleaned, _GENERALIZATION_PATTERNS)
    if hedge_hits >= 2:
        return True, f"hedge {hedge_hits}개 누적 / 입장 표현 0개"
    if gen_hits >= 1 and len(cleaned) >= min_chars:
        return True, f"일반화 어휘 {gen_hits}개 + 입장 표현 0개 ({len(cleaned)}자)"
    return False, ""


class DraftQualityGate:
    """LLM 생성 초안의 플랫폼별 품질 검증 게이트.

    Args:
        custom_rules: 플랫폼별 품질 기준 오버라이드. None이면 기본값 사용.
        strict_mode: True면 경고도 실패로 처리합니다.
    """

    def __init__(
        self,
        custom_rules: dict[str, dict[str, Any]] | None = None,
        strict_mode: bool = False,
    ):
        self.rules = {**PLATFORM_RULES}
        if custom_rules:
            for platform, overrides in custom_rules.items():
                if platform in self.rules:
                    self.rules[platform] = {**self.rules[platform], **overrides}
                else:
                    self.rules[platform] = overrides
        self.strict_mode = strict_mode

    def validate(self, platform: str, draft: str) -> QualityResult:
        """단일 플랫폼 초안의 품질을 검증합니다.

        Args:
            platform: "twitter" | "threads" | "naver_blog" | "newsletter".
            draft: 검증할 초안 텍스트.

        Returns:
            QualityResult 인스턴스.
        """
        result = QualityResult(platform=platform)
        rules = self.rules.get(platform, {})

        if not rules:
            result.add("규칙 존재", True, f"'{platform}'에 대한 품질 기준 없음", "info")
            return result

        if not draft or not draft.strip():
            result.add("초안 존재", False, "초안이 비어 있습니다", "error")
            return result

        text = draft.strip()

        if _looks_like_error_text(text):
            result.add("에러 응답", False, "LLM 에러/SDK 에러로 보이는 응답입니다", "error")
            return result

        # ── 1. 글자 수 검증 ──────────────────────────────────────────
        text_len = len(text)
        min_len = rules.get("min_len", 0)
        max_len = rules.get("max_len", 99999)

        if text_len < min_len:
            result.add(
                "최소 글자 수",
                False,
                f"{text_len}자 (최소 {min_len}자 필요)",
                "error",
            )
        elif text_len > max_len:
            result.add(
                "최대 글자 수",
                False,
                f"{text_len}자 (최대 {max_len}자 초과)",
                "error",
            )
        else:
            result.add(
                "글자 수",
                True,
                f"{text_len}자 (범위: {min_len}~{max_len})",
                "info",
            )

        # ── 2. 한글 비율 검증 ────────────────────────────────────────
        min_kr = rules.get("min_korean_ratio", 0)
        if min_kr > 0:
            kr_ratio = _korean_ratio(text)
            result.add(
                "한글 비율",
                kr_ratio >= min_kr,
                f"{kr_ratio:.0%} (최소 {min_kr:.0%})",
                "warning" if kr_ratio >= min_kr * 0.5 else "error",
            )
            if kr_ratio < min_kr * 0.5:
                result.add("깨진 글", False, "한글 비율이 너무 낮아 초안으로 보기 어렵습니다", "error")

        # ── 3. CTA 존재 여부 ─────────────────────────────────────────
        if rules.get("require_cta", False):
            cta_patterns = rules.get("cta_patterns", [])
            has = _has_cta(text, cta_patterns)
            result.add(
                "CTA 포함",
                has,
                "CTA 패턴 감지됨" if has else "CTA(질문, 유도 문구)가 없습니다",
                "warning",
            )

        # 상투적 CTA('여러분 생각은?' 등)는 require_cta 여부와 무관하게 항상 차단.
        # 새 톤(여운 마무리)의 핵심 위반 패턴이라 require_cta=False여도 검사 유지.
        if _has_generic_cta(text):
            result.add("상투적 CTA", False, "'여러분 생각은?'류의 generic CTA는 금지입니다", "error")

        # ── P1-A: 인플루언서 어휘 zero-tolerance (1회만 등장해도 실패) ─
        influencer_hits = _find_influencer_vocab(text)
        if influencer_hits:
            result.add(
                "인플루언서 어휘",
                False,
                f"자극적 명사화·과장 표현 {len(influencer_hits)}개: {', '.join(influencer_hits[:5])}",
                "error",
            )

        # ── P1-B: 마무리 여운 (twitter/threads 만 — 블로그는 마무리 형식이 다름) ─
        if platform in ("twitter", "threads"):
            closing_violation = _ends_with_cta_or_question(text)
            if closing_violation:
                result.add(
                    "마무리 여운",
                    False,
                    closing_violation + " — 담담한 평서문으로 끝낼 것",
                    "error",
                )

        # ── P1-C: 이모지 카운트 (twitter/threads: 기본 0개, 1개 허용, 그 이상 경고) ─
        if platform in ("twitter", "threads"):
            emoji_count = _count_emojis(text)
            if emoji_count > 3:
                result.add(
                    "이모지 과다",
                    False,
                    f"이모지 {emoji_count}개 — 기본 없음, 정말 의미 있을 때만 1개 이하",
                    "error",
                )
            elif emoji_count > 1:
                result.add(
                    "이모지 절제",
                    False,
                    f"이모지 {emoji_count}개 — 1개 이하 권장",
                    "warning",
                )

        # ── P1-D: 출처 도입 강박 ('~에서 봤는데') ─────────────────────
        if platform in ("twitter", "threads") and _has_lead_dependency(text):
            result.add(
                "도입 강박",
                False,
                "'~에서 봤는데/~에 올라온 글'로 시작하는 출처 도입 강박은 피할 것",
                "warning",
            )

        # ── Phase 2: creator_take 무색무취 검출 ────────────────────────
        # twitter/threads: 글 전체에 입장이 없으면 warning.
        # naver_blog: <creator_take> 태그가 있으면 그 안만 검사 (없으면 missing).
        if platform in ("twitter", "threads"):
            colorless, reason = _is_colorless_take(text)
            if colorless:
                result.add(
                    "무색무취 요약",
                    False,
                    f"운영자 입장이 없는 요약형 글 — {reason}. 한 줄이라도 해석/판단을 넣을 것",
                    "warning",
                )
        elif platform == "naver_blog":
            take = _extract_creator_take(text)
            if take is None:
                result.add(
                    "creator_take 누락",
                    False,
                    "<creator_take> 태그 안 운영자 해석 1문장이 없습니다",
                    "warning",
                )
            else:
                colorless, reason = _is_colorless_take(take, min_chars=20)
                if colorless:
                    result.add(
                        "무색무취 creator_take",
                        False,
                        f"<creator_take> 가 무색무취 — {reason}",
                        "warning",
                    )

        # ── 4. 해시태그 검증 ─────────────────────────────────────────
        hashtag_count = _count_hashtags(text)

        max_ht = rules.get("max_hashtags")
        if max_ht is not None:
            result.add(
                "해시태그 상한",
                hashtag_count <= max_ht,
                f"{hashtag_count}개 (최대 {max_ht}개)",
                "warning",
            )

        min_ht = rules.get("min_hashtags")
        if min_ht is not None:
            result.add(
                "해시태그 하한",
                hashtag_count >= min_ht,
                f"{hashtag_count}개 (최소 {min_ht}개)",
                "warning",
            )

        min_seo = rules.get("min_seo_tags")
        if min_seo is not None:
            result.add(
                "SEO 태그",
                hashtag_count >= min_seo,
                f"{hashtag_count}개 (최소 {min_seo}개 권장)",
                "warning",
            )

        # ── 5. 소제목 구조 (블로그) ──────────────────────────────────
        if rules.get("require_headings", False):
            min_h = rules.get("min_headings", 2)
            heading_count = _count_headings(text)
            result.add(
                "소제목 구조",
                heading_count >= min_h,
                f"소제목 {heading_count}개 (최소 {min_h}개)",
                "warning",
            )

        # ── 6. 금지 패턴 검사 ────────────────────────────────────────
        forbidden = rules.get("forbidden_patterns", [])
        if forbidden:
            found = _has_forbidden(text, forbidden)
            result.add(
                "금지 패턴",
                len(found) == 0,
                f"발견: {', '.join(found)}" if found else "없음",
                "warning",
            )

        # ── 7. 중복 문장 검사 (간단 휴리스틱) ─────────────────────────
        sentences = [s.strip() for s in re.split(r"[.!?。]\s*", text) if len(s.strip()) > 15]
        if len(sentences) >= 4:
            unique = set(sentences)
            dup_ratio = 1.0 - (len(unique) / len(sentences))
            result.add(
                "중복 문장",
                dup_ratio < 0.3,
                f"중복 비율 {dup_ratio:.0%}" if dup_ratio >= 0.3 else "정상",
                "warning",
            )

        # ── 8. 클리셰 검사 ─────────────────────────────────────────────
        cliches = _load_cliche_watchlist()
        if cliches:
            matched_cliches = [c for c in cliches if c in text]
            if len(matched_cliches) >= 3:
                result.add(
                    "클리셰 과다",
                    False,
                    f"상투적 표현 {len(matched_cliches)}개: {', '.join(matched_cliches[:5])}",
                    "warning",
                )
            elif matched_cliches:
                result.add(
                    "클리셰 검사",
                    True,
                    f"감지 {len(matched_cliches)}개 (허용 범위)",
                    "info",
                )

        # ── 9. 반복 문장 구조 검사 ─────────────────────────────────────
        if sentences and len(sentences) >= 3:
            # 연속 2문장이 같은 접두사(3자 이상)로 시작하면 경고
            repetitive_pairs = 0
            for i in range(len(sentences) - 1):
                prefix_len = min(3, len(sentences[i]), len(sentences[i + 1]))
                if prefix_len >= 3 and sentences[i][:prefix_len] == sentences[i + 1][:prefix_len]:
                    repetitive_pairs += 1
            if repetitive_pairs >= 2:
                result.add(
                    "반복 구조",
                    False,
                    f"연속 유사 시작 문장 {repetitive_pairs}쌍 — 문장 구조를 다양하게",
                    "warning",
                )

        # ── 10. 훅 강도 검사 (twitter/threads만, 참고용 info) ────────────
        if platform in ("twitter", "threads") and sentences:
            first_sentence = sentences[0]
            has_number = bool(re.search(r"\d", first_sentence))
            has_question = bool(re.search(r"[?？]", first_sentence))
            has_contrast = bool(re.search(r"(vs|VS|반면|아닌데|근데|그런데)", first_sentence))
            has_emotion = bool(
                re.search(
                    r"(레전드|미쳤|실화|충격|빡|열받|헐|대박|소름|ㅋㅋ|😂|🥲|😱|🤣)",
                    first_sentence,
                )
            )
            hook_strong = has_number or has_question or has_contrast or has_emotion
            if not _has_scene_anchor(text):
                result.add(
                    "구체 장면 없음",
                    False,
                    "첫 문장에 장면·대사·숫자 중 하나가 필요합니다",
                    "error",
                )
            if _has_cliche_opening(text):
                result.add(
                    "상투 오프닝",
                    False,
                    "해설형 오프닝 대신 바로 장면으로 시작해야 합니다",
                    "error",
                )
            if not hook_strong:
                result.add(
                    "훅 강도",
                    False,
                    "첫 문장에서 스크롤을 멈출 구체 훅이 약합니다",
                    "error",
                )

        # ── 11. 모호한 표현 검사 (구체성) ──────────────────────────────
        vague_patterns = [
            (r"높은 연봉", "구체적 금액을 사용하세요"),
            (r"많은 사람들", "구체적 대상을 명시하세요"),
            (r"최근에", "구체적 시점을 사용하세요"),
            (r"어떤 회사", "구체적 정보를 활용하세요"),
            (r"상당한 금액", "구체적 수치를 사용하세요"),
            (r"여러 가지", "구체적으로 나열하세요"),
        ]
        vague_found = []
        for pattern, suggestion in vague_patterns:
            if re.search(pattern, text):
                vague_found.append(suggestion)
        if len(vague_found) >= 3:
            # 3개 이상일 때만 실패 (자연어에서 1-2개는 허용)
            result.add(
                "구체성 부족",
                False,
                f"모호한 표현 {len(vague_found)}개 — {vague_found[0]}",
                "warning",
            )
        elif len(vague_found) >= 1:
            result.add(
                "구체성 참고",
                True,  # 통과 (참고만)
                f"모호한 표현 {len(vague_found)}개 감지 — 참고사항",
                "info",
            )

        # strict_mode 처리
        if self.strict_mode:
            warnings_failed = any(not i.passed and i.severity == "warning" for i in result.items)
            if warnings_failed:
                result.passed = False
                result.should_retry = True

        return result

    def validate_all(self, drafts: dict[str, str]) -> dict[str, QualityResult]:
        """모든 플랫폼 초안을 일괄 검증합니다.

        Args:
            drafts: {"twitter": "...", "threads": "...", ...}.

        Returns:
            플랫폼별 QualityResult 딕셔너리.
        """
        results: dict[str, QualityResult] = {}
        # 내부 메타 키 제외

        for platform, content in iter_publishable_drafts(drafts):
            results[platform] = self.validate(platform, content)

        return results

    def format_summary(self, results: dict[str, QualityResult]) -> str:
        """검증 결과 요약 문자열 생성."""
        lines = ["━" * 40, "📋 초안 품질 게이트 리포트", "━" * 40]

        all_passed = True
        total_score = 0
        count = 0

        for platform, result in results.items():
            lines.append(result.summary())
            if not result.passed:
                all_passed = False
                for item in result.items:
                    if not item.passed:
                        icon = "❌" if item.severity == "error" else "⚠️"
                        lines.append(f"  {icon} {item.rule}: {item.detail}")
            total_score += result.score
            count += 1

        avg_score = total_score / count if count > 0 else 0
        lines.append(f"\n평균 품질 점수: {avg_score:.0f}/100")

        if all_passed:
            lines.append("✅ 전체 플랫폼 품질 게이트 통과")
        else:
            retry_platforms = [p for p, r in results.items() if r.should_retry]
            if retry_platforms:
                lines.append(f"🔄 재생성 권장: {', '.join(retry_platforms)}")
            else:
                lines.append("⚠️ 일부 경고가 있지만 발행 가능")

        lines.append("━" * 40)
        return "\n".join(lines)
