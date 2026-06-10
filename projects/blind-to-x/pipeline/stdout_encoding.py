"""Console stdout encoding policy for Blind-to-X entry points."""

from __future__ import annotations

import locale
import sys


def is_utf8_encoding(value: str | None) -> bool:
    return str(value or "").replace("_", "-").casefold() in {"utf-8", "utf8", "utf-8-sig"}


def should_reconfigure_stdout_to_utf8(
    stdout_encoding: str | None,
    preferred_encoding: str | None,
    utf8_mode: int,
) -> bool:
    if is_utf8_encoding(stdout_encoding):
        return False
    return bool(utf8_mode or is_utf8_encoding(preferred_encoding))


def configure_stdout_encoding() -> None:
    if not hasattr(sys.stdout, "reconfigure"):
        return
    if should_reconfigure_stdout_to_utf8(
        getattr(sys.stdout, "encoding", None),
        locale.getpreferredencoding(False),
        sys.flags.utf8_mode,
    ):
        sys.stdout.reconfigure(encoding="utf-8")
