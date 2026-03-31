"""TopicAngleGenerator — 트렌드 후보를 인지 부조화 훅 제목으로 변환.

유저 분석에서 발견한 바이럴 공식:
    [예상과 반대되는 결과] + [이유]
    → "AI 도입했더니 오히려 야근이 늘어난 이유"
    → "클로드가 승인창을 없앤 진짜 이유"
    → "바이브코딩 격차가 벌어지는 이유"

Usage:
    gen = TopicAngleGenerator(config, llm_router=llm_router)
    angles = gen.run(candidates, channel_key="ai_tech", n=5)
    # → List[ScoredAngle] sorted by viral_score desc
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

from shorts_maker_v2.config import AppConfig
from shorts_maker_v2.pipeline.trend_discovery_step import TrendCandidate
from shorts_maker_v2.providers.llm_router import LLMRouter

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 채널별 인지 부조화 훅 패턴 예시 (LLM few-shot 학습용)
# ---------------------------------------------------------------------------
_CHANNEL_HOOK_EXAMPLES: dict[str, list[str]] = {
    "ai_tech": [
        "AI 도입했더니 오히려 야근이 늘어난 이유",
        "클로드가 승인창을 없앤 진짜 이유",
        "바이브코딩 격차가 벌어지는 이유",
        "ChatGPT를 쓰면 오히려 실력이 떨어지는 이유",
        "5년 안에 사라질 직업이 의외로 이것인 이유",
    ],
    "psychology": [
        "착한 사람이 오히려 더 불행한 이유",
        "열심히 노력할수록 목표가 멀어지는 이유",
        "자존감이 높을수록 관계가 힘들어지는 이유",
        "칭찬받을수록 의욕이 떨어지는 이유",
    ],
    "history": [
        "콜레라가 오히려 현대 도시를 구한 이유",
        "로마가 강대할수록 멸망이 빨라진 이유",
        "징기스칸이 죽인 사람이 많을수록 지구 온도가 내려간 이유",
        "조선이 쇄국할수록 오히려 발전한 분야가 있는 이유",
    ],
    "space": [
        "우주가 넓을수록 오히려 외로울 수밖에 없는 이유",
        "블랙홀이 클수록 오히려 덜 위험한 이유",
        "지구와 가장 비슷한 행성이 오히려 가장 살기 힘든 이유",
    ],
    "health": [
        "건강식을 먹을수록 오히려 살이 찌는 이유",
        "운동을 더 할수록 면역력이 떨어지는 이유",
        "잠을 많이 잘수록 오히려 더 피곤한 이유",
        "스트레스가 없으면 오히려 건강에 해로운 이유",
    ],
}

# ---------------------------------------------------------------------------
# 채널별 금지 표현 (LLM에 강제 지시)
# ---------------------------------------------------------------------------
_CHANNEL_FORBIDDEN: dict[str, str] = {
    "ai_tech": "막연한 미래 예언, '~될 것입니다' 형식, 뉴스 헤드라인 복사",
    "psychology": "학술 전문 용어 그대로 사용, 차갑고 딱딱한 표현",
    "history": "단순 연대기 나열, 교과서식 서술",
    "space": "단위 숫자만 나열 (비유 없이), 지루한 사실 열거",
    "health": "섣부른 의학 진단, 대체의학 권장, 과장된 공포 유발",
}


@dataclass
class ScoredAngle:
    """하나의 주제-각도-제목 세트."""

    topic: str  # 파이프라인 입력용 주제 (한국어)
    angle: str  # 각도 설명 (왜 이 관점인지)
    title: str  # 최종 제목 후보 (인지 부조화 공식 적용)
    hook_pattern: str  # "cognitive_dissonance" | "shocking_stat" | "myth_busting" | ...
    viral_score: float  # 0-10 (LLM 평가)
    source_keyword: str  # 원본 트렌드 키워드
    channel: str  # 채널 키
    title_variants: list[str] = field(default_factory=list)  # 제목 후보 3개


class TopicAngleGenerator:
    """트렌드 후보 → 인지 부조화 훅 제목 + 점수화.

    LLM에게 채널별 few-shot 예시를 제공해
    '[반전 결과] + [이유]' 패턴을 강제 적용한 제목을 생성합니다.
    """

    _SYSTEM_PROMPT = """\
You are a viral YouTube Shorts title strategist for Korean audiences.
Your job is to transform raw trend keywords into compelling short-form video angles.

## The Core Formula (MUST follow)
[예상과 반대되는 결과] + [이유]
Examples:
{examples}

## Rules
1. ALWAYS use the cognitive dissonance pattern — something that contradicts expectation
2. Each title must trigger "어? 왜?" reaction immediately
3. Titles must be 15-30 characters in Korean
4. Generate EXACTLY 3 title variants per candidate, pick the best as "title"
5. Score 0-10 where 10 = guaranteed viral (be honest, most should be 5-8)
6. Avoid: {forbidden}

