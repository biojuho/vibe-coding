from __future__ import annotations

from pathlib import Path
from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)
src_package_path = Path(__file__).resolve().parents[1] / "src" / "shorts_maker_v2"
if src_package_path.exists():
    __path__.append(str(src_package_path))

