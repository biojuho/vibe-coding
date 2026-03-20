"""
NotebookLM Integration — 래퍼 스크립트 (팟캐스트 제외)

3계층 아키텍처의 Execution Layer 스크립트.
notebooklm-py CLI를 감싸서 파이프라인에서 프로그래밍 방식으로 활용합니다.

사용 예시:
    python execution/notebooklm_integration.py research "AI trends 2026" --urls https://example.com
    python execution/notebooklm_integration.py generate-quiz "AI Research" --difficulty hard
    python execution/notebooklm_integration.py bulk-import "My Collection" --urls urls.txt
"""

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

# ──────────────────────────────────────────────
# 상수
# ──────────────────────────────────────────────

# 팟캐스트(audio)는 의도적으로 제외
ALLOWED_GENERATE_TYPES = [
    "video",
    "slide-deck",
    "quiz",
    "flashcards",
    "infographic",
    "mind-map",
    "data-table",
    "report",
]

RELIABLE_TYPES = ["mind-map", "data-table", "report"]  # Rate limit 거의 없음
RATE_LIMITED_TYPES = ["video", "slide-deck", "quiz", "flashcards", "infographic"]

# venv 내 CLI 경로 자동 탐색
_venv_scripts = Path(sys.executable).parent
_cli_candidate = _venv_scripts / "notebooklm.exe"
CLI = str(_cli_candidate) if _cli_candidate.exists() else "notebooklm"


# ──────────────────────────────────────────────
# 유틸리티
# ──────────────────────────────────────────────


