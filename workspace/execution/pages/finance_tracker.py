import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st

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

st.set_page_config(page_title="Finance - Joolife", page_icon="💵", layout="wide")

if not _MODULE_OK:
    st.error(f"Finance 모듈을 불러올 수 없습니다: {_MODULE_ERR}")
    st.stop()

init_db()

st.title("💵 Finance Tracker")
st.caption("Personal income & expense management")

# ── Month Selector ──
current_month = date.today().strftime("%Y-%m")
month = st.text_input("Month (YYYY-MM)", value=current_month)

# ── Monthly Summary ──
summary = get_monthly_summary(month)
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Income", f"₩{summary['income']:,.0f}")
with col2:
    st.metric("Expense", f"₩{summary['expense']:,.0f}")
with col3:
    delta_color = "normal" if summary["net"] >= 0 else "inverse"
    st.metric("Net Balance", f"₩{summary['net']:,.0f}", delta_color=delta_color)

# ── Budget Alerts ──
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

# ── Charts ──
chart_col1, chart_col2 = st.columns(2)

with chart_col1:
    st.subheader("Category Breakdown")
    breakdown = get_category_breakdown(month)
    expense_data = [b for b in breakdown if b["type"] == "expense"]
    if expense_data:
        fig = px.pie(
            values=[d["total"] for d in expense_data],
            names=[d["category"] for d in expense_data],
            title="Expense by Category",
        )
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No expense data for this month.")

with chart_col2:
    st.subheader("6-Month Trend")
    trend = get_trend(6)
    if trend:
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=[t["month"] for t in trend],
                y=[t["income"] for t in trend],
                name="Income",
                line=dict(color="#4ade80"),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[t["month"] for t in trend],
                y=[t["expense"] for t in trend],
                name="Expense",
                line=dict(color="#f87171"),
            )
        )
        fig.update_layout(
            title="Income vs Expense",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#e0e0e0",
        )
        st.plotly_chart(fig, width="stretch")
    else:
        st.info("No historical data yet.")

st.divider()

# ── Add Transaction ──
st.subheader("Add Transaction")
with st.form("add_tx"):
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        tx_type = st.selectbox("Type", ["expense", "income"])
        tx_amount = st.number_input("Amount (₩)", min_value=0, step=1000)
    with tc2:
        tx_category = st.selectbox("Category", CATEGORIES.get(tx_type, ["기타"]))
        tx_desc = st.text_input("Description", placeholder="점심 식사")
    with tc3:
        tx_date = st.date_input("Date", value=date.today())

    if st.form_submit_button("Add", type="primary"):
        if tx_amount > 0:
            tid = add_transaction(tx_type, tx_amount, tx_category, tx_desc, tx_date.isoformat())
            st.success(f"Transaction #{tid} added.")
            st.rerun()

# ── Transaction History ──
st.divider()
st.subheader("Transaction History")
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
            if st.button("🗑", key=f"del_tx_{tx['id']}"):
                delete_transaction(tx["id"])
                st.rerun()
else:
    st.info("No transactions for this month.")

# ── Budget Settings ──
st.divider()
with st.expander("Budget Settings"):
    budgets = {b["category"]: b["monthly_limit"] for b in get_budgets()}
    with st.form("budget_form"):
        budget_values = {}
        for cat in CATEGORIES["expense"]:
            current = budgets.get(cat, 0)
            budget_values[cat] = st.number_input(f"{cat}", value=int(current), step=10000, key=f"budget_{cat}")
        if st.form_submit_button("Save Budgets"):
            for cat, val in budget_values.items():
                if val != budgets.get(cat, 0):
                    set_budget(cat, val)
            st.rerun()

# ── Export ──
st.divider()
csv_data = export_csv(month)
st.download_button("Download CSV", data=csv_data, file_name=f"finance_{month}.csv", mime="text/csv")
