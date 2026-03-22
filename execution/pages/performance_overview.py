"""
📈 Performance Overview — Cross-project KPI Dashboard

Aggregates data from multiple sources:
- result_tracker_db: content publishing metrics
- api_usage_tracker: API cost tracking
- watchdog_history.json: pipeline success rate
- backup_status.json: last backup time
- debug_history_db: debug entry stats
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import streamlit as st
import pandas as pd

# ── Graceful imports ──────────────────────────────────────────

# result_tracker_db
try:
    from execution.result_tracker_db import (
        get_all as rt_get_all,
        get_platform_summary as rt_platform_summary,
        get_daily_trend as rt_daily_trend,
        init_db as rt_init_db,
    )
    _RT_OK = True
except ImportError:
    _RT_OK = False
    rt_get_all = None
    rt_platform_summary = None
    rt_daily_trend = None
    rt_init_db = None

# api_usage_tracker
try:
    from execution.api_usage_tracker import (
        get_usage_summary,
        get_daily_breakdown,
        get_provider_breakdown,
        init_db as api_init_db,
    )
    _API_OK = True
except ImportError:
    _API_OK = False
    get_usage_summary = None
    get_daily_breakdown = None
    get_provider_breakdown = None
    api_init_db = None

# debug_history_db
try:
    from execution.debug_history_db import (
        get_stats as debug_get_stats,
        init_db as debug_init_db,
    )
    _DEBUG_OK = True
except ImportError:
    _DEBUG_OK = False
    debug_get_stats = None
    debug_init_db = None

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="Performance Overview - Joolife",
    page_icon="📈",
    layout="wide",
)

st.title("📈 Performance Overview")
st.caption("Cross-project KPI dashboard — content, costs, platform metrics, system health")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"


# ── Helper: load JSON safely ─────────────────────────────────
def _load_json(path: Path) -> dict | list | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return None


# ── Helper: watchdog stats ───────────────────────────────────
def _watchdog_stats() -> dict:
    """Parse watchdog_history.json for success rate and last run."""
    data = _load_json(TMP_DIR / "watchdog_history.json")
    result = {"success_rate": None, "last_run": None, "total": 0, "success": 0}
    if not data:
        return result

    records = data if isinstance(data, list) else data.get("history", [])
    if not records:
        return result

    result["total"] = len(records)
    result["success"] = sum(
        1 for r in records
        if r.get("status", "").lower() in ("ok", "success", "pass")
    )
    if result["total"] > 0:
        result["success_rate"] = round(result["success"] / result["total"] * 100, 1)

    # Last run timestamp
    last = records[-1] if records else {}
    result["last_run"] = last.get("timestamp") or last.get("time") or last.get("date")
    return result


# ══════════════════════════════════════════════════════════════
# SIDEBAR: System Health
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("🩺 System Health")

    # Last backup
    backup_data = _load_json(TMP_DIR / "backup_status.json")
    if backup_data:
        last_backup = backup_data.get("last_backup") or backup_data.get("timestamp", "—")
        st.metric("Last Backup", str(last_backup)[:16])
    else:
        st.metric("Last Backup", "N/A")

    # Last watchdog run
    wd = _watchdog_stats()
    st.metric("Last Watchdog Run", str(wd["last_run"] or "N/A")[:16])
    if wd["success_rate"] is not None:
        st.metric("Watchdog Success Rate", f"{wd['success_rate']}%")

    # LLM cache size
    llm_cache_dir = TMP_DIR / "llm_cache"
    if llm_cache_dir.exists():
        cache_files = list(llm_cache_dir.glob("*"))
        total_bytes = sum(f.stat().st_size for f in cache_files if f.is_file())
        size_mb = round(total_bytes / (1024 * 1024), 2)
        st.metric("LLM Cache", f"{len(cache_files)} files ({size_mb} MB)")
    else:
        st.metric("LLM Cache", "N/A")

    # Debug DB entry count
    if _DEBUG_OK:
        debug_init_db()
        dstats = debug_get_stats()
        st.metric("Debug DB Entries", dstats.get("total_entries", 0))
    else:
        st.metric("Debug DB Entries", "N/A (module missing)")


# ══════════════════════════════════════════════════════════════
# SECTION 1: KPI Cards
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("KPI Summary")

# Gather KPI values
total_content = 0
if _RT_OK:
    rt_init_db()
    all_content = rt_get_all()
    total_content = len(all_content) if all_content else 0

api_cost_today = 0.0
if _API_OK:
    api_init_db()
    today_summary = get_usage_summary(days=1)
    api_cost_today = today_summary.get("total_cost_usd", 0.0)

cost_per_content = round(api_cost_today / total_content, 4) if total_content > 0 else 0.0

pipeline_rate = wd["success_rate"]

k1, k2, k3, k4 = st.columns(4)
k1.metric("Total Content Published", f"{total_content:,}" if _RT_OK else "N/A")
k2.metric("API Cost Today", f"${api_cost_today:.4f}" if _API_OK else "N/A")
k3.metric(
    "Cost / Content (today)",
    f"${cost_per_content:.4f}" if (_RT_OK and _API_OK) else "N/A",
)
k4.metric(
    "Pipeline Success Rate",
    f"{pipeline_rate}%" if pipeline_rate is not None else "N/A",
    help="From watchdog_history.json",
)


# ══════════════════════════════════════════════════════════════
# SECTION 2: Publishing Trends (last 30 days)
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("📊 Publishing Trends (Last 30 Days)")

if _RT_OK:
    trend = rt_daily_trend(days=30)
    if trend:
        df_trend = pd.DataFrame(trend)
        df_trend["day"] = pd.to_datetime(df_trend["day"])
        df_trend = df_trend.set_index("day")
        st.line_chart(df_trend[["count"]], use_container_width=True)
    else:
        st.info("No publishing data found for the last 30 days.")
else:
    st.warning("result_tracker_db module not available — cannot show publishing trends.")


# ══════════════════════════════════════════════════════════════
# SECTION 3: API Cost Breakdown (last 30 days)
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("💰 API Cost Breakdown (Last 30 Days)")

if _API_OK:
    col_daily, col_provider = st.columns(2)

    with col_daily:
        st.caption("Daily Cost Trend")
        daily = get_daily_breakdown(days=30)
        if daily:
            df_daily = pd.DataFrame(daily)
            df_daily["day"] = pd.to_datetime(df_daily["day"])
            df_daily = df_daily.set_index("day")
            st.bar_chart(df_daily[["cost"]], use_container_width=True)
        else:
            st.info("No API cost data for the last 30 days.")

    with col_provider:
        st.caption("Cost by Provider")
        providers = get_provider_breakdown(days=30)
        if providers:
            df_prov = pd.DataFrame(providers)
            df_prov = df_prov[["provider", "calls", "tokens", "cost"]]
            df_prov["cost"] = df_prov["cost"].apply(lambda x: round(x, 4))
            st.dataframe(df_prov, use_container_width=True, hide_index=True)
        else:
            st.info("No provider data available.")
else:
    st.warning("api_usage_tracker module not available — cannot show API cost breakdown.")


# ══════════════════════════════════════════════════════════════
# SECTION 4: Platform Performance
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("📱 Platform Performance")

if _RT_OK:
    platform_data = rt_platform_summary()
    if platform_data:
        rows = []
        for p in platform_data:
            total_v = p.get("total_views", 0)
            total_l = p.get("total_likes", 0)
            count = p.get("count", 0)
            engagement = round(total_l / total_v * 100, 2) if total_v > 0 else 0.0
            rows.append({
                "Platform": p.get("platform", "").upper(),
                "Content Count": count,
                "Total Views": f"{total_v:,}",
                "Total Likes": f"{total_l:,}",
                "Total Comments": f"{p.get('total_comments', 0):,}",
                "Avg Views": f"{p.get('avg_views', 0):,.0f}",
                "Engagement Rate": f"{engagement}%",
            })
        df_platform = pd.DataFrame(rows)
        st.dataframe(df_platform, use_container_width=True, hide_index=True)
    else:
        st.info("No platform data available yet. Register content in the Result Dashboard.")
else:
    st.warning("result_tracker_db module not available — cannot show platform performance.")


# ── Footer ────────────────────────────────────────────────────
st.divider()
st.caption("Data refreshes on each page load. Use sidebar for system health status.")
