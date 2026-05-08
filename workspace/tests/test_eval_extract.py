"""execution/blind_to_x_eval_extract.py — 추출 + YAML 직렬화 회귀 테스트 (T-254).

Notion SDK는 mock 없이 검증 가능하도록 순수 함수로 분리되어 있다.
"""

from __future__ import annotations

import sys
from pathlib import Path

# repo root의 execution/ 을 sys.path에 추가 (workspace 외부에 위치)
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))


def _make_page(
    *,
    page_id: str,
    status: str,
    source_text: str,
    accepted: str = "",
    rejected: str = "",
    memo: str = "",
    status_prop_type: str = "select",
) -> dict:
    """Notion `databases.query` 응답 형식의 단일 페이지 dict."""
    status_block = {"type": status_prop_type, status_prop_type: {"name": status}}
    return {
        "id": page_id,
        "properties": {
            "상태": status_block,
            "원문": {"type": "rich_text", "rich_text": [{"plain_text": source_text}]},
            "최종 드래프트": {"type": "rich_text", "rich_text": [{"plain_text": accepted}]} if accepted else {},
            "거부된 드래프트": {"type": "rich_text", "rich_text": [{"plain_text": rejected}]} if rejected else {},
            "리뷰어 메모": {"type": "rich_text", "rich_text": [{"plain_text": memo}]} if memo else {},
        },
    }


def test_extract_cases_filters_status_correctly():
    from execution.blind_to_x_eval_extract import extract_cases

    pages = [
        _make_page(page_id="p1", status="승인됨", source_text="원문 A", accepted="드래프트 A"),
        _make_page(page_id="p2", status="패스", source_text="원문 B", rejected="실패 B", memo="톤이 강함"),
        _make_page(page_id="p3", status="검토필요", source_text="원문 C"),
    ]
    props = {
        "status": "상태",
        "source_text": "원문",
        "approved_draft": "최종 드래프트",
        "rejected_draft": "거부된 드래프트",
        "reviewer_memo": "리뷰어 메모",
    }

    golden = extract_cases(pages, props=props, status_filter="승인됨")
    rejected = extract_cases(pages, props=props, status_filter="패스")

    assert len(golden) == 1
    assert golden[0].page_id == "p1"
    assert golden[0].accepted_draft == "드래프트 A"

    assert len(rejected) == 1
    assert rejected[0].page_id == "p2"
    assert rejected[0].reviewer_memo == "톤이 강함"


def test_rejected_without_memo_skipped():
    from execution.blind_to_x_eval_extract import extract_cases

    pages = [
        _make_page(page_id="p1", status="패스", source_text="원문", rejected="거부 드래프트"),  # memo 없음
    ]
    props = {"status": "상태", "source_text": "원문", "reviewer_memo": "리뷰어 메모"}
    rejected = extract_cases(pages, props=props, status_filter="패스")
    assert rejected == []


def test_pages_without_source_text_skipped():
    from execution.blind_to_x_eval_extract import extract_cases

    pages = [
        _make_page(page_id="p1", status="승인됨", source_text=""),
        _make_page(page_id="p2", status="승인됨", source_text="실제 원문"),
    ]
    props = {"status": "상태", "source_text": "원문"}
    golden = extract_cases(pages, props=props, status_filter="승인됨")
    assert len(golden) == 1
    assert golden[0].page_id == "p2"


def test_status_property_type_status_supported():
    """select 가 아닌 status 타입 속성도 지원해야 한다."""
    from execution.blind_to_x_eval_extract import extract_cases

    pages = [
        _make_page(
            page_id="p1",
            status="승인됨",
            source_text="원문",
            accepted="드래프트",
            status_prop_type="status",
        ),
    ]
    props = {"status": "상태", "source_text": "원문"}
    golden = extract_cases(pages, props=props, status_filter="승인됨")
    assert len(golden) == 1


def test_to_yaml_dict_shape():
    from execution.blind_to_x_eval_extract import EvalCase, to_yaml_dict

    cases = [EvalCase(page_id="p1", source_text="원문", accepted_draft="드래프트", status="승인됨")]
    payload = to_yaml_dict(cases, set_label="golden")
    assert payload["label"] == "golden"
    assert payload["count"] == 1
    assert len(payload["tests"]) == 1
    test = payload["tests"][0]
    assert test["description"] == "승인됨:p1"
    assert test["vars"]["source_text"] == "원문"
    assert test["vars"]["accepted_draft"] == "드래프트"


def test_write_eval_yaml_round_trip(tmp_path):
    import yaml

    from execution.blind_to_x_eval_extract import EvalCase, to_yaml_dict, write_eval_yaml

    cases = [
        EvalCase(page_id="p1", source_text="한국어 원문", accepted_draft="짧은 드래프트", status="승인됨"),
        EvalCase(
            page_id="p2",
            source_text="원문 2",
            rejected_draft="거부된 드래프트",
            reviewer_memo="단정 표현 사용",
            status="패스",
        ),
    ]
    out = tmp_path / "subdir" / "golden.yaml"
    write_eval_yaml(to_yaml_dict(cases, set_label="golden"), out)

    assert out.exists()
    with out.open("r", encoding="utf-8") as fp:
        loaded = yaml.safe_load(fp)
    assert loaded["count"] == 2
    assert loaded["tests"][1]["vars"]["reviewer_memo"] == "단정 표현 사용"
