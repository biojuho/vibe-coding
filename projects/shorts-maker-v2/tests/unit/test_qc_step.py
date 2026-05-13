from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from shorts_maker_v2.models import (
    GateVerdict,
    JobManifest,
    SceneAsset,
    SceneOutline,
    ScenePlan,
    StructureOutline,
)
from shorts_maker_v2.pipeline.qc_step import QCStep, SemanticQCStep


def _write_bytes(path: Path, size: int) -> str:
    path.write_bytes(b"x" * size)
    return str(path)


def _write_png(path: Path, width: int = 720, height: int = 1280) -> str:
    """gate_scene_qc 비주얼 정합성 체크를 통과할 수 있는 실제 PNG 파일을 만든다."""
    from PIL import Image

    Image.new("RGB", (width, height), color=(20, 20, 20)).save(path, "PNG")
    return str(path)


def test_gate3_media_passes_with_valid_assets(tmp_path: Path) -> None:
    audio_path = _write_bytes(tmp_path / "audio.wav", 12_000)
    visual_path = _write_bytes(tmp_path / "visual.jpg", 256)
    scene_plans = [
        ScenePlan(scene_id=1, narration_ko="narration", visual_prompt_en="prompt", target_sec=6.0),
    ]
    scene_assets = [
        SceneAsset(
            scene_id=1,
            audio_path=audio_path,
            visual_type="image",
            visual_path=visual_path,
            duration_sec=6.0,
        )
    ]

    report = QCStep.gate3_media(scene_plans, scene_assets, target_duration=(5, 10))

    assert report.verdict == GateVerdict.PASS.value
    assert report.issues == []
    assert report.checks["all_scenes_have_assets"] is True


def test_gate3_media_reports_missing_and_invalid_assets(tmp_path: Path) -> None:
    tiny_audio = _write_bytes(tmp_path / "tiny.wav", 5)
    missing_visual = str(tmp_path / "missing.jpg")
    scene_plans = [
        ScenePlan(scene_id=1, narration_ko="narration", visual_prompt_en="prompt", target_sec=4.0),
        ScenePlan(scene_id=2, narration_ko="narration", visual_prompt_en="prompt", target_sec=4.0),
    ]
    scene_assets = [
        SceneAsset(
            scene_id=1,
            audio_path=tiny_audio,
            visual_type="image",
            visual_path=missing_visual,
            duration_sec=2.0,
        )
    ]

    report = QCStep.gate3_media(scene_plans, scene_assets, target_duration=(8, 10))

    assert report.verdict == GateVerdict.FAIL_RETRY.value
    assert "Missing assets for scenes: [2]" in report.issues
    assert any("audio too small" in issue for issue in report.issues)
    assert any("visual file missing" in issue for issue in report.issues)
    assert any("TTS total 2.0s not in [8,10]" in issue for issue in report.issues)


def test_gate4_final_stub_mode_passes_without_media_checks() -> None:
    manifest = JobManifest(job_id="job-1", topic="topic", status="ok", failed_steps=[])

    report = QCStep.gate4_final(manifest, output_path="missing.mp4", stub_mode=True)

    assert report.verdict == GateVerdict.PASS.value
    assert report.checks["stub_mode"] is True
    assert report.issues == []


def test_gate4_final_stub_mode_holds_when_failed_steps_exist() -> None:
    manifest = JobManifest(
        job_id="job-2",
        topic="topic",
        status="error",
        failed_steps=[{"step": "render", "error": "boom"}],
    )

    report = QCStep.gate4_final(manifest, output_path="missing.mp4", stub_mode=True)

    assert report.verdict == GateVerdict.HOLD.value
    assert report.checks["no_failed_steps"] is False
    assert report.issues == ["1 failed step(s)"]


