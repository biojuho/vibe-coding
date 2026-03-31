"""scaffold.py — 새 채널을 5분 안에 추가하는 스캐폴딩 도구.

Usage:
    python -m ShortsFactory.scaffold --name cooking --display "쿡슈머" --category "요리"

    또는 코드에서:
    from ShortsFactory.scaffold import scaffold_channel
    scaffold_channel("cooking", display_name="쿡슈머", category="요리")
"""

from __future__ import annotations

import logging
import textwrap
from pathlib import Path

logger = logging.getLogger("ShortsFactory.scaffold")

_PROJECT = Path(__file__).resolve().parent.parent
_PROFILES = _PROJECT / "channel_profiles.yaml"
_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
_CAPTION_PILLOW = _PROJECT / "src" / "shorts_maker_v2" / "render" / "caption_pillow.py"


# 기본 팔레트 프리셋 (사용자가 커스텀 가능)
DEFAULT_PALETTES = {
    "warm": {"primary": "#FF6B35", "secondary": "#F59E0B", "accent": "#EF4444", "bg": "#1A0A05"},
    "cool": {"primary": "#06B6D4", "secondary": "#3B82F6", "accent": "#8B5CF6", "bg": "#0A1420"},
    "earth": {"primary": "#8B6914", "secondary": "#D4A574", "accent": "#6B8E23", "bg": "#1A1408"},
    "neon": {"primary": "#00FF88", "secondary": "#00D4FF", "accent": "#FF00FF", "bg": "#0A0E1A"},
    "soft": {"primary": "#E879F9", "secondary": "#FB7185", "accent": "#F59E0B", "bg": "#1A0A1E"},
}


