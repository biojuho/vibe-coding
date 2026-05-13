"""QCStep — Gate 3 (미디어 QC) + Gate 4 (최종 QC).

렌더 전 미디어 자산 검증(Gate 3)과 렌더 후 최종 품질 검수(Gate 4).
"""

from __future__ import annotations

import contextlib
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
    SemanticQCResult,
    StructureOutline,
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

    # 씬별 mean volume(dBFS) 허용 범위. -40↓ 면 사실상 silence(TTS 합성 실패),
    # -0.5↑ 면 clipping 가까움. 정상 TTS-1-HD 출력은 -25 ~ -10 dBFS 부근.
    # T-288 FEATURE.md non-goal #2: 씬별 RMS 오디오 검사 — file 존재만으로는
    # "silent 한 파일"을 잡지 못한다.
    _AUDIO_MEAN_VOLUME_RANGE: tuple[float, float] = (-40.0, -0.5)

    # 씬-씬 평균 RGB 거리 한계. 최대 sqrt(3*255^2) ≈ 441. 130 은 명백히 다른
    # 색조(예: 어두운 시네마틱 → 채도 높은 anime) 만 잡는 보수적 임계값.
    # T-288 FEATURE.md non-goal #1: abrupt transition 감지 — 시각적으로
    # 튀는 씬-씬 컷이 silently ship 되는 것을 막는다.
    _VISUAL_CONTINUITY_MAX_RGB_DIST: float = 130.0

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
        prev_asset: SceneAsset | None = None,
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
            prev_asset: 이전 씬의 미디어 자산. 시각 연속성(abrupt transition)
                감지에 사용. 없으면 (=첫 씬) 해당 체크는 자연 통과.

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

        # 7. 씬별 mean volume(dBFS) — silent TTS / clipping 감지.
        # essential audio_ok 가 통과한 경우에만 ffmpeg 호출 (비용 절약).
        # essential 이 아님: 일시적 ffmpeg 실패가 verdict 를 흔들지 않게.
        if audio_ok and scene_asset.duration_sec > 0:
            levels = QCStep._run_volumedetect(scene_asset.audio_path, timeout=15)
            if levels and "mean_db" in levels:
                mean_db = levels["mean_db"]
                rms_min, rms_max = QCStep._AUDIO_MEAN_VOLUME_RANGE
                rms_ok = rms_min <= mean_db <= rms_max
                checks["audio_mean_volume_ok"] = rms_ok
                if not rms_ok:
                    issues.append(
                        f"Audio mean volume {mean_db:.1f}dBFS outside "
                        f"[{rms_min},{rms_max}] (likely silent TTS or clipping)"
                    )

        # 8. 시각 연속성 — 이전 씬과의 평균 RGB 거리. abrupt transition 감지.
        # essential 아님: 디코드/Pillow 실패는 silently True 로 통과(가짜 fail 안 만듦).
        if prev_asset is not None and visual_ok:
            cont_ok, cont_issue = QCStep._check_visual_continuity(scene_asset, prev_asset)
            checks["visual_continuity_ok"] = cont_ok
            if cont_issue:
                issues.append(cont_issue)

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
    def _run_volumedetect(path: str, *, timeout: int = 30) -> dict[str, float] | None:
        """ffmpeg volumedetect 한 번 돌려서 mean/max(dBFS) 둘 다 파싱.

        Gate 4 의 audio peak 체크와 씬별 RMS 체크가 같은 ffmpeg 호출을
        공유하도록 정리한 헬퍼. 둘 중 하나만 파싱되어도 그 키만 채워 반환.
        스트림이 비어있거나 ffmpeg 자체가 실패하면 None.
        """
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
                timeout=timeout,
                # Windows 한글 코드페이지(cp949) 기본 디코드는 ffmpeg UTF-8
                # stderr 의 한글 경로/메시지에서 깨진다 (`UnicodeDecodeError`).
                # 파싱은 ASCII 라인(`max_volume:`/`mean_volume:`)만 보므로
                # 다른 바이트는 replace 로 흘려보낸다.
                encoding="utf-8",
                errors="replace",
            )
            levels: dict[str, float] = {}
            for line in result.stderr.splitlines():
                # e.g. "[Parsed_volumedetect_0 ...] max_volume: -3.2 dB"
                if "max_volume:" in line:
                    parts = line.split("max_volume:")
                    if len(parts) == 2:
                        val = parts[1].strip().replace("dB", "").strip()
                        with contextlib.suppress(ValueError):
                            levels["max_db"] = float(val)
                elif "mean_volume:" in line:
                    parts = line.split("mean_volume:")
                    if len(parts) == 2:
                        val = parts[1].strip().replace("dB", "").strip()
                        with contextlib.suppress(ValueError):
                            levels["mean_db"] = float(val)
            return levels or None
        except Exception as exc:
            logger.debug("[QC] volumedetect failed: %s", exc)
        return None

    @staticmethod
    def _check_audio_peak(path: str) -> float | None:
        """ffmpeg volumedetect 의 max_volume(dBFS) 만 단일 값으로 반환. 실패 시 None.

        Gate 4 의 기존 호출 시그니처 보존을 위해 남겨둠 — 내부는 공용 헬퍼 위임.
        """
        levels = QCStep._run_volumedetect(path)
        if levels and "max_db" in levels:
            return levels["max_db"]
        return None

    # ── 시각 연속성 헬퍼 ────────────────────────────────────────────────────────

    @staticmethod
    def _mean_rgb(path: str) -> tuple[float, float, float] | None:
        """이미지 thumbnail 평균 RGB. Pillow 없거나 디코드 실패면 None.

        64x64 로 다운샘플 후 산술 평균. 씬별 RMS 비교 비용을 millis 단위로 유지.
        """
        try:
            from PIL import Image, UnidentifiedImageError
        except ImportError:
            return None
        try:
            with Image.open(path) as img:
                img.thumbnail((64, 64))
                rgb = img.convert("RGB")
                pixels = list(rgb.getdata())
        except (UnidentifiedImageError, OSError, ValueError):
            return None
        if not pixels:
            return None
        n = len(pixels)
        r = sum(p[0] for p in pixels) / n
        g = sum(p[1] for p in pixels) / n
        b = sum(p[2] for p in pixels) / n
        return (r, g, b)

    @staticmethod
    def _check_visual_continuity(
        curr: SceneAsset,
        prev: SceneAsset | None,
    ) -> tuple[bool, str | None]:
        """현재 씬과 이전 씬의 평균 RGB 거리로 abrupt transition 감지.

        첫 씬, 비디오 자산, 또는 디코드 실패 시 ``True`` 로 자연 통과 — 가짜
        실패를 만들지 않는다. 거리 한계는 ``_VISUAL_CONTINUITY_MAX_RGB_DIST``.

        Returns:
            ``(ok, issue_text_or_None)``
        """
        if prev is None:
            return True, None
        if curr.visual_type != "image" or prev.visual_type != "image":
            # video 자산은 첫 프레임 추출 비용을 들이지 않고 스킵. T-288 scope.
            return True, None
        curr_mean = QCStep._mean_rgb(curr.visual_path)
        prev_mean = QCStep._mean_rgb(prev.visual_path)
        if curr_mean is None or prev_mean is None:
            # 디코드 실패는 _check_visual_integrity 가 audio/visual essential 로 잡는다.
            return True, None
        dist = (
            (curr_mean[0] - prev_mean[0]) ** 2 + (curr_mean[1] - prev_mean[1]) ** 2 + (curr_mean[2] - prev_mean[2]) ** 2
        ) ** 0.5
        if dist > QCStep._VISUAL_CONTINUITY_MAX_RGB_DIST:
            return False, (
                f"Visual abrupt transition (RGB distance {dist:.1f} > {QCStep._VISUAL_CONTINUITY_MAX_RGB_DIST})"
            )
        return True, None