def test_gate4_final_hold_reports_multiple_media_issues(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    output_path = _write_bytes(tmp_path / "out.mp4", 16)
    manifest = JobManifest(
        job_id="job-3",
        topic="topic",
        status="done",
        total_duration_sec=3.0,
        failed_steps=[{"step": "media", "error": "broken"}],
    )

    monkeypatch.setattr(
        QCStep,
        "_probe_video",
        staticmethod(lambda path: {"width": 720, "height": 1280, "fps": 24.0}),
    )
    monkeypatch.setattr(QCStep, "_check_audio_peak", staticmethod(lambda path: 0.0))

    report = QCStep.gate4_final(manifest, output_path=output_path, target_duration=(40, 50))

    assert report.verdict == GateVerdict.HOLD.value
    assert any("Duration 3.0s not in [40,50]" in issue for issue in report.issues)
    assert any("File size" in issue for issue in report.issues)
    assert any("1 failed step(s)" in issue for issue in report.issues)
    assert any("Resolution 720x1280" in issue for issue in report.issues)
    assert any("FPS 24.0" in issue for issue in report.issues)
    assert any("Audio peak 0.0dBFS" in issue for issue in report.issues)


def test_probe_video_parses_ffprobe_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video_path = _write_bytes(tmp_path / "video.mp4", 32)

    monkeypatch.setattr(
        "shorts_maker_v2.pipeline.qc_step.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="1080,1920,30000/1000", stderr=""),
    )

    info = QCStep._probe_video(video_path)

    assert info == {"width": 1080, "height": 1920, "fps": 30.0}


def test_probe_video_returns_none_on_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video_path = _write_bytes(tmp_path / "video.mp4", 32)

    monkeypatch.setattr(
        "shorts_maker_v2.pipeline.qc_step.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="", stderr="bad"),
    )
    assert QCStep._probe_video(video_path) is None
    assert QCStep._probe_video(str(tmp_path / "missing.mp4")) is None


def test_check_audio_peak_parses_ffmpeg_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video_path = _write_bytes(tmp_path / "video.mp4", 32)

    monkeypatch.setattr(
        "shorts_maker_v2.pipeline.qc_step.subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(
            returncode=0,
            stdout="",
            stderr="[Parsed_volumedetect_0] max_volume: -3.2 dB\n",
        ),
    )

    assert QCStep._check_audio_peak(video_path) == -3.2


