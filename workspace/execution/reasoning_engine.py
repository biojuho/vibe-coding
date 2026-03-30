"""
귀납적 추론 엔진 (Inductive Reasoning Engine)

Popper의 반증주의 기반 3단계 추론 파이프라인:
  Step 1: 사실 추출 (Fact Extraction)
  Step 2: 가설 생성 (Hypothesis Generation) — 기존 패턴과 교차 연결
  Step 3: 반증 시도 (Falsification) — 생존 가설만 패턴 승격

Usage:
    from execution.reasoning_engine import ReasoningAdapter
    adapter = ReasoningAdapter()
    result = adapter.run_full_reasoning(
        report_id="run-001",
        category="AI_테크",
        content_text="뉴스 분석 텍스트...",
    )
    print(result["new_patterns"])  # 새로 생성/강화된 패턴
"""

from __future__ import annotations

import json
import os
import re
import sqlite3
import sys
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402


# ── 도메인 모델 ──────────────────────────────────────────────


@dataclass
class FactFragment:
    """검증 가능한 사실 파편."""

    fact_id: str
    report_id: str
    fact_text: str
    why_question: str
    category: str
    source_title: str
    created_at: str


@dataclass
class Hypothesis:
    """사실 기반 가설."""

    hypothesis_id: str
    hypothesis_text: str
    based_on_facts: list[str] = field(default_factory=list)
    related_pattern: str = ""
    status: str = "pending"  # "pending" | "survived" | "falsified"
    created_at: str = ""


# ── 견고한 JSON 파서 ─────────────────────────────────────────


def _robust_json_parse(text: str) -> list[dict[str, Any]]:
    """5단계 견고 파서 — LLM의 불완전 JSON 대응.

    Returns a list of dicts. If the top-level result is a dict,
    it is wrapped in a list for uniform handling.
    """
    if not text or not text.strip():
        return []

    def _ensure_list(obj: Any) -> list[dict[str, Any]]:
        if isinstance(obj, list):
            return obj
        if isinstance(obj, dict):
            return [obj]
        return []

    # Stage 1: 마크다운 펜스 제거
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # Stage 2: 직접 파싱 시도
    try:
        return _ensure_list(json.loads(cleaned))
    except json.JSONDecodeError:
        pass

    # Stage 3: 값 내부 줄바꿈 치환 (JSON 문자열 값 안의 \n → 공백)
    stage3 = re.sub(
        r'("(?:[^"\\]|\\.)*")',
        lambda m: m.group(0).replace("\n", " ").replace("\r", " "),
        cleaned,
    )
    try:
        return _ensure_list(json.loads(stage3))
    except json.JSONDecodeError:
        pass

    # Stage 4: 전체 newline collapse 후 재시도
    stage4 = cleaned.replace("\n", " ").replace("\r", " ")
    # collapse multiple spaces
    stage4 = re.sub(r"\s+", " ", stage4).strip()
    try:
        return _ensure_list(json.loads(stage4))
    except json.JSONDecodeError:
        pass

    # Stage 5: 최후 수단 — regex로 개별 {...} 객체 추출
    results: list[dict[str, Any]] = []
    brace_depth = 0
    start_idx = -1
    for i, ch in enumerate(cleaned):
        if ch == "{":
            if brace_depth == 0:
                start_idx = i
            brace_depth += 1
        elif ch == "}":
            brace_depth -= 1
            if brace_depth == 0 and start_idx >= 0:
                candidate = cleaned[start_idx : i + 1]
                # collapse newlines inside candidate
                candidate = candidate.replace("\n", " ").replace("\r", " ")
                try:
                    obj = json.loads(candidate)
                    if isinstance(obj, dict):
                        results.append(obj)
                except json.JSONDecodeError:
                    pass
                start_idx = -1

    if results:
        return results

    logger.warning("_robust_json_parse: 모든 단계 실패, 빈 결과 반환")
    return []


# ── DB Layer ─────────────────────────────────────────────────


_DEFAULT_DB_PATH = WORKSPACE_ROOT / ".tmp" / "reasoning.db"


