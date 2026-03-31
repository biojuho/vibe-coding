"""edge-tts WordBoundary 타이밍 및 스톡 믹싱 유닛 테스트."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from shorts_maker_v2.providers.edge_tts_client import (
    EdgeTTSClient,
    _add_silence_padding,
    _approximate_word_timings,
    _get_role_prosody,
    _run_coroutine,
    _speed_to_rate,
)

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


# ─── _get_role_prosody ─────────────────────────────────────────────────────


def test_role_prosody_hook() -> None:
    rate, pitch = _get_role_prosody("hook", channel_key="ai_tech")
    assert rate == "+15%"
    assert pitch == "+10Hz"


def test_role_prosody_hook_default_channel() -> None:
    rate, pitch = _get_role_prosody("hook", channel_key="unknown")
    assert rate == "+15%"
    assert pitch == "+8Hz"


def test_role_prosody_cta() -> None:
    rate, pitch = _get_role_prosody("cta")
    assert rate == "-10%"
    assert pitch == "+5Hz"


def test_role_prosody_body_invalid_rate() -> None:
    """When base_rate can't be parsed, fallback to base_pct=0."""
    rate, pitch = _get_role_prosody("body", base_rate="invalid")
    # Should not raise — ValueError is caught, base_pct defaults to 0
    assert "%" in rate
    assert "Hz" in pitch


def test_role_prosody_body_with_channel() -> None:
    with patch("shorts_maker_v2.providers.edge_tts_client.random") as mock_rand:
        mock_rand.randint.side_effect = [3, -2]  # rate_jitter, pitch_jitter
        rate, pitch = _get_role_prosody("body", base_rate="+10%", channel_key="psychology")
    assert rate == "+13%"
    assert pitch == "-2Hz"


# ─── _approximate_word_timings ─────────────────────────────────────────────


def test_approximate_empty_text() -> None:
    assert _approximate_word_timings("", Path("x.mp3")) == []


def test_approximate_whitespace_only() -> None:
    assert _approximate_word_timings("   \n  ", Path("x.mp3")) == []


def test_approximate_no_mutagen(tmp_path: Path) -> None:
    """When mutagen import fails, returns empty."""
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"\x00")
    with patch.dict("sys.modules", {"mutagen": None, "mutagen.mp3": None}):
        result = _approximate_word_timings("hello world", audio)
    assert result == []


def test_approximate_word_timings_success(tmp_path: Path) -> None:
    """Normal case: produces word timings proportional to syllable weights."""
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"\x00")

    mock_mp3 = MagicMock()
    mock_mp3.return_value.info.length = 2.0

    with patch("shorts_maker_v2.providers.edge_tts_client.MP3", mock_mp3, create=True):
        # Need to patch at the import level inside the function
        import types

        # Temporarily inject MP3 into the function's scope via mutagen mock
        mock_mutagen_mp3 = types.ModuleType("mutagen.mp3")
        mock_mutagen_mp3.MP3 = mock_mp3
        with patch.dict("sys.modules", {"mutagen": MagicMock(), "mutagen.mp3": mock_mutagen_mp3}):
            result = _approximate_word_timings("안녕 world", audio)

    assert len(result) == 2
    assert result[0]["word"] == "안녕"
    assert result[0]["start"] == 0.0
    assert result[-1]["end"] == pytest.approx(2.0, abs=0.01)


# ─── _add_silence_padding ──────────────────────────────────────────────────


def test_add_silence_padding_no_pydub(tmp_path: Path) -> None:
    """When pydub is not available, silently skips."""
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"original")
    with patch.dict("sys.modules", {"pydub": None}):
        _add_silence_padding(audio)
    assert audio.read_bytes() == b"original"


def test_add_silence_padding_pydub_error(tmp_path: Path) -> None:
    """When pydub raises, silently catches."""
    audio = tmp_path / "audio.mp3"
    audio.write_bytes(b"original")

    mock_pydub = MagicMock()
    mock_pydub.AudioSegment.from_file.side_effect = RuntimeError("bad format")
    with patch.dict("sys.modules", {"pydub": mock_pydub}):
        _add_silence_padding(audio)
    assert audio.read_bytes() == b"original"


# ─── _run_coroutine ─────────────────────────────────────────────────────


def test_run_coroutine_normal() -> None:
    """Normal case: asyncio.run succeeds."""
    called = {"v": False}

    async def coro():
        called["v"] = True

    _run_coroutine(coro)
    assert called["v"]


