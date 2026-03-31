import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

try:
    from execution.health_check import (
        STATUS_FAIL,
        STATUS_OK,
        STATUS_SKIP,
        STATUS_WARN,
        get_summary,
        run_all_checks,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="Health Check - Joolife", page_icon="🏥", layout="wide")

if not _MODULE_OK:
    st.error(f"Health Check 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

_ICONS = {STATUS_OK: "✅", STATUS_WARN: "⚠️", STATUS_FAIL: "❌", STATUS_SKIP: "⏭️"}
_CATEGORIES = ["all", "env", "api", "filesystem", "database", "environment"]
_CAT_LABELS = {
    "all": "전체",
    "env": "환경 변수",
    "api": "API 연결",
    "filesystem": "파일시스템",
    "database": "데이터베이스",
    "environment": "실행 환경",
}

st.title("🏥 System Health Check")
st.caption("시스템 상태 일괄 점검 대시보드")

# ── 카테고리 필터 + 실행 버튼 ────────────────────
col_filter, col_btn = st.columns([3, 1])
with col_filter:
    selected_cat = st.selectbox(
        "카테고리 필터",
        _CATEGORIES,
        format_func=lambda c: _CAT_LABELS.get(c, c),
    )
with col_btn:
    st.write("")  # spacer
    run_clicked = st.button("🔍 점검 실행", type="primary", use_container_width=True)

# ── 점검 실행 ─────────────────────────────────────
if run_clicked:
    cat_arg = None if selected_cat == "all" else selected_cat
    with st.spinner("점검 중..."):
        results = run_all_checks(category=cat_arg)
    summary = get_summary(results)

    # KPI 행
    st.divider()
    overall_icon = _ICONS.get(summary["overall"], "?")
    c = summary["counts"]
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("전체 상태", f"{overall_icon} {summary['overall'].upper()}")
    k2.metric("OK", c.get(STATUS_OK, 0))
    k3.metric("WARN", c.get(STATUS_WARN, 0))
    k4.metric("FAIL", c.get(STATUS_FAIL, 0))

    # 결과 테이블 (카테고리별 그룹)
    st.divider()
    categories_in_results = sorted(set(r["category"] for r in results))
    for cat in categories_in_results:
        cat_results = [r for r in results if r["category"] == cat]
        cat_label = _CAT_LABELS.get(cat, cat)
        with st.expander(f"**{cat_label}** ({len(cat_results)}건)", expanded=True):
            for r in cat_results:
                icon = _ICONS.get(r["status"], "?")
                detail = f" — {r['detail']}" if r.get("detail") else ""
                st.markdown(f"{icon} **{r['name']}**{detail}")

    st.divider()
    st.caption(f"총 {summary['total']}개 항목 점검 완료")
else:
    st.info("🔍 **점검 실행** 버튼을 눌러 시스템 상태를 확인하세요.")
