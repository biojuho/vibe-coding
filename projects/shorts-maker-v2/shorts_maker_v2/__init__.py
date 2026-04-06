"""shorts_maker_v2 패키지 브릿지.

이 패키지는 프로젝트 루트에서 `from shorts_maker_v2.xxx import yyy` 형태의
import를 가능하게 하는 **네임스페이스 브릿지**입니다.

실제 소스 코드는 `src/shorts_maker_v2/`에 있으며, 이 __init__.py가
pkgutil.extend_path를 통해 경로를 연결합니다.

⚠️ 삭제하면 모든 테스트와 CLI가 동작하지 않습니다!
"""

from __future__ import annotations

import importlib
from pathlib import Path
from pkgutil import extend_path

__all__ = ["run_cli"]

__path__ = extend_path(__path__, __name__)
src_package_path = Path(__file__).resolve().parents[1] / "src" / "shorts_maker_v2"
if src_package_path.exists():
    __path__.append(str(src_package_path))


def __getattr__(name: str):
    """Forward package entrypoints to the src implementation lazily."""
    if name == "run_cli":
        cli = importlib.import_module("shorts_maker_v2.cli")
        return cli.run_cli
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
