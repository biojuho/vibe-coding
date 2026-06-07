"""
Technical-debt operations dashboard.

Usage:
    streamlit run workspace/execution/pages/debt_dashboard.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import TMP_ROOT

try:
    import streamlit as st
except ImportError:
    print("streamlit is not installed. Run: pip install streamlit")
    sys.exit(1)

_PLOTLY_CHART_CONFIG = {"displayModeBar": False, "displaylogo": False, "responsive": True}


def _inject_debt_dashboard_mobile_css() -> None:
    st.markdown(
        """
        <style>
        @media (max-width: 640px) {
            div[data-testid="stToolbar"] button,
            div[data-testid="stHeaderActionElements"] button,
            button[kind="header"] {
                min-height: 44px !important;
                min-width: 44px !important;
            }
            div[data-testid="stSelectbox"] div[data-baseweb="select"],
            div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
                min-height: 44px !important;
            }
            div[data-testid="stSelectbox"] input[role="combobox"] {
                min-height: 44px !important;
                min-width: 44px !important;
            }
            div[data-testid="stSlider"] {
                padding-bottom: 0.75rem;
            }
            div[data-baseweb="slider"] {
                min-height: 44px !important;
            }
            div[data-baseweb="slider"] [role="slider"] {
                width: 44px !important;
                height: 44px !important;
                min-width: 44px !important;
                min-height: 44px !important;
                margin-top: -16px !important;
            }
            div[data-testid="stExpander"] details summary {
                min-height: 44px !important;
                align-items: center !important;
            }
            div[data-testid="stMetric"] {
                min-width: 0 !important;
                overflow-wrap: anywhere;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


st.set_page_config(page_title="기술부채 현황 - Joolife", page_icon="📊", layout="wide")
_inject_debt_dashboard_mobile_css()
st.title("📊 기술부채 현황")
st.caption("프로젝트별 TDR, 수정 원가, 월간 이자를 한 화면에서 점검합니다.")


# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------


def load_latest_result() -> dict | None:
    result_path = TMP_ROOT / "debt_audit_result.json"
    if not result_path.exists():
        return None
    try:
        return json.loads(result_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def load_trend_data() -> list[dict]:
    try:
        from execution.debt_history_db import DebtHistoryDB

        db = DebtHistoryDB()
        return db.get_trend_data(days=90)
    except Exception:
        return []


def load_project_trend(project_name: str) -> list[dict]:
    try:
        from execution.debt_history_db import DebtHistoryDB

        db = DebtHistoryDB()
        return db.get_project_trend(project_name, days=90)
    except Exception:
        return []


def _build_trend_chart_frame(df, value_columns: list[str]):
    import math

    import pandas as pd

    required_columns = ["timestamp", *value_columns]
    if df.empty or any(column not in df for column in required_columns):
        return None

    chart_df = df[required_columns].copy()
    chart_df["date"] = pd.to_datetime(chart_df["timestamp"], errors="coerce").dt.date
    for column in value_columns:
        chart_df[column] = pd.to_numeric(chart_df[column], errors="coerce")
    finite_mask = chart_df[value_columns].apply(
        lambda series: series.map(lambda value: pd.notna(value) and math.isfinite(float(value)))
    )
    chart_df = chart_df[finite_mask.all(axis=1)].dropna(subset=["date", *value_columns])
    if chart_df.empty:
        return None

    return chart_df[["date", *value_columns]].set_index("date")


def _render_line_chart(data, *, y_axis_title: str = "", series_labels: dict[str, str] | None = None) -> None:
    if data is not None and not getattr(data, "empty", False):
        import plotly.express as px

        chart_data = data.reset_index()
        if series_labels:
            chart_data = chart_data.rename(
                columns={key: value for key, value in series_labels.items() if key in chart_data}
            )
        value_columns = [column for column in chart_data.columns if column != "date"]
        fig = px.line(chart_data, x="date", y=value_columns, render_mode="svg")
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
            legend_title_text="",
            xaxis_title="날짜",
            yaxis_title=y_axis_title,
            margin=dict(l=16, r=16, t=20, b=16),
        )
        st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)


# ---------------------------------------------------------------------------
# Main layout
# ---------------------------------------------------------------------------

result = load_latest_result()
trend = load_trend_data()

if result is None:
    st.warning("기술부채 감사 결과가 없습니다. `python workspace/execution/vibe_debt_auditor.py`를 먼저 실행하세요.")
    st.stop()

# --- 전체 KPI ---
grade = result.get("overall_grade", "UNKNOWN")
grade_colors = {"GREEN": "normal", "YELLOW": "off", "RED": "inverse"}
grade_labels = {"GREEN": "안정", "YELLOW": "주의", "RED": "위험"}
dimension_labels = {
    "complexity": "복잡도",
    "duplication": "중복",
    "test_gap": "테스트 공백",
    "debt_markers": "부채 표식",
    "modularity": "모듈성",
    "doc_sync": "문서 동기화",
}

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("전체 TDR", f"{result.get('overall_tdr', 0):.1f}%")
    st.caption("판단 기준: 5% 미만이면 안정권")
with col2:
    st.metric("등급", grade_labels.get(grade, grade))
with col3:
    st.metric("수정 원가", f"{result.get('total_principal_hours', 0):.1f}시간")
with col4:
    st.metric("월간 이자", f"{result.get('total_interest_monthly_hours', 0):.1f}시간/월")