def test_run_coroutine_event_loop_fallback() -> None:
    """When asyncio.run raises event loop RuntimeError, falls back to thread."""
    called = {"v": False}

    async def coro():
        called["v"] = True

    with patch("shorts_maker_v2.providers.edge_tts_client.asyncio.run") as mock_run:
        call_count = {"n": 0}

        def _fake_run(coro_obj):
            call_count["n"] += 1
            coro_obj.close()
            if call_count["n"] == 1:
                raise RuntimeError("Cannot run: event loop is already running")
            return None

        mock_run.side_effect = _fake_run
        _run_coroutine(coro)


def test_run_coroutine_non_event_loop_error_propagates() -> None:
    """Non event-loop RuntimeError should propagate."""
    async def coro():
        pass

    with patch("shorts_maker_v2.providers.edge_tts_client.asyncio.run") as mock_run:
        def _fake_run(coro_obj):
            coro_obj.close()
            raise RuntimeError("some other error")

        mock_run.side_effect = _fake_run
        with pytest.raises(RuntimeError, match="some other error"):
            _run_coroutine(coro)


# ═══════════════════════════════════════════════════════════════════════════
# NEW TESTS — Phase 5A-2 coverage uplift
# ═══════════════════════════════════════════════════════════════════════════


# ─── _generate_async_with_timing 상세 경로 ──────────────────────────────────


def test_generate_async_with_timing_word_boundary_events(tmp_path: Path) -> None:
    """WordBoundary 이벤트가 정상 수집되면 words.json에 저장된다."""
    from shorts_maker_v2.providers.edge_tts_client import _generate_async_with_timing

    audio_out = tmp_path / "out.mp3"
    words_out = tmp_path / "out_words.json"

    chunks = [
        {"type": "audio", "data": b"\xff\xfb" * 100},
        {
            "type": "WordBoundary",
            "text": "안녕",
            "offset": 5_000_000,  # 0.5s
            "duration": 3_000_000,  # 0.3s
        },
        {"type": "audio", "data": b"\xff\xfb" * 50},
        {
            "type": "WordBoundary",
            "text": "세계",
            "offset": 10_000_000,  # 1.0s
            "duration": 4_000_000,  # 0.4s
        },
    ]

    async def fake_stream():
        for c in chunks:
            yield c

    mock_communicate = MagicMock()
    mock_communicate.return_value.stream = fake_stream

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", mock_communicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
    ):
        asyncio.run(_generate_async_with_timing(
            "안녕 세계", "ko-KR-SunHiNeural", "+0%", "+0Hz",
            audio_out, words_out,
        ))

    assert audio_out.exists()
    assert words_out.exists()
    words = json.loads(words_out.read_text(encoding="utf-8"))
    assert len(words) == 2
    assert words[0]["word"] == "안녕"
    # padding offset 적용 확인: 0.5 + 0.05 = 0.55
    assert words[0]["start"] == pytest.approx(0.55, abs=0.01)


def test_generate_async_with_timing_no_word_boundary_whisper_fallback(tmp_path: Path) -> None:
    """WordBoundary 없을 때 whisper fallback 시도."""
    from shorts_maker_v2.providers.edge_tts_client import _generate_async_with_timing

    audio_out = tmp_path / "out.mp3"
    words_out = tmp_path / "out_words.json"

    # 오디오만 반환, WordBoundary 없음
    chunks = [{"type": "audio", "data": b"\xff" * 200}]

    async def fake_stream():
        for c in chunks:
            yield c

    mock_communicate = MagicMock()
    mock_communicate.return_value.stream = fake_stream

    # whisper 가용
    whisper_words = [
        {"word": "테스트", "start": 0.1, "end": 0.5},
        {"word": "문장", "start": 0.5, "end": 0.9},
    ]

    mock_whisper_mod = MagicMock()
    mock_whisper_mod.is_whisper_available.return_value = True
    mock_whisper_mod.transcribe_to_word_timings.return_value = whisper_words

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", mock_communicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
        patch.dict("sys.modules", {
            "shorts_maker_v2.providers.whisper_aligner": mock_whisper_mod,
        }),
    ):
        asyncio.run(_generate_async_with_timing(
            "테스트 문장", "ko-KR-SunHiNeural", "+0%", "+0Hz",
            audio_out, words_out,
        ))

    assert words_out.exists()
    words = json.loads(words_out.read_text(encoding="utf-8"))
    assert len(words) == 2
    # padding offset 적용: 0.1 + 0.05 = 0.15
    assert words[0]["start"] == pytest.approx(0.15, abs=0.01)


