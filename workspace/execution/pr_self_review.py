"""
PR 셀프 리뷰 자동화 — git diff를 LLM에 보내 리뷰 생성.

3계층 아키텍처의 Execution 레이어 스크립트.
`LLMClient`(자동 fallback)를 사용하여 비용 최적화.

Usage (CLI):
    # 현재 브랜치 vs main 전체 리뷰
    python workspace/execution/pr_self_review.py

    # 특정 브랜치/커밋 비교
    python workspace/execution/pr_self_review.py --base main --head HEAD

    # staged 변경만 리뷰
    python workspace/execution/pr_self_review.py --staged

    # 특정 프로젝트 디렉토리만
    python workspace/execution/pr_self_review.py --path projects/hanwoo-dashboard

    # 출력 형식 선택
    python workspace/execution/pr_self_review.py --format markdown
    python workspace/execution/pr_self_review.py --format json

    # 리뷰 깊이 조절
    python workspace/execution/pr_self_review.py --depth quick   # 빠른 요약
    python workspace/execution/pr_self_review.py --depth deep    # 상세 리뷰

Usage (library):
    from execution.pr_self_review import SelfReviewer
    reviewer = SelfReviewer()
    result = reviewer.review(base="main", head="HEAD")
    print(result["summary"])
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import REPO_ROOT  # noqa: E402

# ── 상수 ──────────────────────────────────────────────

MAX_DIFF_CHARS = 48_000  # LLM 컨텍스트 한도 고려
MAX_DIFF_FILES = 50  # 파일 수 상한

REVIEW_DEPTH_PROMPTS = {
    "quick": "핵심 변경사항만 3줄 이내로 요약해. 명백한 버그가 있으면 '⚠️ 버그' 태그로 표시.",
    "standard": (
        "코드 리뷰어 관점에서 다음을 분석해:\n"
        "1. **변경 요약**: 무엇이 왜 변경되었는지\n"
        "2. **위험 요소**: 잠재적 버그, 보안 이슈, 성능 문제\n"
        "3. **개선 제안**: 코드 품질, 패턴 일관성, 테스트 필요성\n"
        "4. **점수**: 10점 만점 (1=위험, 10=완벽)"
    ),
    "deep": (
        "시니어 개발자로서 상세한 코드 리뷰를 수행해:\n"
        "1. **변경 요약**: 각 파일별 변경 목적과 영향\n"
        "2. **아키텍처 영향**: 기존 패턴과의 일관성, 의존성 변화\n"
        "3. **버그 & 보안**: 잠재적 런타임 에러, 경쟁 조건, 입력 검증 누락\n"
        "4. **성능**: 불필요한 연산, N+1 쿼리, 메모리 누수 가능성\n"
        "5. **테스트**: 누락된 테스트 케이스, 경계 조건\n"
        "6. **네이밍/가독성**: 변수명, 함수명, 주석의 명확성\n"
        "7. **파일별 점수**: 이모지로 표시 (✅ 좋음, ⚠️ 주의, 🔴 위험)\n"
        "8. **종합 점수**: 10점 만점"
    ),
}

SYSTEM_PROMPT = (
    "당신은 숙련된 코드 리뷰 전문가입니다. "
    "주어진 git diff를 분석하고, 실질적이고 구체적인 피드백을 제공합니다. "
    "코드 리뷰 기준:\n"
    "- 즉시 수정이 필요한 버그는 반드시 지적\n"
    "- 보안 취약점은 절대 간과하지 않음\n"
    "- 제안은 구체적 코드 예시와 함께\n"
    "- 긍정적인 변경도 인정\n"
    "- 한국어로 응답"
)


# ── 모델 ──────────────────────────────────────────────


@dataclass
class DiffChunk:
    """git diff의 파일 단위 청크."""

    filepath: str
    status: str  # M, A, D, R
    diff_text: str
    additions: int = 0
    deletions: int = 0


@dataclass
class ReviewResult:
    """리뷰 결과."""

    summary: str
    diff_stats: dict[str, Any] = field(default_factory=dict)
    provider_used: str = ""
    model_used: str = ""
    truncated: bool = False

    def as_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "diff_stats": self.diff_stats,
            "provider_used": self.provider_used,
            "model_used": self.model_used,
            "truncated": self.truncated,
        }


# ── Git 유틸 ──────────────────────────────────────────


def _run_git(*args: str, cwd: Path | None = None) -> str:
    """git 커맨드 실행 후 stdout 반환."""
    result = subprocess.run(
        ["git", *args],
        cwd=str(cwd or REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def get_current_branch(cwd: Path | None = None) -> str:
    """현재 브랜치 이름 반환."""
    return _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=cwd).strip()


def get_diff(
    *,
    base: str = "main",
    head: str = "HEAD",
    staged: bool = False,
    path_filter: str | None = None,
    cwd: Path | None = None,
) -> str:
    """git diff 실행."""
    args = ["diff", "--stat", "--patch", "--no-color"]

    if staged:
        args.append("--cached")
    else:
        args.extend([f"{base}...{head}"])

    if path_filter:
        args.extend(["--", path_filter])

    return _run_git(*args, cwd=cwd)


def get_diff_stat(
    *,
    base: str = "main",
    head: str = "HEAD",
    staged: bool = False,
    path_filter: str | None = None,
    cwd: Path | None = None,
) -> dict[str, Any]:
    """diff 통계 반환 (파일 수, 추가/삭제 행 수)."""
    args = ["diff", "--numstat", "--no-color"]

    if staged:
        args.append("--cached")
    else:
        args.extend([f"{base}...{head}"])

    if path_filter:
        args.extend(["--", path_filter])

    output = _run_git(*args, cwd=cwd)

    files: list[dict[str, Any]] = []
    total_additions = 0
    total_deletions = 0

    for line in output.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            adds = int(parts[0]) if parts[0] != "-" else 0
            dels = int(parts[1]) if parts[1] != "-" else 0
            filepath = parts[2]
            files.append({"path": filepath, "additions": adds, "deletions": dels})
            total_additions += adds
            total_deletions += dels

    return {
        "file_count": len(files),
        "total_additions": total_additions,
        "total_deletions": total_deletions,
        "files": files,
    }


def _truncate_diff(diff_text: str, max_chars: int = MAX_DIFF_CHARS) -> tuple[str, bool]:
    """diff가 너무 크면 잘라냄."""
    if len(diff_text) <= max_chars:
        return diff_text, False

    truncated = diff_text[:max_chars]
    # 마지막 완전한 파일 경계에서 자름
    last_diff_marker = truncated.rfind("\ndiff --git ")
    if last_diff_marker > max_chars // 2:
        truncated = truncated[:last_diff_marker]

    truncated += f"\n\n... (전체 diff의 {len(truncated) * 100 // len(diff_text)}%만 표시, 나머지 생략)\n"
    return truncated, True


# ── 리뷰어 ──────────────────────────────────────────────


class SelfReviewer:
    """LLMClient 기반 PR 셀프 리뷰어."""

    def __init__(
        self,
        *,
        providers: list[str] | None = None,
        depth: str = "standard",
    ):
        from execution.llm_client import LLMClient

        self.client = LLMClient(
            providers=providers,
            caller_script="pr_self_review",
            cache_ttl_sec=3600,  # 리뷰 캐시 1시간
        )
        self.depth = depth if depth in REVIEW_DEPTH_PROMPTS else "standard"

    def review(
        self,
        *,
        base: str = "main",
        head: str = "HEAD",
        staged: bool = False,
        path_filter: str | None = None,
        cwd: Path | None = None,
    ) -> ReviewResult:
        """diff를 가져와 LLM 리뷰 생성."""
        # 1. diff 가져오기
        diff_text = get_diff(
            base=base,
            head=head,
            staged=staged,
            path_filter=path_filter,
            cwd=cwd,
        )

        if not diff_text.strip():
            return ReviewResult(
                summary="변경사항이 없습니다.",
                diff_stats={"file_count": 0, "total_additions": 0, "total_deletions": 0},
            )

        # 2. 통계
        diff_stats = get_diff_stat(
            base=base,
            head=head,
            staged=staged,
            path_filter=path_filter,
            cwd=cwd,
        )

        # 3. 크기 제한
        diff_text, truncated = _truncate_diff(diff_text)

        # 4. 프롬프트 구성
        depth_instruction = REVIEW_DEPTH_PROMPTS[self.depth]
        branch = get_current_branch(cwd) if not staged else "(staged)"
        compare_desc = "staged changes" if staged else f"{base}...{head}"

        user_prompt = (
            f"## 리뷰 대상\n"
            f"- 브랜치: `{branch}`\n"
            f"- 비교: `{compare_desc}`\n"
            f"- 파일 수: {diff_stats['file_count']}개\n"
            f"- 변경: +{diff_stats['total_additions']} / -{diff_stats['total_deletions']}\n"
            f"{'- ⚠️ diff가 너무 커서 일부만 포함됨' if truncated else ''}\n\n"
            f"## 리뷰 기준\n{depth_instruction}\n\n"
            f"## Git Diff\n```diff\n{diff_text}\n```"
        )

        # 5. LLM 호출
        review_text = self.client.generate_text(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.3,  # 낮은 온도로 일관된 리뷰
        )

        # 6. 사용된 프로바이더 확인
        enabled = self.client.enabled_providers()
        provider_used = enabled[0] if enabled else "unknown"

        return ReviewResult(
            summary=review_text,
            diff_stats=diff_stats,
            provider_used=provider_used,
            truncated=truncated,
        )


# ── CLI ──────────────────────────────────────────────


def _format_markdown(result: ReviewResult) -> str:
    """리뷰 결과를 마크다운으로 포맷."""
    stats = result.diff_stats
    lines = [
        "# 📝 PR 셀프 리뷰",
        "",
        f"**파일**: {stats.get('file_count', 0)}개 | "
        f"**변경**: +{stats.get('total_additions', 0)} / -{stats.get('total_deletions', 0)} | "
        f"**프로바이더**: {result.provider_used}",
    ]

    if result.truncated:
        lines.append("> ⚠️ diff가 너무 커서 일부만 리뷰되었습니다.")

    lines.extend(["", "---", "", result.summary])
    return "\n".join(lines)


def _format_plain(result: ReviewResult) -> str:
    """리뷰 결과를 플레인 텍스트로 포맷."""
    stats = result.diff_stats
    header = (
        f"{'=' * 60}\n"
        f"  PR 셀프 리뷰\n"
        f"  파일: {stats.get('file_count', 0)}개 | "
        f"+{stats.get('total_additions', 0)} / -{stats.get('total_deletions', 0)}\n"
        f"{'=' * 60}\n"
    )
    return header + "\n" + result.summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PR self review -- git diff를 LLM에 보내 리뷰 생성",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--base", default="main", help="비교 기준 브랜치/커밋 (기본: main)")
    parser.add_argument("--head", default="HEAD", help="비교 대상 (기본: HEAD)")
    parser.add_argument("--staged", action="store_true", help="staged 변경만 리뷰")
    parser.add_argument("--path", default=None, help="특정 경로만 리뷰 (예: projects/hanwoo-dashboard)")
    parser.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        default="standard",
        help="리뷰 깊이 (기본: standard)",
    )
    parser.add_argument(
        "--format",
        dest="output_format",
        choices=["plain", "markdown", "json"],
        default="plain",
        help="출력 형식 (기본: plain)",
    )
    parser.add_argument(
        "--provider",
        default=None,
        help="사용할 LLM 프로바이더 (예: google, openai). 미지정 시 자동 fallback",
    )
    parser.add_argument(
        "--repo",
        default=None,
        help="리뷰할 저장소 경로 (기본: 현재 워크스페이스 루트)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    providers = [args.provider] if args.provider else None
    cwd = Path(args.repo) if args.repo else None

    try:
        reviewer = SelfReviewer(providers=providers, depth=args.depth)
        result = reviewer.review(
            base=args.base,
            head=args.head,
            staged=args.staged,
            path_filter=args.path,
            cwd=cwd,
        )

        if args.output_format == "json":
            print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
        elif args.output_format == "markdown":
            print(_format_markdown(result))
        else:
            print(_format_plain(result))

        return 0

    except RuntimeError as exc:
        print(f"❌ 리뷰 실패: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"❌ 예상치 못한 오류: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
