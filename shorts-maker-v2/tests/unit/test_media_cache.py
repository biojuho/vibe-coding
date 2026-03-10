from __future__ import annotations

from pathlib import Path

from shorts_maker_v2.utils.media_cache import MediaCache


def test_cache_put_and_get(tmp_path: Path) -> None:
    """put한 이미지를 get으로 캐시 히트."""
    cache = MediaCache(cache_dir=tmp_path / "cache", enabled=True)
    prompt = "A beautiful sunset over mountains"

    # 원본 이미지 생성
    src = tmp_path / "original.png"
    src.write_bytes(b"\x89PNG" + b"\x00" * 100)

    # 캐시에 저장
    cache.put(prompt, src)

    # 캐시에서 조회 (dest 없이)
    result = cache.get(prompt)
    assert result is not None
    assert result.exists()


def test_cache_get_with_dest(tmp_path: Path) -> None:
    """get 시 dest_path로 복사."""
    cache = MediaCache(cache_dir=tmp_path / "cache", enabled=True)
    prompt = "A cat sitting on a chair"

    src = tmp_path / "cat.png"
    src.write_bytes(b"\x89PNG" + b"\x00" * 50)
    cache.put(prompt, src)

    dest = tmp_path / "output" / "scene_01.png"
    result = cache.get(prompt, dest_path=dest)
    assert result is not None
    assert result == dest
    assert dest.exists()


def test_cache_miss(tmp_path: Path) -> None:
    """캐시에 없는 프롬프트는 None 반환."""
    cache = MediaCache(cache_dir=tmp_path / "cache", enabled=True)
    result = cache.get("unknown prompt that was never cached")
    assert result is None


def test_cache_disabled(tmp_path: Path) -> None:
    """enabled=False이면 항상 None 반환."""
    cache = MediaCache(cache_dir=tmp_path / "cache", enabled=False)
    prompt = "test prompt"

    src = tmp_path / "img.png"
    src.write_bytes(b"\x89PNG" + b"\x00" * 50)

    cache.put(prompt, src)
    result = cache.get(prompt)
    assert result is None


def test_cache_stats(tmp_path: Path) -> None:
    """stats()가 hits, misses, total_files를 정확히 추적."""
    cache = MediaCache(cache_dir=tmp_path / "cache", enabled=True)

    src = tmp_path / "img.png"
    src.write_bytes(b"\x89PNG" + b"\x00" * 50)

    cache.put("prompt_a", src)
    cache.get("prompt_a")  # hit
    cache.get("prompt_b")  # miss

    stats = cache.stats()
    assert stats["hits"] == 1
    assert stats["misses"] == 1
    assert stats["total_files"] == 1


def test_cache_duplicate_put(tmp_path: Path) -> None:
    """동일 프롬프트 중복 put 시 덮어쓰지 않음."""
    cache = MediaCache(cache_dir=tmp_path / "cache", enabled=True)
    prompt = "same prompt"

    src1 = tmp_path / "img1.png"
    src1.write_bytes(b"\x89PNG" + b"\x00" * 50)
    cache.put(prompt, src1)

    src2 = tmp_path / "img2.png"
    src2.write_bytes(b"\x89PNG" + b"\x00" * 100)
    cache.put(prompt, src2)

    stats = cache.stats()
    assert stats["total_files"] == 1  # 중복 저장 방지