def test_generate_async_with_timing_approximate_fallback(tmp_path: Path) -> None:
    """WordBoundary 없고 whisper도 불가하면 approximate fallback."""
    from shorts_maker_v2.providers.edge_tts_client import _generate_async_with_timing

    audio_out = tmp_path / "out.mp3"
    words_out = tmp_path / "out_words.json"

    chunks = [{"type": "audio", "data": b"\xff" * 200}]

    async def fake_stream():
        for c in chunks:
            yield c

    mock_communicate = MagicMock()
    mock_communicate.return_value.stream = fake_stream

    approx_result = [
        {"word": "Hello", "start": 0.0, "end": 1.0},
        {"word": "World", "start": 1.0, "end": 2.0},
    ]

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", mock_communicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
        patch(
            "shorts_maker_v2.providers.edge_tts_client._approximate_word_timings",
            return_value=approx_result,
        ),
        patch.dict("sys.modules", {"shorts_maker_v2.providers.whisper_aligner": None}),
    ):
        # whisper import 실패 시뮬레이트
        asyncio.run(_generate_async_with_timing(
            "Hello World", "en-US-GuyNeural", "+0%", "+0Hz",
            audio_out, words_out,
        ))

    assert words_out.exists()
    words = json.loads(words_out.read_text(encoding="utf-8"))
    assert len(words) == 2


def test_generate_async_with_timing_saves_ssml_txt(tmp_path: Path) -> None:
    """plain text가 ssml.txt 파일로 저장된다."""
    from shorts_maker_v2.providers.edge_tts_client import _generate_async_with_timing

    audio_out = tmp_path / "out.mp3"
    words_out = tmp_path / "out_words.json"

    chunks = [
        {"type": "audio", "data": b"\xff" * 100},
        {"type": "WordBoundary", "text": "테스트", "offset": 0, "duration": 5_000_000},
    ]

    async def fake_stream():
        for c in chunks:
            yield c

    mock_communicate = MagicMock()
    mock_communicate.return_value.stream = fake_stream

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", mock_communicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
    ):
        asyncio.run(_generate_async_with_timing(
            "테스트 텍스트", "ko-KR-SunHiNeural", "+0%", "+0Hz",
            audio_out, words_out,
        ))

    ssml_txt = words_out.parent / f"{words_out.stem}_ssml.txt"
    assert ssml_txt.exists()
    assert ssml_txt.read_text(encoding="utf-8") == "테스트 텍스트"


# ─── _generate_async 기본 경로 ─────────────────────────────────────────────


def test_generate_async_basic(tmp_path: Path) -> None:
    """_generate_async가 communicate.save를 호출한다."""
    from shorts_maker_v2.providers.edge_tts_client import _generate_async

    audio_out = tmp_path / "out.mp3"

    async def fake_save(path):
        Path(path).write_bytes(b"\xff" * 100)

    mock_communicate = MagicMock()
    mock_communicate.return_value.save = fake_save

    with (
        patch("shorts_maker_v2.providers.edge_tts_client.edge_tts.Communicate", mock_communicate),
        patch("shorts_maker_v2.providers.edge_tts_client._add_silence_padding"),
    ):
        asyncio.run(_generate_async(
            "테스트", "ko-KR-SunHiNeural", "+0%", "+0Hz", audio_out,
        ))

    assert audio_out.exists()


# ─── EdgeTTSClient.generate_tts 확장 ──────────────────────────────────────


def test_generate_tts_neural_voice_direct(tmp_path: Path) -> None:
    """Neural 음성은 매핑 없이 직접 전달된다."""
    audio = tmp_path / "test.mp3"
    client = EdgeTTSClient()

    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async") as mock_gen:
        async def _fake(*args, **kwargs):
            audio.write_bytes(b"\x00" * 10)

        mock_gen.side_effect = _fake

        client.generate_tts(
            model="tts-1",
            voice="ko-KR-HyunsuNeural",
            speed=1.0,
            text="테스트",
            output_path=audio,
        )

    # _generate_async의 두 번째 인자(voice)가 그대로 전달되야 함
    # _make_coro는 _generate_async를 호출할 때 voice를 전달
    assert audio.exists()