def _validate_text_field(value: str, field_name: str, max_len: int = 50) -> str:
    """문자열 필드 검증: 길이 제한 + YAML 특수문자 방지.

    Args:
        value: 검증 대상
        field_name: 오류 메시지용 필드명
        max_len: 최대 길이 (기본 50)

    Returns:
        검증 통과한 원본 문자열

    Raises:
        ValueError: 검증 실패 시
    """
    import re as _re

    if not value or not value.strip():
        raise ValueError(f"{field_name} must not be empty or whitespace-only.")
    value = value.strip()
    if len(value) > max_len:
        raise ValueError(f"{field_name} too long ({len(value)} chars). Max: {max_len}.")
    # YAML injection 방지: 작은/큰따옴표 쌍 불일치, 백슬래시 시퀀스, 제어문자 차단
    _FORBIDDEN = _re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\\`]")
    if _FORBIDDEN.search(value):
        raise ValueError(f"{field_name} contains forbidden characters (control chars or backslash).")
    return value


def scaffold_channel(
    channel_id: str,
    *,
    display_name: str = "",
    category: str = "",
    palette_style: str = "cool",
    palette: dict | None = None,
    first_template: str = "countdown",
) -> dict[str, str]:
    """새 채널을 스캐폴딩합니다.

    Args:
        channel_id: 채널 ID (예: "cooking")
        display_name: 표시 이름 (예: "쿡슈머")
        category: 카테고리 (예: "요리/레시피")
        palette_style: 팔레트 스타일 (warm/cool/earth/neon/soft)
        palette: 커스텀 팔레트 (지정 시 palette_style 무시)
        first_template: 첫 템플릿 유형 (countdown/listicle/quiz/compare)

    Returns:
        생성된 파일 경로 딕셔너리
    """
    import re as _re

    # --- 입력 검증 ---
    # 1) channel_id: 소문자 영숫자 + 언더스코어, 2~31자, 문자로 시작
    if not _re.match(r"^[a-z][a-z0-9_]{1,30}$", channel_id):
        raise ValueError(
            f"Invalid channel_id '{channel_id}'. "
            "Must be lowercase alphanumeric + underscores, 2-31 chars, start with letter."
        )

    # 2) display_name / category: 빈 값이면 자동 생성, 지정되면 검증
    if not display_name:
        display_name = channel_id.replace("_", " ").title()
    else:
        display_name = _validate_text_field(display_name, "display_name", max_len=50)

    category = display_name if not category else _validate_text_field(category, "category", max_len=50)

    # 3) palette_style: 허용 목록 검증
    if palette is None and palette_style not in DEFAULT_PALETTES:
        raise ValueError(
            f"Invalid palette_style '{palette_style}'. Must be one of: {', '.join(sorted(DEFAULT_PALETTES.keys()))}"
        )

    # 4) first_template: 허용 목록 검증
    _ALLOWED_TEMPLATES = {"countdown", "listicle", "quiz", "compare"}
    if first_template not in _ALLOWED_TEMPLATES:
        raise ValueError(
            f"Invalid first_template '{first_template}'. Must be one of: {', '.join(sorted(_ALLOWED_TEMPLATES))}"
        )

    pal = palette or DEFAULT_PALETTES.get(palette_style, DEFAULT_PALETTES["cool"])
    caption_style = f"{channel_id}_style"

    created = {}

    # 1. channel_profiles.yaml에 추가
    profile_block = _build_profile_yaml(channel_id, display_name, category, pal, caption_style)
    _append_to_profiles(profile_block)
    created["channel_profiles.yaml"] = str(_PROFILES)
    logger.info(f"[1/4] channel_profiles.yaml updated: {channel_id}")

    # 2. 첫 템플릿 생성
    tmpl_file = _create_first_template(channel_id, display_name, first_template)
    created["template"] = str(tmpl_file)
    logger.info(f"[2/4] Template created: {tmpl_file.name}")

    # 3. __init__.py에 자동 등록
    cls_name = f"{channel_id.title().replace('_', '')}CountdownTemplate"
    _register_in_init(channel_id, cls_name)
    created["registry"] = str(_TEMPLATES_DIR / "__init__.py")
    logger.info(f"[3/4] Auto-registered in __init__.py: {cls_name}")

    # 4. 가이드 출력
    guide = _generate_guide(channel_id, display_name, caption_style, pal)
    created["guide"] = guide
    logger.info(f"[4/4] Scaffold complete for '{channel_id}'!")

    return created


def _build_profile_yaml(
    channel_id: str,
    display_name: str,
    category: str,
    palette: dict,
    caption_style: str,
) -> str:
    """channel_profiles.yaml에 추가할 YAML 블록."""
    # display_name, category는 이미 _validate_text_field로 검증됨
    return textwrap.dedent(f"""
  # --- {display_name} ---
  {channel_id}:
    display_name: "{display_name}"
    youtube_url: ""
    category: "{category}"
    notion_channel_name: "{category}"
    tts_voice: "ko-KR-HyunsuNeural"
    tts_speed: 1.05
    tts_voice_roles:
      hook: ko-KR-GookMinNeural
      body: ko-KR-HyunsuNeural
      cta: ko-KR-BongJinNeural
    visual_styles:
      - "Clean modern aesthetic, minimal design, {category} theme, 4K"
    target_duration_sec: 35
    target_chars: "300-340"
    hook_pattern: "shocking_stat"
    structure_presets:
      - listicle
      - countdown
    default_structure: "listicle"
    persona_channel_context: |
      채널: {display_name} ({category} 전문 숏츠)
      타겟 시청자: 20-40대 관심층
      톤: 전문적이면서 친근한
    bgm_energy: "medium"
    caption_style: "{caption_style}"
    caption_combo: ["{caption_style}", "{caption_style}", "{caption_style}"]
    highlight_keywords: []
    highlight_color: "{palette["primary"]}"
    palette: {{primary: "{palette["primary"]}", secondary: "{palette["secondary"]}", accent: "{palette["accent"]}", bg: "{palette["bg"]}"}}
    font: {{title: "NanumGothicBold", body: "NanumGothic"}}
    hook_style: "clean_popup"
    transition: "clean_slide"
    disclaimer: false
    intro_path: "assets/intros/{channel_id}_intro.png"
    intro_duration: 2.0
""")


def _append_to_profiles(block: str):
    """channel_profiles.yaml 끝에 블록 추가."""
    with open(_PROFILES, "a", encoding="utf-8") as f:
        f.write(block)


def _create_first_template(channel_id: str, display_name: str, template_type: str) -> Path:
    """첫 번째 템플릿 파일 생성 (CountdownMixin 기반)."""
    cls_name = f"{channel_id.title().replace('_', '')}CountdownTemplate"
    tmpl_name = f"{channel_id}_countdown"

    code = textwrap.dedent(f'''\
        """{channel_id}_countdown.py — {display_name} 카운트다운형 템플릿"""
        from __future__ import annotations
        from ShortsFactory.templates.base_template import BaseTemplate
        from ShortsFactory.templates.countdown_mixin import CountdownMixin


        class {cls_name}(CountdownMixin, BaseTemplate):
            template_name = "{tmpl_name}"

            default_hook_text = "{display_name} TOP 5"
            hook_animation = "clean_popup"
            hook_font_size = 80
            body_animation = "slide_up"
            default_cta_text = "더 알고 싶다면!"
    ''')

    out = _TEMPLATES_DIR / f"{channel_id}_countdown.py"
    out.write_text(code, encoding="utf-8")
    return out


def _register_in_init(channel_id: str, cls_name: str) -> None:
    """__init__.py에 import + TEMPLATE_REGISTRY 항목을 자동 추가합니다."""
    init_path = _TEMPLATES_DIR / "__init__.py"
    content = init_path.read_text(encoding="utf-8")

    module_name = f"{channel_id}_countdown"
    import_line = f"from ShortsFactory.templates.{module_name} import {cls_name}"
    registry_key = f"{channel_id}_countdown"
    registry_entry = f'    "{registry_key}": {cls_name},'

    # 이미 등록되어 있으면 스킵
    if import_line in content:
        logger.info(f"  Already registered: {cls_name}")
        return

    # 1) import 추가: TEMPLATE_REGISTRY 바로 위에 삽입
    marker = "TEMPLATE_REGISTRY: dict["
    if marker in content:
        content = content.replace(
            marker,
            f"# {channel_id.replace('_', ' ').title()}\n{import_line}\n\n{marker}",
        )

    # 2) registry 항목 추가: 닫는 중괄호 직전에 삽입
    closing_brace = "\n}\n"
    if closing_brace in content:
        content = content.replace(
            closing_brace,
            f"\n    # {channel_id.replace('_', ' ').title()}\n{registry_entry}\n}}\n",
        )

    init_path.write_text(content, encoding="utf-8")
    logger.info(f"  Registered {cls_name} in __init__.py")


def _generate_guide(channel_id: str, display_name: str, caption_style: str, palette: dict) -> str:
    """완료 후 가이드 텍스트."""
    return textwrap.dedent(f"""
    === {display_name} 채널 스캐폴딩 완료! ===

    자동 완료된 항목:
    ✅ channel_profiles.yaml에 채널 추가
    ✅ {channel_id}_countdown.py 템플릿 생성
    ✅ templates/__init__.py에 자동 등록

    남은 단계:
    1. caption_pillow.py에 '{caption_style}' 프리셋 추가
    2. channel_profiles.yaml에서 highlight_keywords 채우기

    사용법:
      factory = ShortsFactory(channel="{channel_id}")
      factory.create("{channel_id}_countdown", {{"items": [...]}})
      factory.render("output.mp4")

    CLI:
      python -m ShortsFactory render --channel {channel_id} --template {channel_id}_countdown --data '...'
    """).strip()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ShortsFactory 채널 스캐폴딩")
    parser.add_argument("--name", required=True, help="채널 ID")
    parser.add_argument("--display", default="", help="표시 이름")
    parser.add_argument("--category", default="", help="카테고리")
    parser.add_argument("--palette", default="cool", choices=list(DEFAULT_PALETTES.keys()))
    args = parser.parse_args()

    result = scaffold_channel(
        args.name,
        display_name=args.display,
        category=args.category,
        palette_style=args.palette,
    )
    print(result.get("guide", "Done!"))
