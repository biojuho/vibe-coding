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

    # essential check 이름 — lenient 모드에서도 실패하면 fail_retry로 판정.
    # 나머지(duration/hook_concise/no_cta_words/chars_per_sec_ok)는 lenient에서 issues로만 남기고 통과.
    _ESSENTIAL_CHECKS: frozenset[str] = frozenset({"audio_ok", "visual_ok"})

    # TTS가 트런케이션·헤더손상으로 거의 빈 오디오를 만들었을 때 잡기 위한 하한.
    _AUDIO_MIN_DURATION_SEC: float = 0.5

    # Shorts에 쓸 만한 비주얼의 최소 해상도(가로/세로 둘 다). 썸네일 잘못 다운로드된 경우 탈락.
    _VISUAL_MIN_DIM: int = 540

    # 한국어 자연 TTS 속도의 합리적 범위(자/초). 1.5↓는 음성 과느림/공백,
    # 10↑는 트런케이션 신호(긴 나레이션이 1~2초로 합성).
    _CHARS_PER_SEC_RANGE: tuple[float, float] = (1.5, 10.0)

    # closing/cta 역할에서 금지하는 CTA 표현. user_shorts_philosophy(시간을 훔치는 이야기) 준수.
    # 영어 + 한국어 변형 다수 포함.
    _FORBIDDEN_CTA: tuple[str, ...] = (
        "구독",
        "좋아요",
        "알림",
        "팔로우",
        "공유",
        "댓글",
        "지금 클릭",
        "지금 누르세요",
        "눌러주세요",
        "꼭 보세요",
        "subscribe",
        "like",
        "comment",
        "follow",
        "share",
    )

    @staticmethod
    def gate_scene_qc(
        scene_plan: ScenePlan,
        scene_asset: SceneAsset,
        prev_scene: ScenePlan | None = None,
        next_scene: ScenePlan | None = None,
        *,
        strictness: str = "strict",
    ) -> SceneQCResult:
        """씬별 품질 검수 (구조적 체크만, LLM 없음).

        Args:
            scene_plan: 대본 씬
            scene_asset: 생성된 미디어 자산
            prev_scene: 이전 씬 (톤 일관성 체크용)
            next_scene: 다음 씬
            strictness: ``"strict"``(기본, 이슈 1개도 허용 안함) /
                ``"lenient"`` (audio/visual 파일 존재만 essential, 그 외 이슈는 통과) /
                ``"off"`` (모든 체크를 스킵하고 즉시 pass).

        Returns:
            SceneQCResult with verdict
        """
        sid = scene_plan.scene_id

        if strictness == "off":
            return SceneQCResult(scene_id=sid, checks={}, verdict="pass", issues=[])

        if strictness not in {"strict", "lenient"}:
            raise ValueError(f"gate_scene_qc: strictness must be 'strict' | 'lenient' | 'off', got {strictness!r}")

        checks: dict[str, bool] = {}
        issues: list[str] = []

        # 1. 오디오 정합성: 파일 존재 + 최소 크기 + 최소 듀레이션
        audio_ok, audio_issue = QCStep._check_audio_integrity(scene_asset)
        checks["audio_ok"] = audio_ok
        if audio_issue:
            issues.append(audio_issue)

        # 2. 비주얼 정합성: 파일 존재 + 디코딩 가능 + 최소 해상도
        visual_ok, visual_issue = QCStep._check_visual_integrity(scene_asset)
        checks["visual_ok"] = visual_ok
        if visual_issue:
            issues.append(visual_issue)

        # 3. 오디오 길이 적합성 (역할별 기준)
        role = scene_plan.structure_role
        dur_min, dur_max = QCStep._ROLE_DURATION_RANGE.get(role, (1.0, 15.0))
        dur = scene_asset.duration_sec
        dur_ok = dur_min <= dur <= dur_max
        checks["duration_ok"] = dur_ok
        if not dur_ok:
            issues.append(f"Duration {dur:.1f}s outside [{dur_min},{dur_max}]s for role '{role}'")

        # 4. 나레이션-오디오 합성 속도 정합성(자/초).
        # 비어있는 나레이션이나 0초 오디오는 위 체크에서 잡으므로 여기선 skip.
        narration_text = scene_plan.narration_ko.strip()
        if narration_text and dur > 0:
            cps = len(narration_text) / dur
            cps_min, cps_max = QCStep._CHARS_PER_SEC_RANGE
            cps_ok = cps_min <= cps <= cps_max
            checks["chars_per_sec_ok"] = cps_ok
            if not cps_ok:
                issues.append(
                    f"Narration/audio rate {cps:.1f} chars/s outside "
                    f"[{cps_min},{cps_max}] (likely TTS truncation or empty audio)"
                )

        # 5. hook 씬: 대본이 충분히 짧고 강렬한지 (글자수 기반 경험적 체크)
        if role == "hook":
            narration_len = len(scene_plan.narration_ko)
            # hook은 너무 길면 안 됨 (200자 이하 권장)
            hook_concise = narration_len <= 200
            checks["hook_concise"] = hook_concise
            if not hook_concise:
                issues.append(f"Hook narration too long ({narration_len} chars, max 200)")

        # 6. closing/cta 씬: CTA 금지어 체크 (한국어 변형 포함)
        if role in ("closing", "cta"):
            text = scene_plan.narration_ko.lower()
            for word in QCStep._FORBIDDEN_CTA:
                if word.lower() in text:
                    checks["no_cta_words"] = False
                    issues.append(f"Closing contains forbidden CTA word: '{word}'")
                    break
            else:
                checks["no_cta_words"] = True

        # Verdict 계산.
        # strict: 이슈가 1개라도 있으면 fail_retry.
        # lenient: essential check(audio_ok / visual_ok)가 실패한 경우에만 fail_retry,
        #          그 외 이슈는 issues 리스트로만 보존하고 통과.
        if strictness == "lenient":
            essential_failed = any(not checks.get(name, True) for name in QCStep._ESSENTIAL_CHECKS)
            verdict = "fail_retry" if essential_failed else "pass"
        else:
            verdict = "pass" if not issues else "fail_retry"

        return SceneQCResult(
            scene_id=sid,
            checks=checks,
            verdict=verdict,
            issues=issues,
        )

    # ── 정합성 헬퍼 ────────────────────────────────────────────────────────────

    @staticmethod
    def _check_audio_integrity(asset: SceneAsset) -> tuple[bool, str | None]:
        """오디오 자산의 essential 정합성 체크.

        파일 존재 + 최소 크기(10KB) + 최소 듀레이션(0.5s). 셋 중 하나라도
        실패하면 audio_ok=False. duration_sec은 SceneAsset이 신뢰할 만한
        값을 가지고 있다는 전제 — TTS 스텝에서 정확히 측정되므로 ffprobe
        재확인은 비용 대비 효익이 낮다.
        """
        path = asset.audio_path
        if not os.path.isfile(path):
            return False, "Audio file missing"
        size = os.path.getsize(path)
        if size <= 10_000:
            return False, f"Audio too small ({size}B)"
        if asset.duration_sec < QCStep._AUDIO_MIN_DURATION_SEC:
            return False, (
                f"Audio duration {asset.duration_sec:.2f}s below "
                f"minimum {QCStep._AUDIO_MIN_DURATION_SEC}s (likely TTS truncation)"
            )
        return True, None

    @staticmethod
    def _check_visual_integrity(asset: SceneAsset) -> tuple[bool, str | None]:
        """비주얼 자산의 essential 정합성 체크.

        - image: Pillow로 열고 width/height >= _VISUAL_MIN_DIM.
        - video: ffprobe로 첫 비디오 스트림의 width/height >= _VISUAL_MIN_DIM.
        Pillow/ffprobe 자체 실패는 fail 처리 — 깨진 자산을 통과시키지 않는다.
        """
        path = asset.visual_path
        if not os.path.isfile(path):
            return False, "Visual file missing"

        if asset.visual_type == "image":
            try:
                from PIL import Image, UnidentifiedImageError
            except ImportError:
                logger.warning("[QC] Pillow not installed — skipping visual integrity check")
                return True, None
            try:
                with Image.open(path) as img:
                    img.verify()
                with Image.open(path) as img:
                    w, h = img.size
            except (UnidentifiedImageError, OSError, ValueError) as exc:
                return False, f"Visual image unreadable: {exc.__class__.__name__}"
            if w < QCStep._VISUAL_MIN_DIM or h < QCStep._VISUAL_MIN_DIM:
                return False, (f"Visual dimensions {w}x{h} below minimum {QCStep._VISUAL_MIN_DIM}px")
            return True, None

        # video
        probe = QCStep._probe_video(path)
        if probe is None:
            return False, "Visual video unreadable (ffprobe failed)"
        w, h = probe.get("width", 0), probe.get("height", 0)
        if w < QCStep._VISUAL_MIN_DIM or h < QCStep._VISUAL_MIN_DIM:
            return False, (f"Visual dimensions {w}x{h} below minimum {QCStep._VISUAL_MIN_DIM}px")
        return True, None

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
        output_exists = os.path.isfile(output_path)
        checks["file_exists"] = output_exists
        if output_exists:
            file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
            size_ok = 2.0 <= file_size_mb <= 50.0
            checks["file_size_ok"] = size_ok
            if not size_ok:
                issues.append(f"File size {file_size_mb:.1f}MB outside [2,50]MB")
        else:
            issues.append(f"Output file missing: {output_path}")

        # Check 3: 실패 스텝 없음
        no_failures = len(manifest.failed_steps) == 0
        checks["no_failed_steps"] = no_failures
        if not no_failures:
            issues.append(f"{len(manifest.failed_steps)} failed step(s)")

        # Check 4: 해상도/FPS (ffprobe 사용, 실패 시 skip)
        probe = QCStep._probe_video(output_path) if output_exists else None
        checks["video_probe_ok"] = probe is not None
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
        elif output_exists:
            issues.append("Could not inspect video metadata with ffprobe")

        # Check 5: 오디오 피크 (ffprobe volumedetect)
        peak_db = QCStep._check_audio_peak(output_path) if output_exists else None
        checks["audio_peak_probe_ok"] = peak_db is not None
        if peak_db is not None:
            peak_ok = peak_db <= -1.0  # -1dBFS 이하
            checks["audio_peak_ok"] = peak_ok
            if not peak_ok:
                issues.append(f"Audio peak {peak_db:.1f}dBFS, too loud")
        elif output_exists:
            issues.append("Could not inspect audio peak with ffmpeg volumedetect")

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

    # ── Safe Zone QC ──────────────────────────────────────────────────────────

    @staticmethod
    def gate_safe_zone(
        scene_plans: list[ScenePlan],
        scene_assets: list[SceneAsset],
        canvas_height: int = 1920,
    ) -> QCReport:
        """Safe Zone 검증: 자막이 YouTube Shorts UI 영역을 침범하지 않는지 확인.

        caption_pillow.calculate_safe_position으로 예상 위치를 계산하고,
        validate_safe_zone으로 안전 영역 내 배치 여부를 검증한다.
        """
        from shorts_maker_v2.render.caption_pillow import (
            CaptionStyle,
            calculate_safe_position,
            validate_safe_zone,
        )

        checks: dict[str, bool] = {}
        issues: list[str] = []

        default_style = CaptionStyle(
            font_size=76,
            margin_x=40,
            bottom_offset=200,
            text_color="#FFFFFF",
            stroke_color="#000000",
            stroke_width=4,
            line_spacing=12,
            font_candidates=(),
        )

        for plan in scene_plans:
            role = plan.structure_role
            estimated_lines = max(1, len(plan.narration_ko) // 20)
            estimated_height = estimated_lines * (default_style.font_size + default_style.line_spacing)

            y_pos = calculate_safe_position(canvas_height, estimated_height, default_style, role=role)
            result = validate_safe_zone(y_pos, estimated_height, canvas_height)

            is_safe = result["in_safe_zone"]
            checks[f"safe_zone_s{plan.scene_id}"] = is_safe
            if not is_safe:
                overflow_details = []
                if result["top_overflow_px"] > 0:
                    overflow_details.append(f"top overflow {result['top_overflow_px']}px")
                if result["bottom_overflow_px"] > 0:
                    overflow_details.append(f"bottom overflow {result['bottom_overflow_px']}px")
                issues.append(
                    f"Scene {plan.scene_id} [{role}]: caption outside safe zone ({', '.join(overflow_details)})"
                )

        verdict = GateVerdict.PASS.value if not issues else GateVerdict.HOLD.value
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
