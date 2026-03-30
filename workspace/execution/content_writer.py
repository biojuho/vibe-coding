"""
AI 기반 콘텐츠 작성기 (NotebookLM 파이프라인 Phase 1)

3계층 아키텍처의 Execution Layer 스크립트.
추출된 텍스트와 프롬프트 템플릿을 결합하여 Gemini / Claude / GPT로 블로그 아티클을 생성합니다.

환경 변수:
    CONTENT_WRITER_AI_MODEL   사용할 AI 모델 (기본: gemini)
    GOOGLE_AI_API_KEY         Gemini API 키
    ANTHROPIC_API_KEY         Claude API 키  (선택)
    OPENAI_API_KEY            GPT API 키 (선택)
    CONTENT_WRITER_PROMPTS_DIR 프롬프트 템플릿 디렉토리 (기본: directives/prompts/)

사용 예:
    python workspace/execution/content_writer.py write --text-file .tmp/extracted.txt --project my_project
    python workspace/execution/content_writer.py write --text "..." --project default
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime
from pathlib import Path

import yaml

from execution._logging import logger

# 기본 리소스 경로 (Execution Layer 기준)
_ROOT = Path(__file__).resolve().parent.parent
_PROMPTS_DIR = Path(os.environ.get("CONTENT_WRITER_PROMPTS_DIR", str(_ROOT / "directives" / "prompts")))

# 지원 모델 제공사
SUPPORTED_PROVIDERS = ["gemini", "claude", "gpt"]

DEFAULT_PROVIDER = os.environ.get("CONTENT_WRITER_AI_MODEL", "gemini")


# ── 프롬프트 템플릿 로드 ────────────────────────────────────────────────────


def load_prompt_template(project: str) -> dict:
    """프로젝트별 프롬프트 템플릿을 로드합니다.

    탐색 순서:
    1. directives/prompts/notebooklm_{project}.yaml
    2. directives/prompts/notebooklm_default.yaml

    Args:
        project: 프로젝트 이름 (예: "my_project", "default").

    Returns:
        {
            "system": str,
            "user_prefix": str,
            "tone": str,
            "language": str,
            "output_format": str  # "markdown"
        }
    """
    candidates = [
        _PROMPTS_DIR / f"notebooklm_{project}.yaml",
        _PROMPTS_DIR / "notebooklm_default.yaml",
    ]

    for path in candidates:
        if path.exists():
            with path.open(encoding="utf-8") as f:
                template = yaml.safe_load(f)
            logger.info("[ContentWriter] 프롬프트 템플릿 로드: %s", path.name)
            return template or {}

    logger.warning("[ContentWriter] 프롬프트 템플릿 없음 — 기본값 사용")
    return _default_template()


def _default_template() -> dict:
    return {
        "system": (
            "당신은 전문적인 콘텐츠 라이터입니다. "
            "제공된 자료를 바탕으로 한국어로 블로그 아티클을 작성하세요. "
            "독자는 일반 대중이며, 명확하고 가독성 높은 글을 작성하세요."
        ),
        "user_prefix": "다음 자료를 바탕으로 블로그 아티클을 작성해주세요:",
        "tone": "informative",
        "language": "ko",
        "output_format": "markdown",
    }


# ── Gemini 글 작성 ──────────────────────────────────────────────────────────


def _write_with_gemini(text: str, template: dict) -> str:
    """Google Gemini API로 아티클을 생성합니다."""
    try:
        import google.generativeai as genai
    except ImportError:
        raise ImportError("google-generativeai 미설치. pip install google-generativeai")

    api_key = os.environ.get("GOOGLE_AI_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_AI_API_KEY 또는 GEMINI_API_KEY 환경 변수 필요")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=template.get("system", ""),
    )

    user_message = _build_user_message(text, template)
    response = model.generate_content(user_message)

    return response.text.strip()


# ── Claude 글 작성 ──────────────────────────────────────────────────────────


def _write_with_claude(text: str, template: dict) -> str:
    """Anthropic Claude API로 아티클을 생성합니다."""
    try:
        import anthropic
    except ImportError:
        raise ImportError("anthropic 미설치. pip install anthropic")

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY 환경 변수 필요")

    client = anthropic.Anthropic(api_key=api_key)
    user_message = _build_user_message(text, template)

    message = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=4096,
        system=template.get("system", ""),
        messages=[{"role": "user", "content": user_message}],
    )
    return message.content[0].text.strip()


# ── GPT 글 작성 ─────────────────────────────────────────────────────────────


def _write_with_gpt(text: str, template: dict) -> str:
    """OpenAI GPT API로 아티클을 생성합니다."""
    try:
        from openai import OpenAI
    except ImportError:
        raise ImportError("openai 미설치. pip install openai")

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수 필요")

    client = OpenAI(api_key=api_key)
    user_message = _build_user_message(text, template)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": template.get("system", "")},
            {"role": "user", "content": user_message},
        ],
        temperature=0.7,
        max_tokens=4096,
    )
    return response.choices[0].message.content.strip()


# ── 프롬프트 조립 ───────────────────────────────────────────────────────────


def _build_user_message(text: str, template: dict) -> str:
    """사용자 메시지를 조립합니다.

    템플릿의 user_prefix와 추출 텍스트를 결합하여
    구조화된 아티클 작성 프롬프트를 반환합니다.
    """
    prefix = template.get("user_prefix", "다음 자료를 바탕으로 블로그 아티클을 작성해주세요:")
    output_format = template.get("output_format", "markdown")
    language = template.get("language", "ko")

    # 입력 텍스트가 너무 길면 자르기 (Gemini Flash 기준 1M 토큰이지만 안전하게)
    max_input_chars = 60_000
    if len(text) > max_input_chars:
        text = text[:max_input_chars] + "\n\n[... 텍스트가 너무 길어 일부 생략됨 ...]"
        logger.warning("[ContentWriter] 입력 텍스트가 %d자를 초과하여 자름", max_input_chars)

    return f"""{prefix}