def _get_db_path() -> Path:
    env = os.getenv("REASONING_DB_PATH", "").strip()
    return Path(env) if env else _DEFAULT_DB_PATH


def _init_db(conn: sqlite3.Connection) -> None:
    """3개 테이블 초기화."""
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS fact_fragments (
            fact_id TEXT PRIMARY KEY,
            report_id TEXT,
            fact_text TEXT,
            why_question TEXT,
            category TEXT,
            source_title TEXT,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS hypotheses (
            hypothesis_id TEXT PRIMARY KEY,
            hypothesis_text TEXT,
            based_on_facts TEXT,
            related_pattern TEXT,
            status TEXT DEFAULT 'pending',
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS reasoning_patterns (
            pattern_id TEXT PRIMARY KEY,
            pattern_text TEXT,
            category TEXT,
            evidence_facts TEXT,
            strength TEXT DEFAULT 'emerging',
            survival_count INTEGER DEFAULT 1,
            created_at TEXT,
            updated_at TEXT
        );
        """
    )


def _get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or _get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


def _strength_for_count(count: int) -> str:
    """survival_count 기반 strength 산출."""
    if count >= 5:
        return "strong"
    if count >= 3:
        return "moderate"
    return "emerging"


# ── ReasoningAdapter (핵심 엔진) ─────────────────────────────


class ReasoningAdapter:
    """Popper 반증주의 기반 3단계 추론 어댑터.

    LLM 호출 3회/런. 기존 LLMClient를 활용합니다.
    """

    def __init__(
        self,
        *,
        db_path: Path | None = None,
        llm_client: Any | None = None,
        providers: list[str] | None = None,
    ):
        self.db_path = db_path
        self._llm = llm_client

        # lazy import: LLMClient is heavy
        self._providers = providers

    @property
    def llm(self) -> Any:
        if self._llm is None:
            from execution.llm_client import LLMClient

            kwargs: dict[str, Any] = {
                "caller_script": "reasoning_engine",
                "cache_ttl_sec": 0,  # 추론은 매번 새로운 결과 필요
            }
            if self._providers:
                kwargs["providers"] = self._providers
            self._llm = LLMClient(**kwargs)
        return self._llm

    def is_available(self) -> bool:
        """LLM 프로바이더가 하나 이상 활성화되어 있는지 확인."""
        try:
            return len(self.llm.enabled_providers()) > 0
        except Exception:
            return False

    # ── Step 1: 사실 추출 ────────────────────────────────────

    def step1_extract_facts(
        self,
        content_text: str,
        *,
        report_id: str,
        category: str,
        source_title: str = "",
        max_facts: int = 8,
    ) -> list[FactFragment]:
        """콘텐츠에서 검증 가능한 사실 파편 추출 (최대 max_facts개)."""
        system_prompt = (
            "당신은 전문 사실 추출기입니다. "
            "콘텐츠에서 검증 가능한 사실을 추출하세요.\n"
            "규칙:\n"
            f"- 최대 {max_facts}개\n"
            "- 각 사실은 독립적으로 검증 가능해야 합니다\n"
            "- JSON 값 안에 줄바꿈을 넣지 마세요\n"
            '- 출력: JSON 배열만. [{"fact_text": "...", "why_question": "왜 중요한가?"}]\n'
            "- 다른 텍스트는 절대 포함하지 마세요"
        )
        user_prompt = f"카테고리: {category}\n\n콘텐츠:\n{content_text[:3000]}"

        raw = self.llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        # generate_json returns dict or list
        items: list[dict[str, Any]]
        if isinstance(raw, list):
            items = raw[:max_facts]
        elif isinstance(raw, dict):
            # some models wrap in {"facts": [...]}
            for key in ("facts", "results", "data", "items"):
                if key in raw and isinstance(raw[key], list):
                    items = raw[key][:max_facts]
                    break
            else:
                items = [raw]
        else:
            items = []

        now = datetime.now(tz=timezone.utc).isoformat()
        facts: list[FactFragment] = []
        for i, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            fact_text = str(item.get("fact_text", "")).strip()
            if not fact_text:
                continue
            fact = FactFragment(
                fact_id=f"F-{report_id}-{i}",
                report_id=report_id,
                fact_text=fact_text,
                why_question=str(item.get("why_question", "")).strip(),
                category=category,
                source_title=source_title,
                created_at=now,
            )
            facts.append(fact)

        # DB 저장
        self._save_facts(facts)
        logger.info("Step1 사실 추출 완료: %d개", len(facts))
        return facts

    def _save_facts(self, facts: list[FactFragment]) -> None:
        with _get_connection(self.db_path) as conn:
            for f in facts:
                conn.execute(
                    "INSERT OR REPLACE INTO fact_fragments VALUES (?,?,?,?,?,?,?)",
                    (
                        f.fact_id,
                        f.report_id,
                        f.fact_text,
                        f.why_question,
                        f.category,
                        f.source_title,
                        f.created_at,
                    ),
                )

    # ── Step 2: 가설 생성 ────────────────────────────────────

    def step2_hypothesize(
        self,
        facts: list[FactFragment],
        *,
        category: str,
        max_hypotheses: int = 5,
    ) -> list[Hypothesis]:
        """사실 교차 연결 → 가설 생성."""
        existing_patterns = self._load_patterns(category)
        pattern_summary = (
            "\n".join(
                f"- [{p['pattern_id']}] {p['pattern_text']} (strength: {p['strength']})" for p in existing_patterns
            )
            or "(기존 패턴 없음)"
        )

        facts_text = "\n".join(f"- [{f.fact_id}] {f.fact_text}" for f in facts)

        system_prompt = (
            "당신은 패턴 분석 전문가입니다. "
            "사실들 사이의 패턴을 발견하고 가설을 세우세요.\n"
            "규칙:\n"
            f"- 최대 {max_hypotheses}개 가설\n"
            "- 기존 패턴과 교차 연결 시도\n"
            "- JSON 값 안에 줄바꿈을 넣지 마세요\n"
            '- 출력: JSON 배열만. [{"hypothesis": "가설 텍스트", '
            '"based_on": ["F-xxx-1", "F-xxx-2"], '
            '"pattern": "연결된 패턴 또는 새 패턴 제안"}]\n'
            "- 다른 텍스트는 절대 포함하지 마세요"
        )
        user_prompt = f"카테고리: {category}\n\n사실들:\n{facts_text}\n\n기존 패턴:\n{pattern_summary}"

        raw = self.llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.5,
        )

        items: list[dict[str, Any]]
        if isinstance(raw, list):
            items = raw[:max_hypotheses]
        elif isinstance(raw, dict):
            for key in ("hypotheses", "results", "data", "items"):
                if key in raw and isinstance(raw[key], list):
                    items = raw[key][:max_hypotheses]
                    break
            else:
                items = [raw]
        else:
            items = []

        now = datetime.now(tz=timezone.utc).isoformat()
        hypotheses: list[Hypothesis] = []
        for i, item in enumerate(items, 1):
            if not isinstance(item, dict):
                continue
            h_text = str(item.get("hypothesis", "")).strip()
            if not h_text:
                continue
            h = Hypothesis(
                hypothesis_id=f"H-{uuid.uuid4().hex[:8]}",
                hypothesis_text=h_text,
                based_on_facts=item.get("based_on", []),
                related_pattern=str(item.get("pattern", "")),
                status="pending",
                created_at=now,
            )
            hypotheses.append(h)

        self._save_hypotheses(hypotheses)
        logger.info("Step2 가설 생성 완료: %d개", len(hypotheses))
        return hypotheses

    def _load_patterns(self, category: str) -> list[dict[str, Any]]:
        """카테고리별 기존 패턴 로드."""
        with _get_connection(self.db_path) as conn:
            rows = conn.execute(
                "SELECT * FROM reasoning_patterns WHERE category = ? ORDER BY survival_count DESC LIMIT 20",
                (category,),
            ).fetchall()
            return [dict(r) for r in rows]

    def _save_hypotheses(self, hypotheses: list[Hypothesis]) -> None:
        with _get_connection(self.db_path) as conn:
            for h in hypotheses:
                conn.execute(
                    "INSERT OR REPLACE INTO hypotheses VALUES (?,?,?,?,?,?)",
                    (
                        h.hypothesis_id,
                        h.hypothesis_text,
                        json.dumps(h.based_on_facts, ensure_ascii=False),
                        h.related_pattern,
                        h.status,
                        h.created_at,
                    ),
                )

    # ── Step 3: 반증 ─────────────────────────────────────────

    def step3_falsify(
        self,
        hypotheses: list[Hypothesis],
        *,
        category: str,
    ) -> list[dict[str, Any]]:
        """반증 시도 → 생존자만 패턴 승격."""
        h_text = "\n".join(f"- [{h.hypothesis_id}] {h.hypothesis_text}" for h in hypotheses)

        system_prompt = (
            "당신은 반증 전문가입니다. 각 가설을 반증하세요.\n"
            "규칙:\n"
            "- 반증을 견딘 가설만 survived\n"
            "- 반증에 실패하면 falsified\n"
            "- JSON 값 안에 줄바꿈을 넣지 마세요. 간결하게.\n"
            '- 출력: JSON 배열만. [{"hypothesis_id": "H-xxx", '
            '"hypothesis": "요약", '
            '"status": "survived" 또는 "falsified", '
            '"counter": "반증 내용", '
            '"new_pattern": "생존 시 패턴 텍스트 (falsified면 빈 문자열)"}]\n'
            "- 다른 텍스트는 절대 포함하지 마세요"
        )
        user_prompt = f"카테고리: {category}\n\n가설들:\n{h_text}"

        raw = self.llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=0.3,
        )

        items: list[dict[str, Any]]
        if isinstance(raw, list):
            items = raw
        elif isinstance(raw, dict):
            for key in ("results", "hypotheses", "data", "items"):
                if key in raw and isinstance(raw[key], list):
                    items = raw[key]
                    break
            else:
                items = [raw]
        else:
            items = []

        now = datetime.now(tz=timezone.utc).isoformat()
        new_patterns: list[dict[str, Any]] = []

        # 가설 ID → 가설 매핑
        h_map = {h.hypothesis_id: h for h in hypotheses}

        with _get_connection(self.db_path) as conn:
            for item in items:
                if not isinstance(item, dict):
                    continue

                h_id = str(item.get("hypothesis_id", ""))
                status = str(item.get("status", "falsified")).lower()
                new_pattern_text = str(item.get("new_pattern", "")).strip()

                # 가설 상태 업데이트
                if h_id in h_map:
                    h_map[h_id].status = status
                    conn.execute(
                        "UPDATE hypotheses SET status = ? WHERE hypothesis_id = ?",
                        (status, h_id),
                    )

                # 생존 가설 → 패턴 승격
                if status == "survived" and new_pattern_text:
                    pattern_info = self._upsert_pattern(
                        conn,
                        pattern_text=new_pattern_text,
                        category=category,
                        evidence_facts=h_map[h_id].based_on_facts if h_id in h_map else [],
                        now=now,
                    )
                    new_patterns.append(pattern_info)

        logger.info(
            "Step3 반증 완료: %d survived, %d falsified, %d 패턴",
            sum(1 for it in items if isinstance(it, dict) and it.get("status") == "survived"),
            sum(1 for it in items if isinstance(it, dict) and it.get("status") == "falsified"),
            len(new_patterns),
        )
        return new_patterns

    def _upsert_pattern(
        self,
        conn: sqlite3.Connection,
        *,
        pattern_text: str,
        category: str,
        evidence_facts: list[str],
        now: str,
    ) -> dict[str, Any]:
        """패턴 삽입 또는 기존 패턴 강화."""
        # 유사 패턴 검색 (단순 텍스트 매칭)
        existing = conn.execute(
            "SELECT * FROM reasoning_patterns WHERE category = ? AND pattern_text = ?",
            (category, pattern_text),
        ).fetchone()

        if existing:
            new_count = existing["survival_count"] + 1
            new_strength = _strength_for_count(new_count)
            # 기존 evidence에 새 evidence 합치기
            old_evidence = json.loads(existing["evidence_facts"] or "[]")
            merged = list(set(old_evidence + evidence_facts))
            conn.execute(
                "UPDATE reasoning_patterns "
                "SET survival_count = ?, strength = ?, evidence_facts = ?, updated_at = ? "
                "WHERE pattern_id = ?",
                (
                    new_count,
                    new_strength,
                    json.dumps(merged, ensure_ascii=False),
                    now,
                    existing["pattern_id"],
                ),
            )
            return {
                "pattern_id": existing["pattern_id"],
                "pattern_text": pattern_text,
                "strength": new_strength,
                "survival_count": new_count,
                "action": "strengthened",
            }
        else:
            pid = f"P-{uuid.uuid4().hex[:8]}"
            conn.execute(
                "INSERT INTO reasoning_patterns VALUES (?,?,?,?,?,?,?,?)",
                (
                    pid,
                    pattern_text,
                    category,
                    json.dumps(evidence_facts, ensure_ascii=False),
                    "emerging",
                    1,
                    now,
                    now,
                ),
            )
            return {
                "pattern_id": pid,
                "pattern_text": pattern_text,
                "strength": "emerging",
                "survival_count": 1,
                "action": "created",
            }

    # ── 통합 실행 ─────────────────────────────────────────────

    def run_full_reasoning(
        self,
        *,
        report_id: str,
        category: str,
        content_text: str,
        source_title: str = "",
        use_chain: bool = False,
        use_verifier: bool = False,
    ) -> dict[str, Any]:
        """3단계 추론 파이프라인 전체 실행.

        Args:
            report_id: 보고서 ID
            category: 카테고리
            content_text: 분석할 콘텐츠 텍스트
            source_title: 출처 제목
            use_chain: True면 각 Step에서 ReasoningChain (다중 샘플 합의) 적용
            use_verifier: True면 Step 3 반증에 ConfidenceVerifier 추가 검증

        Returns:
            {
                "report_id": str,
                "category": str,
                "facts": [...],
                "hypotheses": [...],
                "new_patterns": [...],
                "stats": {...},
                "advanced_reasoning": {...},  # use_chain/use_verifier 사용 시
            }
        """
        logger.info("=== 귀납적 추론 시작: %s [%s] ===", report_id, category)
        advanced_info: dict[str, Any] = {}

        # Step 1
        facts = self.step1_extract_facts(
            content_text,
            report_id=report_id,
            category=category,
            source_title=source_title,
        )
        if not facts:
            logger.warning("사실 추출 결과 없음 → 추론 중단")
            return {
                "report_id": report_id,
                "category": category,
                "facts": [],
                "hypotheses": [],
                "new_patterns": [],
                "stats": {"survived": 0, "falsified": 0, "patterns_created": 0, "patterns_strengthened": 0},
            }

        # Step 2
        hypotheses = self.step2_hypothesize(facts, category=category)

        if not hypotheses:
            logger.warning("가설 생성 결과 없음 → 반증 건너뜀")
            return {
                "report_id": report_id,
                "category": category,
                "facts": [asdict(f) for f in facts],
                "hypotheses": [],
                "new_patterns": [],
                "stats": {"survived": 0, "falsified": 0, "patterns_created": 0, "patterns_strengthened": 0},
            }

        # Step 3
        new_patterns = self.step3_falsify(hypotheses, category=category)

        # Advanced: ConfidenceVerifier로 반증 결과 추가 검증
        if use_verifier and new_patterns:
            try:
                from execution.confidence_verifier import ConfidenceVerifier

                verifier = ConfidenceVerifier(llm_client=self.llm)
                verification_results = []
                for pattern in new_patterns:
                    v_result = verifier.verify(
                        question=f"패턴 '{pattern.get('pattern_text', '')}'이 {category} 카테고리에서 타당한가?",
                        answer=pattern.get("pattern_text", ""),
                    )
                    verification_results.append(
                        {
                            "pattern_id": pattern.get("pattern_id"),
                            "confidence": v_result.confidence,
                            "is_reliable": v_result.is_reliable,
                        }
                    )
                advanced_info["verification"] = verification_results
                logger.info("ConfidenceVerifier 검증 완료: %d 패턴", len(verification_results))
            except Exception as e:
                logger.warning("ConfidenceVerifier 실패: %s", e)

        # Advanced: ReasoningChain으로 결과 종합 검증
        if use_chain:
            try:
                from execution.reasoning_chain import ReasoningChain

                chain = ReasoningChain(llm_client=self.llm, n_samples=3)
                chain_result = chain.reason(
                    system_prompt="당신은 추론 결과를 검증하는 전문가입니다.",
                    user_prompt=(
                        f"카테고리: {category}\n"
                        f"추출된 사실 수: {len(facts)}\n"
                        f"생성된 가설 수: {len(hypotheses)}\n"
                        f"발견된 패턴: {json.dumps([p.get('pattern_text', '') for p in new_patterns], ensure_ascii=False)}\n\n"
                        f"이 추론 결과의 품질과 일관성을 0~10으로 평가하고 간단히 설명하세요."
                    ),
                )
                advanced_info["chain_review"] = {
                    "confidence": chain_result.confidence,
                    "consensus_ratio": chain_result.consensus_ratio,
                    "n_samples": chain_result.n_samples_used,
                    "review": chain_result.answer[:300],
                }
                logger.info("ReasoningChain 검증 완료: confidence=%.2f", chain_result.confidence)
            except Exception as e:
                logger.warning("ReasoningChain 실패: %s", e)

        stats = {
            "survived": sum(1 for h in hypotheses if h.status == "survived"),
            "falsified": sum(1 for h in hypotheses if h.status == "falsified"),
            "patterns_created": sum(1 for p in new_patterns if p.get("action") == "created"),
            "patterns_strengthened": sum(1 for p in new_patterns if p.get("action") == "strengthened"),
        }

        result: dict[str, Any] = {
            "report_id": report_id,
            "category": category,
            "facts": [asdict(f) for f in facts],
            "hypotheses": [asdict(h) for h in hypotheses],
            "new_patterns": new_patterns,
            "stats": stats,
        }
        if advanced_info:
            result["advanced_reasoning"] = advanced_info

        logger.info("=== 귀납적 추론 완료: %s ===", stats)
        return result

    # ── 유틸리티 ──────────────────────────────────────────────

    def get_pattern_stats(self, category: str | None = None) -> dict[str, Any]:
        """패턴 DB 통계."""
        with _get_connection(self.db_path) as conn:
            if category:
                total = conn.execute(
                    "SELECT COUNT(*) FROM reasoning_patterns WHERE category = ?",
                    (category,),
                ).fetchone()[0]
            else:
                total = conn.execute("SELECT COUNT(*) FROM reasoning_patterns").fetchone()[0]

            by_strength = {}
            for s in ("emerging", "moderate", "strong"):
                if category:
                    by_strength[s] = conn.execute(
                        "SELECT COUNT(*) FROM reasoning_patterns WHERE strength = ? AND category = ?",
                        (s, category),
                    ).fetchone()[0]
                else:
                    by_strength[s] = conn.execute(
                        "SELECT COUNT(*) FROM reasoning_patterns WHERE strength = ?",
                        (s,),
                    ).fetchone()[0]

            if category:
                top_patterns = conn.execute(
                    "SELECT pattern_id, pattern_text, strength, survival_count "
                    "FROM reasoning_patterns WHERE category = ? "
                    "ORDER BY survival_count DESC LIMIT 10",
                    (category,),
                ).fetchall()
                total_facts = conn.execute(
                    "SELECT COUNT(*) FROM fact_fragments WHERE category = ?",
                    (category,),
                ).fetchone()[0]
            else:
                top_patterns = conn.execute(
                    "SELECT pattern_id, pattern_text, strength, survival_count "
                    "FROM reasoning_patterns ORDER BY survival_count DESC LIMIT 10"
                ).fetchall()
                total_facts = conn.execute("SELECT COUNT(*) FROM fact_fragments").fetchone()[0]

            return {
                "total_patterns": total,
                "by_strength": by_strength,
                "top_patterns": [dict(r) for r in top_patterns],
                "total_facts": total_facts,
                "total_hypotheses": conn.execute("SELECT COUNT(*) FROM hypotheses").fetchone()[0],
            }
