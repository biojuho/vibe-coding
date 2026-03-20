"""future_countdown.py — 미래 기술 예측 카운트다운 템플릿

시간 기반 레이아웃:
  0~2초       : 인트로 ("2030년까지 바뀔 기술 TOP 5", 바운스 팝업)
  2~N초       : 각 항목 8초씩 (큰 순번 + 기술명 글로우 + 설명 카드 + 블러 배경)
  N~N+3초     : 아웃트로 ("다음 영상에서 더 자세히!")

1위 특별 효과:
  - 화면 전체 플래시 (0.2초)
  - 골드 색상 (#FFD700)
  - 줌 펄스: 1.0→1.05→1.0 ×2
  - 파티클 밀도 3배
"""

from __future__ import annotations

from typing import Any

from ShortsFactory.templates.base_template import BaseTemplate, Scene

# ── 타이밍 상수 ───────────────────────────────────────────────────
_INTRO_START = 0.0
_INTRO_DURATION = 2.0
_ITEM_START = 2.0
_ITEM_DURATION = 8.0
_OUTRO_DURATION = 3.0

# ── 색상 상수 ────────────────────────────────────────────────────
_RANK_COLOR = "#7C3AED"
_TITLE_COLOR = "#00D4FF"
_GOLD_COLOR = "#FFD700"


class FutureCountdownTemplate(BaseTemplate):
    """미래 기술 예측 카운트다운 템플릿.

    입력: items: [{rank, title, description, image_path}]
    출력: 인트로 → 카운트다운(N→1) → 아웃트로
    """

    template_name = "future_countdown"

    def build_scenes(self, data: dict[str, Any]) -> list[Scene]:
        scenes: list[Scene] = []
        items = data.get("items", [])
        total_items = len(items)

        # 인트로 제목 (기본: "2030년까지 바뀔 기술 TOP N")
        intro_text = data.get(
            "intro_text",
            f"2030년까지 바뀔 기술 TOP {total_items}",
        )

        # ── 1) 인트로 (0~2초) ────────────────────────────────────
        scenes.append(
            Scene(
                role="hook",
                text=intro_text,
                duration=_INTRO_DURATION,
                start_time=_INTRO_START,
                animation="bounce_popup",
                extra={
                    "font_size": 80,
                    "text_color": _TITLE_COLOR,
                    "glow": True,
                    "glow_color": _TITLE_COLOR,
                    "glow_radius": 15,
                    "bounce_duration": 0.4,
                },
            )
        )

        # ── 2) 카운트다운 항목 (역순: N→1) ─────────────────────
        # items를 rank 기준 내림차순 정렬 (높은 번호부터)
        sorted_items = sorted(items, key=lambda x: x.get("rank", 0), reverse=True)
        item_time = _ITEM_START

        for item in sorted_items:
            rank = item.get("rank", 0)
            title = item.get("title", "")
            description = item.get("description", "")
            image_path = item.get("image_path")
            is_first = rank == 1

            # 1위 특별 효과
            if is_first:
                title_color = _GOLD_COLOR
                anim = "zoom_pulse_flash"
                particle_density = 3.0
            else:
                title_color = _TITLE_COLOR
                anim = "fade_in"
                particle_density = 1.0

            scenes.append(
                Scene(
                    role="body",
                    text=title,
                    keywords=[title] if title else [],
                    duration=_ITEM_DURATION,
                    start_time=item_time,
                    animation=anim,
                    extra={
                        "rank": rank,
                        "description": description,
                        "image_path": image_path,
                        "is_first": is_first,
                        # 순번 워터마크
                        "watermark_number": rank,
                        "watermark_font_size": 200,
                        "watermark_color": _RANK_COLOR if not is_first else _GOLD_COLOR,
                        "watermark_opacity": 0.5,
                        # 기술명 글로우
                        "font_size": 70,
                        "text_color": title_color,
                        "glow": True,
                        "glow_color": title_color,
                        "glow_radius": 20,
                        # 설명 카드 (하단 40%)
                        "description_card": True,
                        "card_bg": "#111827",
                        "card_bg_opacity": 0.85,
                        "card_radius": 16,
                        "card_font_size": 38,
                        "card_y_ratio": 0.6,  # 화면 상단 60% 아래부터
                        # 배경 이미지 처리
                        "blur_sigma": 25,
                        "brightness": 0.3,
                        # 파티클 밀도
                        "particle_density": particle_density,
                        # 1위 전용
                        "flash_duration": 0.2 if is_first else 0,
                        "zoom_pulse_count": 2 if is_first else 0,
                        "zoom_scale": 1.05 if is_first else 1.0,
                    },
                )
            )

            # SFX 마커: 순번 등장 시 사운드
            sfx_type = "impact" if is_first else "whoosh"
            scenes[-1].extra["sfx_marker"] = {
                "type": sfx_type,
                "time": item_time,
            }

            item_time += _ITEM_DURATION

        # ── 3) 아웃트로 (N+3초) ─────────────────────────────────
        outro_text = data.get(
            "outro_text",
            "다음 영상에서 더 자세히!",
        )
        scenes.append(
            Scene(
                role="cta",
                text=outro_text,
                duration=_OUTRO_DURATION,
                start_time=item_time,
                animation="fade_in",
                extra={
                    "font_size": 60,
                    "text_color": "#FFFFFF",
                    "subscribe_icon": True,
                    "gradient_shift": True,
                    "gradient_start": "#0B0D21",
                    "gradient_end": "#1a0a2e",
                },
            )
        )

        return self.finalize_scenes(scenes)

    def get_total_duration(self, scenes: list[Scene]) -> float:
        """전체 영상 길이(초)를 반환합니다."""
        if not scenes:
            return 0.0
        last = scenes[-1]
        return (last.start_time or 0.0) + last.duration

    def get_sfx_markers(self, scenes: list[Scene]) -> list[dict[str, Any]]:
        """모든 SFX 마커를 추출합니다."""
        markers = []
        for scene in scenes:
            marker = scene.extra.get("sfx_marker")
            if marker:
                markers.append(marker)
        return markers

    def get_particle_density_map(
        self,
        scenes: list[Scene],
    ) -> list[dict[str, Any]]:
        """씬별 파티클 밀도 맵을 반환합니다.

        FFmpeg 렌더링 시 1위 구간에 파티클 3배 밀도를 적용하기 위한 정보.

        Returns:
            [{"start": 10.0, "end": 18.0, "density": 3.0}, ...] 형태.
        """
        density_map = []
        for scene in scenes:
            pd = scene.extra.get("particle_density", 1.0)
            if pd != 1.0:
                density_map.append(
                    {
                        "start": scene.start_time or 0.0,
                        "end": (scene.start_time or 0.0) + scene.duration,
                        "density": pd,
                    }
                )
        return density_map
