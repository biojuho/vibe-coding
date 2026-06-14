import sys
from datetime import date
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import streamlit as st  # noqa: E402

try:
    import plotly.express as px
    import plotly.graph_objects as go

    from execution.finance_db import (
        CATEGORIES,
        add_transaction,
        check_budget_alerts,
        delete_transaction,
        export_csv,
        get_budgets,
        get_category_breakdown,
        get_monthly_summary,
        get_transactions,
        get_trend,
        init_db,
        set_budget,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_OK = False
    _MODULE_ERR = str(e)

st.set_page_config(page_title="가계부 - Joolife", page_icon="💵", layout="wide")

if not _MODULE_OK:
    st.error(f"Finance 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

PLOTLY_CHART_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}

TYPE_LABELS = {
    "expense": "지출",
    "income": "수입",
}

MOBILE_TOUCH_TARGET_CSS = """
<style>
@media (max-width: 640px) {
    div[data-testid="stButton"] button,
    div[data-testid="stDownloadButton"] button,
    div[data-testid="stFormSubmitButton"] button,
    div[data-testid="stHeader"] button,
    div[data-testid="stToolbar"] button,
    div[data-testid="stHeaderActionElements"] a,
    div[data-testid="stNumberInput"] button,
    div[data-baseweb="select"],
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"],
    div[data-baseweb="input"] > div,
    div[data-baseweb="input"] input,
    input,
    textarea {
        min-height: 44px !important;
        min-width: 44px !important;
    }

    input,
    textarea,
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"] > div {
        align-items: center !important;
        font-size: 1rem !important;
    }

    a[href^="#"],
    div[data-testid="stHeadingWithActionElements"] a {
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        min-height: 44px !important;
        min-width: 44px !important;
    }

    .modebar,
    .modebar-container {
        display: none !important;
    }
}
</style>
"""


def _inject_finance_mobile_css() -> None:
    st.markdown(MOBILE_TOUCH_TARGET_CSS, unsafe_allow_html=True)


def _render_plotly_chart(fig: object) -> None:
    st.plotly_chart(fig, width="stretch", config=PLOTLY_CHART_CONFIG)


def _format_transaction_type(type_: str) -> str:
    return TYPE_LABELS.get(type_, type_)


def _month_start(month: str) -> date:
    year_text, month_text = month.split("-", 1)
    return date(int(year_text), int(month_text), 1)


def _format_month_label(month: str) -> str:
    return month.replace("-", ".")


def _parse_transaction_date(value: str) -> str | None:
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


init_db()
_inject_finance_mobile_css()

st.title("💵 가계부", anchor=False)
st.caption("수입과 지출을 한 화면에서 기록하고 월별 흐름을 확인합니다")

# ── 조회 월 ──
current_month = date.today().strftime("%Y-%m")
month = st.text_input("조회 월 (YYYY-MM)", value=current_month)

# ── 월간 요약 ──
summary = get_monthly_summary(month)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("수입", f"₩{summary['income']:,.0f}")
with col2:
    st.metric("지출", f"₩{summary['expense']:,.0f}")
with col3:
    delta_color = "normal" if summary["net"] >= 0 else "inverse"
    st.metric("잔액", f"₩{summary['net']:,.0f}", delta_color=delta_color)

# ── 예산 알림 ──
alerts = check_budget_alerts(month)
if alerts:
    for a in alerts:
        if a["over"]:
            st.error(f"🚨 **{a['category']}** 예산 초과! ₩{a['spent']:,.0f} / ₩{a['budget']:,.0f}")
        else:
            st.warning(
                f"⚠️ **{a['category']}** 예산 {a['ratio'] * 100:.0f}% 사용 (₩{a['spent']:,.0f} / ₩{a['budget']:,.0f})"
            )

st.divider()

# ── 거래 추가 ──
st.subheader("거래 추가", anchor=False)
with st.form("add_tx"):
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        tx_type = st.selectbox("구분", ["expense", "income"], format_func=_format_transaction_type)
        tx_amount = st.number_input("금액 (₩)", min_value=0, step=1000)
    with tc2:
        tx_category = st.selectbox("분류", CATEGORIES.get(tx_type, ["기타"]))
        tx_desc = st.text_input("메모", placeholder="점심 식사")
    with tc3:
        tx_date_text = st.text_input("날짜 (YYYY-MM-DD)", value=date.today().isoformat(), placeholder="2026-06-08")

    if st.form_submit_button("추가", type="primary", width="stretch"):
        parsed_tx_date = _parse_transaction_date(tx_date_text)
        if tx_amount <= 0:
            st.warning("금액을 0보다 크게 입력하세요.")
        elif parsed_tx_date is None:
            st.error("날짜는 YYYY-MM-DD 형식으로 입력하세요.")
        else:
            tid = add_transaction(tx_type, tx_amount, tx_category, tx_desc, parsed_tx_date)
            st.success(f"거래 #{tid} 추가됨")
            st.rerun()

st.divider()

# ── 차트 ──
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("분류별 지출", anchor=False)
    breakdown = get_category_breakdown(month)
    expense_data = [b for b in breakdown if b["type"] == "expense"]
    if expense_data:
        fig = px.pie(
            values=[d["total"] for d in expense_data],
            names=[d["category"] for d in expense_data],
            title="지출 분포",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        _render_plotly_chart(fig)
    else:
        st.info("이번 달 지출 데이터가 없습니다.")

with chart_col2:
    st.subheader("6개월 추이", anchor=False)
    trend = get_trend(6)
    if trend:
        fig = go.Figure()
        trend_months = [_month_start(t["month"]) for t in trend]
        trend_labels = [_format_month_label(t["month"]) for t in trend]
        fig.add_trace(
            go.Scatter(
                x=trend_months,
                y=[t["income"] for t in trend],
                name="수입",
                customdata=trend_labels,
                hovertemplate="%{customdata}<br>수입: ₩%{y:,.0f}<extra></extra>",
                line=dict(color="#4ade80"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=trend_months,
                y=[t["expense"] for t in trend],
                name="지출",
                customdata=trend_labels,
                hovertemplate="%{customdata}<br>지출: ₩%{y:,.0f}<extra></extra>",
                line=dict(color="#f87171"),
            )
        )
        fig.update_layout(
            title="월별 수입/지출",
            legend_title_text="",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        fig.update_xaxes(dtick="M1", tickformat="%Y.%m", ticklabelmode="period", title_text="월")
        fig.update_yaxes(tickprefix="₩", separatethousands=True, title_text="금액")
        _render_plotly_chart(fig)
    else:
        st.info("아직 추이 데이터가 없습니다.")

# ── 거래 내역 ──
st.divider()
st.subheader("거래 내역", anchor=False)
transactions = get_transactions(month=month, limit=50)

if transactions:
    for tx in transactions:
        icon = "📈" if tx["type"] == "income" else "📉"
        tc1, tc2, tc3, tc4 = st.columns([1, 3, 2, 1])
        with tc1:
            st.markdown(f"{icon}")
        with tc2:
            st.markdown(f"**{tx['category']}** — {tx.get('description', '')}")
            st.caption(tx["date"])
        with tc3:
            color = "green" if tx["type"] == "income" else "red"
            st.markdown(f":{color}[₩{tx['amount']:,.0f}]")
        with tc4:
            if st.button("삭제", key=f"del_tx_{tx['id']}", width="stretch"):
                delete_transaction(tx["id"])
                st.rerun()
else:
    st.info("이번 달 거래가 없습니다.")

# ── 예산 설정 ──
st.divider()
show_budget_settings = st.checkbox("예산 설정 열기")
if show_budget_settings:
    budgets = {b["category"]: b["monthly_limit"] for b in get_budgets()}
    with st.form("budget_form"):
        budget_values = {}
        for cat in CATEGORIES["expense"]:
            current = budgets.get(cat, 0)
            budget_values[cat] = st.number_input(f"{cat}", value=int(current), step=10000, key=f"budget_{cat}")
        if st.form_submit_button("예산 저장", width="stretch"):
            for cat, val in budget_values.items():
                if val != budgets.get(cat, 0):
                    set_budget(cat, val)
            st.rerun()

# ── 내보내기 ──
st.divider()
csv_data = export_csv(month)
st.download_button(
    "CSV 다운로드",
    data=csv_data,
    file_name=f"finance_{month}.csv",
    mime="text/csv",
    width="stretch",
)