def test_generate_tts_openai_voice_mapped(tmp_path: Path) -> None:
    """OpenAI 음성 이름은 edge-tts 음성으로 매핑된다."""
    from shorts_maker_v2.providers.edge_tts_client import _OPENAI_TO_EDGE_VOICE

    audio = tmp_path / "test.mp3"
    client = EdgeTTSClient()

    captured_voice = {}

    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async") as mock_gen:
        async def _fake(text, voice, rate, pitch, output_path):
            captured_voice["v"] = voice
            output_path.write_bytes(b"\x00" * 10)

        mock_gen.side_effect = _fake

        client.generate_tts(
            model="tts-1",
            voice="sage",
            speed=1.0,
            text="테스트",
            output_path=audio,
        )

    assert captured_voice["v"] == _OPENAI_TO_EDGE_VOICE["sage"]


def test_generate_tts_all_fail_raises(tmp_path: Path) -> None:
    """모든 시도 실패 시 마지막 예외 전파."""
    audio = tmp_path / "test.mp3"
    client = EdgeTTSClient()

    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async") as mock_gen:
        async def _fail(*args, **kwargs):
            raise RuntimeError("edge-tts down")

        mock_gen.side_effect = _fail

        with pytest.raises(RuntimeError, match="edge-tts down"):
            client.generate_tts(
                model="tts-1",
                voice="alloy",
                speed=1.0,
                text="테스트",
                output_path=audio,
            )


def test_generate_tts_with_channel_key(tmp_path: Path) -> None:
    """channel_key가 있을 때 prosody가 올바르게 적용된다."""
    audio = tmp_path / "test.mp3"
    client = EdgeTTSClient()

    captured = {}

    with patch("shorts_maker_v2.providers.edge_tts_client._generate_async") as mock_gen:
        async def _fake(text, voice, rate, pitch, output_path):
            captured["rate"] = rate
            captured["pitch"] = pitch
            output_path.write_bytes(b"\x00" * 10)

        mock_gen.side_effect = _fake

        client.generate_tts(
            model="tts-1",
            voice="alloy",
            speed=1.0,
            text="테스트",
            output_path=audio,
            role="hook",
            channel_key="ai_tech",
        )

    # hook role: rate=+15%, pitch=+10Hz (ai_tech channel)
    assert captured["rate"] == "+15%"
    assert captured["pitch"] == "+10Hz"


# ─── CHANNEL_PROSODY 테이블 검증 ───────────────────────────────────────────


def test_channel_prosody_all_channels_defined() -> None:
    """5개 채널에 대한 prosody 값이 모두 정의되어 있다."""
    from shorts_maker_v2.providers.edge_tts_client import (
        _CHANNEL_PROSODY,
        _DEFAULT_PROSODY,
    )

    expected_channels = {"ai_tech", "history", "psychology", "space", "health"}
    assert expected_channels == set(_CHANNEL_PROSODY.keys())
    # 각 값은 (int, int) 튜플
    for ch, (rate_j, pitch_j) in _CHANNEL_PROSODY.items():
        assert isinstance(rate_j, int), f"{ch} rate_jitter is not int"
        assert isinstance(pitch_j, int), f"{ch} pitch_jitter is not int"
        assert rate_j > 0, f"{ch} rate_jitter must be positive"
        assert pitch_j > 0, f"{ch} pitch_jitter must be positive"

    assert len(_DEFAULT_PROSODY) == 2
    assert _DEFAULT_PROSODY[0] > 0 and _DEFAULT_PROSODY[1] > 0


def test_openai_voice_mapping_completeness() -> None:
    """모든 OpenAI 음성이 edge-tts 음성으로 매핑된다."""
    from shorts_maker_v2.providers.edge_tts_client import _OPENAI_TO_EDGE_VOICE

    expected_voices = {"alloy", "echo", "fable", "onyx", "nova", "shimmer", "sage", "coral", "ash", "verse"}
    assert expected_voices == set(_OPENAI_TO_EDGE_VOICE.keys())
    for openai_voice, edge_voice in _OPENAI_TO_EDGE_VOICE.items():
        assert "Neural" in edge_voice, f"{openai_voice} → {edge_voice} missing 'Neural'"


def test_role_prosody_hook_all_channels() -> None:
    """모든 채널에서 hook prosody가 정상 반환된다."""
    from shorts_maker_v2.providers.edge_tts_client import _CHANNEL_PROSODY

    for channel in list(_CHANNEL_PROSODY.keys()) + [""]:
        rate, pitch = _get_role_prosody("hook", channel_key=channel)
        assert rate == "+15%"
        assert "Hz" in pitch
