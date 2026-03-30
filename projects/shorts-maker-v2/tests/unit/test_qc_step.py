from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from shorts_maker_v2.models import GateVerdict, JobManifest, SceneAsset, ScenePlan
from shorts_maker_v2.pipeline.qc_step import QCStep


def _write_bytes(path: Path, size: int) -> str:
    path.write_bytes(b"x" * size)
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
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan(role="body")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=5.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "pass"
        assert result.issues == []
        assert result.checks["audio_ok"] is True
        assert result.checks["visual_ok"] is True
        assert result.checks["duration_ok"] is True

    def test_audio_missing(self, tmp_path: Path) -> None:
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan()
        asset = self._make_asset(audio_path=str(tmp_path / "missing.wav"), visual_path=visual)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.verdict == "fail_retry"
        assert result.checks["audio_ok"] is False
        assert any("Audio file missing" in i for i in result.issues)

    def test_audio_too_small(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "tiny.wav", 50)
        visual = _write_bytes(tmp_path / "v.jpg", 100)
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
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan(role="hook")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=20.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["duration_ok"] is False
        assert any("Duration" in i for i in result.issues)

    def test_hook_concise_check_pass(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan(role="hook", narration="짧은 훅")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["hook_concise"] is True

    def test_hook_too_long(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan(role="hook", narration="가" * 201)
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["hook_concise"] is False
        assert any("Hook narration too long" in i for i in result.issues)

    def test_closing_cta_forbidden_words(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan(role="closing", narration="구독과 좋아요 부탁드립니다")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["no_cta_words"] is False
        assert any("forbidden CTA word" in i for i in result.issues)

    def test_closing_no_cta_words(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan(role="closing", narration="다음에 또 만나요")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=4.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["no_cta_words"] is True

    def test_unknown_role_uses_wide_duration_range(self, tmp_path: Path) -> None:
        audio = _write_bytes(tmp_path / "a.wav", 20_000)
        visual = _write_bytes(tmp_path / "v.jpg", 100)
        plan = self._make_plan(role="unknown_role")
        asset = self._make_asset(audio_path=audio, visual_path=visual, dur=14.0)

        result = QCStep.gate_scene_qc(plan, asset)

        assert result.checks["duration_ok"] is True


# ── gate4_final 추가 분기 ───────────────────────────────────────────────────


def test_gate4_final_pass_all_checks(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = _write_bytes(tmp_path / "out.mp4", 5 * 1024 * 1024)  # 5MB
    manifest = JobManifest(
        job_id="pass-1", topic="t", status="ok",
        total_duration_sec=45.0, failed_steps=[],
    )
    monkeypatch.setattr(
        QCStep, "_probe_video",
        staticmethod(lambda path: {"width": 1080, "height": 1920, "fps": 30.0}),
    )
    monkeypatch.setattr(QCStep, "_check_audio_peak", staticmethod(lambda path: -3.0))

    report = QCStep.gate4_final(manifest, output_path=out)

    assert report.verdict == GateVerdict.PASS.value
    assert report.issues == []


def test_gate4_final_missing_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    manifest = JobManifest(
        job_id="miss-1", topic="t", status="ok",
        total_duration_sec=45.0, failed_steps=[],
    )
    monkeypatch.setattr(QCStep, "_probe_video", staticmethod(lambda path: None))
    monkeypatch.setattr(QCStep, "_check_audio_peak", staticmethod(lambda path: None))

    report = QCStep.gate4_final(manifest, output_path=str(tmp_path / "gone.mp4"))

    assert report.verdict == GateVerdict.HOLD.value
    assert any("Output file missing" in i for i in report.issues)
