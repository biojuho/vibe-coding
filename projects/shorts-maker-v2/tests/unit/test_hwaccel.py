"""Unit tests for hwaccel utilities."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from shorts_maker_v2.utils.hwaccel import (
    _CPU_FALLBACK,
    _HW_ENCODERS,
    _encoder_available,
    _test_encode,
    detect_gpu_info,
    detect_hw_encoder,
    get_hw_decode_params,
)


def _clear_cache() -> None:
    detect_hw_encoder.cache_clear()
    detect_gpu_info.cache_clear()


def test_cpu_fallback_on_none() -> None:
    _clear_cache()
    codec, params = detect_hw_encoder("none")
    assert codec == "libx264"
    assert "-pix_fmt" in params


def test_hw_encoders_defined() -> None:
    assert len(_HW_ENCODERS) >= 3


def test_cpu_fallback_tuple() -> None:
    codec, params = _CPU_FALLBACK
    assert isinstance(codec, str)
    assert isinstance(params, list)


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=False)
@patch("shorts_maker_v2.utils.hwaccel._encoder_available", return_value=True)
def test_auto_fallback_when_test_fails(mock_avail: MagicMock, mock_test: MagicMock) -> None:
    _clear_cache()
    codec, _ = detect_hw_encoder("auto")
    assert codec == "libx264"


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
@patch("shorts_maker_v2.utils.hwaccel._encoder_available", return_value=True)
def test_auto_picks_first_available(mock_avail: MagicMock, mock_test: MagicMock) -> None:
    _clear_cache()
    codec, _ = detect_hw_encoder("auto")
    assert codec == _HW_ENCODERS[0][0]


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
def test_forced_nvenc(mock_test: MagicMock) -> None:
    _clear_cache()
    codec, params = detect_hw_encoder("nvenc")
    assert codec == "h264_nvenc"
    assert "-preset" in params or "-rc" in params


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=False)
def test_forced_but_failed(mock_test: MagicMock) -> None:
    _clear_cache()
    codec, _ = detect_hw_encoder("qsv")
    assert codec == "libx264"


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
@patch("shorts_maker_v2.utils.hwaccel._encoder_available", return_value=False)
def test_auto_fallback_when_not_available(mock_avail: MagicMock, mock_test: MagicMock) -> None:
    _clear_cache()
    codec, _ = detect_hw_encoder("auto")
    assert codec == "libx264"


def test_encoder_params_are_lists() -> None:
    for codec, params in _HW_ENCODERS:
        assert isinstance(codec, str)
        assert isinstance(params, list)
        assert len(params) >= 2


def test_detect_cache_same_result() -> None:
    _clear_cache()
    r1 = detect_hw_encoder("none")
    r2 = detect_hw_encoder("none")
    assert r1 == r2


@patch("shorts_maker_v2.utils.hwaccel._test_encode", return_value=True)
def test_forced_amf(mock_test: MagicMock) -> None:
    _clear_cache()
    codec, params = detect_hw_encoder("amf")
    assert codec == "h264_amf"
    assert isinstance(params, list)


@patch("shorts_maker_v2.utils.hwaccel.subprocess.run")
def test_encoder_available_reads_ffmpeg_output(mock_run: MagicMock) -> None:
    mock_run.return_value.stdout = b" h264_nvenc "

    assert _encoder_available("h264_nvenc") is True


@patch("shorts_maker_v2.utils.hwaccel.subprocess.run", side_effect=RuntimeError("boom"))
def test_encoder_available_returns_false_on_error(mock_run: MagicMock) -> None:
    assert _encoder_available("h264_nvenc") is False


@patch("shorts_maker_v2.utils.hwaccel.subprocess.run")
def test_test_encode_returns_true_when_output_file_exists(mock_run: MagicMock) -> None:
    def _run_side_effect(cmd, capture_output=True, timeout=15):
        from pathlib import Path

        Path(cmd[-1]).write_bytes(b"ok")
        process = MagicMock()
        process.returncode = 0
        return process

    mock_run.side_effect = _run_side_effect

    assert _test_encode("h264_nvenc") is True


@patch("shorts_maker_v2.utils.hwaccel.subprocess.run")
def test_test_encode_returns_false_when_encoder_fails(mock_run: MagicMock) -> None:
    mock_run.return_value.returncode = 1

    assert _test_encode("h264_nvenc") is False


def test_get_hw_decode_params_none_returns_empty() -> None:
    assert get_hw_decode_params("none") == []


@patch("shorts_maker_v2.utils.hwaccel.detect_hw_encoder", return_value=("h264_nvenc", []))
def test_get_hw_decode_params_maps_known_encoder(mock_detect: MagicMock) -> None:
    assert get_hw_decode_params("auto") == ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]


@patch("shorts_maker_v2.utils.hwaccel.get_hw_decode_params", return_value=["-hwaccel", "cuda"])
@patch("shorts_maker_v2.utils.hwaccel.detect_hw_encoder", return_value=("h264_nvenc", []))
@patch("shorts_maker_v2.utils.hwaccel.subprocess.run")
def test_detect_gpu_info_reads_gpu_and_decoder_support(
    mock_run: MagicMock,
    mock_detect: MagicMock,
    mock_decode: MagicMock,
) -> None:
    _clear_cache()
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = b"NVIDIA RTX 4090\n"

    info = detect_gpu_info()

    assert info["gpu_name"] == "NVIDIA RTX 4090"
    assert info["encoder"] == "h264_nvenc"
    assert info["decoder_support"] == "yes"


@patch("shorts_maker_v2.utils.hwaccel.get_hw_decode_params", return_value=[])
@patch("shorts_maker_v2.utils.hwaccel.detect_hw_encoder", return_value=("libx264", []))
@patch("shorts_maker_v2.utils.hwaccel.subprocess.run", side_effect=RuntimeError("missing nvidia-smi"))
def test_detect_gpu_info_handles_missing_gpu_tools(
    mock_run: MagicMock,
    mock_detect: MagicMock,
    mock_decode: MagicMock,
) -> None:
    _clear_cache()

    info = detect_gpu_info()

    assert info["gpu_name"] == "Unknown"
    assert info["encoder"] == "libx264"
    assert info["decoder_support"] == "no"