# ── SemanticQCStep: LLM 기반 씬-씬 의미 QC (T-288 non-goal #3) ────────────────


class SemanticQCStep:
    """Post-asset 의미 QC: 씬-씬 연결성 + 톤 일관성 LLM judge.

    script_review 가 *script 단계* 의 글로벌 점수(hook/flow/cta/...)를 매기는
    반면, SemanticQCStep 은 scene_qc 의 retry 가 끝난 *최종 상태* 의 narration
    리스트를 보고 어느 씬 전환이 약한지 구체적으로 잡는다. 단일 LLM 호출 —
    per-scene 호출이 아니라 비용/지연이 한 번에 고정된다.

    이 게이트는 verdict 만 보고하고 regen 을 트리거하지 않는다 (씬 narration
    재생성은 script 단계 책임). 결과가 임계값 미만이면 orchestrator 가
    ``manifest.degraded_steps`` 로 표면화한다.
    """

    _SYSTEM_PROMPT = (
        "You are a YouTube Shorts narrative quality judge. "
        "Read the full scene-by-scene narration and score:\n"
        "  - scene_flow_score (0-10): How logically does each scene connect "
        "to the previous and next? Score harshly if any transition feels abrupt, "
        "non-sequitur, or repetitive.\n"
        "  - tone_consistency_score (0-10): Is the emotional tone consistent "
        "throughout? Score harshly if any scene tonally clashes with the rest.\n"
        "  - overall_score (0-10): Your single-number judgment.\n"
        "\nIDENTIFY weak transitions: list the specific scene_id pairs where "
        "the connection feels weakest, with a short reason each.\n"
        "\nThe channel philosophy is 'quiet storytelling — stealing the viewer's "
        "time'. Avoid CTAs, action demands. The closing scene should leave a "
        "lingering thought, not a call to action.\n"
        "\nOutput ONLY valid JSON:\n"
        "{\n"
        '  "scene_flow_score": <0-10>,\n'
        '  "tone_consistency_score": <0-10>,\n'
        '  "overall_score": <0-10>,\n'
        '  "weak_transitions": [\n'
        '    {"from": <scene_id>, "to": <scene_id>, "reason": "<short>"}\n'
        "  ],\n"
        '  "feedback": "<one-line summary>"\n'
        "}"
    )

    def __init__(self, llm_router: Any, min_score: int = 6):
        self.llm_router = llm_router
        self.min_score = min_score

    def run(
        self,
        scene_plans: list[ScenePlan],
        structure_outline: StructureOutline | None = None,
    ) -> SemanticQCResult:
        """씬 의미 QC 한 번 실행. LLM 실패는 verdict='error' 로 반환 — raise 안 함."""
        if not scene_plans:
            return SemanticQCResult(
                verdict="error",
                feedback="No scene_plans provided",
            )

        user_prompt = self._build_user_prompt(scene_plans, structure_outline)
        raw_response = ""
        try:
            response = self.llm_router.generate_json(
                system_prompt=self._SYSTEM_PROMPT,
                user_prompt=user_prompt,
                temperature=0.2,  # 채점은 deterministic 쪽이 안전
            )
        except Exception as exc:
            logger.warning("[SemanticQC] LLM call failed: %s", exc)
            return SemanticQCResult(
                verdict="error",
                feedback=f"LLM error: {exc.__class__.__name__}",
            )

        if not isinstance(response, dict):
            return SemanticQCResult(
                verdict="error",
                feedback=f"LLM returned non-dict: {type(response).__name__}",
                raw_response=str(response)[:500],
            )

        # 안전한 정수 추출 (LLM 이 문자열이나 None 줄 수 있음)
        scene_flow = self._coerce_score(response.get("scene_flow_score"))
        tone_consistency = self._coerce_score(response.get("tone_consistency_score"))
        overall = self._coerce_score(response.get("overall_score"))

        raw_transitions = response.get("weak_transitions", [])
        weak_transitions: list[dict[str, Any]] = []
        if isinstance(raw_transitions, list):
            for t in raw_transitions[:20]:  # 비정상 응답 방어
                if isinstance(t, dict):
                    weak_transitions.append(
                        {
                            "from": self._coerce_int(t.get("from"), default=0),
                            "to": self._coerce_int(t.get("to"), default=0),
                            "reason": str(t.get("reason", ""))[:200],
                        }
                    )

        feedback = str(response.get("feedback", ""))[:300]
        raw_response = str(response)[:1000]

        # Verdict: 두 핵심 차원의 최소값이 임계값 미만이면 degraded.
        weakest = min(scene_flow, tone_consistency)
        verdict = "pass" if weakest >= self.min_score else "degraded"

        logger.info(
            "[SemanticQC] flow=%d tone=%d overall=%d verdict=%s weak_count=%d",
            scene_flow,
            tone_consistency,
            overall,
            verdict,
            len(weak_transitions),
        )

        return SemanticQCResult(
            scene_flow_score=scene_flow,
            tone_consistency_score=tone_consistency,
            overall_score=overall,
            weak_transitions=weak_transitions,
            verdict=verdict,
            feedback=feedback,
            raw_response=raw_response,
        )

    @staticmethod
    def _coerce_score(value: Any, *, lo: int = 0, hi: int = 10) -> int:
        """0..10 정수로 강제. 비정상 값은 0."""
        v = SemanticQCStep._coerce_int(value, default=0)
        return max(lo, min(hi, v))

    @staticmethod
    def _coerce_int(value: Any, *, default: int = 0) -> int:
        if isinstance(value, bool):
            return default
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            with contextlib.suppress(ValueError):
                return int(float(value))
        return default

    @staticmethod
    def _build_user_prompt(
        scene_plans: list[ScenePlan],
        structure_outline: StructureOutline | None,
    ) -> str:
        lines = ["=== FULL SCENE-BY-SCENE NARRATION ==="]
        for plan in scene_plans:
            lines.append(f"Scene {plan.scene_id} [{plan.structure_role}]: narration_ko: {plan.narration_ko!r}")
        if structure_outline is not None:
            lines.append("")
            lines.append("=== INTENDED STRUCTURE ===")
            for s in structure_outline.scenes:
                lines.append(f"Scene {s.scene_id} [{s.role}]: intent={s.intent!r} emotional_beat={s.emotional_beat!r}")
        lines.append("")
        lines.append("Score now. Output JSON only.")
        return "\n".join(lines)
