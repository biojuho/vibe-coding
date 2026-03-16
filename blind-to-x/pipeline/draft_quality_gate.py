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

logger = logging.getLogger(__name__)


# ── 플랫폼별 품질 기준 ──────────────────────────────────────────────
PLATFORM_RULES: dict[str, dict[str, Any]] = {
    "twitter": {
        "min_len": 60,
        "max_len": 280,
        "require_cta": True,
        "cta_patterns": [
            r"[?？]",                  # 질문으로 끝나는지
            r"(어떻게|어떰|공감|RT|리트윗|생각|의견|댓글|여러분|나만)",
        ],
        "max_hashtags": 3,
        "forbidden_patterns": [
            r"https?://",            # 외부 링크 금지
        ],
        "min_korean_ratio": 0.3,     # 한글 비율 최소
    },
    "threads": {
        "min_len": 80,
        "max_len": 500,
        "require_cta": True,
        "cta_patterns": [
            r"[?？]",
            r"(댓글|저장|공감|여러분|어떻게|어떤|의견|생각)",
        ],
        "max_hashtags": 5,
        "min_hashtags": 1,
        "forbidden_patterns": [],
        "min_korean_ratio": 0.3,
    },
    "naver_blog": {
        "min_len": 1000,
        "max_len": 5000,
        "require_headings": True,
        "min_headings": 2,
        "min_seo_tags": 5,
        "require_cta": True,
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
            rule=rule, passed=passed, detail=detail, severity=severity,
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
    korean_chars = sum(1 for c in text if '\uac00' <= c <= '\ud7a3')
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

        # strict_mode 처리
        if self.strict_mode:
            warnings_failed = any(
                not i.passed and i.severity == "warning" for i in result.items
            )
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
        skip_keys = {"_provider_used", "_regulation_check"}

        for platform, content in drafts.items():
            if platform in skip_keys:
                continue
            if not content or not isinstance(content, str):
                continue
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
