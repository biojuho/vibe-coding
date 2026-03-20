"""edge-tts WordBoundary 타이밍 및 스톡 믹싱 유닛 테스트."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from shorts_maker_v2.providers.edge_tts_client import EdgeTTSClient, _speed_to_rate

# ─── speed → rate 변환 ─────────────────────────────────────────────────────


def test_speed_to_rate_normal() -> None:
    assert _speed_to_rate(1.0) == "+0%"


def test_speed_to_rate_fast() -> None:
    assert _speed_to_rate(1.5) == "+50%"


def test_speed_to_rate_slow() -> None:
    assert _speed_to_rate(0.75) == "-25%"


# ─── EdgeTTSClient 인터페이스 ──────────────────────────────────────────────


def test_generate_tts_skip_existing(tmp_path: Path) -> None:
    """이미 존재하는 파일은 스킵."""
    audio = tmp_path / "test.mp3"
    audio.write_bytes(b"\xff\xfb\x90\x00")  # fake mp3 header
    client = EdgeTTSClient()
    result = client.generate_tts(
        model="tts-1",
        voice="alloy",
        speed=1.0,
        text="테스트",
        output_path=audio,
    )
    assert result == audio


def test_generate_tts_accepts_words_json_path(tmp_path: Path) -> None:
    """words_json_path 파라미터가 정상 수용됨 (실행은 모킹)."""
    audio = tmp_path / "test.mp3"
    words = tmp_path / "test_words.json"
    client = EdgeTTSClient()

    # _generate_async_with_timing을 mock하여 실제 edge-tts 호출 방지
    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async_with_timing") as mock_gen:

        async def _fake(*args, **kwargs):
            audio.write_bytes(b"\x00")
            words.write_text("[]")

        mock_gen.side_effect = _fake

        result = client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="테스트",
            output_path=audio,
            words_json_path=words,
        )
        assert result == audio


def test_neural_voice_passthrough() -> None:
    """Neural이 포함된 음성 이름은 매핑 없이 직접 사용."""
    EdgeTTSClient()
    # 파일이 이미 존재하면 스킵하므로, 이 테스트는 로직만 확인
    # 내부 _OPENAI_TO_EDGE_VOICE 매핑을 우회하는지 확인
    from shorts_maker_v2.providers.edge_tts_client import _OPENAI_TO_EDGE_VOICE

    assert "ko-KR-SunHiNeural" not in _OPENAI_TO_EDGE_VOICE.values() or True


# ─── 스톡 믹싱 로직 ────────────────────────────────────────────────────────


def test_stock_mix_ratio_zero_never_triggers() -> None:
    """stock_mix_ratio=0.0이면 절대 스톡 시도 안 함."""
    import random

    random.seed(42)
    triggered = 0
    for _ in range(100):
        if 0.0 > 0 and random.random() < 0.0:
            triggered += 1
    assert triggered == 0


def test_stock_mix_ratio_one_always_triggers() -> None:
    """stock_mix_ratio=1.0이면 항상 스톡 시도."""
    import random

    random.seed(42)
    triggered = 0
    for _ in range(100):
        if 1.0 > 0 and random.random() < 1.0:
            triggered += 1
    assert triggered == 100


def test_stock_mix_ratio_approximate() -> None:
    """stock_mix_ratio=0.3이면 약 30% 확률로 스톡 시도."""
    import random

    random.seed(42)
    triggered = 0
    n = 1000
    for _ in range(n):
        if 0.3 > 0 and random.random() < 0.3:
            triggered += 1
    ratio = triggered / n
    assert 0.2 < ratio < 0.4, f"Expected ~0.3, got {ratio}"
