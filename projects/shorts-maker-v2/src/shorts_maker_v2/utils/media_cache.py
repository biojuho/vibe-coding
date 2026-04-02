"""프롬프트 해시 기반 이미지 캐싱 시스템.

동일 visual prompt로 생성된 이미지를 캐시하여 재생성을 방지합니다.
캐시 키는 프롬프트 텍스트의 SHA-256 해시이며, 파일명에 확장자를 보존합니다.
"""

from __future__ import annotations

import contextlib
import hashlib
import logging
import shutil
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)


class MediaCache:
    """프롬프트 → 이미지 파일 캐시.

    - get(prompt) → 캐시 히트 시 Path 반환, 미스 시 None
    - put(prompt, file_path) → 파일을 캐시에 복사
    - stats() → dict[str, int] (hits, misses, total_files)
    """

    def __init__(
        self,
        cache_dir: str | Path,
        *,
        enabled: bool = True,
        max_size_mb: int = 500,
        ttl_days: int = 30,
    ):
        self.cache_dir = Path(cache_dir).resolve()
        self.enabled = enabled
        self.max_size_mb = max_size_mb
        self.ttl_days = ttl_days
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()

        if self.enabled:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            # 백그라운드 스레드에서 캐시 정리 수행 (초기화 지연 방지)
            cleanup_thread = threading.Thread(target=self._run_cleanup_cycle, daemon=True)
            cleanup_thread.start()

    def _run_cleanup_cycle(self) -> None:
        """백그라운드에서 TTL 및 최대 용량 제한을 적용합니다.

        No lock needed — filesystem ops don't touch _hits/_misses.
        """
        self._cleanup_expired()
        self._enforce_max_size()

    def _cleanup_expired(self) -> None:
        """TTL이 지난 파일 삭재."""
        if self.ttl_days <= 0 or not self.cache_dir.exists():
            return

        now = time.time()
        ttl_sec = self.ttl_days * 86400

        for f in self.cache_dir.iterdir():
            if f.is_file():
                try:
                    mtime = f.stat().st_mtime
                    if now - mtime > ttl_sec:
                        f.unlink(missing_ok=True)
                except Exception as exc:
                    logger.debug("[MediaCache] TTL 정리 중 파일 접근 실패 (%s): %s", f.name, exc)

    def _enforce_max_size(self) -> None:
        """max_size_mb 초과 시 가장 오래된 파일부터 삭제 (LRU 근사)."""
        if self.max_size_mb <= 0 or not self.cache_dir.exists():
            return

        files = []
        total_size = 0
        for f in self.cache_dir.iterdir():
            if f.is_file():
                try:
                    stat = f.stat()
                    files.append((f, stat.st_mtime, stat.st_size))
                    total_size += stat.st_size
                except Exception as exc:
                    logger.debug("[MediaCache] 파일 stat 실패 (%s): %s", f.name, exc)

        max_bytes = self.max_size_mb * 1024 * 1024
        if total_size <= max_bytes:
            return

        # 오래된 순 정렬
        files.sort(key=lambda x: x[1])

        for f, _mtime, size in files:
            try:
                f.unlink(missing_ok=True)
                total_size -= size
                if total_size <= max_bytes:
                    break
            except Exception as exc:
                logger.debug("[MediaCache] 캐시 파일 삭제 실패 (%s): %s", f.name, exc)

    @staticmethod
    def _hash_prompt(prompt: str) -> str:
        """프롬프트 텍스트의 SHA-256 해시 (16진수 앞 16자리)."""
        return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]

    def _find_cached(self, prompt_hash: str) -> Path | None:
        """캐시 디렉토리에서 해시 이름으로 시작하는 파일 검색."""
        for f in self.cache_dir.iterdir():
            if f.name.startswith(prompt_hash) and f.is_file():
                return f
        return None

    def get(self, prompt: str, dest_path: Path | None = None) -> Path | None:
        """캐시에서 프롬프트에 대한 이미지를 조회.

        Args:
            prompt: 비주얼 프롬프트 텍스트
            dest_path: 히트 시 복사할 대상 경로 (None이면 캐시 원본 경로 반환)

        Returns:
            캐시 히트 시 Path (dest_path 또는 캐시 원본), 미스 시 None
        """
        if not self.enabled:
            return None

        prompt_hash = self._hash_prompt(prompt)
        cached = self._find_cached(prompt_hash)

        if cached is None:
            with self._lock:
                self._misses += 1
            return None

        with self._lock:
            self._hits += 1

        if dest_path is not None:
            dest_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(cached), str(dest_path))
            return dest_path

        # hit 시 mtime 업데이트 (LRU 갱신)
        with contextlib.suppress(Exception):
            cached.touch(exist_ok=True)

        return cached

    def put(self, prompt: str, file_path: Path) -> Path:
        """이미지를 캐시에 저장.

        Args:
            prompt: 비주얼 프롬프트 텍스트
            file_path: 캐시에 저장할 이미지 파일 경로

        Returns:
            캐시된 파일 경로
        """
        if not self.enabled:
            return file_path

        prompt_hash = self._hash_prompt(prompt)
        ext = file_path.suffix or ".png"
        cache_path = self.cache_dir / f"{prompt_hash}{ext}"

        if not cache_path.exists():
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(file_path), str(cache_path))

        return cache_path

    def stats(self) -> dict[str, int]:
        """캐시 통계 반환."""
        # lock 밖에서 I/O 수행 (get/put 블로킹 방지)
        total_files = sum(1 for f in self.cache_dir.iterdir() if f.is_file()) if self.cache_dir.exists() else 0
        with self._lock:
            return {
                "hits": self._hits,
                "misses": self._misses,
                "total_files": total_files,
            }