def test_check_audio_peak_returns_none_on_exception(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video_path = _write_bytes(tmp_path / "video.mp4", 32)

    def raise_error(*args, **kwargs):
        del args, kwargs
        raise RuntimeError("ffmpeg missing")

    monkeypatch.setattr("shorts_maker_v2.pipeline.qc_step.subprocess.run", raise_error)

    assert QCStep._check_audio_peak(video_path) is None


def test_check_audio_peak_returns_none_for_missing_file(tmp_path: Path) -> None:
    assert QCStep._check_audio_peak(str(tmp_path / "no.mp4")) is None


# ── gate_scene_qc 테스트 ─────────────────────────────────────────────────────


class TestGateSceneQC:
    """씬별 QC (gate_scene_qc)."""

    def _make_plan(self, sid=1, role="body", narration="나레이션 텍스트"):
        return ScenePlan(
            scene_id=sid,
            narration_ko=narration,
            visual_prompt_en="prompt",
            target_sec=6.0,
            structure_role=role,
        )

    def _make_asset(self, sid=1, audio_path="", visual_path="", dur=5.0):
        return SceneAsset(
            scene_id=sid,
            audio_path=audio_path,
            visual_type="image",
            visual_path=visual_path,
            duration_sec=dur,
        )

    def test_pass_all_checks(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="body")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=5.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "pass"
        assert result.issues == []
        assert result.checks["audio_ok"] is True
        assert result.checks["visual_ok"] is True
        assert result.checks["duration_ok"] is True

    def test_audio_missing(self, tmp_path: Path) -> None:
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan()
        asset = self._make_asset(audio_path=str(tmp_path / "missing.wav"), visual_path=visual)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "fail_retry"
        assert result.checks["audio_ok"] is False
        assert any("Audio file missing" in i for i in result.issues)

    def test_audio_too_small(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "tiny.wav", 50)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan()
        asset = self._make_asset(audio_path=audio, visual_path=visual)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["audio_ok"] is False
        assert any("Audio too small" in i for i in result.issues)

    def test_visual_missing(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        plan = self._make_plan()
        asset = self._make_asset(audio_path=audio, visual_path=str(tmp_path / "no.jpg"))

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["visual_ok"] is False
        assert any("Visual file missing" in i for i in result.issues)

    def test_duration_out_of_range(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="hook")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=20.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["duration_ok"] is False
        assert any("Duration" in i for i in result.issues)

    def test_hook_concise_check_pass(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="hook", narration="짧은 훅")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["hook_concise"] is True

    def test_hook_too_long(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="hook", narration="가" * 201)
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["hook_concise"] is False
        assert any("Hook narration too long" in i for i in result.issues)

    def test_closing_cta_forbidden_words(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="closing", narration="구독과 좋아요 부탁드립니다")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["no_cta_words"] is False
        assert any("forbidden CTA word" in i for i in result.issues)

    def test_closing_no_cta_words(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="closing", narration="다음에 또 만나요")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["no_cta_words"] is True

    def test_unknown_role_uses_wide_duration_range(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="unknown_role")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=14.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["duration_ok"] is True


class TestGateSceneQCStrictness:
    """qc_strictness 파라미터 분기 (strict / lenient / off)."""

    def _make_plan(self, sid=1, role="hook", narration="나레이션"):
        return ScenePlan(
            scene_id=sid,
            narration_ko=narration,
            visual_prompt_en="prompt",
            target_sec=4.0,
            structure_role=role,
        )

    def _make_asset(self, sid=1, audio_path="", visual_path="", dur=5.0):
        return SceneAsset(
            scene_id=sid,
            audio_path=audio_path,
            visual_type="image",
            visual_path=visual_path,
            duration_sec=dur,
        )

    def test_off_returns_pass_without_running_checks(self, tmp_path: Path) -> None:
        # 파일이 없어도 off는 검사하지 않으므로 pass.
        plan = self._make_plan()
        asset = self._make_asset(
            audio_path=str(tmp_path / "missing.wav"),
            visual_path=str(tmp_path / "missing.jpg"),
        )

        result = QCStep.gate_scene_qc(plan, asset, strictness="off")

        assert result.verdict == "pass"
        assert result.checks == {}
        assert result.issues == []

    def test_lenient_passes_when_only_non_essential_issues(self, tmp_path: Path) -> None:
        # hook narration 너무 길고 duration도 범위 밖이지만 audio/visual 파일은 정상.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="hook", narration="가" * 250)
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=20.0)

        result = QCStep.gate_scene_qc(plan, asset, strictness="lenient")

        assert result.verdict == "pass"
        # 이슈는 그대로 보존되어 manifest로 흘러간다.
        assert any("Hook narration too long" in i for i in result.issues)
        assert any("Duration" in i for i in result.issues)
        # essential check는 통과 상태여야 함.
        assert result.checks["audio_ok"] is True
        assert result.checks["visual_ok"] is True

    def test_lenient_fails_when_essential_check_fails(self, tmp_path: Path) -> None:
        # 비주얼 파일이 없으면 lenient여도 fail_retry.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        plan = self._make_plan(role="body")
        asset = self._make_asset(audio_path=audio, visual_path=str(tmp_path / "no.jpg"), dur=5.0)

        result = QCStep.gate_scene_qc(plan, asset, strictness="lenient")

        assert result.verdict == "fail_retry"
        assert result.checks["visual_ok"] is False

    def test_strict_default_unchanged(self, tmp_path: Path) -> None:
        # 기본값 strict: 비-essential 이슈에도 fail_retry — 기존 동작 회귀 보호.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="hook", narration="가" * 250)
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)  # strictness 기본값

        assert result.verdict == "fail_retry"
        assert any("Hook narration too long" in i for i in result.issues)

    def test_unknown_strictness_raises(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._make_plan(role="body")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=5.0)

        with pytest.raises(ValueError, match="strictness"):
            QCStep.gate_scene_qc(plan, asset, strictness="bogus")


# ── gate4_final 추가 분기 ───────────────────────────────────────────────────


def test_gate4_final_pass_all_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _write_bytes(tmp_path / "out.mp4", 5 * 1024 * 1024)  # 5MB
    manifest = JobManifest(
        job_id="pass-1",
        topic="t",
        status="ok",
        total_duration_sec=45.0,
        failed_steps=[],
    )
    monkeypatch.setattr(
        QCStep,
        "_probe_video",
        staticmethod(lambda path: {"width": 1080, "height": 1920, "fps": 30.0}),
    )
    monkeypatch.setattr(QCStep, "_check_audio_peak", staticmethod(lambda path: -3.0))

    report = QCStep.gate4_final(manifest, output_path=out)

    assert report.verdict == GateVerdict.PASS.value
    assert report.issues == []


