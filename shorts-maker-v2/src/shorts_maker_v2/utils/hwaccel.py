"""FFmpeg 하드웨어 가속 인코더 자동 감지.

NVENC (NVIDIA) → QSV (Intel) → AMF (AMD) → libx264 (CPU) 순서로 감지.
프로세스 라이프타임 동안 결과를 캐싱하여 반복 호출 시 오버헤드 제거.
"""
from __future__ import annotations

import logging
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# 인코더별 최적 파라미터 (codec, ffmpeg_params)
_HW_ENCODERS: list[tuple[str, list[str]]] = [
    # NVIDIA NVENC
    (
        "h264_nvenc",
        ["-preset", "p4", "-rc", "vbr", "-cq", "22", "-pix_fmt", "yuv420p"],
    ),
    # Intel Quick Sync Video
    (
        "h264_qsv",
        ["-preset", "faster", "-global_quality", "22", "-pix_fmt", "nv12"],
    ),
    # AMD AMF
    (
        "h264_amf",
        ["-quality", "balanced", "-rc", "vbr_latency", "-qp_i", "22", "-qp_p", "22", "-pix_fmt", "nv12"],
    ),
]

_CPU_FALLBACK = ("libx264", ["-pix_fmt", "yuv420p"])


def _encoder_available(codec: str) -> bool:
    """ffmpeg -encoders 출력에서 codec 존재 여부 확인."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-encoders"],
            capture_output=True,
            timeout=10,
        )
        return codec in result.stdout.decode(errors="replace")
    except Exception:
        return False


def _test_encode(codec: str) -> bool:
    """1초 테스트 인코딩으로 실제 작동 여부 확인."""
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "test.mp4"
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "color=black:s=64x64:d=1:r=1",
            "-c:v", codec,
            "-frames:v", "1",
            str(out),
        ]
        try:
            result = subprocess.run(
                cmd, capture_output=True, timeout=15,
            )
            return result.returncode == 0 and out.exists()
        except Exception:
            return False


@lru_cache(maxsize=1)
def detect_hw_encoder(preference: str = "auto") -> tuple[str, list[str]]:
    """가용 HW 인코더를 감지하여 (codec, ffmpeg_params) 반환.

    Args:
        preference: "auto" | "nvenc" | "qsv" | "amf" | "none"

    Returns:
        (codec_name, ffmpeg_extra_params) 튜플.
        예: ("h264_nvenc", ["-preset", "p4", "-rc", "vbr", ...])
    """
    if preference == "none":
        logger.info("[HW_ACCEL] forced CPU: libx264")
        return _CPU_FALLBACK

    # 특정 인코더 강제 지정
    if preference in ("nvenc", "qsv", "amf"):
        codec = f"h264_{preference}"
        for enc_codec, enc_params in _HW_ENCODERS:
            if enc_codec == codec:
                if _test_encode(codec):
                    logger.info("[HW_ACCEL] forced: %s", codec)
                    return codec, enc_params
                logger.warning("[HW_ACCEL] forced %s failed, fallback to libx264", codec)
                return _CPU_FALLBACK
        return _CPU_FALLBACK

    # 자동 감지
    for codec, params in _HW_ENCODERS:
        if _encoder_available(codec) and _test_encode(codec):
            logger.info("[HW_ACCEL] detected: %s", codec)
            print(f"[HW_ACCEL] detected: {codec}")
            return codec, params

    logger.info("[HW_ACCEL] no HW encoder found, using libx264")
    print("[HW_ACCEL] no HW encoder found, using libx264 (CPU)")
    return _CPU_FALLBACK


# ── Sprint 3: GPU 디코딩 & 시스템 감지 ────────────────────────────────────────

def get_hw_decode_params(preference: str = "auto") -> list[str]:
    """GPU 디코딩을 위한 ffmpeg input 파라미터 반환.

    Args:
        preference: "auto" | "cuda" | "dxva2" | "none"

    Returns:
        ffmpeg input 옵션 리스트. 예: ["-hwaccel", "cuda"]
    """
    if preference == "none":
        return []

    # 인코더가 감지된 경우 대응하는 디코더 추가
    codec, _ = detect_hw_encoder(preference)
    if codec == "h264_nvenc":
        return ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"]
    elif codec == "h264_qsv":
        return ["-hwaccel", "qsv"]
    elif codec == "h264_amf":
        return ["-hwaccel", "dxva2"]
    return []


@lru_cache(maxsize=1)
def detect_gpu_info() -> dict[str, str]:
    """시스템 GPU 정보 감지 (로깅/벤치마크용).

    Returns:
        {"gpu_name": "...", "encoder": "...", "decoder_support": "yes/no"}
    """
    info: dict[str, str] = {
        "gpu_name": "Unknown",
        "encoder": "libx264 (CPU)",
        "decoder_support": "no",
    }

    # GPU 이름 감지 (NVIDIA)
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True,
            timeout=5,
        )
        if result.returncode == 0:
            gpu_name = result.stdout.decode(errors="replace").strip().split("\n")[0]
            info["gpu_name"] = gpu_name
    except Exception:
        pass

    # 인코더 정보
    codec, _ = detect_hw_encoder("auto")
    info["encoder"] = codec

    # 디코더 지원 여부
    decode_params = get_hw_decode_params("auto")
    info["decoder_support"] = "yes" if decode_params else "no"

    logger.info(
        "[GPU_INFO] GPU=%s | Encoder=%s | HW Decode=%s",
        info["gpu_name"], info["encoder"], info["decoder_support"],
    )
    return info

