"""중앙 환경변수 로더.

역할별로 분리된 .env 파일들을 한 번에 로드합니다.
기존 load_dotenv() 호출을 이 모듈의 load_all_env()로 점진적 교체하세요.

사용법:
    from execution._env_loader import load_all_env
    load_all_env()
"""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

_ROOT = Path(__file__).resolve().parent.parent

# 로드 순서: project → llm → social → 레거시 .env (override=False로 중복 방지)
_ENV_FILES = [
    _ROOT / ".env.project",
    _ROOT / ".env.llm",
    _ROOT / ".env.social",
    _ROOT / ".env",  # 레거시 호환 (점진적 제거 예정)
]

_loaded = False


def load_all_env(*, force: bool = False) -> None:
    """모든 역할별 .env 파일을 로드합니다.

    이미 로드되었으면 스킵합니다 (force=True로 재로드 가능).
    """
    global _loaded  # noqa: PLW0603
    if _loaded and not force:
        return
    for env_file in _ENV_FILES:
        if env_file.exists():
            load_dotenv(env_file, override=False)
    _loaded = True