---
{text}
---

요구사항:
- 언어: {language}
- 출력 형식: {output_format}
- 구조: 제목(H1) + 소제목(H2) + 본문 + 핵심 요약 섹션 포함
- Notion에 바로 붙여넣기 가능한 Markdown 출력
- 독자가 바로 이해할 수 있는 명확한 문체

아티클을 작성해주세요."""


# ── 폴백 체인 ───────────────────────────────────────────────────────────────


def write_article(
    text: str,
    *,
    project: str = "default",
    provider: str | None = None,
) -> dict:
    """AI로 아티클을 생성합니다. 실패 시 폴백 체인을 시도합니다.

    폴백 체인: gemini → claude → gpt

    Args:
        text: 기반이 될 추출 텍스트.
        project: 프롬프트 템플릿을 결정하는 프로젝트 이름.
        provider: 명시적 AI 제공사 지정. None이면 환경 변수 또는 gemini 기본값.

    Returns:
        {
            "article": str,
            "title": str,
            "provider": str,
            "project": str,
            "char_count": int,
            "generated_at": str,
        }
    """
    template = load_prompt_template(project)
    primary_provider = provider or DEFAULT_PROVIDER

    provider_funcs = {
        "gemini": _write_with_gemini,
        "claude": _write_with_claude,
        "gpt": _write_with_gpt,
    }

    # 폴백 순서 구성 (primary 먼저)
    chain = [primary_provider] + [p for p in SUPPORTED_PROVIDERS if p != primary_provider]

    last_error = None
    for p in chain:
        fn = provider_funcs.get(p)
        if fn is None:
            continue
        try:
            logger.info("[ContentWriter] %s로 글 작성 시도...", p)
            article = fn(text, template)
            if not article.strip():
                raise ValueError("빈 응답 반환")

            # 제목 추출 (첫 번째 # 헤딩)
            title = ""
            for line in article.splitlines():
                if line.startswith("# "):
                    title = line.lstrip("# ").strip()
                    break

            logger.info("[ContentWriter] %s 글 작성 완료 (%d자)", p, len(article))
            return {
                "article": article,
                "title": title,
                "provider": p,
                "project": project,
                "char_count": len(article),
                "generated_at": datetime.utcnow().isoformat() + "Z",
            }
        except Exception as exc:
            logger.warning("[ContentWriter] %s 실패: %s → 다음 provider 시도", p, exc)
            last_error = exc

    raise RuntimeError(f"모든 AI provider 실패. 마지막 오류: {last_error}")


# ── CLI 엔트리포인트 ─────────────────────────────────────────────────────────


def main():
    """CLI 엔트리포인트."""
    parser = argparse.ArgumentParser(description="AI 기반 콘텐츠 작성기")
    sub = parser.add_subparsers(dest="command", required=True)

    p_write = sub.add_parser("write", help="아티클 생성")
    group = p_write.add_mutually_exclusive_group(required=True)
    group.add_argument("--text", help="직접 입력할 텍스트")
    group.add_argument("--text-file", help="텍스트 파일 경로")
    p_write.add_argument("--project", default="default", help="프로젝트 이름 (프롬프트 템플릿 선택)")
    p_write.add_argument("--provider", choices=SUPPORTED_PROVIDERS, default=None, help="AI 모델 선택")
    p_write.add_argument("--output", help="결과 저장 경로 (JSON)")

    args = parser.parse_args()

    if args.command == "write":
        if args.text:
            text = args.text
        else:
            text = Path(args.text_file).read_text(encoding="utf-8")

        result = write_article(text, project=args.project, provider=args.provider)

        if args.output:
            out = Path(args.output)
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"✓ 결과 저장: {args.output}")
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
