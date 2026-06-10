"""Main entry point for the Blind-to-X pipeline."""

import asyncio
import sys

from pipeline.stdout_encoding import configure_stdout_encoding

configure_stdout_encoding()

from config import load_env, setup_logging
from pipeline.cli import run_main

if __name__ == "__main__":
    load_env()
    setup_logging()

    # Windows 특유의 asyncio 파이프 종료 타이밍 버그 우회
    if sys.platform == "win32":
        try:
            from asyncio.proactor_events import _ProactorBasePipeTransport

            original_del = _ProactorBasePipeTransport.__del__

            def silenced_del(self, *args, **kwargs):
                try:
                    original_del(self, *args, **kwargs)
                except ValueError as e:
                    if "closed pipe" not in str(e):
                        raise

            _ProactorBasePipeTransport.__del__ = silenced_del
        except ImportError:
            pass

        try:
            from asyncio.base_subprocess import BaseSubprocessTransport

            original_subprocess_del = BaseSubprocessTransport.__del__

            def silenced_subprocess_del(self, *args, **kwargs):
                try:
                    original_subprocess_del(self, *args, **kwargs)
                except ValueError as e:
                    if "closed pipe" not in str(e):
                        raise

            BaseSubprocessTransport.__del__ = silenced_subprocess_del
        except ImportError:
            pass

    asyncio.run(run_main())