def test_gate4_final_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = JobManifest(
        job_id="miss-1",
        topic="t",
        status="ok",
        total_duration_sec=45.0,
        failed_steps=[],
    )
    monkeypatch.setattr(QCStep, "_probe_video", staticmethod(lambda path: None))
    monkeypatch.setattr(QCStep, "_check_audio_peak", staticmethod(lambda path: None))

    report = QCStep.gate4_final(manifest, output_path=str(tmp_path / "gone.mp4"))

    assert report.verdict == GateVerdict.HOLD.value
    assert any("Output file missing" in i for i in report.issues)


def test_gate4_final_holds_when_media_probes_are_unavailable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _write_bytes(tmp_path / "out.mp4", 5 * 1024 * 1024)
    manifest = JobManifest(
        job_id="probe-miss",
        topic="t",
        status="ok",
        total_duration_sec=45.0,
        failed_steps=[],
    )
    monkeypatch.setattr(QCStep, "_probe_video", staticmethod(lambda path: None))
    monkeypatch.setattr(QCStep, "_check_audio_peak", staticmethod(lambda path: None))

    report = QCStep.gate4_final(manifest, output_path=out)

    assert report.verdict == GateVerdict.HOLD.value
    assert report.checks["video_probe_ok"] is False
    assert report.checks["audio_peak_probe_ok"] is False
    assert any("ffprobe" in issue for issue in report.issues)
    assert any("ffmpeg" in issue for issue in report.issues)


# ── 강화된 씬별 QC: 정합성/CTA 변형/cps 회귀 테스트 ────────────────────────────