## Output (valid JSON only)
{{
  "angles": [
    {{
      "topic": "파이프라인 입력용 주제 키워드 (5-15자)",
      "angle": "이 각도를 선택한 이유 한 줄 (한국어)",
      "title": "최종 제목 (인지 부조화 공식 적용, 한국어)",
      "title_variants": ["후보1", "후보2", "후보3"],
      "hook_pattern": "cognitive_dissonance|shocking_stat|myth_busting|counterintuitive_question",
      "viral_score": 7.5,
      "source_keyword": "원본 트렌드 키워드"
    }}
  ]
}}
"""

    def __init__(self, config: AppConfig, llm_router: LLMRouter):
        self.config = config
        self.llm_router = llm_router

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run(
        self,
        candidates: list[TrendCandidate],
        channel_key: str,
        n: int = 5,
    ) -> list[ScoredAngle]:
        """트렌드 후보를 각도+제목으로 변환.

        Args:
            candidates: TrendDiscoveryStep에서 반환된 후보 리스트
            channel_key: 채널 키
            n: 반환할 최대 결과 수

        Returns:
            viral_score 내림차순 정렬된 ScoredAngle 리스트
        """
        if not candidates:
            logger.warning("[TopicAngle] No candidates provided")
            return []

        start = time.monotonic()

        # 배치 처리: 최대 10개 후보를 한 번의 LLM 호출로 처리
        batch = candidates[:10]
        system_prompt = self._build_system_prompt(channel_key)
        user_prompt = self._build_user_prompt(batch, channel_key, n)

        try:
            result = self.llm_router.generate_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                temperature=0.8,
            )
            angles = self._parse_angles(result, channel_key)
        except Exception as exc:
            logger.warning("[TopicAngle] LLM failed: %s", exc)
            angles = self._fallback_angles(batch[:n], channel_key)

        # 점수 정렬 후 n개 반환
        angles.sort(key=lambda a: a.viral_score, reverse=True)
        result_angles = angles[:n]

        elapsed = round(time.monotonic() - start, 2)
        logger.info(
            "[TopicAngle] done: %d angles in %.1fs (channel=%s, top_score=%.1f)",
            len(result_angles),
            elapsed,
            channel_key,
            result_angles[0].viral_score if result_angles else 0,
        )
        return result_angles

    def run_single(self, keyword: str, channel_key: str) -> ScoredAngle | None:
        """단일 키워드에 대한 각도 생성 (빠른 테스트용)."""
        candidate = TrendCandidate(
            keyword=keyword,
            source="manual",
            score=0.8,
            channel=channel_key,
        )
        results = self.run([candidate], channel_key, n=1)
        return results[0] if results else None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _build_system_prompt(self, channel_key: str) -> str:
        examples = _CHANNEL_HOOK_EXAMPLES.get(channel_key, _CHANNEL_HOOK_EXAMPLES["ai_tech"])
        examples_str = "\n".join(f'  - "{ex}"' for ex in examples)
        forbidden = _CHANNEL_FORBIDDEN.get(channel_key, "막연한 표현, 뉴스 헤드라인 복사")
        return self._SYSTEM_PROMPT.format(
            examples=examples_str,
            forbidden=forbidden,
        )

    @staticmethod
    def _build_user_prompt(
        candidates: list[TrendCandidate],
        channel_key: str,
        n: int,
    ) -> str:
        channel_name_map = {
            "ai_tech": "퓨처 시냅스 (AI/기술 채널)",
            "psychology": "토닥토닥 심리 (심리학 채널)",
            "history": "역사팝콘 (역사/고고학 채널)",
            "space": "도파민 랩 (우주/천문학 채널)",
            "health": "건강 스포일러 (의학/건강 채널)",
        }
        ch_name = channel_name_map.get(channel_key, channel_key)

        lines = [
            f"채널: {ch_name}",
            f"상위 {n}개 각도를 생성하세요.",
            "",
            "트렌드 후보 목록:",
        ]
        for i, c in enumerate(candidates, 1):
            lines.append(f"  {i}. [{c.source}] {c.keyword} (트렌드 강도: {c.score:.2f})")

        lines.extend(
            [
                "",
                "각 후보에 대해 가장 바이럴 가능성이 높은 각도와 인지 부조화 제목을 생성하세요.",
                f"최종적으로 viral_score 기준 상위 {n}개만 반환하세요.",
            ]
        )
        return "\n".join(lines)

    def _parse_angles(self, result: dict, channel_key: str) -> list[ScoredAngle]:
        """LLM JSON 응답 → ScoredAngle 리스트."""
        if not isinstance(result, dict):
            return []

        raw_angles = result.get("angles", [])
        angles: list[ScoredAngle] = []

        for item in raw_angles:
            if not isinstance(item, dict):
                continue
            topic = str(item.get("topic", "")).strip()
            title = str(item.get("title", "")).strip()
            if not topic or not title:
                continue

            try:
                viral_score = float(item.get("viral_score", 5.0))
                viral_score = max(0.0, min(10.0, viral_score))
            except (TypeError, ValueError):
                viral_score = 5.0

            angles.append(
                ScoredAngle(
                    topic=topic,
                    angle=str(item.get("angle", "")).strip(),
                    title=title,
                    hook_pattern=str(item.get("hook_pattern", "cognitive_dissonance")).strip(),
                    viral_score=viral_score,
                    source_keyword=str(item.get("source_keyword", topic)).strip(),
                    channel=channel_key,
                    title_variants=[str(v).strip() for v in item.get("title_variants", []) if str(v).strip()],
                )
            )
        return angles

    @staticmethod
    def _fallback_angles(
        candidates: list[TrendCandidate],
        channel_key: str,
    ) -> list[ScoredAngle]:
        """LLM 호출 실패 시 키워드 기반 기본 각도 생성."""
        angles: list[ScoredAngle] = []
        for c in candidates:
            # 간단한 인지 부조화 패턴 적용
            title = f"{c.keyword}이(가) 오히려 역효과를 내는 이유"
            angles.append(
                ScoredAngle(
                    topic=c.keyword,
                    angle="LLM 실패 — 기본 인지 부조화 패턴 적용",
                    title=title,
                    hook_pattern="cognitive_dissonance",
                    viral_score=c.score * 6.0,  # 트렌드 강도를 점수로 변환
                    source_keyword=c.keyword,
                    channel=channel_key,
                    title_variants=[title],
                )
            )
        return angles
