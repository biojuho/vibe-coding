#!/usr/bin/env python3
"""ShortsFactory — 5채널 통합 쇼츠 파이프라인.

채널 이름만 바꾸면 전체 스타일(색상, 폰트, 전환, 훅)이 자동 전환됩니다.

사용법:
    factory = ShortsFactory(channel="ai_tech")
    factory.create("ai_news_breaking", {
        "news_title": "GPT-5 출시 임박",
        "points": [...],
    })
    factory.render("output.mp4")
"""
from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("ShortsFactory")

# ── 프로젝트 루트 자동 탐지 ──
_HERE = Path(__file__).resolve().parent
_PROJECT = _HERE.parent  # shorts-maker-v2/

# 통합 설정: channel_profiles.yaml (Single Source of Truth)
_CHANNEL_PROFILES = _PROJECT / "channel_profiles.yaml"


def _ensure_paths():
    """sys.path에 프로젝트 경로 추가."""
    import sys
    for p in [str(_PROJECT / "src"), str(_PROJECT)]:
        if p not in sys.path:
            sys.path.insert(0, p)


def _get_template_registry() -> dict:
    """템플릿 레지스트리를 shorts_maker_v2.templates에서 가져옵니다 (Single Source of Truth)."""
    _ensure_paths()
    from shorts_maker_v2 import templates as tmpl_mod
    return {t["name"]: t for t in tmpl_mod.list_all()}


def _load_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _import_generator(module_path: str, cls_name: str):
    """동적으로 생성기 클래스를 임포트합니다."""
    import importlib
    import sys
    src = _PROJECT / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    if str(_PROJECT) not in sys.path:
        sys.path.insert(0, str(_PROJECT))
    mod = importlib.import_module(module_path)
    return getattr(mod, cls_name)


class ChannelConfig:
    """채널 설정을 캡슐화합니다."""

    def __init__(self, channel_id: str, raw: dict):
        self.id = channel_id
        self._raw = raw
        self.name: str = raw.get("name", channel_id)
        self.display_name: str = raw.get("display_name", self.name)
        self.palette: dict = raw.get("palette", {})
        self.font: dict = raw.get("font", {})
        self.color_preset: str = raw.get("color_preset", raw.get("caption_style", "default"))
        self.caption_combo: list = raw.get("caption_combo", ["default", "default", "default"])
        self.default_templates: list = raw.get("default_templates", [])
        self.keyword_highlights: Any = raw.get("highlight_keywords", raw.get("keyword_highlights", {}))
        self.highlight_color: str = raw.get("highlight_color", "#FFFFFF")
        self.hook_style: str = raw.get("hook_style", "clean_popup")
        self.transition: str = raw.get("transition", "fade")
        self.disclaimer: bool = raw.get("disclaimer", False)
        self.disclaimer_text: str = raw.get(
            "disclaimer_text",
            "※ 의학적 조언이 아닌 정보 제공 목적입니다."
        )

    def get_all_keywords(self) -> dict[str, str]:
        """모든 키워드 → 색상 매핑을 반환합니다. list/dict 형식 모두 지원."""
        result = {}
        kw = self.keyword_highlights
        if isinstance(kw, list):
            # channel_profiles.yaml 기본 형식: ["단어1", "단어2", ...]
            for w in kw:
                if isinstance(w, str):
                    result[w] = self.highlight_color
        elif isinstance(kw, dict):
            # Factory 확장 형식: {category: {color, words, pattern}}
            for _cat, data in kw.items():
                if isinstance(data, dict):
                    color = data.get("color", self.palette.get("primary", "#FFFFFF"))
                    for w in data.get("words", []):
                        result[w] = color
                elif isinstance(data, str):
                    result[_cat] = data
        return result

    def get_keyword_patterns(self) -> list[tuple[str, str]]:
        """regex 패턴 → 색상 매핑을 반환합니다."""
        result = []
        kw = self.keyword_highlights
        if isinstance(kw, dict):
            for _cat, data in kw.items():
                if isinstance(data, dict) and "pattern" in data:
                    result.append((data["pattern"], data.get("color", "#FFFFFF")))
        return result

    def __repr__(self):
        return f"<ChannelConfig {self.id}: {self.display_name} ({len(self.default_templates)} templates)>"


class RenderJob:
    """렌더링 작업 단위."""

    def __init__(self, template: str, data: dict, channel: ChannelConfig):
        self.template = template
        self.data = data
        self.channel = channel
        self.created_at = time.time()
        self.status = "pending"
        self.output_path: str | None = None
        self.error: str | None = None
        self.duration_sec: float = 0

    def to_dict(self) -> dict:
        return {
            "template": self.template,
            "channel": self.channel.id,
            "status": self.status,
            "output": self.output_path,
            "error": self.error,
            "duration_sec": round(self.duration_sec, 1),
        }