class TestSceneQCIntegrity:
    """강화된 essential 정합성 + non-essential cps + CTA 한국어 변형 회귀 보호."""

    def _plan(
        self, sid: int = 1, role: str = "body", narration: str = "이것은 충분한 길이의 나레이션 문장입니다"
    ) -> ScenePlan:
        return ScenePlan(
            scene_id=sid,
            narration_ko=narration,
            visual_prompt_en="prompt",
            target_sec=5.0,
            structure_role=role,
        )

    def _asset(self, sid: int, audio_path: str, visual_path: str, dur: float = 5.0) -> SceneAsset:
        return SceneAsset(
            scene_id=sid,
            audio_path=audio_path,
            visual_type="image",
            visual_path=visual_path,
            duration_sec=dur,
        )

    def test_visual_image_below_min_dim_fails(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        # 539x539 → 540 미만이므로 essential fail.
        visual = _write_png(tmp_path / "tiny.png", width=539, height=539)
        plan = self._plan()
        asset = self._asset(1, audio, visual)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "fail_retry"
        assert result.checks["visual_ok"] is False
        assert any("Visual dimensions" in i for i in result.issues)

    def test_visual_corrupted_bytes_fails(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        # 100바이트의 "xxxx..." — Pillow가 못 여는 파일. 기존엔 file-exists만으로 통과시켰음.
        bad_visual = _write_bytes(tmp_path / "bad.png", 100)
        plan = self._plan()
        asset = self._asset(1, audio, bad_visual)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "fail_retry"
        assert result.checks["visual_ok"] is False
        assert any("Visual image unreadable" in i for i in result.issues)

    def test_audio_duration_below_minimum_fails(self, tmp_path: Path) -> None:
        # 사이즈는 충분하지만 듀레이션이 0.2초 → TTS 트런케이션 신호로 fail.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._plan()
        asset = self._asset(1, audio, visual, dur=0.2)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "fail_retry"
        assert result.checks["audio_ok"] is False
        assert any("Audio duration" in i and "below minimum" in i for i in result.issues)

    def test_chars_per_sec_too_high_flags_truncation(self, tmp_path: Path) -> None:
        # 긴 나레이션 + 짧은 오디오 = 트런케이션 신호. 200자 / 5초 = 40 c/s.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._plan(role="body", narration="가" * 200)
        asset = self._asset(1, audio, visual, dur=5.0)

        result = QCStep.gate_scene_qc(plan, asset)

        # essential은 통과지만 strict에선 non-essential 이슈로 fail_retry
        assert result.checks["audio_ok"] is True
        assert result.checks["visual_ok"] is True
        assert result.checks["chars_per_sec_ok"] is False
        assert any("Narration/audio rate" in i for i in result.issues)
        assert result.verdict == "fail_retry"

    def test_chars_per_sec_lenient_passes_when_essentials_ok(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._plan(role="body", narration="가" * 200)
        asset = self._asset(1, audio, visual, dur=5.0)

        result = QCStep.gate_scene_qc(plan, asset, strictness="lenient")

        assert result.verdict == "pass"
        assert result.checks["chars_per_sec_ok"] is False
        assert any("Narration/audio rate" in i for i in result.issues)

    @pytest.mark.parametrize(
        "forbidden_phrase",
        ["팔로우 부탁해요", "이 영상을 공유해", "댓글로 알려주세요", "subscribe to our channel"],
    )
    def test_closing_korean_cta_variants_are_caught(self, tmp_path: Path, forbidden_phrase: str) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._plan(role="closing", narration=forbidden_phrase)
        asset = self._asset(1, audio, visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["no_cta_words"] is False
        assert any("forbidden CTA word" in i for i in result.issues)
        assert result.verdict == "fail_retry"

    def test_cta_role_also_subject_to_forbidden_list(self, tmp_path: Path) -> None:
        # closing뿐 아니라 cta 역할도 CTA 금지어 체크 대상.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        plan = self._plan(role="cta", narration="구독해주세요")
        asset = self._asset(1, audio, visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["no_cta_words"] is False
        assert any("forbidden CTA word" in i for i in result.issues)

    def test_full_pass_with_realistic_assets(self, tmp_path: Path) -> None:
        # essential + non-essential 모두 통과하는 케이스 — strict에서 pass.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png", width=1080, height=1920)
        plan = self._plan(role="body", narration="이 씬은 사용자에게 적절한 페이스로 전달되는 문장입니다")
        asset = self._asset(1, audio, visual, dur=5.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "pass"
        assert result.issues == []
        assert result.checks["audio_ok"] is True
        assert result.checks["visual_ok"] is True
        assert result.checks["duration_ok"] is True
        assert result.checks["chars_per_sec_ok"] is True


# ── 씬별 RMS 오디오 (audio_mean_volume_ok) ──────────────────────────────────


def _write_png_color(path: Path, color: tuple[int, int, int], size: tuple[int, int] = (720, 1280)) -> str:
    """지정 색상의 PNG. visual continuity 테스트용 — 평균 RGB 가 정확히 ``color`` 가 된다."""
    from PIL import Image

    Image.new("RGB", size, color=color).save(path, "PNG")
    return str(path)


class TestSceneQCAudioMeanVolume:
    """T-288 FEATURE.md non-goal #2: 씬별 RMS 오디오. 파일 존재만으로는
    silent TTS 를 못 잡는다 — mean_volume 으로 잡는다."""

    def _plan(self) -> ScenePlan:
        return ScenePlan(
            scene_id=1,
            narration_ko="씬별 RMS 회귀 보호용 나레이션",
            visual_prompt_en="prompt",
            target_sec=5.0,
            structure_role="body",
        )

    def _asset(self, audio_path: str, visual_path: str, dur: float = 5.0) -> SceneAsset:
        return SceneAsset(
            scene_id=1,
            audio_path=audio_path,
            visual_type="image",
            visual_path=visual_path,
            duration_sec=dur,
        )

    def test_mean_volume_in_range_passes(self, tmp_path: Path, monkeypatch) -> None:
        # -20 dBFS — 일반 TTS-1-HD 출력 범위 안. ok=True, issue 없음.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        monkeypatch.setattr(
            QCStep,
            "_run_volumedetect",
            staticmethod(lambda path, **kw: {"mean_db": -20.0, "max_db": -5.0}),
        )

        result = QCStep.gate_scene_qc(self._plan(), self._asset(audio, visual))

        assert result.checks["audio_mean_volume_ok"] is True
        assert not any("mean volume" in i.lower() for i in result.issues)

    def test_mean_volume_too_quiet_flags(self, tmp_path: Path, monkeypatch) -> None:
        # -45 dBFS — silent TTS 신호. ok=False + "silent" 키워드 issue.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        monkeypatch.setattr(
            QCStep,
            "_run_volumedetect",
            staticmethod(lambda path, **kw: {"mean_db": -45.0}),
        )

        result = QCStep.gate_scene_qc(self._plan(), self._asset(audio, visual))

        assert result.checks["audio_mean_volume_ok"] is False
        assert any("silent" in i.lower() for i in result.issues)
        # strict 모드: 이슈가 있으니 fail_retry — regen 트리거 의도.
        assert result.verdict == "fail_retry"

    def test_mean_volume_clipping_flags(self, tmp_path: Path, monkeypatch) -> None:
        # -0.1 dBFS — clipping 가까움. ok=False + "clipping" 키워드.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        monkeypatch.setattr(
            QCStep,
            "_run_volumedetect",
            staticmethod(lambda path, **kw: {"mean_db": -0.1}),
        )

        result = QCStep.gate_scene_qc(self._plan(), self._asset(audio, visual))

        assert result.checks["audio_mean_volume_ok"] is False
        assert any("clipping" in i.lower() for i in result.issues)

    def test_mean_volume_ffmpeg_unavailable_silently_skipped(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        # _run_volumedetect 가 None 을 반환 (ffmpeg 미설치/실패) → 가짜 fail 만들지 않는다.
        # checks dict 에 audio_mean_volume_ok 자체가 들어가지 않아야 한다.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        monkeypatch.setattr(
            QCStep,
            "_run_volumedetect",
            staticmethod(lambda path, **kw: None),
        )

        result = QCStep.gate_scene_qc(self._plan(), self._asset(audio, visual))

        assert "audio_mean_volume_ok" not in result.checks
        assert not any("mean volume" in i.lower() for i in result.issues)

    def test_mean_volume_skipped_when_essential_audio_fails(
        self,
        tmp_path: Path,
        monkeypatch,
    ) -> None:
        # essential audio_ok 가 깨졌으면 volumedetect 자체를 안 부른다 (비용 절약).
        # 미설정 sentinel 로 검증.
        called: list[str] = []
        monkeypatch.setattr(
            QCStep,
            "_run_volumedetect",
            staticmethod(lambda path, **kw: called.append(path) or {"mean_db": -20.0}),
        )
        # 50 byte → audio_ok essential 실패
        audio = _write_bytes(tmp_path / "a.wav", 50)
        visual = _write_png(tmp_path / "v.png")

        result = QCStep.gate_scene_qc(self._plan(), self._asset(audio, visual))

        assert result.checks["audio_ok"] is False
        assert "audio_mean_volume_ok" not in result.checks
        assert called == []  # ffmpeg 호출 자체가 없어야 한다


# ── 시각 연속성 (visual_continuity_ok) ──────────────────────────────────────


class TestSceneQCVisualContinuity:
    """T-288 FEATURE.md non-goal #1: abrupt transition 감지. 씬-씬 평균 RGB
    거리가 임계값 초과하면 issues 로 표면화."""

    def _plan(self, sid: int = 2) -> ScenePlan:
        return ScenePlan(
            scene_id=sid,
            narration_ko="씬별 연속성 회귀 보호용 나레이션",
            visual_prompt_en="prompt",
            target_sec=5.0,
            structure_role="body",
        )

    def _img_asset(self, sid: int, audio_path: str, visual_path: str) -> SceneAsset:
        return SceneAsset(
            scene_id=sid,
            audio_path=audio_path,
            visual_type="image",
            visual_path=visual_path,
            duration_sec=5.0,
        )

    def _video_asset(self, sid: int, audio_path: str, visual_path: str) -> SceneAsset:
        return SceneAsset(
            scene_id=sid,
            audio_path=audio_path,
            visual_type="video",
            visual_path=visual_path,
            duration_sec=5.0,
        )

    def test_first_scene_no_prev_skipped(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_png(tmp_path / "v.png")
        # prev_asset=None → 연속성 체크 skip (key 자체가 안 들어감)
        result = QCStep.gate_scene_qc(
            self._plan(sid=1),
            self._img_asset(1, audio, visual),
            prev_asset=None,
        )
        assert "visual_continuity_ok" not in result.checks

    def test_similar_scenes_pass(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        # 둘 다 동일한 어두운 회색 톤 — 평균 RGB 거리 0 근처
        prev_v = _write_png_color(tmp_path / "prev.png", color=(40, 40, 40))
        curr_v = _write_png_color(tmp_path / "curr.png", color=(50, 50, 50))
        prev = self._img_asset(1, audio, prev_v)
        curr = self._img_asset(2, audio, curr_v)

        result = QCStep.gate_scene_qc(self._plan(), curr, prev_asset=prev)

        assert result.checks["visual_continuity_ok"] is True
        assert not any("abrupt transition" in i for i in result.issues)

    def test_abrupt_transition_flags(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        # 어두운 검정 vs 밝은 핑크 — RGB 거리 ~ sqrt(255^2 + 192^2 + 203^2) ≈ 379
        prev_v = _write_png_color(tmp_path / "prev.png", color=(0, 0, 0))
        curr_v = _write_png_color(tmp_path / "curr.png", color=(255, 192, 203))
        prev = self._img_asset(1, audio, prev_v)
        curr = self._img_asset(2, audio, curr_v)

        result = QCStep.gate_scene_qc(self._plan(), curr, prev_asset=prev)

        assert result.checks["visual_continuity_ok"] is False
        assert any("abrupt transition" in i.lower() for i in result.issues)

    def test_video_prev_asset_silently_passes(self, tmp_path: Path) -> None:
        # prev 가 video 면 첫 프레임 추출 비용 들이지 않고 자연 통과. 가짜 fail 막음.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        prev_v = str(tmp_path / "prev.mp4")  # 실제 파일 만들 필요 없음 (skip path)
        curr_v = _write_png(tmp_path / "curr.png")
        prev = self._video_asset(1, audio, prev_v)
        curr = self._img_asset(2, audio, curr_v)

        result = QCStep.gate_scene_qc(self._plan(), curr, prev_asset=prev)

        # skip 경로: ok=True, issue 없음 (False positive 방지)
        assert result.checks["visual_continuity_ok"] is True
        assert not any("abrupt transition" in i for i in result.issues)

    def test_skipped_when_essential_visual_fails(self, tmp_path: Path) -> None:
        # essential visual_ok 가 깨졌으면 연속성 체크 자체를 안 돌린다.
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        prev_v = _write_png_color(tmp_path / "prev.png", color=(40, 40, 40))
        # 깨진 visual — 100바이트 garbage, Pillow 디코드 실패 → visual_ok=False
        bad_curr = _write_bytes(tmp_path / "curr.png", 100)
        prev = self._img_asset(1, audio, prev_v)
        curr = self._img_asset(2, audio, bad_curr)

        result = QCStep.gate_scene_qc(self._plan(), curr, prev_asset=prev)

        assert result.checks["visual_ok"] is False
        assert "visual_continuity_ok" not in result.checks


# ── SemanticQCStep: LLM 기반 씬-씬 의미 QC (T-288 non-goal #3) ───────────────


class _StubLLMRouter:
    """SemanticQCStep 테스트용 generate_json stub."""

    def __init__(self, *, response=None, raise_exc=None):
        self.response = response
        self.raise_exc = raise_exc
        self.calls: list[dict] = []

    def generate_json(self, *, system_prompt, user_prompt, temperature=0.7):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "temperature": temperature,
            }
        )
        if self.raise_exc is not None:
            raise self.raise_exc
        return self.response


class TestSemanticQCStep:
    """SemanticQCStep: post-asset LLM judge of scene flow + tone consistency."""

    def _plans(self) -> list[ScenePlan]:
        return [
            ScenePlan(scene_id=1, narration_ko="첫 단서", visual_prompt_en="p1", target_sec=5.0, structure_role="hook"),
            ScenePlan(
                scene_id=2, narration_ko="이어지는 결", visual_prompt_en="p2", target_sec=5.0, structure_role="body"
            ),
            ScenePlan(
                scene_id=3,
                narration_ko="조용한 여운",
                visual_prompt_en="p3",
                target_sec=5.0,
                structure_role="closing",
            ),
        ]

    def test_high_scores_yield_pass_and_full_manifest(self) -> None:
        stub = _StubLLMRouter(
            response={
                "scene_flow_score": 9,
                "tone_consistency_score": 8,
                "overall_score": 9,
                "weak_transitions": [],
                "feedback": "흐름과 톤 모두 일관됨",
            }
        )
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=self._plans())

        assert result.verdict == "pass"
        assert result.scene_flow_score == 9
        assert result.tone_consistency_score == 8
        assert result.overall_score == 9
        assert result.weak_transitions == []
        assert "일관" in result.feedback
        # 프롬프트가 실제 씬 narration 을 포함하는지 확인 — generic 호출 방어
        assert len(stub.calls) == 1
        assert "첫 단서" in stub.calls[0]["user_prompt"]
        assert "Scene 3 [closing]" in stub.calls[0]["user_prompt"]

    def test_low_scene_flow_degraded(self) -> None:
        stub = _StubLLMRouter(
            response={
                "scene_flow_score": 4,
                "tone_consistency_score": 8,
                "overall_score": 5,
                "weak_transitions": [
                    {"from": 2, "to": 3, "reason": "절벽 같은 단절"},
                ],
                "feedback": "씬 2→3 단절",
            }
        )
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=self._plans())

        assert result.verdict == "degraded"
        assert result.scene_flow_score == 4
        assert len(result.weak_transitions) == 1
        assert result.weak_transitions[0]["from"] == 2
        assert result.weak_transitions[0]["to"] == 3

    def test_low_tone_consistency_degraded(self) -> None:
        # tone 만 떨어져도 두 차원 중 최소값이 임계값 미만이면 degraded.
        stub = _StubLLMRouter(
            response={
                "scene_flow_score": 9,
                "tone_consistency_score": 3,
                "overall_score": 6,
                "weak_transitions": [],
                "feedback": "톤 일관성 부족",
            }
        )
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=self._plans())

        assert result.verdict == "degraded"
        assert result.tone_consistency_score == 3

    def test_llm_exception_returns_error_verdict(self) -> None:
        # LLM 예외는 catch — opt-in 기능이 영상 ship 을 막으면 안 됨.
        stub = _StubLLMRouter(raise_exc=RuntimeError("rate limit"))
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=self._plans())

        assert result.verdict == "error"
        assert "rate limit" not in result.feedback  # 클래스명만 노출, 메시지는 로그로만
        assert "RuntimeError" in result.feedback

    def test_non_dict_response_returns_error(self) -> None:
        stub = _StubLLMRouter(response="not a dict")
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=self._plans())

        assert result.verdict == "error"
        assert "non-dict" in result.feedback

    def test_empty_scene_plans_short_circuits(self) -> None:
        stub = _StubLLMRouter(response={"scene_flow_score": 10})
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=[])

        assert result.verdict == "error"
        # LLM 자체를 부르지 않는다 — 비용 절감 + 의미 없는 채점 방지.
        assert stub.calls == []

    def test_missing_scores_coerced_to_zero_and_fail(self) -> None:
        # LLM 이 키를 누락하거나 None 을 주면 모두 0 으로 강제 → degraded.
        stub = _StubLLMRouter(
            response={"feedback": "incomplete response", "weak_transitions": "not a list"},
        )
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=self._plans())

        assert result.verdict == "degraded"
        assert result.scene_flow_score == 0
        assert result.tone_consistency_score == 0
        # weak_transitions 가 list 가 아닐 때 빈 리스트로 정리되어야 함
        assert result.weak_transitions == []

    def test_structure_outline_included_in_prompt_when_provided(self) -> None:
        stub = _StubLLMRouter(
            response={
                "scene_flow_score": 8,
                "tone_consistency_score": 8,
                "overall_score": 8,
                "weak_transitions": [],
                "feedback": "ok",
            }
        )
        step = SemanticQCStep(llm_router=stub, min_score=6)
        outline = StructureOutline(
            scenes=[
                SceneOutline(1, "hook", "Grab attention", "Dark bg", "curiosity", 5.0),
                SceneOutline(2, "body", "Build the thought", "Soft mood", "noticing", 5.0),
                SceneOutline(3, "closing", "Leave a lingering thought", "Wide sky", "quiet", 5.0),
            ],
            total_estimated_sec=15.0,
        )

        result = step.run(scene_plans=self._plans(), structure_outline=outline)

        assert result.verdict == "pass"
        prompt = stub.calls[0]["user_prompt"]
        assert "INTENDED STRUCTURE" in prompt
        assert "Grab attention" in prompt
        assert "lingering thought" in prompt

    def test_string_score_coerced_to_int(self) -> None:
        # 일부 LLM 은 점수를 "7" 처럼 문자열로 줄 수 있음 — 강제 변환.
        stub = _StubLLMRouter(
            response={
                "scene_flow_score": "7",
                "tone_consistency_score": "8.4",  # float string
                "overall_score": "7",
                "weak_transitions": [],
                "feedback": "ok",
            }
        )
        step = SemanticQCStep(llm_router=stub, min_score=6)

        result = step.run(scene_plans=self._plans())

        assert result.scene_flow_score == 7
        assert result.tone_consistency_score == 8
        assert result.verdict == "pass"
