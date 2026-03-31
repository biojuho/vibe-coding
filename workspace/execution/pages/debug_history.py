import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

try:
    import plotly.express as px
    from execution.debug_history_db import (
        get_stats,
        list_entries,
        list_patterns,
        lookup_pattern,
        search_entries,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="Debug History - Joolife", page_icon="🪲", layout="wide")

if not _MODULE_OK:
    st.error(f"Debug History 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()


# ── 헤더 ─────────────────────────────────────────
st.title("🪲 Debug History")
st.caption("디버깅 이력 및 에러 패턴 분석")

# ── 통계 KPI ──────────────────────────────────────
stats = get_stats()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("총 엔트리", stats["total_entries"])
critical = stats["by_severity"].get("P0", 0) + stats["by_severity"].get("P1", 0)
k2.metric("P0/P1 (심각)", critical)
k3.metric("지침 업데이트율", f"{stats['directive_update_rate']}%")
k4.metric("테스트 추가율", f"{stats['test_addition_rate']}%")
top_module = max(stats["top_modules"], key=stats["top_modules"].get) if stats["top_modules"] else "-"
k5.metric("최다 버그 모듈", top_module)

# ── 차트 ──────────────────────────────────────────
st.divider()

if stats["total_entries"] > 0:
    chart1, chart2 = st.columns(2)
    with chart1:
        sev_data = stats["by_severity"]
        if sev_data:
            fig = px.pie(
                names=list(sev_data.keys()),
                values=list(sev_data.values()),
                title="심각도별 분포",
                color_discrete_sequence=px.colors.sequential.RdBu,
            )
            st.plotly_chart(fig, use_container_width=True)
    with chart2:
        layer_data = stats["by_layer"]
        if layer_data:
            fig = px.pie(
                names=list(layer_data.keys()),
                values=list(layer_data.values()),
                title="계층별 분포",
                color_discrete_sequence=px.colors.sequential.Teal,
            )
            st.plotly_chart(fig, use_container_width=True)

# ── 엔트리 목록 ──────────────────────────────────
st.divider()
st.subheader("디버깅 이력")

f1, f2, f3 = st.columns(3)
with f1:
    sev_filter = st.selectbox("심각도", ["전체", "P0", "P1", "P2", "P3"])
with f2:
    layer_filter = st.selectbox("계층", ["전체", "directive", "orchestration", "execution"])
with f3:
    module_filter = st.text_input("모듈명 검색")

sev_arg = None if sev_filter == "전체" else sev_filter
layer_arg = None if layer_filter == "전체" else layer_filter
mod_arg = module_filter.strip() or None

entries = list_entries(severity=sev_arg, layer=layer_arg, module=mod_arg, limit=50)

if entries:
    for e in entries:
        d_flag = "📝" if e.get("directive_updated") else ""
        t_flag = "🧪" if e.get("test_added") else ""
        flags = f" {d_flag}{t_flag}" if d_flag or t_flag else ""
        st.markdown(f"**[{e['severity']}]** `{e.get('module') or '(no module)'}` — {e['symptom']}{flags}")
        if e.get("root_cause"):
            st.caption(f"  원인: {e['root_cause']}")
        if e.get("solution"):
            st.caption(f"  해결: {e['solution']}")
else:
    st.info("디버깅 이력이 없습니다.")

# ── 키워드 검색 ──────────────────────────────────
st.divider()
st.subheader("키워드 검색")
search_keyword = st.text_input("키워드 입력", key="search_kw")
if search_keyword:
    results = search_entries(search_keyword)
    if results:
        for e in results:
            st.markdown(f"**[{e['severity']}]** `{e.get('module', '')}` — {e['symptom']}")
    else:
        st.info("검색 결과 없음")

# ── 에러 패턴 ────────────────────────────────────
st.divider()
st.subheader("등록된 에러 패턴")

patterns = list_patterns()
if patterns:
    for p in patterns:
        hint = f" (모듈: {p['module_hint']})" if p.get("module_hint") else ""
        st.markdown(f"**[{p['error_type']}]** `{p['pattern']}` — seen {p['times_seen']}x{hint}")
        st.caption(f"  첫 확인: {p['first_check']} | 도구: {p['tool']}")
else:
    st.info("등록된 패턴 없음 — `python workspace/execution/debug_history_db.py seed` 로 초기화하세요.")

# ── 패턴 검색 ────────────────────────────────────
st.divider()
st.subheader("에러 메시지 패턴 검색")
error_msg = st.text_input("에러 메시지 입력", key="pattern_lookup")
if error_msg:
    matches = lookup_pattern(error_msg)
    if matches:
        for m in matches:
            st.success(f"**[{m['error_type']}]** `{m['pattern']}` — 첫 확인: {m['first_check']} / 도구: {m['tool']}")
    else:
        st.warning("알려진 패턴 없음")
