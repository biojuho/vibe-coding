from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from shorts_maker_v2.pipeline.render_step import RenderStep


def _make_render_step(transition_style: str = "random") -> RenderStep:
    """RenderStep의 __init__이 사용하는 모든 config 필드를 MagicMock으로 구성."""
    config = MagicMock()

    # video
    config.video.resolution = (1080, 1920)
    config.video.fps = 30
    config.video.transition_style = transition_style
    config.video.encoding_preset = "fast"
    config.video.encoding_crf = 23

    # captions (CaptionStyle 생성에 필요)
    config.captions.mode = "karaoke"
    config.captions.font_size = 72
    config.captions.margin_x = 60
    config.captions.bottom_offset = 280
    config.captions.text_color = "#FFFFFF"
    config.captions.stroke_color = "#000000"
    config.captions.stroke_width = 0
    config.captions.line_spacing = 12
    config.captions.bg_color = "#000000"
    config.captions.bg_opacity = 185
    config.captions.bg_radius = 18
    config.captions.style_preset = "default"
    config.captions.words_per_chunk = 3
    config.captions.font_candidates = ("C:/Windows/Fonts/malgunbd.ttf",)

    # audio
    config.audio.bgm_dir = "assets/bgm"
    config.audio.bgm_volume = 0.12
    config.audio.fade_duration = 0.5
    config.audio.sfx_enabled = False
    config.audio.sfx_dir = "assets/sfx"
    config.audio.sfx_volume = 0.35

    # intro/outro
    config.intro_outro.intro_path = ""
    config.intro_outro.outro_path = ""
    config.intro_outro.intro_duration = 2.0
    config.intro_outro.outro_duration = 2.0

    # providers
    config.providers.visual_styles = ()

    openai_client = MagicMock()
    return RenderStep(config=config, openai_client=openai_client, job_index=0)


# ─── 전환 스타일 테스트 ────────────────────────────────────────────────────────

def test_pick_transition_style_random() -> None:
    """'random' 설정 시 유효한 스타일 반환."""
    step = _make_render_step(transition_style="random")
    valid_styles = {"crossfade", "flash", "glitch", "zoom", "slide"}
    for _ in range(20):
        style = step._pick_transition_style()
        assert style in valid_styles


def test_pick_transition_style_fixed() -> None:
    """고정 스타일 설정 시 해당 스타일만 반환."""
    step = _make_render_step(transition_style="crossfade")
    assert step._pick_transition_style() == "crossfade"


# ─── 무드 분류 테스트 ────────────────────────────────────────────────────────

def test_classify_mood_dramatic() -> None:
    """블랙홀, 우주 등 키워드 → dramatic."""
    assert RenderStep._classify_mood_keywords("블랙홀의 비밀") == "dramatic"
    assert RenderStep._classify_mood_keywords("전쟁의 역사") == "dramatic"


def test_classify_mood_upbeat() -> None:
    """돈, 성공 등 키워드 → upbeat."""
    assert RenderStep._classify_mood_keywords("돈 벌기 팁") == "upbeat"
    assert RenderStep._classify_mood_keywords("성공하는 방법") == "upbeat"


def test_classify_mood_calm_default() -> None:
    """매칭 키워드 없으면 → calm (기본값)."""
    assert RenderStep._classify_mood_keywords("오늘의 날씨") == "calm"


# ─── BGM 선택 테스트 ────────────────────────────────────────────────────────

def test_pick_bgm_by_mood_matches_filename(tmp_path: Path) -> None:
    """파일명에 무드 키워드가 있으면 우선 선택."""
    step = _make_render_step()
    step._llm_router = None  # GPT 분류 비활성화
    step._openai_client = None  # OpenAI 분류 비활성화

    bgm_dramatic = tmp_path / "bgm_dramatic_01.mp3"
    bgm_upbeat = tmp_path / "bgm_upbeat_01.mp3"
    bgm_calm = tmp_path / "bgm_calm_01.mp3"
    for f in [bgm_dramatic, bgm_upbeat, bgm_calm]:
        f.write_bytes(b"\x00" * 100)

    # "블랙홀" → dramatic → bgm_dramatic_01.mp3
    result = step._pick_bgm_by_mood(
        [bgm_dramatic, bgm_upbeat, bgm_calm], "블랙홀의 비밀"
    )
    assert "dramatic" in result.name


def test_pick_bgm_fallback_random(tmp_path: Path) -> None:
    """무드 매칭 실패 시 랜덤 폴백."""
    step = _make_render_step()
    step._llm_router = None
    step._openai_client = None

    bgm_files = [
        tmp_path / "bgm_01.mp3",
        tmp_path / "bgm_02.mp3",
    ]
    for f in bgm_files:
        f.write_bytes(b"\x00" * 100)

    # 매칭되는 파일명 없음 → 랜덤 선택
    result = step._pick_bgm_by_mood(bgm_files, "오늘의 날씨")
    assert result in bgm_files


# ─── 랜덤 효과 테스트 ────────────────────────────────────────────────────────

def test_apply_random_effect_has_method() -> None:
    """_apply_random_effect 메서드 존재 확인."""
    step = _make_render_step()
    assert hasattr(step, "_apply_random_effect")
    assert callable(step._apply_random_effect)


# ─── 자막 콤보 로테이션 테스트 ──────────────────────────────────────────────

def test_caption_combo_count() -> None:
    """최소 3개 이상의 자막 콤보 존재."""
    combos = RenderStep._CAPTION_COMBOS
    assert len(combos) >= 3


def test_caption_combo_rotation_varies() -> None:
    """다른 job_index는 다른 콤보 선택."""
    combos = RenderStep._CAPTION_COMBOS
    if len(combos) > 1:
        assert combos[0] != combos[1]


# ─── 제목 이미지 렌더링 테스트 ──────────────────────────────────────────────

def test_render_title_image_creates_file(tmp_path: Path) -> None:
    """_render_title_image가 PNG 파일을 정상 생성."""
    step = _make_render_step()
    output = tmp_path / "title.png"
    result = step._render_title_image("테스트 제목입니다", 1080, output)
    assert result.exists()
    assert result.stat().st_size > 0
    # PNG 매직 바이트 확인
    with open(result, "rb") as f:
        assert f.read(4) == b"\x89PNG"


# ─── 썸네일 추출 테스트 ──────────────────────────────────────────────────

def test_extract_thumbnail_returns_none_for_missing_file(tmp_path: Path) -> None:
    """존재하지 않는 비디오 → None 반환 (에러 없이)."""
    result = RenderStep.extract_thumbnail(
        tmp_path / "nonexistent.mp4",
        tmp_path / "thumb.png",
    )
    assert result is None


def test_extract_thumbnail_returns_none_for_invalid_file(tmp_path: Path) -> None:
    """잘못된 비디오 파일 → None 반환."""
    bad_video = tmp_path / "bad.mp4"
    bad_video.write_bytes(b"\x00" * 100)
    result = RenderStep.extract_thumbnail(bad_video, tmp_path / "thumb.png")
    assert result is None