class ShortsFactory:
    """5채널 통합 쇼츠 팩토리.

    채널 이름만 바꾸면 전체 스타일이 자동 전환됩니다.

    Examples:
        >>> factory = ShortsFactory(channel="ai_tech")
        >>> factory.create("ai_news_breaking", {"news_title": "GPT-5"})
        >>> factory.render("output.mp4")
    """

    def __init__(self, channel: str, config_path: str | Path | None = None):
        # Single Source of Truth: channel_profiles.yaml
        cfg_path = Path(config_path) if config_path else _CHANNEL_PROFILES
        if not cfg_path.exists():
            raise FileNotFoundError(f"채널 설정 파일을 찾을 수 없습니다: {cfg_path}")

        raw = _load_yaml(cfg_path)
        channels = raw.get("channels", {})
        if channel not in channels:
            avail = ", ".join(channels.keys())
            raise ValueError(f"알 수 없는 채널 '{channel}'. 사용 가능: {avail}")

        self.channel = ChannelConfig(channel, channels[channel])
        self._registry = _get_template_registry()
        self._jobs: list[RenderJob] = []
        self._current_job: RenderJob | None = None

        logger.info(f"ShortsFactory init: {self.channel}")

    @staticmethod
    def list_channels(config_path: str | Path | None = None) -> list[dict]:
        """사용 가능한 채널 목록을 반환합니다."""
        cfg_path = Path(config_path) if config_path else _CHANNEL_PROFILES
        raw = _load_yaml(cfg_path)
        result = []
        for cid, cdata in raw.get("channels", {}).items():
            result.append({
                "id": cid,
                "name": cdata.get("category", cid),
                "display_name": cdata.get("display_name", cid),
                "templates": cdata.get("default_templates", []),
                "color_preset": cdata.get("color_preset", cdata.get("caption_style", "default")),
            })
        return result

    @staticmethod
    def list_templates() -> list[str]:
        """사용 가능한 템플릿 목록을 반환합니다 (Single Source: templates/__init__.py)."""
        reg = _get_template_registry()
        return sorted(reg.keys())

    def create(self, template: str, data: dict) -> "ShortsFactory":
        """렌더링 작업을 생성합니다.

        Args:
            template: 템플릿 이름 (e.g., "ai_news_breaking")
            data: 템플릿에 전달할 데이터 (dict)

        Returns:
            self (체이닝 가능)
        """
        if template not in self._registry:
            avail = ", ".join(sorted(self._registry.keys()))
            raise ValueError(f"Unknown template '{template}'. Available: {avail}")

        # [QA 수정] caller의 원본 dict 변형 방지
        data = dict(data)

        # health 채널 면책조항 자동 삽입
        if self.channel.disclaimer and "disclaimer" not in data:
            data["disclaimer"] = self.channel.disclaimer_text

        job = RenderJob(template, data, self.channel)
        self._jobs.append(job)
        self._current_job = job
        logger.info(f"  Job created: {template} ({self.channel.display_name})")
        return self

    def render(self, output: str = "output.mp4", **kwargs) -> str:
        """현재(마지막) 작업을 렌더링합니다.

        Returns:
            출력 파일 경로
        """
        if not self._current_job:
            raise RuntimeError("create()로 먼저 작업을 생성하세요.")

        job = self._current_job
        job.status = "rendering"
        t0 = time.time()

        try:
            reg = self._registry[job.template]
            _ensure_paths()
            GenCls = _import_generator(reg["module"], reg["generator_cls"])
            gen = GenCls(**job.data)
            result = gen.generate(output)
            job.output_path = result
            job.status = "done"
            job.duration_sec = time.time() - t0
            logger.info(f"  Render OK: {result} ({job.duration_sec:.1f}s)")
            return result

        except Exception as e:
            job.status = "error"
            job.error = str(e)
            job.duration_sec = time.time() - t0
            logger.error(f"  Render FAIL: {e}")
            raise

    def render_all(self, output_dir: str = "output", prefix: str = "") -> list[dict]:
        """대기 중인 모든 작업을 렌더링합니다.

        Returns:
            각 작업의 결과 리스트
        """
        out_dir = Path(output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        results = []

        for i, job in enumerate(self._jobs):
            if job.status != "pending":
                results.append(job.to_dict())
                continue

            fname = f"{prefix}{self.channel.id}_{job.template}_{i:03d}.mp4"
            out_path = str(out_dir / fname)
            self._current_job = job

            try:
                self.render(out_path)
            except Exception as e:
                logger.error(f"  ❌ 작업 {i} 실패: {e}")

            results.append(job.to_dict())

        return results

    def info(self) -> dict:
        """현재 채널 정보를 반환합니다."""
        kw = self.channel.get_all_keywords()
        return {
            "channel": self.channel.id,
            "display_name": self.channel.display_name,
            "palette": self.channel.palette,
            "color_preset": self.channel.color_preset,
            "caption_combo": self.channel.caption_combo,
            "hook_style": self.channel.hook_style,
            "transition": self.channel.transition,
            "templates": self.channel.default_templates,
            "keywords": len(kw),
            "disclaimer": self.channel.disclaimer,
            "jobs_pending": sum(1 for j in self._jobs if j.status == "pending"),
            "jobs_done": sum(1 for j in self._jobs if j.status == "done"),
        }

    # ── Phase 1: Main Pipeline 연동용 브리지 메서드 ──────────────────────────

    def render_from_plan(
        self,
        scenes: list[dict],
        assets: dict[int, str | Path],
        output: str,
        *,
        audio_paths: dict[int, str | Path] | None = None,
        template: str | None = None,
    ) -> str:
        """Main Pipeline의 ScenePlan 데이터를 받아 ShortsFactory 스타일로 렌더링합니다.

        이 메서드는 Main Pipeline의 orchestrator가 RenderAdapter를 통해 호출합니다.
        ShortsFactory의 6대 엔진(Text/Color/Background/Layout/Hook/Transition)을
        활용하여 채널별 스타일이 적용된 최종 영상을 렌더링합니다.

        Args:
            scenes: ScenePlan 딕셔너리 리스트.
                각 항목: {"scene_id", "narration_ko", "visual_prompt_en",
                          "target_sec", "structure_role"}
            assets: scene_id → 비주얼 파일 경로 매핑
            output: 최종 출력 파일 경로
            audio_paths: scene_id → TTS 오디오 파일 경로 매핑 (선택)
            template: 사용할 템플릿 이름 (선택, 없으면 채널 기본 템플릿)

        Returns:
            렌더링된 영상 파일 경로
        """
        from ShortsFactory.templates import TEMPLATE_REGISTRY, Scene

        # 템플릿 선택
        tmpl_name = template or (
            self.channel.default_templates[0]
            if self.channel.default_templates
            else "ai_news"
        )
        tmpl_cls = TEMPLATE_REGISTRY.get(tmpl_name)
        if tmpl_cls is None:
            logger.warning(
                "Template '%s' not found in TEMPLATE_REGISTRY, using base render",
                tmpl_name,
            )
            # 폴백: 기존 RenderJob 경로
            data = {"scenes": scenes, "assets": assets}
            self.create(tmpl_name, data)
            return self.render(output)

        # ChannelConfig을 dict로 변환하여 BaseTemplate에 전달
        channel_dict = {
            "id": self.channel.id,
            "palette": self.channel.palette,
            "font": self.channel.font,
            "color_preset": self.channel.color_preset,
            "caption_combo": self.channel.caption_combo,
            "hook_style": self.channel.hook_style,
            "transition": self.channel.transition,
            "disclaimer": self.channel.disclaimer,
            "highlight_color": self.channel.highlight_color,
            "keyword_highlights": self.channel.keyword_highlights,
        }

        # 템플릿 인스턴스 생성
        tmpl = tmpl_cls(channel_dict)

        # ScenePlan → Scene 변환
        factory_scenes: list[Scene] = []
        for sp in scenes:
            scene = Scene(
                role=sp.get("structure_role", "body"),
                text=sp.get("narration_ko", ""),
                keywords=[],
                image_path=Path(assets[sp["scene_id"]]) if sp["scene_id"] in assets else None,
                duration=sp.get("target_sec", 5.0),
            )
            factory_scenes.append(scene)

        # 공통 후처리 (면책조항 등)
        factory_scenes = tmpl.finalize_scenes(factory_scenes)

        # 씬 에셋 렌더링 (자막 이미지 생성)
        run_dir = Path(output).parent / ".render_work"
        factory_scenes = tmpl.render_scene_assets(factory_scenes, run_dir)

        # 렌더 작업 기록
        job = RenderJob(tmpl_name, {"scene_count": len(factory_scenes)}, self.channel)
        job.status = "rendering"
        self._jobs.append(job)
        t0 = time.time()

        try:
            # FFmpeg filter_complex 렌더링은 ShortsFactory/render.py가 담당
            from ShortsFactory.render import RenderStep as SFRenderStep
            renderer = SFRenderStep(self.channel)
            result = renderer.render_scenes(factory_scenes, str(output))
            job.output_path = result
            job.status = "done"
            job.duration_sec = time.time() - t0
            logger.info("render_from_plan OK: %s (%0.1fs)", result, job.duration_sec)
            return result
        except Exception as e:
            job.status = "error"
            job.error = str(e)
            job.duration_sec = time.time() - t0
            logger.error("render_from_plan FAIL: %s", e)
            raise

    def get_template_info(self, template_name: str) -> dict | None:
        """템플릿 정보를 반환합니다 (RenderAdapter용)."""
        from ShortsFactory.templates import TEMPLATE_REGISTRY
        cls = TEMPLATE_REGISTRY.get(template_name)
        if cls is None:
            return None
        return {
            "name": template_name,
            "class": cls.__name__,
            "module": cls.__module__,
            "channel": getattr(cls, "channel", self.channel.id),
        }

    def __repr__(self):
        return f"<ShortsFactory channel={self.channel.id} jobs={len(self._jobs)}>"

