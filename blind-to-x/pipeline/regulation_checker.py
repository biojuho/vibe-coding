"""Platform regulation & algorithm compliance checker.

트렌드 & 플랫폼 규제 반영 콘텐츠 창작 시스템의 핵심 모듈.
각 플랫폼(X, Threads, 네이버 블로그)의 규제 사항을 점검하고,
생성된 콘텐츠가 규제를 준수하는지 검증합니다.

규제 데이터는 classification_rules.yaml의 platform_regulations 섹션에서 로드됩니다.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

_RULES_FILE = Path(__file__).parent.parent / "classification_rules.yaml"
_regulation_cache: dict | None = None


def _load_regulations() -> dict:
    """classification_rules.yaml에서 규제 데이터를 1회 로드 후 캐시."""
    global _regulation_cache
    if _regulation_cache is not None:
        return _regulation_cache
    if yaml is None or not _RULES_FILE.exists():
        _regulation_cache = {}
        return _regulation_cache
    try:
        with open(_RULES_FILE, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        _regulation_cache = data.get("platform_regulations", {})
    except Exception as exc:
        logger.warning("Failed to load platform regulations: %s", exc)
        _regulation_cache = {}
    return _regulation_cache


def reload_regulations() -> None:
    """규제 캐시를 강제 초기화 (테스트 또는 동적 갱신 시 사용)."""
    global _regulation_cache
    _regulation_cache = None


@dataclass
class ValidationItem:
    """단일 검증 항목 결과."""
    rule: str
    passed: bool
    detail: str = ""
    severity: str = "warning"  # "warning" | "error"


@dataclass
class ValidationReport:
    """플랫폼별 콘텐츠 규제 검증 리포트."""
    platform: str
    passed: bool = True
    items: list[ValidationItem] = field(default_factory=list)
    score: int = 100  # 규제 준수 점수 (100점 만점)

    def add(self, rule: str, passed: bool, detail: str = "", severity: str = "warning") -> None:
        """검증 항목 추가."""
        item = ValidationItem(rule=rule, passed=passed, detail=detail, severity=severity)
        self.items.append(item)
        if not passed:
            if severity == "error":
                self.passed = False
                self.score -= 20
            else:
                self.score -= 10
        self.score = max(0, self.score)

    def to_text(self) -> str:
        """검증 리포트를 텍스트로 포맷팅."""
        lines = [f"[{self.platform} 규제 검증 — 점수: {self.score}/100]"]
        for item in self.items:
            icon = "✅" if item.passed else ("❌" if item.severity == "error" else "⚠️")
            lines.append(f"{icon} {item.rule}: {item.detail}")
        return "\n".join(lines)

    def to_dict(self) -> dict[str, Any]:
        """JSON-serializable dict 변환."""
        return {
            "platform": self.platform,
            "passed": self.passed,
            "score": self.score,
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


class RegulationChecker:
    """플랫폼별 규제 점검 및 컴플라이언스 필터 모듈.

    Args:
        config: 파이프라인 설정 dict.
        strict_mode: True면 규제 위반 콘텐츠의 발행을 차단합니다.
    """

    def __init__(self, config: dict | None = None, strict_mode: bool = False):
        self.config = config or {}
        self.strict_mode = strict_mode
        self.regulations = _load_regulations()

    def get_platform_rules(self, platform: str) -> dict:
        """특정 플랫폼의 규제 데이터를 반환합니다."""
        return self.regulations.get(platform, {})

    def get_do_dont_checklist(self, platform: str) -> dict[str, list[str]]:
        """플랫폼별 Do/Don't 체크리스트를 반환합니다."""
        rules = self.get_platform_rules(platform)
        return {
            "do": rules.get("do_checklist", []),
            "dont": rules.get("dont_checklist", []),
        }

    def get_algorithm_tips(self, platform: str) -> list[str]:
        """플랫폼별 알고리즘 우대 요소를 반환합니다."""
        rules = self.get_platform_rules(platform)
        return rules.get("algorithm_favors", [])

    def build_regulation_context(self, platforms: list[str] | None = None) -> str:
        """드래프트 생성 프롬프트에 주입할 규제 컨텍스트 문자열을 생성합니다.

        Args:
            platforms: 컨텍스트를 생성할 플랫폼 목록. None이면 전체.

        Returns:
            LLM 프롬프트에 삽입할 규제 가이드 텍스트.
        """
        if not self.regulations:
            return ""

        target_platforms = platforms or list(self.regulations.keys())
        lines: list[str] = [
            "\n[플랫폼 규제 준수 가이드 — 반드시 지켜야 할 사항]",
        ]

        for platform in target_platforms:
            rules = self.get_platform_rules(platform)
            if not rules:
                continue

            display = rules.get("display_name", platform)
            lines.append(f"\n■ {display}")

            # Do 체크리스트
            do_list = rules.get("do_checklist", [])
            if do_list:
                lines.append("  [반드시 해야 할 것]")
                for item in do_list:
                    lines.append(f"  ✅ {item}")

            # Don't 체크리스트
            dont_list = rules.get("dont_checklist", [])
            if dont_list:
                lines.append("  [절대 하지 말아야 할 것]")
                for item in dont_list:
                    lines.append(f"  ❌ {item}")

            # 알고리즘 우대
            algo_list = rules.get("algorithm_favors", [])
            if algo_list:
                lines.append("  [알고리즘이 우대하는 콘텐츠]")
                for item in algo_list:
                    lines.append(f"  💡 {item}")

        # 통합 안내
        lines.append(
            "\n※ 위 규제를 위반하면 도달률 하락, shadowban, 계정 제재가 발생할 수 있습니다."
        )
        lines.append(
            "※ 각 플랫폼 초안 작성 후 반드시 <regulation_check> 태그 안에 자체 검증 결과를 작성하세요."
        )

        return "\n".join(lines)

    def validate_twitter(self, content: str) -> ValidationReport:
        """X(트위터) 콘텐츠의 규제 준수 여부를 검증합니다."""
        report = ValidationReport(platform="X (Twitter)")
        rules = self.get_platform_rules("x_twitter")

        # 1. 글자 수 검증
        max_len = rules.get("max_length", 280)
        content_len = len(content.strip())
        report.add(
            "글자 수 제한",
            content_len <= max_len,
            f"{content_len}자 (최대 {max_len}자)",
            severity="error" if content_len > max_len else "warning",
        )

        # 2. 외부 링크 단독 여부
        url_pattern = r"https?://\S+"
        urls = re.findall(url_pattern, content)
        text_without_urls = re.sub(url_pattern, "", content).strip()
        if urls and len(text_without_urls) < 30:
            report.add(
                "외부 링크 단독 게시 금지",
                False,
                "본문이 너무 짧고 링크만 포함됨 — 알고리즘 불이익",
                severity="error",
            )
        else:
            report.add("외부 링크 단독 게시 금지", True, "정상")

        # 3. 해시태그 개수
        hashtags = re.findall(r"#\w+", content)
        max_hashtags = rules.get("max_hashtags", 3)
        report.add(
            "해시태그 제한",
            len(hashtags) <= max_hashtags,
            f"{len(hashtags)}개 (최대 {max_hashtags}개)",
        )

        # 4. 금지어 체크
        penalty_words = rules.get("penalty_words", [])
        found_penalties = [w for w in penalty_words if w in content]
        report.add(
            "페널티 유발 단어",
            len(found_penalties) == 0,
            f"발견: {', '.join(found_penalties)}" if found_penalties else "없음",
            severity="error" if found_penalties else "warning",
        )

        return report

    def validate_threads(self, content: str) -> ValidationReport:
        """Threads 콘텐츠의 규제 준수 여부를 검증합니다."""
        report = ValidationReport(platform="Threads")
        rules = self.get_platform_rules("threads")

        # 1. 글자 수
        max_len = rules.get("max_length", 500)
        content_len = len(content.strip())
        report.add(
            "글자 수 제한",
            content_len <= max_len,
            f"{content_len}자 (최대 {max_len}자)",
            severity="error" if content_len > max_len else "warning",
        )

        # 2. 외부 링크 체크 (Threads는 외부 링크 포함 시 추천 피드 제외)
        urls = re.findall(r"https?://\S+", content)
        report.add(
            "외부 링크 미포함",
            len(urls) == 0,
            f"링크 {len(urls)}개 발견 — 추천 피드에서 제외될 수 있음" if urls else "정상",
            severity="warning",
        )

        # 3. 해시태그 개수 (3~5개 이내)
        hashtags = re.findall(r"#\w+", content)
        max_hashtags = rules.get("max_hashtags", 5)
        report.add(
            "해시태그 제한",
            len(hashtags) <= max_hashtags,
            f"{len(hashtags)}개 (최대 {max_hashtags}개)",
        )

        # 4. 상업적 CTA 과다 체크
        commercial_cta = rules.get("commercial_cta_words", ["구매", "할인", "프로모션", "쿠폰", "광고"])
        found_cta = [w for w in commercial_cta if w in content]
        report.add(
            "상업적 CTA 금지",
            len(found_cta) == 0,
            f"발견: {', '.join(found_cta)}" if found_cta else "없음",
            severity="error" if found_cta else "warning",
        )

        return report

    def validate_naver_blog(self, content: str) -> ValidationReport:
        """네이버 블로그 콘텐츠의 규제 준수 여부를 검증합니다."""
        report = ValidationReport(platform="네이버 블로그")
        rules = self.get_platform_rules("naver_blog")

        # 1. 글자 수 (최소 1500자)
        min_len = rules.get("min_length", 1500)
        content_len = len(content.strip())
        report.add(
            "최소 글자 수",
            content_len >= min_len,
            f"{content_len}자 (최소 {min_len}자)",
            severity="error" if content_len < 500 else "warning",
        )

        # 2. 소제목 구조 체크 (## 또는 ###)
        subheadings = re.findall(r"^#{2,3}\s+.+", content, re.MULTILINE)
        min_subheadings = rules.get("min_subheadings", 3)
        report.add(
            "소제목 구조화",
            len(subheadings) >= min_subheadings,
            f"소제목 {len(subheadings)}개 (최소 {min_subheadings}개 필요)",
        )

        # 3. SEO 태그 확인
        hashtags = re.findall(r"#\w+", content)
        min_tags = rules.get("min_seo_tags", 10)
        report.add(
            "SEO 태그",
            len(hashtags) >= min_tags,
            f"태그 {len(hashtags)}개 (최소 {min_tags}개 권장)",
        )

        # 4. 키워드 도배 체크 (동일 키워드 10회 이상 반복)
        words = re.findall(r"\b\w{2,}\b", content)
        word_counts: dict[str, int] = {}
        for w in words:
            word_counts[w] = word_counts.get(w, 0) + 1
        max_repeat = rules.get("max_keyword_repeat", 10)
        stuffed = [f"{w}({c}회)" for w, c in word_counts.items() if c >= max_repeat and len(w) >= 3]
        report.add(
            "키워드 도배 금지",
            len(stuffed) == 0,
            f"과다 반복: {', '.join(stuffed[:3])}" if stuffed else "정상",
            severity="error" if stuffed else "warning",
        )

        # 5. 복사 콘텐츠 패턴 (간단 휴리스틱: 연속 동일 문장 반복)
        sentences = re.split(r"[.!?]\s+", content)
        unique_sentences = set(s.strip() for s in sentences if len(s.strip()) > 20)
        total_long = sum(1 for s in sentences if len(s.strip()) > 20)
        if total_long > 3:
            dup_ratio = 1.0 - (len(unique_sentences) / total_long)
            report.add(
                "중복 문장 검사",
                dup_ratio < 0.3,
                f"중복 비율 {dup_ratio:.0%}" if dup_ratio >= 0.3 else "정상",
                severity="warning",
            )

        return report

    def validate_content(self, content: str, platform: str) -> ValidationReport:
        """플랫폼에 따라 적절한 검증을 수행합니다.

        Args:
            content: 검증할 콘텐츠 텍스트.
            platform: "twitter" | "threads" | "naver_blog".

        Returns:
            ValidationReport 인스턴스.
        """
        validators = {
            "twitter": self.validate_twitter,
            "x_twitter": self.validate_twitter,
            "threads": self.validate_threads,
            "naver_blog": self.validate_naver_blog,
        }
        validator = validators.get(platform)
        if validator:
            return validator(content)

        # 알 수 없는 플랫폼은 기본 통과
        report = ValidationReport(platform=platform)
        report.add("플랫폼 인식", True, f"'{platform}'에 대한 전용 규제 룰 없음")
        return report

    def validate_all_drafts(self, drafts: dict[str, str]) -> dict[str, ValidationReport]:
        """모든 플랫폼 드래프트를 일괄 검증합니다.

        Args:
            drafts: {"twitter": "...", "threads": "...", "naver_blog": "..."}.

        Returns:
            플랫폼별 ValidationReport 딕셔너리.
        """
        reports: dict[str, ValidationReport] = {}
        platform_map = {
            "twitter": "twitter",
            "threads": "threads",
            "naver_blog": "naver_blog",
        }
        for key, platform in platform_map.items():
            content = drafts.get(key, "")
            if content and not content.startswith("Error"):
                reports[key] = self.validate_content(content, platform)
            else:
                # 콘텐츠가 비어 있거나 에러인 경우 스킵
                report = ValidationReport(platform=platform)
                report.add("콘텐츠 존재", False, "초안 없음 또는 생성 실패", severity="warning")
                reports[key] = report

        return reports

    def format_validation_summary(self, reports: dict[str, ValidationReport]) -> str:
        """검증 리포트를 통합 요약 텍스트로 포맷팅합니다."""
        lines = ["━" * 40, "📋 플랫폼 규제 준수 검증 리포트", "━" * 40]

        all_passed = True
        for platform, report in reports.items():
            lines.append(report.to_text())
            lines.append("")
            if not report.passed:
                all_passed = False

        if all_passed:
            lines.append("✅ 전체 플랫폼 규제 검증 통과")
        else:
            lines.append("⚠️ 일부 플랫폼에서 규제 위반 또는 경고가 발견되었습니다")

        lines.append("━" * 40)
        return "\n".join(lines)
