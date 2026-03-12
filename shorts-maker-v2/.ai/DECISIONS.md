# 🏛️ 아키텍처 결정 기록

## AD-001: ShortsFactory 역할 재정의
- **날짜**: 2026-03-12
- **결정**: ShortsFactory를 "deprecated legacy"에서 **"전문 렌더링 레이어"**로 재포지셔닝
- **근거**: 6대 엔진 + 18종 템플릿 + 채널별 스타일은 렌더링 전용으로 특화된 고가치 자산
- **영향**: ARCHITECTURE.md 재작성, `interfaces.py` 통합 인터페이스 도입

## AD-002: 레지스트리 이원 체계 유지
- **날짜**: 2026-03-12
- **결정**: `_REGISTRY` (대본 생성기) + `TEMPLATE_REGISTRY` (비주얼 렌더링) 두 레지스트리를 별도 유지
- **근거**: 서로 다른 목적(스크립트 생성 vs 비주얼 렌더링)에 맞는 별개의 매핑 구조
- **영향**: `src/.../templates/__init__.py`에서 `TEMPLATE_REGISTRY`를 re-export하여 단일 접근점 제공

## AD-003: render_from_plan 브리지 패턴
- **날짜**: 2026-03-12
- **결정**: Main Pipeline이 ScenePlan/SceneAsset을 ShortsFactory에 전달하는 브리지 메서드 `render_from_plan()` 도입
- **근거**: 기존 `create/render` API를 유지하면서 새로운 통합 경로를 제공
- **영향**: `RenderAdapter.render_with_plan()` → `ShortsFactory.render_from_plan()` → Template → Engine 경로
