"""blind-to-x 드래프트 품질 평가용 골든/거부 케이스 추출기 (T-254).

`directives/llm_eval_promptfoo.md` 의 1단계 스크립트.

Notion에서 다음 두 그룹을 추출해 promptfoo 입력 YAML로 변환한다:
  - 골든셋: status=승인됨 인 페이지의 (원문, 채택 드래프트)
  - 부정셋: status=패스 + reviewer_memo가 있는 페이지의 (원문, 거부 드래프트, reviewer_memo)

설계 원칙:
  - 순수 변환 함수(`extract_cases`, `to_yaml_dict`)는 Notion SDK 의존성 없음 → 단위 테스트 용이.
  - CLI 진입점은 Notion 호출을 lazy-import하므로 환경에 따라 sub-import 실패하지 않음.

Usage:
    python execution/blind_to_x_eval_extract.py --dry-run
    python execution/blind_to_x_eval_extract.py --apply --max-pages 200
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "tests" / "eval" / "blind-to-x"
DEFAULT_GOLDEN_FILENAME = "golden_cases.yaml"
DEFAULT_REJECTED_FILENAME = "rejected_cases.yaml"


@dataclass
class EvalCase:
    """promptfoo 입력 케이스의 정규화된 형태.

    promptfoo의 `tests` 항목에 1:1 매핑된다 — `vars`는 프롬프트 변수, `assert`는 검증 어서션.
    """

    page_id: str
    source_text: str
    accepted_draft: str = ""
    rejected_draft: str = ""
    reviewer_memo: str = ""
    status: str = ""

    def to_promptfoo_dict(self) -> dict[str, Any]:
        """promptfoo `tests` 항목 형식으로 직렬화."""
        vars_block: dict[str, Any] = {
            "source_text": self.source_text,
            "page_id": self.page_id,
        }
        if self.accepted_draft:
            vars_block["accepted_draft"] = self.accepted_draft
        if self.rejected_draft:
            vars_block["rejected_draft"] = self.rejected_draft
        if self.reviewer_memo:
            vars_block["reviewer_memo"] = self.reviewer_memo

        return {
            "description": f"{self.status}:{self.page_id}",
            "vars": vars_block,
        }


def _extract_text(prop: dict[str, Any] | None) -> str:
    """Notion 속성에서 사람이 읽는 텍스트만 추출 (rich_text/title 양쪽 지원)."""
    if not prop:
        return ""
    items: Iterable[dict[str, Any]] = prop.get("rich_text") or prop.get("title") or []
    return "".join(item.get("plain_text", "") for item in items).strip()


def extract_cases(
    pages: Iterable[dict[str, Any]],
    *,
    props: dict[str, str],
    status_filter: str,
) -> list[EvalCase]:
    """Notion 페이지 목록에서 EvalCase 시퀀스를 추출.

    Args:
        pages: Notion `databases.query` 응답의 `results` 리스트(또는 동등한 dict 시퀀스).
        props: `notion.properties` 매핑 (예: {"status": "상태", "source_text": "원문", ...}).
            blind-to-x `config.yaml` 의 `notion.properties` 와 동일 형식.
        status_filter: "승인됨" 또는 "패스" — 이 상태값을 가진 페이지만 통과.

    Returns:
        추출된 EvalCase 리스트. reviewer_memo가 비어있는 거부 페이지는 자동 스킵된다.
    """
    cases: list[EvalCase] = []
    status_prop = props.get("status", "상태")
    source_prop = props.get("source_text", "원문")
    accepted_prop = props.get("approved_draft", "최종 드래프트")
    rejected_prop = props.get("rejected_draft", "거부된 드래프트")
    memo_prop = props.get("reviewer_memo", "리뷰어 메모")

    for page in pages:
        properties = page.get("properties", {})
        status_data = properties.get(status_prop, {})
        status_name = (status_data.get("select") or status_data.get("status") or {}).get("name", "")
        if status_name != status_filter:
            continue

        source_text = _extract_text(properties.get(source_prop))
        if not source_text:
            continue

        accepted = _extract_text(properties.get(accepted_prop))
        rejected = _extract_text(properties.get(rejected_prop))
        memo = _extract_text(properties.get(memo_prop))

        # 거부 케이스는 reviewer_memo가 있어야 학습 가치가 있음
        if status_filter == "패스" and not memo:
            continue

        cases.append(
            EvalCase(
                page_id=page.get("id", ""),
                source_text=source_text,
                accepted_draft=accepted,
                rejected_draft=rejected,
                reviewer_memo=memo,
                status=status_name,
            )
        )
    return cases


def to_yaml_dict(cases: list[EvalCase], *, set_label: str) -> dict[str, Any]:
    """promptfoo 형식의 dict 로 변환 (yaml.safe_dump 가능)."""
    return {
        "label": set_label,
        "count": len(cases),
        "tests": [c.to_promptfoo_dict() for c in cases],
    }


def write_eval_yaml(payload: dict[str, Any], output_path: Path) -> None:
    """YAML 직렬화 + 디렉터리 생성."""
    import yaml  # 지연 import — 단위 테스트에서 불필요한 의존 회피

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as fp:
        yaml.safe_dump(payload, fp, allow_unicode=True, sort_keys=False)


def load_blind_config(config_path: Path) -> dict[str, Any]:
    """blind-to-x config.yaml 로드 (lazy import)."""
    import yaml

    with config_path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def _query_notion_pages(database_id: str, max_pages: int) -> list[dict[str, Any]]:
    """Notion DB 전체 페이지를 cursor 기반으로 조회. CLI 전용."""
    from notion_client import Client  # type: ignore[import-not-found]

    import os

    token = os.getenv("NOTION_API_KEY") or os.getenv("NOTION_TOKEN")
    if not token:
        raise RuntimeError("NOTION_API_KEY 환경변수가 필요합니다.")

    client = Client(auth=token)
    pages: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        params: dict[str, Any] = {"database_id": database_id, "page_size": min(100, max_pages - len(pages))}
        if cursor:
            params["start_cursor"] = cursor
        resp = client.databases.query(**params)
        pages.extend(resp.get("results", []))
        if not resp.get("has_more") or len(pages) >= max_pages:
            break
        cursor = resp.get("next_cursor")
    return pages


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="blind-to-x 평가 케이스 추출")
    parser.add_argument("--config", default=str(REPO_ROOT / "projects" / "blind-to-x" / "config.yaml"))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true", help="추출만 시도하고 파일 저장은 생략")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    config = load_blind_config(Path(args.config))
    notion_cfg = config.get("notion", {})
    database_id = notion_cfg.get("database_id")
    props = notion_cfg.get("properties", {})
    if not database_id:
        logger.error("notion.database_id 설정이 없습니다.")
        return 2

    logger.info("Notion 페이지 조회 (max=%d) ...", args.max_pages)
    pages = _query_notion_pages(database_id, args.max_pages)
    logger.info("조회 완료: %d 페이지", len(pages))

    golden = extract_cases(pages, props=props, status_filter="승인됨")
    rejected = extract_cases(pages, props=props, status_filter="패스")
    logger.info("추출 결과: golden=%d, rejected=%d", len(golden), len(rejected))

    if args.dry_run:
        logger.info("dry-run: 파일 저장 생략")
        sys.stdout.write(json.dumps({"golden": len(golden), "rejected": len(rejected)}, ensure_ascii=False) + "\n")
        return 0

    output_dir = Path(args.output_dir)
    write_eval_yaml(to_yaml_dict(golden, set_label="golden"), output_dir / DEFAULT_GOLDEN_FILENAME)
    write_eval_yaml(to_yaml_dict(rejected, set_label="rejected"), output_dir / DEFAULT_REJECTED_FILENAME)
    logger.info("저장 완료: %s", output_dir)
    sys.stdout.write(
        json.dumps(
            {
                "golden_path": str(output_dir / DEFAULT_GOLDEN_FILENAME),
                "rejected_path": str(output_dir / DEFAULT_REJECTED_FILENAME),
                "golden": len(golden),
                "rejected": len(rejected),
                "samples": [asdict(c) for c in golden[:1]],
            },
            ensure_ascii=False,
        )
        + "\n"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
