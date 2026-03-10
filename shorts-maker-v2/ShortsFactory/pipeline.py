"""
pipeline.py — ShortsFactory 메인 클래스
=======================================
채널 설정 로드 → 엔진 초기화 → 템플릿 → 씬 빌드 → 렌더링.

v2: FFmpeg 기반 비디오 렌더링, 애니메이션, BGM 덕킹 추가.

사용법:
    factory = ShortsFactory(channel="ai_tech")
    factory.create("ai_news", {"hook_text": "🚨 속보", ...})
    factory.render("output.mp4")
"""
from __future__ import annotations

import json
import logging
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).parent / "config"
_WIDTH, _HEIGHT = 1080, 1920
_FPS = 30


def _load_channels(config_dir: Path | None = None) -> dict[str, Any]:
    path = (config_dir or _CONFIG_DIR) / "channels.yaml"
    if not path.exists():
        raise FileNotFoundError(f"channels.yaml not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("channels", {})


def _ffmpeg_available() -> bool:
    """FFmpeg CLI가 PATH에 있는지 확인."""
    return shutil.which("ffmpeg") is not None


class ShortsFactory:
    """5채널 통합 숏츠 제작 파이프라인.

    Args:
        channel: 채널 키 (ai_tech, psychology, history, space, health).
        config_dir: config 디렉토리 경로 (기본: ShortsFactory/config/).
    """

    def __init__(self, channel: str, *, config_dir: str | Path | None = None) -> None:
        self._config_dir = Path(config_dir) if config_dir else _CONFIG_DIR
        self._channels = _load_channels(self._config_dir)

        if channel not in self._channels:
            available = list(self._channels.keys())
            raise ValueError(
                f"알 수 없는 채널: '{channel}'. 사용 가능: {available}"
            )

        self.channel_key = channel
        self.channel_config = self._channels[channel]
        self._scenes = []
        self._template = None
        self._template_name = ""
        self._data = {}

        logger.info(
            "[ShortsFactory] 채널 '%s' (%s) 초기화 완료",
            channel, self.channel_config.get("name", channel),
        )

    def create(self, template_name: str, data: dict[str, Any]) -> "ShortsFactory":
        """템플릿과 데이터로 씬을 구성합니다.

        Args:
            template_name: 템플릿 이름 (ai_news, psych_experiment 등).
            data: 콘텐츠 데이터 dict.

        Returns:
            self (메서드 체이닝용).
        """
        from ShortsFactory.templates import TEMPLATE_REGISTRY

        if template_name not in TEMPLATE_REGISTRY:
            available = list(TEMPLATE_REGISTRY.keys())
            raise ValueError(
                f"알 수 없는 템플릿: '{template_name}'. 사용 가능: {available}"
            )

        template_cls = TEMPLATE_REGISTRY[template_name]
        self._template = template_cls(self.channel_config)
        self._template_name = template_name
        self._data = data
        self._scenes = self._template.build_scenes(data)

        logger.info(
            "[ShortsFactory] '%s' 템플릿으로 %d개 씬 생성",
            template_name, len(self._scenes),
        )
        return self

    def render(
        self,
        output_path: str | Path,
        *,
        bg_music: str | Path | None = None,
        progress_callback: Any | None = None,
    ) -> Path:
        """씬을 렌더링하여 최종 영상을 생성합니다.

        1) 씬별 에셋(자막/배지/글로우) 렌더링
        2) 배경 + 그리드 오버레이 생성
        3) FFmpeg filter_complex로 최종 MP4 합성

        Args:
            output_path: 출력 mp4 파일 경로.
            bg_music: 배경음악 경로 (None이면 BGM 미적용).
            progress_callback: 진행률 콜백 (0.0~1.0).

        Returns:
            생성된 영상 파일 경로.
        """
        if not self._scenes:
            raise RuntimeError("create()를 먼저 호출해야 합니다.")

        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # 에셋 렌더링 디렉토리
        assets_dir = output_path.parent / f".assets_{output_path.stem}"
        assets_dir.mkdir(parents=True, exist_ok=True)

        total = len(self._scenes)
        start_time = time.time()

        # 1) 씬 자막/에셋 렌더링
        logger.info("[ShortsFactory] 씬 자막 렌더링 시작 (%d 씬)", total)
        self._render_scene_assets_v2(self._scenes, assets_dir)

        # 2) 배경 이미지 생성
        bg_path = assets_dir / "background.png"
        self._template.background.create_gradient(output_path=bg_path)

        # 3) 그리드 오버레이
        grid_path = assets_dir / "grid_overlay.png"
        self._template.background.create_grid_overlay(output_path=grid_path)

        # 4) 파티클 오버레이
        particle_path = assets_dir / "particles.png"
        self._template.background.create_particle_overlay(output_path=particle_path)

        # 5) 매니페스트 저장
        sfx_markers = []
        if hasattr(self._template, "get_sfx_markers"):
            sfx_markers = self._template.get_sfx_markers(self._scenes)

        total_duration = self._calculate_total_duration()

        manifest = {
            "channel": self.channel_key,
            "template": self._template_name,
            "total_duration": total_duration,
            "scenes": [
                {
                    "role": s.role,
                    "text": s.text,
                    "keywords": s.keywords,
                    "image": str(s.image_path) if s.image_path else None,
                    "duration": s.duration,
                    "start_time": s.start_time,
                    "animation": s.animation,
                    "extra": s.extra,
                }
                for s in self._scenes
            ],
            "assets": {
                "background": str(bg_path),
                "grid_overlay": str(grid_path),
                "particles": str(particle_path),
            },
            "sfx_markers": sfx_markers,
            "bg_music": str(bg_music) if bg_music else None,
            "output": str(output_path),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        manifest_path = assets_dir / "manifest.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        # 6) FFmpeg 렌더링
        if _ffmpeg_available():
            self._render_video_ffmpeg(
                manifest, output_path, assets_dir, bg_music,
            )
        else:
            logger.warning(
                "[ShortsFactory] FFmpeg 미설치. 매니페스트만 생성됨: %s",
                manifest_path,
            )

        elapsed = time.time() - start_time
        logger.info(
            "[ShortsFactory] 렌더링 완료 (%.1f초). 출력: %s",
            elapsed, output_path,
        )

        if progress_callback:
            progress_callback(1.0)

        return output_path

    # ── 에셋 렌더링 (v2 — 글로우, 배지 지원) ──────────────────────

    def _render_scene_assets_v2(self, scenes: list, assets_dir: Path) -> None:
        """각 씬의 에셋(자막, 글로우, 배지)을 렌더링합니다."""
        for i, scene in enumerate(scenes):
            if not scene.text or scene.image_path is not None:
                continue

            extra = scene.extra or {}
            img_path = assets_dir / f"scene_{i:02d}_{scene.role}.png"

            # 글로우 텍스트
            if extra.get("glow"):
                self._template.text.render_subtitle_with_glow(
                    scene.text,
                    glow_color=extra.get("glow_color"),
                    glow_radius=extra.get("glow_radius", 20),
                    keywords=scene.keywords,
                    role=scene.role,
                    output_path=img_path,
                )
            else:
                self._template.text.render_subtitle(
                    scene.text, keywords=scene.keywords,
                    role=scene.role, output_path=img_path,
                )

            scene.image_path = img_path

            # 배지 렌더
            if extra.get("badge_number"):
                badge_path = assets_dir / f"badge_{i:02d}.png"
                self._template.text.render_badge(
                    extra["badge_number"],
                    badge_color=extra.get("badge_color", "#7C3AED"),
                    output_path=badge_path,
                )
                extra["badge_image"] = str(badge_path)

    # ── FFmpeg 렌더링 ──────────────────────────────────────────────

    def _render_video_ffmpeg(
        self,
        manifest: dict,
        output_path: Path,
        assets_dir: Path,
        bg_music: str | Path | None,
    ) -> None:
        """매니페스트 기반으로 FFmpeg filter_complex를 구성하여 MP4를 생성합니다.

        구조:
        - 입력 0: 배경 이미지 (루프)
        - 입력 1: 그리드 오버레이 (루프)
        - 입력 2~N: 씬 자막 이미지들
        - 입력 N+1: BGM (선택)
        """
        total_dur = manifest["total_duration"]
        scenes = manifest["scenes"]
        bg_path = manifest["assets"]["background"]
        grid_path = manifest["assets"]["grid_overlay"]

        # FFmpeg 입력 목록 구성
        inputs: list[str] = []
        # 0: 배경
        inputs.extend(["-loop", "1", "-t", f"{total_dur}", "-i", bg_path])
        # 1: 그리드
        inputs.extend(["-loop", "1", "-t", f"{total_dur}", "-i", grid_path])

        # 2~N: 씬 이미지들
        scene_input_indices: list[int] = []
        input_idx = 2
        for scene in scenes:
            if scene.get("image"):
                inputs.extend(["-loop", "1", "-t", f"{total_dur}", "-i", scene["image"]])
                scene_input_indices.append(input_idx)
                input_idx += 1
            else:
                scene_input_indices.append(-1)

        # BGM 입력
        bgm_input_idx = -1
        if bg_music and Path(str(bg_music)).exists():
            inputs.extend(["-stream_loop", "-1", "-i", str(bg_music)])
            bgm_input_idx = input_idx
            input_idx += 1

        # filter_complex 구성
        filter_parts: list[str] = []

        # 배경 스케일
        filter_parts.append(f"[0:v]scale={_WIDTH}:{_HEIGHT}:force_original_aspect_ratio=decrease,"
                            f"pad={_WIDTH}:{_HEIGHT}:(ow-iw)/2:(oh-ih)/2[bg]")

        # 그리드를 배경에 오버레이
        filter_parts.append(f"[1:v]scale={_WIDTH}:{_HEIGHT}[grid]")
        filter_parts.append("[bg][grid]overlay=0:0:format=auto[base]")

        # 씬별 오버레이
        current_base = "base"
        scene_idx = 0
        for i, scene in enumerate(scenes):
            si = scene_input_indices[i]
            if si < 0:
                continue

            start = scene.get("start_time", 0) or 0
            dur = scene.get("duration", 5)
            end = start + dur
            anim = scene.get("animation", "none")
            extra = scene.get("extra", {})

            # 이미지 스케일 (씬 이미지는 자체 크기 유지, 중앙 배치)
            overlay_label = f"s{scene_idx}"

            # 애니메이션별 오버레이 필터
            if anim == "slide_up":
                slide_dur = extra.get("slide_duration", 0.3)
                # Y: 화면 하단 → 중앙 (ease-out)
                y_expr = f"if(lt(t-{start},{slide_dur}),H-((H-((H-overlay_h)/2))*(t-{start})/{slide_dur}),(H-overlay_h)/2)"
                filter_parts.append(
                    f"[{si}:v]format=rgba,scale=-2:{int(_HEIGHT*0.15)}[{overlay_label}]"
                )
                filter_parts.append(
                    f"[{current_base}][{overlay_label}]overlay=(W-overlay_w)/2:'{y_expr}'"
                    f":enable='between(t,{start},{end})'[out{scene_idx}]"
                )

            elif anim == "slide_in_right":
                slide_in = extra.get("slide_in_duration", 0.3)
                slide_out = extra.get("slide_out_duration", 0.3)
                out_start = end - slide_out
                # X: 화면 오른쪽 → 중앙 → 왼쪽
                x_expr = (
                    f"if(lt(t-{start},{slide_in}),"
                    f"W-((W-((W-overlay_w)/2))*(t-{start})/{slide_in}),"
                    f"if(gt(t,{out_start}),"
                    f"((W-overlay_w)/2)-(((W-overlay_w)/2+overlay_w)*(t-{out_start})/{slide_out}),"
                    f"(W-overlay_w)/2))"
                )
                filter_parts.append(
                    f"[{si}:v]format=rgba[{overlay_label}]"
                )
                filter_parts.append(
                    f"[{current_base}][{overlay_label}]overlay='{x_expr}':(H-overlay_h)/2"
                    f":enable='between(t,{start},{end})'[out{scene_idx}]"
                )

            elif anim == "fade_in":
                fade_dur = min(0.5, dur * 0.3)
                filter_parts.append(
                    f"[{si}:v]format=rgba,"
                    f"fade=in:st={start}:d={fade_dur}:alpha=1[{overlay_label}]"
                )
                filter_parts.append(
                    f"[{current_base}][{overlay_label}]overlay=(W-overlay_w)/2:(H-overlay_h)/2"
                    f":enable='between(t,{start},{end})'[out{scene_idx}]"
                )

            elif anim == "glitch_flash":
                # 글리치 효과는 moviepy에서 처리하므로, 여기서는 단순 오버레이
                filter_parts.append(
                    f"[{si}:v]format=rgba[{overlay_label}]"
                )
                filter_parts.append(
                    f"[{current_base}][{overlay_label}]overlay=(W-overlay_w)/2:(H-overlay_h)/2"
                    f":enable='between(t,{start},{end})'[out{scene_idx}]"
                )

            else:  # none
                filter_parts.append(
                    f"[{si}:v]format=rgba[{overlay_label}]"
                )
                filter_parts.append(
                    f"[{current_base}][{overlay_label}]overlay=(W-overlay_w)/2:(H-overlay_h)/2"
                    f":enable='between(t,{start},{end})'[out{scene_idx}]"
                )

            current_base = f"out{scene_idx}"
            scene_idx += 1

        # 최종 출력 레이블
        final_video = current_base

        # 오디오 처리
        audio_parts: list[str] = []
        if bgm_input_idx >= 0:
            # BGM 덕킹: -12dB로 볼륨 조절 + 페이드 아웃
            audio_parts.append(
                f"[{bgm_input_idx}:a]volume=-12dB,"
                f"afade=t=out:st={total_dur - 2}:d=2,"
                f"atrim=0:{total_dur}[bgm]"
            )
            final_audio = "bgm"
        else:
            # 무음 오디오 생성
            audio_parts.append(
                f"anullsrc=r=44100:cl=stereo,atrim=0:{total_dur}[silence]"
            )
            final_audio = "silence"

        # 전체 필터 체인 결합
        all_filters = filter_parts + audio_parts
        filter_complex = ";\n".join(all_filters)

        # FFmpeg 명령어 구성
        cmd = [
            "ffmpeg", "-y",
            *inputs,
            "-filter_complex", filter_complex,
            "-map", f"[{final_video}]",
            "-map", f"[{final_audio}]",
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "23",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-r", str(_FPS),
            "-t", str(total_dur),
            "-movflags", "+faststart",
            str(output_path),
        ]

        # 디버그: 필터 저장
        filter_path = assets_dir / "filter_complex.txt"
        filter_path.write_text(filter_complex, encoding="utf-8")
        logger.info("[ShortsFactory] FFmpeg 필터 저장: %s", filter_path)

        # 실행
        logger.info("[ShortsFactory] FFmpeg 렌더 시작...")
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
            )
            if result.returncode != 0:
                logger.error("[ShortsFactory] FFmpeg 오류:\n%s", result.stderr[-2000:])
                # 오류 로그 저장
                error_log = assets_dir / "ffmpeg_error.log"
                error_log.write_text(result.stderr, encoding="utf-8")
            else:
                logger.info("[ShortsFactory] FFmpeg 렌더 성공: %s", output_path)
        except subprocess.TimeoutExpired:
            logger.error("[ShortsFactory] FFmpeg 타임아웃 (300초)")
        except FileNotFoundError:
            logger.error("[ShortsFactory] FFmpeg 실행 파일을 찾을 수 없습니다")

    # ── 유틸리티 ──────────────────────────────────────────────────

    def _calculate_total_duration(self) -> float:
        """전체 영상 길이를 계산합니다."""
        if not self._scenes:
            return 0.0
        max_end = 0.0
        cumulative = 0.0
        for s in self._scenes:
            if s.start_time is not None:
                end = s.start_time + s.duration
            else:
                end = cumulative + s.duration
                cumulative = end
            max_end = max(max_end, end)
        return max_end

    def batch_render(
        self,
        csv_path: str | Path,
        output_dir: str | Path,
    ) -> list[dict[str, Any]]:
        """CSV 배치 렌더링. batch.py에 위임."""
        from ShortsFactory.batch import BatchProcessor
        processor = BatchProcessor(config_dir=self._config_dir)
        return processor.run(
            str(csv_path), str(output_dir), channel=self.channel_key,
        )

    @staticmethod
    def list_channels(config_dir: str | Path | None = None) -> list[dict[str, str]]:
        """사용 가능한 채널 목록을 반환합니다."""
        channels = _load_channels(Path(config_dir) if config_dir else None)
        return [
            {"key": k, "name": v.get("name", k), "hook_style": v.get("hook_style", "")}
            for k, v in channels.items()
        ]
