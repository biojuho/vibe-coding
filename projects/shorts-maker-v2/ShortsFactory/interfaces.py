"""ShortsFactory Interfaces — 메인 파이프라인과의 통합 인터페이스.

ShortsFactory를 "Professional Rendering Layer"로 메인 파이프라인에 통합하기 위한
인터페이스 정의입니다. 이를 통해 두 모듈 간의 명확한 경계(boundary)를 설정합니다.

Architecture:
    src/shorts_maker_v2/pipeline/ (Orchestrator)
        → ShortsFactory (Rendering Layer: 비주얼, 컬러, 레이아웃, 전환)

사용법:
    from ShortsFactory.interfaces import RenderRequest, RenderResult

    request = RenderRequest(
        channel_id="ai_tech",
        template_name="ai_news_breaking",
        content_data={"news_title": "GPT-5 출시", ...},
        output_path="output/gpt5.mp4",
    )
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class RenderRequest:
    """메인 파이프라인 → ShortsFactory 렌더링 요청.

    Attributes:
        channel_id: 채널 키 (e.g., "ai_tech", "psychology")
        template_name: 템플릿 이름 (e.g., "ai_news_breaking")
        content_data: 템플릿에 전달할 데이터 (스크립트, 키워드, 포인트 등)
        output_path: 출력 파일 경로
        overrides: 선택적 렌더링 오버라이드 (transition, hook_style 등)
        audio_path: 사전 생성된 오디오 파일 경로 (TTS 결과물)
        subtitle_data: 자막 데이터 (word-level timing 포함)
        assets: 추가 에셋 경로 (인트로, 아웃트로, 워터마크 등)
    """

    channel_id: str
    template_name: str
    content_data: dict[str, Any]
    output_path: str | Path
    overrides: dict[str, Any] = field(default_factory=dict)
    audio_path: str | Path | None = None
    subtitle_data: dict[str, Any] | None = None
    assets: dict[str, str | Path] = field(default_factory=dict)

    def __post_init__(self):
        self.output_path = Path(self.output_path)


@dataclass
class RenderResult:
    """ShortsFactory → 메인 파이프라인 렌더링 결과.

    Attributes:
        success: 성공 여부
        output_path: 렌더링된 파일 경로
        duration_sec: 렌더링 소요 시간 (초)
        template_used: 사용된 템플릿 이름
        channel_id: 사용된 채널 ID
        metadata: 추가 메타데이터 (해상도, 프레임레이트, 씬 수 등)
        error: 실패 시 에러 메시지
    """

    success: bool
    output_path: Path | None = None
    duration_sec: float = 0.0
    template_used: str = ""
    channel_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


@dataclass
class TemplateInfo:
    """템플릿 정보 (카탈로그용).

    Attributes:
        name: 템플릿 이름
        channel: 채널 키
        description: 설명
        generator_cls: 생성기 클래스 이름
        module: 모듈 경로
        supports_countdown: 카운트다운 지원 여부
    """

    name: str
    channel: str
    description: str = ""
    generator_cls: str = ""
    module: str = ""
    supports_countdown: bool = False


class RenderAdapter:
    """메인 파이프라인 ↔ ShortsFactory 어댑터.

    Pipeline의 render_step에서 직접 ShortsFactory를 호출하는 대신
    이 어댑터를 통해 호출하여 인터페이스 안정성을 보장합니다.

    Examples:
        adapter = RenderAdapter()
        result = adapter.render(RenderRequest(
            channel_id="ai_tech",
            template_name="ai_news_breaking",
            content_data={...},
            output_path="output.mp4",
        ))
    """

    def __init__(self):
        self._factory_cache: dict[str, Any] = {}

    def render(self, request: RenderRequest) -> RenderResult:
        """렌더링 요청을 처리합니다.

        Args:
            request: 렌더링 요청

        Returns:
            렌더링 결과
        """
        from .pipeline import ShortsFactory

        t0 = time.time()
        try:
            # 팩토리 캐시 (같은 채널 재사용)
            if request.channel_id not in self._factory_cache:
                self._factory_cache[request.channel_id] = ShortsFactory(channel=request.channel_id)
            factory = self._factory_cache[request.channel_id]

            # 데이터 준비
            data = dict(request.content_data)
            if request.overrides:
                data.update(request.overrides)
            if request.audio_path:
                data["audio_path"] = str(request.audio_path)
            if request.subtitle_data:
                data["subtitle_data"] = request.subtitle_data

            # 렌더링 실행
            factory.create(request.template_name, data)
            output = factory.render(str(request.output_path))

            return RenderResult(
                success=True,
                output_path=Path(output),
                duration_sec=time.time() - t0,
                template_used=request.template_name,
                channel_id=request.channel_id,
                metadata={
                    "overrides": request.overrides,
                    "has_audio": request.audio_path is not None,
                    "has_subtitles": request.subtitle_data is not None,
                },
            )

        except Exception as e:
            return RenderResult(
                success=False,
                duration_sec=time.time() - t0,
                template_used=request.template_name,
                channel_id=request.channel_id,
                error=str(e),
            )

    def render_with_plan(
        self,
        channel_id: str,
        scenes: list[dict],
        assets: dict[int, str],
        output_path: str | Path,
        *,
        audio_paths: dict[int, str] | None = None,
        template: str | None = None,
    ) -> RenderResult:
        """ScenePlan 기반 렌더링 (Main Pipeline orchestrator 용).

        RenderAdapter.render()가 RenderRequest(content_data) 기반인 반면,
        이 메서드는 ScenePlan + SceneAsset을 직접 전달합니다.

        Args:
            channel_id: 채널 키
            scenes: ScenePlan 딕셔너리 리스트
            assets: scene_id → 비주얼 파일 경로
            output_path: 출력 경로
            audio_paths: scene_id → TTS 오디오 경로
            template: 템플릿 이름 (선택)

        Returns:
            RenderResult
        """
        from .pipeline import ShortsFactory

        t0 = time.time()
        try:
            if channel_id not in self._factory_cache:
                self._factory_cache[channel_id] = ShortsFactory(channel=channel_id)
            factory = self._factory_cache[channel_id]

            output = factory.render_from_plan(
                scenes=scenes,
                assets=assets,
                output=str(output_path),
                audio_paths=audio_paths,
                template=template,
            )

            return RenderResult(
                success=True,
                output_path=Path(output),
                duration_sec=time.time() - t0,
                template_used=template or "",
                channel_id=channel_id,
                metadata={"scene_count": len(scenes), "mode": "plan-based"},
            )
        except Exception as e:
            return RenderResult(
                success=False,
                duration_sec=time.time() - t0,
                template_used=template or "",
                channel_id=channel_id,
                error=str(e),
            )

    def list_templates(self, channel_id: str | None = None) -> list[TemplateInfo]:
        """사용 가능한 템플릿 목록을 반환합니다.

        Args:
            channel_id: 특정 채널만 필터링 (None이면 전체)

        Returns:
            TemplateInfo 리스트
        """
        from .pipeline import _get_template_registry

        registry = _get_template_registry()
        templates = []

        for name, info in registry.items():
            if channel_id and info.get("channel") != channel_id:
                continue
            templates.append(
                TemplateInfo(
                    name=name,
                    channel=info.get("channel", ""),
                    description=info.get("description", ""),
                    generator_cls=info.get("generator_cls", ""),
                    module=info.get("module", ""),
                    supports_countdown="countdown" in name,
                )
            )

        return templates

    def get_channel_info(self, channel_id: str) -> dict[str, Any]:
        """채널 정보를 반환합니다.

        Args:
            channel_id: 채널 키

        Returns:
            채널 정보 딕셔너리
        """
        from .pipeline import ShortsFactory

        factory = ShortsFactory(channel=channel_id)
        return factory.info()