# --- TDR 추세 ---
if trend:
    st.divider()
    st.subheader("TDR 추세 (90일)")

    try:
        import pandas as pd

        df = pd.DataFrame(trend)
        chart_df = _build_trend_chart_frame(df, ["overall_tdr"])
        if chart_df is not None:
            _render_line_chart(chart_df, y_axis_title="TDR %", series_labels={"overall_tdr": "전체 TDR"})
    except ImportError:
        st.info("추세 차트를 보려면 pandas가 필요합니다: pip install pandas")

# --- 프로젝트별 현황 ---
st.divider()
st.subheader("프로젝트별 현황")

projects = result.get("projects", [])
if projects:
    proj_cols = st.columns(len(projects))
    for i, proj in enumerate(projects):
        with proj_cols[i]:
            p_grade = proj.get("tdr_grade", "?")
            st.markdown(f"### {proj['name']}")
            st.metric("TDR", f"{proj.get('tdr_percent', 0):.1f}%")
            st.metric("평균 부채 점수", f"{proj.get('avg_score', 0):.1f} / 100")
            st.metric("파일 수", proj.get("file_count", 0))
            st.metric("코드 라인", f"{proj.get('total_code_lines', 0):,}")
            st.metric("수정 원가", f"{proj.get('total_principal_minutes', 0):.0f}분")

            # 지표별 점수 막대
            dims = proj.get("dimension_averages", {})
            if dims:
                st.markdown("**지표별 점수**")
                for dim, score in dims.items():
                    label = dimension_labels.get(dim, dim.replace("_", " "))
                    bar_len = int(score / 5)
                    bar = "█" * bar_len + "░" * (20 - bar_len)
                    st.text(f"{label:15s} {bar} {score:.0f}")

# --- 상위 부채 파일 ---
st.divider()
st.subheader("상위 기술부채 파일")

file_scores = result.get("file_scores", [])
if file_scores:
    # 프로젝트 필터
    all_projects = sorted(set(f.get("project", "") for f in file_scores))
    selected_proj_label = st.selectbox("프로젝트 필터", ["전체"] + all_projects)

    filtered = file_scores
    if selected_proj_label != "전체":
        filtered = [f for f in file_scores if f.get("project") == selected_proj_label]

    # 점수 필터
    min_score = st.slider("최소 부채 점수", 0, 100, 20)
    filtered = [f for f in filtered if f.get("total_score", 0) >= min_score]

    st.caption(f"부채 점수 {min_score}점 이상 파일 {len(filtered)}개 표시")

    for f in filtered[:30]:
        with st.expander(f"{f.get('total_score', 0):.1f} | {f.get('relative_path', '')}"):
            mcol1, mcol2, mcol3 = st.columns(3)
            with mcol1:
                st.metric("라인", f.get("code_lines", 0))
                st.metric("함수", f.get("function_count", 0))
            with mcol2:
                st.metric("최대 복잡도", f.get("max_complexity", 0))
                st.metric("최대 함수 길이", f.get("max_function_length", 0))
            with mcol3:
                st.metric("부채 표식", f.get("debt_marker_count", 0))
                st.metric("중복 블록", f.get("duplicate_block_count", 0))

            st.markdown("**지표별 점수**")
            dim_cols = st.columns(6)
            for j, dim in enumerate(
                ["complexity", "duplication", "test_gap", "debt_markers", "modularity", "doc_sync"]
            ):
                with dim_cols[j]:
                    st.metric(dimension_labels.get(dim, dim.replace("_", " ")), f"{f.get(f'{dim}_score', 0):.0f}")

            # 복잡한 함수
            top_funcs = f.get("top_functions", [])
            if top_funcs:
                st.markdown("**복잡한 함수**")
                for tf in top_funcs[:5]:
                    st.text(f"  {tf['name']}() L{tf['line']} - CC:{tf['complexity']} Len:{tf['length']}")

            # 부채 표식
            markers = f.get("debt_markers", [])
            if markers:
                st.markdown("**부채 표식**")
                for m in markers[:5]:
                    st.text(f"  L{m['line']} [{m['type']}] {m['text'][:80]}")

            st.metric("수정 원가", f"{f.get('principal_minutes', 0):.0f}분")

# --- 프로젝트별 추세 상세 ---
if projects:
    st.divider()
    st.subheader("프로젝트 추세 상세")
    proj_name = st.selectbox("프로젝트 선택", [p["name"] for p in projects], key="proj_trend")
    proj_trend = load_project_trend(proj_name)

    if proj_trend:
        try:
            import pandas as pd

            df = pd.DataFrame(proj_trend)
            tdr_chart = _build_trend_chart_frame(df, ["tdr_percent"])
            score_chart = _build_trend_chart_frame(df, ["avg_score"])
            if tdr_chart is not None and score_chart is not None:
                chart_cols = st.columns(2)
                with chart_cols[0]:
                    st.markdown("**TDR %**")
                    _render_line_chart(tdr_chart, y_axis_title="TDR %", series_labels={"tdr_percent": "TDR"})
                with chart_cols[1]:
                    st.markdown("**평균 부채 점수**")
                    _render_line_chart(
                        score_chart,
                        y_axis_title="평균 부채 점수",
                        series_labels={"avg_score": "평균 부채 점수"},
                    )
        except ImportError:
            pass
    else:
        st.info("아직 히스토리 데이터가 없습니다. 감사기를 여러 번 실행하면 추세가 쌓입니다.")

# --- 하단 메타데이터 ---
st.divider()
ts = result.get("timestamp", "")
st.caption(
    f"마지막 스캔: {ts[:19].replace('T', ' ') if ts else '-'} | "
    f"{result.get('total_files', 0)}개 파일, {result.get('scan_duration_seconds', 0)}초"
)
