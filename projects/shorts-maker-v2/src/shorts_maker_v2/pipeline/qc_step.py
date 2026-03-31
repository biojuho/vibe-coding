"""QCStep — Gate 3 (미디어 QC) + Gate 4 (최종 QC).

렌더 전 미디어 자산 검증(Gate 3)과 렌더 후 최종 품질 검수(Gate 4).
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

from shorts_maker_v2.models import (
    GateVerdict,
    JobManifest,
    QCReport,
    SceneAsset,
    ScenePlan,
    SceneQCResult,
)

logger = logging.getLogger(__name__)


class QCStep:
    """품질 검수 게이트 (Gate 3 + Gate 4)."""

    # ── Gate 3: 미디어 QC ─────────────────────────────────────────────────────

    @staticmethod
    def gate3_media(
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset],
        target_duration: tuple[int, int] = (40, 50),
    ) -> QCReport:
        """Gate 3: 미디어 자산 품질 검증.

        Args:
            scene_plans: 대본 씬 목록
            scene_assets: 생성된 미디어 자산 목록
            target_duration: (min, max) 초

        Returns:
            QCReport with verdict and issues
        """
        checks: dict[str, bool] = {}
        issues: list[str] = []

        # Check 1: 모든 씬에 자산 존재
        plan_ids = {s.scene_id for s in scene_plans}
        asset_ids = {a.scene_id for a in scene_assets}
        missing = plan_ids - asset_ids
        checks["all_scenes_have_assets"] = len(missing) == 0
        if missing:
            issues.append(f"Missing assets for scenes: {sorted(missing)}")

        # Check 2: 파일 존재 + 최소 크기
        for asset in scene_assets:
            # 오디오 파일 확인
            if not os.path.isfile(asset.audio_path):
                checks[f"audio_exists_s{asset.scene_id}"] = False
                issues.append(f"Scene {asset.scene_id}: audio file missing")
            else:
                size = os.path.getsize(asset.audio_path)
                ok = size > 10_000  # 10KB 최소
                checks[f"audio_size_s{asset.scene_id}"] = ok
                if not ok:
                    issues.append(f"Scene {asset.scene_id}: audio too small ({size}B)")

            # 비주얼 파일 확인
            if not os.path.isfile(asset.visual_path):
                checks[f"visual_exists_s{asset.scene_id}"] = False
                issues.append(f"Scene {asset.scene_id}: visual file missing")
            else:
                checks[f"visual_exists_s{asset.scene_id}"] = True

        # Check 3: TTS 총 길이
        total_dur = sum(a.duration_sec for a in scene_assets)
        dur_min, dur_max = target_duration
        in_range = dur_min <= total_dur <= dur_max
        checks["tts_duration_in_range"] = in_range
        if not in_range:
            issues.append(f"TTS total {total_dur:.1f}s not in [{dur_min},{dur_max}]")

        # Verdict
        essential = [
            checks.get("all_scenes_have_assets", False),
        ]
        verdict = GateVerdict.PASS.value if all(essential) and not issues else GateVerdict.FAIL_RETRY.value

        return QCReport(checks=checks, verdict=verdict, issues=issues)

    # ── 씬별 QC ──────────────────────────────────────────────────────────────

    # 역할별 오디오 길이 기준 (초)
    _ROLE_DURATION_RANGE: dict[str, tuple[float, float]] = {
        "hook": (2.0, 8.0),
        "body": (3.0, 12.0),
        "cta": (2.0, 8.0),
        "closing": (2.0, 8.0),
    }

    @staticmethod
    def gate_scene_qc(
        scene_plan: ScenePlan,
        scene_asset: SceneAsset,
        prev_scene: ScenePlan | None = None,
        next_scene: ScenePlan | None = None,
    ) -> SceneQCResult:
        """씬별 품질 검수 (구조적 체크만, LLM 없음).

        Args:
            scene_plan: 대본 씬
            scene_asset: 생성된 미디어 자산
            prev_scene: 이전 씬 (톤 일관성 체크용)
            next_scene: 다음 씬

        Returns:
            SceneQCResult with verdict
        """
        checks: dict[str, bool] = {}
        issues: list[str] = []
        sid = scene_plan.scene_id

        # 1. 오디오 파일 존재 + 최소 크기
        if os.path.isfile(scene_asset.audio_path):
            size = os.path.getsize(scene_asset.audio_path)
            ok = size > 10_000
            checks["audio_ok"] = ok
            if not ok:
                issues.append(f"Audio too small ({size}B)")
        else:
            checks["audio_ok"] = False
            issues.append("Audio file missing")

        # 2. 비주얼 파일 존재
        if os.path.isfile(scene_asset.visual_path):
            checks["visual_ok"] = True
        else:
            checks["visual_ok"] = False
            issues.append("Visual file missing")

        # 3. 오디오 길이 적합성 (역할별 기준)
        role = scene_plan.structure_role
        dur_min, dur_max = QCStep._ROLE_DURATION_RANGE.get(role, (1.0, 15.0))
        dur = scene_asset.duration_sec
        dur_ok = dur_min <= dur <= dur_max
        checks["duration_ok"] = dur_ok
        if not dur_ok:
            issues.append(f"Duration {dur:.1f}s outside [{dur_min},{dur_max}]s for role '{role}'")

        # 4. hook 씬: 대본이 충분히 짧고 강렬한지 (글자수 기반 경험적 체크)
        if role == "hook":
            narration_len = len(scene_plan.narration_ko)
            # hook은 너무 길면 안 됨 (200자 이하 권장)
            hook_concise = narration_len <= 200
            checks["hook_concise"] = hook_concise
            if not hook_concise:
                issues.append(f"Hook narration too long ({narration_len} chars, max 200)")

        # 5. closing 씬: CTA 금지어 체크
        if role in ("closing", "cta"):
            _FORBIDDEN = ("구독", "좋아요", "알림", "subscribe", "like", "comment", "follow")
            text = scene_plan.narration_ko.lower()
            for word in _FORBIDDEN:
                if word.lower() in text:
                    checks["no_cta_words"] = False
                    issues.append(f"Closing contains forbidden CTA word: '{word}'")
                    break
            else:
                checks["no_cta_words"] = True

        verdict = "pass" if not issues else "fail_retry"
        return SceneQCResult(
            scene_id=sid,
            checks=checks,
            verdict=verdict,
            issues=issues,
        )

    # ── Gate 4: 최종 QC ───────────────────────────────────────────────────────

    @staticmethod
    def gate4_final(
        manifest: JobManifest,
        output_path: str,
        target_duration: tuple[int, int] = (40, 50),
        stub_mode: bool = False,
    ) -> QCReport:
        """Gate 4: 렌더 완료 후 최종 품질 검수.

        Args:
            manifest: 작업 매니페스트
            output_path: 렌더된 MP4 경로
            target_duration: (min, max) 초
            stub_mode: True면 duration/filesize 체크를 skip (테스트용 stub 렌더)

        Returns:
            QCReport — PASS 또는 HOLD (자동 재생성 없음)
        """
        checks: dict[str, bool] = {}
        issues: list[str] = []
        dur_min, dur_max = target_duration

        # stub 렌더: duration/filesize/resolution/audio 체크 불필요
        if stub_mode:
            logger.info("[QC Gate 4] stub_mode — skipping media validation")
            no_failures = len(manifest.failed_steps) == 0
            checks["no_failed_steps"] = no_failures
            checks["stub_mode"] = True
            if not no_failures:
                issues.append(f"{len(manifest.failed_steps)} failed step(s)")
            verdict = GateVerdict.PASS.value if no_failures else GateVerdict.HOLD.value
            return QCReport(checks=checks, verdict=verdict, issues=issues)

        # Check 1: 영상 길이
        dur = manifest.total_duration_sec
        dur_ok = dur_min <= dur <= dur_max
        checks["duration_in_range"] = dur_ok
        if not dur_ok:
            issues.append(f"Duration {dur:.1f}s not in [{dur_min},{dur_max}]")

        # Check 2: 파일 존재 + 크기
        if os.path.isfile(output_path):
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            size_ok = 2.0 <= file_size_mb <= 50.0
            checks["file_size_ok"] = size_ok
            if not size_ok:
                issues.append(f"File size {file_size_mb:.1f}MB outside [2,50]MB")
        else:
            checks["file_exists"] = False
            issues.append(f"Output file missing: {output_path}")

        # Check 3: 실패 스텝 없음
        no_failures = len(manifest.failed_steps) == 0
        checks["no_failed_steps"] = no_failures
        if not no_failures:
            issues.append(f"{len(manifest.failed_steps)} failed step(s)")

        # Check 4: 해상도/FPS (ffprobe 사용, 실패 시 skip)
        probe = QCStep._probe_video(output_path)
        if probe:
            w, h = probe.get("width", 0), probe.get("height", 0)
            res_ok = w == 1080 and h == 1920
            checks["resolution_1080x1920"] = res_ok
            if not res_ok:
                issues.append(f"Resolution {w}x{h}, expected 1080x1920")

            fps = probe.get("fps", 0)
            fps_ok = 29 <= fps <= 31
            checks["fps_30"] = fps_ok
            if not fps_ok:
                issues.append(f"FPS {fps}, expected ~30")

        # Check 5: 오디오 피크 (ffprobe volumedetect)
        peak_db = QCStep._check_audio_peak(output_path)
        if peak_db is not None:
            peak_ok = peak_db <= -1.0  # -1dBFS 이하
            checks["audio_peak_ok"] = peak_ok
            if not peak_ok:
                issues.append(f"Audio peak {peak_db:.1f}dBFS, too loud")

        # Gate 4 verdict: HOLD (not FAIL_RETRY — 렌더 후 자동 재생성 안함)
        if all(checks.values()):
            verdict = GateVerdict.PASS.value
            logger.info("[QC Gate 4] PASS ✅ — all checks passed")
        else:
            verdict = GateVerdict.HOLD.value
            logger.warning(
                "[QC Gate 4] HOLD ⚠️ — issues: %s",
                "; ".join(issues),
            )

        return QCReport(checks=checks, verdict=verdict, issues=issues)

    # ── ffprobe 유틸리티 ──────────────────────────────────────────────────────

    @staticmethod
    def _probe_video(path: str) -> dict[str, Any] | None:
        """ffprobe로 영상 메타데이터 추출. 실패 시 None."""
        if not os.path.isfile(path):
            return None
        try:
            result = subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-select_streams",
                    "v:0",
                    "-show_entries",
                    "stream=width,height,r_frame_rate",
                    "-of",
                    "csv=p=0",
                    path,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                return None
            parts = result.stdout.strip().split(",")
            if len(parts) >= 3:
                w, h = int(parts[0]), int(parts[1])
                # r_frame_rate is like "30/1"
                fps_parts = parts[2].split("/")
                fps = (
                    int(fps_parts[0]) / int(fps_parts[1])
                    if len(fps_parts) == 2 and int(fps_parts[1]) != 0
                    else float(fps_parts[0])
                )
                return {"width": w, "height": h, "fps": fps}
        except Exception as exc:
            logger.debug("[QC] ffprobe failed: %s", exc)
        return None

    @staticmethod
    def _check_audio_peak(path: str) -> float | None:
        """ffmpeg volumedetect로 오디오 피크 측정. 실패 시 None."""
        if not os.path.isfile(path):
            return None
        try:
            result = subprocess.run(
                [
                    "ffmpeg",
                    "-i",
                    path,
                    "-af",
                    "volumedetect",
                    "-vn",
                    "-sn",
                    "-dn",
                    "-f",
                    "null",
                    "-",
                ],
                capture_output=True,
                text=True,
                timeout=30,
            )
            # Parse max_volume from stderr
            for line in result.stderr.splitlines():
                if "max_volume" in line:
                    # e.g. "[Parsed_volumedetect_0 ... max_volume: -3.2 dB"
                    parts = line.split("max_volume:")
                    if len(parts) == 2:
                        val = parts[1].strip().replace("dB", "").strip()
                        return float(val)
        except Exception as exc:
            logger.debug("[QC] volumedetect failed: %s", exc)
        return None
