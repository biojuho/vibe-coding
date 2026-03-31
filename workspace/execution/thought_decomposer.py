"""
Forest-of-Thought — 복잡 문제 재귀적 서브태스크 분해기.

긴 컨텍스트와 복잡한 요청을 독립 서브태스크 트리로 분해하고,
각 서브태스크를 독립 LLM 호출로 실행한 뒤 결과를 bottom-up 합성합니다.
이를 통해 "context rot" (긴 컨텍스트에서의 추론 품질 저하)를 방지합니다.

Usage:
    from execution.thought_decomposer import ThoughtDecomposer
    from execution.llm_client import LLMClient

    decomposer = ThoughtDecomposer(llm_client=LLMClient())
    result = decomposer.solve(
        "Python으로 REST API 서버를 구현하세요. "
        "인증, 데이터베이스, 에러 처리를 포함해야 합니다."
    )
    print(result.final_answer)
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from execution._logging import logger  # noqa: E402


@dataclass
class TaskNode:
    """서브태스크 트리 노드."""

    task_text: str
    depth: int = 0
    children: list[TaskNode] = field(default_factory=list)
    result: str = ""
    status: str = "pending"  # "pending" | "completed" | "failed"


@dataclass
class CompositeResult:
    """분해 + 실행 + 합성 결과."""

    final_answer: str
    tree: TaskNode
    total_subtasks: int
    completed_subtasks: int
    failed_subtasks: int
    depth_reached: int


class ThoughtDecomposer:
    """Forest-of-Thought 서브태스크 분해기.

    1. 분해 (Decompose): LLM을 사용하여 복잡한 작업을 1~5개 서브태스크로 분해
    2. 실행 (Execute): 리프 노드부터 bottom-up으로 각 서브태스크 독립 실행
    3. 합성 (Synthesize): 서브태스크 결과를 합쳐 최종 답변 생성

    깊이 제한 (기본 3)으로 과도한 분해를 방지합니다.
    """

    def __init__(
        self,
        llm_client: Any,
        *,
        max_depth: int = 3,
        max_children: int = 5,
    ):
        self.llm = llm_client
        self.max_depth = max_depth
        self.max_children = max_children

    def decompose(self, task_description: str, *, depth: int = 0) -> TaskNode:
        """작업을 서브태스크 트리로 분해합니다.

        재귀적으로 각 서브태스크를 다시 분해하되,
        max_depth에 도달하면 리프 노드로 남깁니다.
        """
        root = TaskNode(task_text=task_description, depth=depth)

        # 깊이 제한
        if depth >= self.max_depth:
            logger.info("ThoughtDecomposer: 최대 깊이 %d 도달, 리프로 유지", depth)
            return root

        # 분해 가능 여부 판단 — 단순한 작업은 분해하지 않음
        if self._is_atomic(task_description):
            logger.info("ThoughtDecomposer: 원자적 작업, 분해 불필요")
            return root

        # LLM에게 서브태스크 분해 요청
        try:
            subtasks = self._generate_subtasks(task_description)
        except Exception as e:
            logger.warning("ThoughtDecomposer: 분해 실패 (%s), 리프로 유지", e)
            return root

        if not subtasks or len(subtasks) < 2:
            # 분해할 필요 없는 단순 작업
            return root

        for st in subtasks[: self.max_children]:
            child = self.decompose(st, depth=depth + 1)
            root.children.append(child)

        return root

    def _is_atomic(self, task: str) -> bool:
        """작업이 더 이상 분해할 필요 없는 원자적 작업인지 판단."""
        word_count = len(task.split())
        char_count = len(task)
        # 짧은 작업: 20단어 미만 AND 100자 미만 (CJK 텍스트는 공백이 적음)
        if word_count < 20 and char_count < 100:
            return True
        # 단일 동사 + 목적어 패턴도 원자적
        simple_patterns = ["print", "return", "import", "install", "add", "remove"]
        task_lower = task.lower().strip()
        for p in simple_patterns:
            if task_lower.startswith(p):
                return True
        return False

    def _generate_subtasks(self, task: str) -> list[str]:
        """LLM을 사용하여 작업을 서브태스크로 분해."""
        system_prompt = (
            "당신은 복잡한 소프트웨어 개발 작업을 독립된 서브태스크로 분해하는 전문가입니다.\n"
            "규칙:\n"
            "- 2~5개의 독립된 서브태스크로만 분해\n"
            "- 각 서브태스크는 다른 서브태스크 없이 독립적으로 답변 가능해야 함\n"
            "- 순서가 중요하면 의존성 순으로 나열\n"
            '- 출력: JSON 배열만. ["서브태스크1", "서브태스크2", ...]\n'
            "- 다른 텍스트는 절대 포함하지 마세요"
        )

        raw = self.llm.generate_json(
            system_prompt=system_prompt,
            user_prompt=f"다음 작업을 서브태스크로 분해하세요:\n\n{task}",
            temperature=0.3,
        )

        if isinstance(raw, list):
            return [str(item) for item in raw if isinstance(item, str)]
        if isinstance(raw, dict):
            for key in ("subtasks", "tasks", "steps", "items"):
                if key in raw and isinstance(raw[key], list):
                    return [str(item) for item in raw[key] if isinstance(item, str)]
        return []

    def execute_tree(self, tree: TaskNode) -> TaskNode:
        """트리를 bottom-up으로 실행합니다.

        리프 노드를 먼저 실행하고, 부모 노드는 자식 결과를 종합합니다.
        """
        if tree.children:
            # 자식 먼저 실행 (재귀)
            for child in tree.children:
                self.execute_tree(child)

            # 자식 결과를 종합하여 부모 실행
            child_results = "\n\n".join(
                f"[서브태스크 {i + 1}] {c.task_text}\n결과: {c.result}"
                for i, c in enumerate(tree.children)
                if c.status == "completed"
            )

            try:
                tree.result = self.llm.generate_text(
                    system_prompt=("서브태스크 결과를 종합하여 원래 작업에 대한 완전한 답변을 작성하세요."),
                    user_prompt=(f"원래 작업: {tree.task_text}\n\n서브태스크 결과:\n{child_results}"),
                    temperature=0.3,
                )
                tree.status = "completed"
            except Exception as e:
                tree.result = f"합성 실패: {e}"
                tree.status = "failed"
        else:
            # 리프 노드: 직접 실행
            try:
                tree.result = self.llm.generate_text(
                    system_prompt="주어진 작업을 완수하세요. 간결하고 정확하게 답변하세요.",
                    user_prompt=tree.task_text,
                    temperature=0.5,
                )
                tree.status = "completed"
            except Exception as e:
                tree.result = f"실행 실패: {e}"
                tree.status = "failed"

        logger.info(
            "ThoughtDecomposer node [depth=%d]: %s → %s",
            tree.depth,
            tree.task_text[:50],
            tree.status,
        )
        return tree

    def solve(self, task_description: str) -> CompositeResult:
        """분해 → 실행 → 합성 전체 파이프라인.

        Args:
            task_description: 해결할 복잡한 작업 설명

        Returns:
            CompositeResult
        """
        logger.info("=== ThoughtDecomposer 시작: %s ===", task_description[:80])

        # 1. 분해
        tree = self.decompose(task_description)

        # 2. 실행
        tree = self.execute_tree(tree)

        # 3. 통계 수집
        total, completed, failed, max_depth = self._tree_stats(tree)

        logger.info(
            "=== ThoughtDecomposer 완료: %d/%d 성공, 깊이 %d ===",
            completed,
            total,
            max_depth,
        )

        return CompositeResult(
            final_answer=tree.result,
            tree=tree,
            total_subtasks=total,
            completed_subtasks=completed,
            failed_subtasks=failed,
            depth_reached=max_depth,
        )

    def _tree_stats(self, node: TaskNode) -> tuple[int, int, int, int]:
        """트리 통계: (total, completed, failed, max_depth)."""
        total = 1
        completed = 1 if node.status == "completed" else 0
        failed = 1 if node.status == "failed" else 0
        max_depth = node.depth

        for child in node.children:
            ct, cc, cf, cd = self._tree_stats(child)
            total += ct
            completed += cc
            failed += cf
            max_depth = max(max_depth, cd)

        return total, completed, failed, max_depth
