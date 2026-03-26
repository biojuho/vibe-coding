"""hwaccel 모듈 유닛 테스트."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from shorts_maker_v2.utils.hwaccel import (
    _CPU_FALLBACK,
    _HW_ENCODERS,
    detect_hw_encoder,
)


def _clear_cache():
    """lru_cache 초기화."""
    detect_hw_encoder.cache_clear()


def test_cpu_fallback_on_none() -> None:
    """preference='none'이면 libx264 반환."""
    _clear_cache()
    codec, params = detect_hw_encoder("none")
    assert codec == "libx264"
    assert "-pix_fmt" in params


def test_hw_encoders_defined() -> None:
    """최소 3개 HW 인코더 정의."""
    assert len(_HW_ENCODERS) >= 3


def test_cpu_fallback_tuple() -> None:
    """CPU 폴백이 (str, list) 형태."""
    codec, params = _CPU_FALLBACK
    assert isinstance(codec, str)
    assert isinstance(params, list)


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=False)
@patch("shorts_maker_v2.utils.hwaccel._encoder_available", return_value=True)
def test_auto_fallback_when_test_fails(mock_avail: MagicMock, mock_test: MagicMock) -> None:
    """인코더 존재하지만 테스트 실패 시 libx264 폴백."""
    _clear_cache()
    codec, _ = detect_hw_encoder("auto")
    assert codec == "libx264"


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
@patch("shorts_maker_v2.utils.hwaccel._encoder_available", return_value=True)
def test_auto_picks_first_available(mock_avail: MagicMock, mock_test: MagicMock) -> None:
    """자동 감지 시 첫 번째 가용 인코더 선택."""
    _clear_cache()
    codec, _ = detect_hw_encoder("auto")
    assert codec == _HW_ENCODERS[0][0]  # h264_nvenc


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
def test_forced_nvenc(mock_test: MagicMock) -> None:
    """강제 nvenc 지정 시 h264_nvenc 반환."""
    _clear_cache()
    codec, params = detect_hw_encoder("nvenc")
    assert codec == "h264_nvenc"
    assert "-preset" in params or "-rc" in params


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=False)
def test_forced_but_failed(mock_test: MagicMock) -> None:
    """강제 인코더가 실패하면 libx264 폴백."""
    _clear_cache()
    codec, _ = detect_hw_encoder("qsv")
    assert codec == "libx264"


# ─── Phase 3-E: additional encoder stability tests ────────────────────────


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
@patch("shorts_maker_v2.utils.hwaccel._encoder_available", return_value=False)
def test_auto_fallback_when_not_available(mock_avail: MagicMock, mock_test: MagicMock) -> None:
    """인코더가 ffmpeg에 없으면 libx264 폴백."""
    _clear_cache()
    codec, _ = detect_hw_encoder("auto")
    assert codec == "libx264"


def test_encoder_params_are_lists() -> None:
    """모든 HW 인코더 파라미터가 list 형태."""
    for codec, params in _HW_ENCODERS:
        assert isinstance(codec, str), f"codec should be str: {codec}"
        assert isinstance(params, list), f"params should be list for {codec}"
        assert len(params) >= 2, f"params too short for {codec}"


def test_detect_cache_same_result() -> None:
    """같은 preference → 같은 결과 (lru_cache)."""
    _clear_cache()
    r1 = detect_hw_encoder("none")
    r2 = detect_hw_encoder("none")
    assert r1 == r2


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
def test_forced_amf(mock_test: MagicMock) -> None:
    """강제 amf 지정 시 h264_amf 반환."""
    _clear_cache()
    codec, params = detect_hw_encoder("amf")
    assert codec == "h264_amf"
    assert isinstance(params, list)