def _run(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess:
    """notebooklm CLI 명령어 실행 래퍼."""
    cmd = [CLI] + args
    print(f"  → {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and result.returncode != 0:
        print(f"  ✗ 에러 (exit {result.returncode}): {result.stderr.strip()}")
    return result


def _run_json(args: list[str]) -> dict | None:
    """CLI 명령어 실행 후 JSON 파싱."""
    result = _run(args + ["--json"], check=False)
    if result.returncode != 0:
        print(f"  ✗ JSON 파싱 실패: {result.stderr.strip()}")
        return None
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"  ✗ JSON 디코드 실패: {result.stdout[:200]}")
        return None


def check_auth() -> bool:
    """인증 상태 확인. auth check가 불안정할 수 있으므로 list --json fallback."""
    result = _run(["list", "--json"], check=False)
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            if "notebooks" in data:
                print(f"  ✓ 인증 정상 (노트북 {data.get('count', len(data['notebooks']))}개)")
                return True
        except (json.JSONDecodeError, KeyError):
            pass
    print("  ⚠ 인증 만료. 'notebooklm login' 실행 필요")
    return False


# ──────────────────────────────────────────────
# 핵심 워크플로우
# ──────────────────────────────────────────────


def research_workflow(
    title: str,
    urls: list[str] | None = None,
    query: str | None = None,
    questions: list[str] | None = None,
    search_mode: str = "deep",
) -> dict | None:
    """
    리서치 워크플로우: 노트북 생성 → 소스 추가 → 질의응답.

    Args:
        title: 노트북 제목
        urls: 추가할 URL 리스트
        query: 웹 리서치 쿼리 (선택)
        questions: 소스에 대한 질문 리스트 (선택)

    Returns:
        {"notebook_id": str, "sources": list, "answers": list}
    """
    if not check_auth():
        return None

    # 1. 노트북 생성
    nb_data = _run_json(["create", title])
    if not nb_data:
        return None
    nb_id = nb_data["id"]
    print(f"  ✓ 노트북 생성: {nb_id}")

    # 2. 노트북 활성화
    _run(["use", nb_id])

    # 3. 소스 추가
    source_ids = []
    if urls:
        for url in urls:
            src = _run_json(["source", "add", url])
            if src and "source_id" in src:
                source_ids.append(src["source_id"])
                print(f"  ✓ 소스 추가: {url}")

    # 4. 웹 리서치 (단일 위키 대신 주제에 맞춰 자동 소스 탐색 및 연동)
    if query:
        cmd = ["source", "add-research", query, "--mode", search_mode]
        if search_mode == "deep":
            cmd.append("--import-all")
        _run(cmd)
        print(f"  ✓ 자동 소스 탐색 및 연동 완료 ({search_mode} Research): {query}")

    # 5. 소스 처리 대기
    if source_ids:
        print("  ⏳ 소스 인덱싱 대기...")
        time.sleep(15)  # 기본 대기

    # 6. 질의응답 (선택)
    answers = []
    if questions:
        for q in questions:
            result = _run_json(["ask", q])
            if result and "answer" in result:
                answers.append({"question": q, "answer": result["answer"]})
                print(f"  ✓ Q: {q[:50]}...")

    return {"notebook_id": nb_id, "sources": source_ids, "answers": answers}


def generate_content(
    notebook_id: str,
    content_type: str,
    *,
    instructions: str = "",
    options: list[str] | None = None,
) -> dict | None:
    """
    콘텐츠 생성 (팟캐스트 제외).

    Args:
        notebook_id: 노트북 ID
        content_type: 생성 유형 (video, quiz, mind-map 등)
        instructions: 추가 지시사항
        options: 추가 CLI 옵션

    Returns:
        {"task_id": str, "status": str} 또는 동기 결과
    """
    if content_type == "audio":
        print("  ✗ 팟캐스트(audio)는 현재 제외된 기능입니다.")
        return None

    if content_type not in ALLOWED_GENERATE_TYPES:
        print(f"  ✗ 지원하지 않는 유형: {content_type}")
        print(f"    사용 가능: {', '.join(ALLOWED_GENERATE_TYPES)}")
        return None

    if content_type in RATE_LIMITED_TYPES:
        print(f"  ⚠ {content_type}은 Rate Limiting 가능성 있음")

    _run(["use", notebook_id])

    cmd = ["generate", content_type]
    if instructions:
        cmd.append(instructions)
    if options:
        cmd.extend(options)

    result = _run_json(cmd)
    return result


def bulk_import(title: str, urls_file: str) -> dict | None:
    """
    URL 일괄 임포트.

    Args:
        title: 노트북 제목
        urls_file: URL 목록 파일 경로 (줄당 1개 URL)

    Returns:
        {"notebook_id": str, "imported": int, "failed": int}
    """
    path = Path(urls_file)
    if not path.exists():
        print(f"  ✗ 파일 없음: {urls_file}")
        return None

    urls = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not urls:
        print("  ✗ URL이 없습니다.")
        return None

    print(f"  📥 {len(urls)}개 URL 임포트 시작...")
    result = research_workflow(title, urls=urls)
    if result:
        print(f"  ✓ 완료: {len(result['sources'])}개 성공")
    return result


def auto_research_and_generate(
    topic: str,
    *,
    generate_types: list[str] | None = None,
    search_mode: str = "deep",
    questions: list[str] | None = None,
) -> dict | None:
    """
    원스톱 자동 리서치 파이프라인.

    주제(topic)를 주면:
    1. 노트북 자동 생성
    2. 웹 딥 리서치로 다양한 소스 자동 수집·연동 (위키 한정 탈피)
    3. 질의응답 (옵션)
    4. 마인드맵·인포그래픽·슬라이드 아티팩트 생성

    Args:
        topic: 리서치할 주제 (자연어)
        generate_types: 생성할 아티팩트 유형 리스트. 기본값: ["mind-map", "infographic", "slide-deck"]
        search_mode: 웹 리서치 깊이 ("deep" | "fast")
        questions: 수집된 소스에 물어볼 질문 목록

    Returns:
        {"notebook_id": str, "sources": list, "answers": list, "artifacts": list}
    """
    if not check_auth():
        return None

    if generate_types is None:
        generate_types = ["mind-map", "infographic", "slide-deck"]

    title = f"Auto Research: {topic[:60]}"
    print(f"\n🔍 자동 리서치 시작: '{topic}'")
    print(f"  ℹ 아티팩트: {', '.join(generate_types)}")

    # 1 & 2: 노트북 생성 + 딥 리서치 소스 자동 수집·연동
    research = research_workflow(
        title,
        query=topic,
        search_mode=search_mode,
        questions=questions,
    )
    if not research:
        return None

    nb_id = research["notebook_id"]
    print(f"  ✓ 노트북 ID: {nb_id}")
    print(f"  ✓ 소스 연동 수: {len(research['sources'])}개")

    # 소스 인덱싱 추가 대기
    if search_mode == "deep":
        print("  ⏳ 딥 리서치 인덱싱 대기 (30초)...")
        time.sleep(30)

    # 3: 아티팩트 생성 (마인드맵은 즉시, Rate Limit 없음)
    artifact_results = []
    for i, gen_type in enumerate(generate_types):
        if gen_type not in ALLOWED_GENERATE_TYPES:
            print(f"  ⚠ 건너뜀 (지원하지 않는 유형): {gen_type}")
            continue
        print(f"  🛠 {gen_type} 생성 중...")
        result = generate_content(nb_id, gen_type)
        if result:
            artifact_results.append({"type": gen_type, **result})
            print(f"  ✓ {gen_type} 생성 요청 완료")
        else:
            print(f"  ✗ {gen_type} 생성 실패 (Rate Limit 가능성)")
        # Rate-limited 유형 사이에 짧은 대기
        if gen_type in RATE_LIMITED_TYPES and i < len(generate_types) - 1:
            print("  ⏳ 연속 요청 Rate Limit 방지 (5초 대기)...")
            time.sleep(5)

    return {
        "notebook_id": nb_id,
        "sources": research["sources"],
        "answers": research.get("answers", []),
        "artifacts": artifact_results,
    }


# ──────────────────────────────────────────────
# CLI 엔트리포인트
# ──────────────────────────────────────────────


def main():
    """CLI 엔트리포인트."""
    parser = argparse.ArgumentParser(
        description="NotebookLM Integration (팟캐스트 제외)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # research
    p_research = sub.add_parser("research", help="리서치 워크플로우")
    p_research.add_argument("title", help="노트북 제목")
    p_research.add_argument("--urls", nargs="*", help="추가할 URL 목록")
    p_research.add_argument("--query", help="웹 리서치 쿼리 (자동 소스 연동)")
    p_research.add_argument("--questions", nargs="*", help="질문 목록")
    p_research.add_argument(
        "--search-mode", choices=["deep", "fast"], default="deep", help="웹 리서치 모드 (기본: deep)"
    )

    # generate
    p_gen = sub.add_parser("generate", help="콘텐츠 생성")
    p_gen.add_argument("notebook_id", help="노트북 ID")
    p_gen.add_argument("type", choices=ALLOWED_GENERATE_TYPES, help="생성 유형")
    p_gen.add_argument("--instructions", default="", help="추가 지시사항")

    # bulk-import
    p_bulk = sub.add_parser("bulk-import", help="URL 일괄 임포트")
    p_bulk.add_argument("title", help="노트북 제목")
    p_bulk.add_argument("--urls", required=True, help="URL 목록 파일 경로")

    # auto-research
    p_auto = sub.add_parser("auto-research", help="주제 입력 시 자동 소스 탐색 + 아티팩트 생성")
    p_auto.add_argument("topic", help="리서치할 주제 (\ubaa8든 소스 자동 탐색)")
    p_auto.add_argument(
        "--generate",
        nargs="*",
        default=["mind-map", "report"],
        metavar="TYPE",
        help=f"생성할 유형 (기본: mind-map infographic slide-deck). 선택 가능: {', '.join(ALLOWED_GENERATE_TYPES)}",
    )
    p_auto.add_argument("--search-mode", choices=["deep", "fast"], default="deep", help="리서치 모드")
    p_auto.add_argument("--questions", nargs="*", help="소스에 묻어볼 질문 목록")

    # auth-check
    sub.add_parser("auth-check", help="인증 상태 확인")

    args = parser.parse_args()

    if args.command == "research":
        result = research_workflow(
            args.title, urls=args.urls, query=args.query, questions=args.questions, search_mode=args.search_mode
        )
    elif args.command == "auto-research":
        result = auto_research_and_generate(
            args.topic,
            generate_types=args.generate,
            search_mode=args.search_mode,
            questions=args.questions,
        )
    elif args.command == "generate":
        result = generate_content(args.notebook_id, args.type, instructions=args.instructions)
    elif args.command == "bulk-import":
        result = bulk_import(args.title, args.urls)
    elif args.command == "auth-check":
        check_auth()
        return

    if result:
        print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
