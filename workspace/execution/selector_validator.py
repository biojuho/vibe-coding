"""
스크래퍼 CSS 셀렉터 유효성 자동 검증.

각 사이트의 목록/상세 페이지를 curl_cffi로 받아
등록된 셀렉터가 현재 HTML에 존재하는지 확인합니다.
실패 시 로그 경고 + .tmp/selector_failures.json 저장.

Usage (CLI):
    python workspace/execution/selector_validator.py            # 전체 검증
    python workspace/execution/selector_validator.py --site ppomppu  # 특정 사이트만
    python workspace/execution/selector_validator.py --json         # JSON 출력

Usage (library):
    from execution.selector_validator import run_all_validations
    results = run_all_validations()
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

load_dotenv()
from execution._logging import logger  # noqa: E402

_ROOT = Path(__file__).resolve().parent.parent
_OUTPUT_PATH = _ROOT / ".tmp" / "selector_failures.json"

# ── 검증 정의 ──────────────────────────────────────────────────
# pattern: CSS 셀렉터를 HTML에서 찾기 위한 간이 정규식 변환
# selectors: 반드시 존재해야 하는 셀렉터 목록
# optional: 없어도 경고만 (실패 처리 안 함)

SITE_CHECKS: list[dict[str, Any]] = [
    {
        "name": "ppomppu-list",
        "url": "https://www.ppomppu.co.kr/zboard/zboard.php?id=humor",
        "encoding": "cp949",
        "selectors": [
            "a[href*='view.php?id=humor']",
        ],
        "optional": [
            ".list_table",
            "td.title",
        ],
    },
    {
        "name": "ppomppu-post",
        "url": "https://www.ppomppu.co.kr/zboard/view.php?id=humor&no=744732",
        "encoding": "cp949",
        "selectors": [
            ".board-contents",
        ],
        "optional": [
            "h1",
            "#vote_list_btn_txt",
            ".JS_ContentMain",
        ],
    },
    {
        "name": "blind-list",
        "url": "https://www.teamblind.com/kr/topics/trending",
        "encoding": "utf-8",
        "selectors": [
            ".article-list",
        ],
        "optional": [
            ".tit h3 a",
            ".article-list .tit",
        ],
    },
    {
        "name": "fmkorea-list",
        "url": "https://www.fmkorea.com/index.php?mid=humor",
        "encoding": "utf-8",
        "selectors": [],
        "optional": [
            ".fm_best_widget",
            ".hotdeal_row",
            "li.li",
        ],
    },
]


def _css_to_pattern(selector: str) -> str:
    """CSS 셀렉터를 HTML 검색용 간이 정규식으로 변환.

    완전한 CSS 파싱이 아닌 존재 여부만 빠르게 확인합니다.
    """
    # class 셀렉터: .foo → class="...foo..."
    if selector.startswith("."):
        cls = selector[1:].split(" ")[0].split("[")[0]
        return rf'class=["\'][^"\']*{re.escape(cls)}[^"\']*["\']'

    # id 셀렉터: #foo → id="foo"
    if selector.startswith("#"):
        return rf'id=["\' ]{re.escape(selector[1:])}["\' ]'

    # 속성 셀렉터: a[href*='view.php'] → href containing 'view.php'
    attr_match = re.match(r'\w+\[(\w+)\*=["\']([^"\']+)["\']', selector)
    if attr_match:
        return re.escape(attr_match.group(2))

    # 태그: h1, main 등
    tag = selector.split("[")[0].split(".")[0].split("#")[0]
    if tag:
        return rf"<{re.escape(tag)}[\s>]"

    return re.escape(selector)


def _fetch_html(url: str, encoding: str = "utf-8", timeout: int = 20) -> str | None:
    """curl_cffi로 HTML 가져오기."""
    try:
        from curl_cffi.requests import Session

        with Session(timeout=timeout) as session:
            resp = session.get(url, impersonate="chrome120")
            resp.raise_for_status()
            if encoding in ("cp949", "euc-kr"):
                try:
                    return resp.content.decode("cp949")
                except (UnicodeDecodeError, LookupError):
                    return resp.content.decode("euc-kr", errors="replace")
            return resp.text
    except Exception as exc:
        logger.warning("Fetch failed for %s: %s", url, exc)
        return None


def _check_selector(html: str, selector: str) -> bool:
    """HTML에서 셀렉터 패턴이 존재하는지 확인."""
    pattern = _css_to_pattern(selector)
    return bool(re.search(pattern, html, re.IGNORECASE))


def validate_site(site: dict[str, Any]) -> dict[str, Any]:
    """단일 사이트 셀렉터 검증."""
    name = site["name"]
    url = site["url"]
    encoding = site.get("encoding", "utf-8")
    required = site.get("selectors", [])
    optional = site.get("optional", [])

    result: dict[str, Any] = {
        "name": name,
        "url": url,
        "checked_at": datetime.now().isoformat(timespec="seconds"),
        "fetch_ok": False,
        "required_pass": [],
        "required_fail": [],
        "optional_pass": [],
        "optional_miss": [],
        "status": "skip",
    }

    html = _fetch_html(url, encoding)
    if html is None:
        result["status"] = "fetch_error"
        result["detail"] = "HTML fetch failed"
        return result

    result["fetch_ok"] = True
    result["html_len"] = len(html)

    for sel in required:
        if _check_selector(html, sel):
            result["required_pass"].append(sel)
        else:
            result["required_fail"].append(sel)

    for sel in optional:
        if _check_selector(html, sel):
            result["optional_pass"].append(sel)
        else:
            result["optional_miss"].append(sel)

    if result["required_fail"]:
        result["status"] = "fail"
        result["detail"] = f"Missing required selectors: {result['required_fail']}"
        logger.warning("[%s] Selector validation FAIL: %s", name, result["required_fail"])
    elif result["optional_miss"]:
        result["status"] = "warn"
        result["detail"] = f"Missing optional selectors: {result['optional_miss']}"
        logger.warning("[%s] Selector validation WARN: %s", name, result["optional_miss"])
    else:
        result["status"] = "ok"
        result["detail"] = f"All {len(required)} required + {len(optional)} optional selectors found"
        logger.info("[%s] Selector validation OK", name)

    return result


def run_all_validations(site_name: str | None = None) -> list[dict[str, Any]]:
    """모든 (또는 지정된) 사이트 셀렉터 검증."""
    sites = SITE_CHECKS
    if site_name:
        sites = [s for s in SITE_CHECKS if site_name in s["name"]]

    results = [validate_site(s) for s in sites]

    # 실패 항목을 .tmp에 저장
    failures = [r for r in results if r["status"] in ("fail", "fetch_error")]
    if failures:
        _OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        _OUTPUT_PATH.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.warning("%d selector failure(s) saved to %s", len(failures), _OUTPUT_PATH)

    return results


def get_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {"ok": 0, "warn": 0, "fail": 0, "fetch_error": 0, "skip": 0}
    for r in results:
        counts[r.get("status", "skip")] = counts.get(r.get("status", "skip"), 0) + 1
    return {
        "total": len(results),
        **counts,
        "healthy": counts["fail"] == 0 and counts["fetch_error"] == 0,
    }


# ── CLI ────────────────────────────────────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser(description="스크래퍼 셀렉터 자동 검증")
    parser.add_argument("--site", type=str, help="특정 사이트만 검증 (예: ppomppu)")
    parser.add_argument("--json", action="store_true", help="JSON 형식으로 출력")
    args = parser.parse_args()

    results = run_all_validations(args.site)
    summary = get_summary(results)

    if args.json:
        print(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2))
        return 0

    icons = {"ok": "✅", "warn": "⚠️", "fail": "❌", "fetch_error": "🔴", "skip": "⏭️"}
    print("\n스크래퍼 셀렉터 검증 결과\n" + "=" * 50)
    for r in results:
        icon = icons.get(r["status"], "?")
        miss_info = ""
        if r.get("required_fail"):
            miss_info = f"  → 누락 필수: {r['required_fail']}"
        if r.get("optional_miss"):
            miss_info += f"  → 누락 선택: {r['optional_miss']}"
        print(f"  {icon} {r['name']:25s} [{r['status']:10s}] {r.get('detail', '')}{miss_info}")

    print(
        f"\n  결과: {summary['ok']}ok / {summary['warn']}warn / {summary['fail']}fail "
        f"/ {summary['fetch_error']}error  (총 {summary['total']}개)"
    )
    if not summary["healthy"]:
        print("\n  ⚠️  셀렉터 수정 필요 — projects/blind-to-x/scrapers/ 확인")

    return 0 if summary["healthy"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
