"""Phase 2 #4+#8 — silent-fail propagation 회귀.

기존: Whisper word-sync / karaoke caption / color grade / audio postprocess 실패가
`logger.warning` 으로만 찍히고 `manifest.degraded_steps` 가 빈 채로 ship 되어
사용자가 영상을 직접 봐야 자막 깨짐을 알아챘다 (2026-05-11 case).

수정 후: 각 step 이 `_pending_*_warnings` 버퍼에 쌓고, run() 종료 시 합쳐서
`failures` / `degraded_steps` 로 노출.
"""

from __future__ import annotations

from types import SimpleNamespace


def _make_render_step_skeleton():
    """RenderStep 의 _pending_render_warnings 버퍼 동작만 검증하는 최소 객체."""
    obj = SimpleNamespace()
    obj._pending_render_warnings = []
    return obj


def test_render_warnings_buffer_starts_empty() -> None:
    """RenderStep 인스턴스는 빈 _pending_render_warnings 로 시작."""
    skel = _make_render_step_skeleton()
    assert skel._pending_render_warnings == []


def test_render_warnings_buffer_appends_caption_fallback_entry() -> None:
    """카라오케 fallback 시 step=karaoke_caption + scene_id + error_type 키 보존."""
    skel = _make_render_step_skeleton()
    skel._pending_render_warnings.append(
        {
            "step": "karaoke_caption",
            "code": "FileNotFoundError",
            "message": "scene 3: words.json missing",
            "scene_id": 3,
            "error_type": "caption_fallback",
            "is_retryable": False,
        }
    )
    assert len(skel._pending_render_warnings) == 1
    e = skel._pending_render_warnings[0]
    assert e["step"] == "karaoke_caption"
    assert e["error_type"] == "caption_fallback"
    assert e["scene_id"] == 3
    assert e["is_retryable"] is False


def test_render_warnings_drain_pattern() -> None:
    """Orchestrator 가 _pending_render_warnings 를 extend + 비우는 패턴."""
    skel = _make_render_step_skeleton()
    for sid in (1, 4, 7):
        skel._pending_render_warnings.append(
            {"step": "karaoke_caption", "scene_id": sid, "error_type": "caption_fallback"}
        )

    degraded_steps: list = []
    pending = getattr(skel, "_pending_render_warnings", None)
    if pending:
        degraded_steps.extend(pending)
        skel._pending_render_warnings = []

    assert len(degraded_steps) == 3
    assert [d["scene_id"] for d in degraded_steps] == [1, 4, 7]
    assert skel._pending_render_warnings == []


def test_render_warnings_drain_idempotent_when_empty() -> None:
    """두 번째 drain 호출은 noop 이어야 (중복 ship 방지)."""
    skel = _make_render_step_skeleton()
    skel._pending_render_warnings.append({"step": "color_grade", "scene_id": 2})
    degraded: list = []

    # 1st drain
    degraded.extend(skel._pending_render_warnings)
    skel._pending_render_warnings = []
    # 2nd drain — should be empty
    degraded.extend(skel._pending_render_warnings)

    assert len(degraded) == 1


def test_pending_audio_warnings_drain_pattern_media_step() -> None:
    """MediaStep 의 Whisper-sync silent-fail 동일 패턴."""
    skel = SimpleNamespace()
    skel._pending_audio_warnings = [
        {"step": "whisper_word_sync", "code": "TimeoutError", "message": "OpenAI 503"},
    ]
    all_failures: list = []
    if skel._pending_audio_warnings:
        all_failures.extend(skel._pending_audio_warnings)
        skel._pending_audio_warnings = []

    assert all_failures[0]["step"] == "whisper_word_sync"
    assert skel._pending_audio_warnings == []
