"""
📈 운영 성과 대시보드 — 프로젝트 통합 KPI

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

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import streamlit as st  # noqa: E402
import pandas as pd  # noqa: E402

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

PROJECT_ROOT = WORKSPACE_ROOT
TMP_DIR = PROJECT_ROOT / ".tmp"
NO_RECORD_LABEL = "기록 없음"
MODULE_MISSING_LABEL = "모듈 없음"
MOBILE_TOUCH_TARGET_CSS = """
<style>
@media (max-width: 640px) {
    button[data-testid="stBaseButton-headerNoPadding"],
    button[data-testid="stExpandSidebarButton"],
    button[data-testid="stMainMenuButton"],
    button[data-testid="stBaseButton-elementToolbar"] {
        width: 44px !important;
        height: 44px !important;
        min-width: 44px !important;
        min-height: 44px !important;
    }

    button[data-testid="stBaseButton-header"] {
        min-width: 44px !important;
        min-height: 44px !important;
        height: 44px !important;
        padding-inline: 12px !important;
    }

    button[data-testid="stBaseButton-elementToolbar"] svg,
    [data-testid="stElementToolbarButtonIcon"] {
        width: 24px !important;
        height: 24px !important;
    }
}
</style>
"""

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="운영 성과 - Joolife",
    page_icon="📈",
    layout="wide",
)

st.markdown(MOBILE_TOUCH_TARGET_CSS, unsafe_allow_html=True)

st.title("📈 운영 성과", anchor=False)
st.caption("콘텐츠 · 비용 · 플랫폼 · 시스템 상태를 한 화면에서 확인합니다.")


# ── Helper: load JSON safely ─────────────────────────────────
def _load_json(path: Path) -> dict | list | None:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        pass
    return None


def _render_line_chart(data) -> None:
    st.line_chart(data, width="stretch")


def _render_bar_chart(data) -> None:
    st.bar_chart(data, width="stretch")


def _render_dataframe(data, **kwargs) -> None:
    st.dataframe(data, width="stretch", **kwargs)


def _has_multiple_rows(data) -> bool:
    try:
        return len(data) > 1
    except TypeError:
        return False


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
    result["success"] = sum(1 for r in records if r.get("status", "").lower() in ("ok", "success", "pass"))
    if result["total"] > 0:
        result["success_rate"] = round(result["success"] / result["total"] * 100, 1)

    # Last run timestamp
    last = records[-1] if records else {}
    result["last_run"] = last.get("timestamp") or last.get("time") or last.get("date")
    return result


# ══════════════════════════════════════════════════════════════
# SIDEBAR: 시스템 상태
# ══════════════════════════════════════════════════════════════
with st.sidebar:
    st.header("🩺 시스템 상태", anchor=False)

    # Last backup
    backup_data = _load_json(TMP_DIR / "backup_status.json")
    if backup_data:
        last_backup = backup_data.get("last_backup") or backup_data.get("timestamp", "—")
        st.metric("마지막 백업", str(last_backup)[:16])
    else:
        st.metric("마지막 백업", NO_RECORD_LABEL)

    # Last watchdog run
    wd = _watchdog_stats()
    st.metric("감시기 마지막 실행", str(wd["last_run"] or NO_RECORD_LABEL)[:16])
    if wd["success_rate"] is not None:
        st.metric("감시기 성공률", f"{wd['success_rate']}%")

    # LLM cache size
    llm_cache_dir = TMP_DIR / "llm_cache"
    if llm_cache_dir.exists():
        cache_files = list(llm_cache_dir.glob("*"))
        total_bytes = sum(f.stat().st_size for f in cache_files if f.is_file())
        size_mb = round(total_bytes / (1024 * 1024), 2)
        st.metric("LLM 캐시", f"{len(cache_files)}개 ({size_mb} MB)")
    else:
        st.metric("LLM 캐시", NO_RECORD_LABEL)

    # Debug DB entry count
    if _DEBUG_OK:
        debug_init_db()
        dstats = debug_get_stats()
        st.metric("디버그 DB 항목", dstats.get("total_entries", 0))
    else:
        st.metric("디버그 DB 항목", MODULE_MISSING_LABEL)


# ══════════════════════════════════════════════════════════════
# SECTION 1: KPI 카드
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("KPI 요약", anchor=False)

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
k1.metric("게시 콘텐츠", f"{total_content:,}" if _RT_OK else MODULE_MISSING_LABEL)
k2.metric("오늘 API 비용", f"${api_cost_today:.4f}" if _API_OK else MODULE_MISSING_LABEL)
k3.metric(
    "콘텐츠당 비용(오늘)",
    f"${cost_per_content:.4f}" if (_RT_OK and _API_OK) else MODULE_MISSING_LABEL,
)
with k4:
    st.metric("파이프라인 성공률", f"{pipeline_rate}%" if pipeline_rate is not None else NO_RECORD_LABEL)
    st.caption("자동 점검 이력 기준")


# ══════════════════════════════════════════════════════════════
# SECTION 2: 게시 추이(최근 30일)
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("📊 게시 추이(최근 30일)", anchor=False)

if _RT_OK:
    trend = rt_daily_trend(days=30)
    if trend:
        df_trend = pd.DataFrame(trend)
        df_trend["day"] = pd.to_datetime(df_trend["day"])
        df_trend = df_trend.set_index("day")
        df_trend = df_trend.rename(columns={"count": "게시 수"})
        if _has_multiple_rows(df_trend):
            _render_line_chart(df_trend[["게시 수"]])
        else:
            st.info("최근 30일 게시 데이터가 1건뿐입니다.")
            _render_dataframe(df_trend.reset_index(), hide_index=True)
    else:
        st.info("최근 30일 게시 데이터가 아직 없습니다.")
else:
    st.warning("게시 추이를 표시하려면 result_tracker_db 모듈이 필요합니다.")


# ══════════════════════════════════════════════════════════════
# SECTION 3: API 비용 분석(최근 30일)
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("💰 API 비용 분석(최근 30일)", anchor=False)

if _API_OK:
    col_daily, col_provider = st.columns(2)

    with col_daily:
        st.caption("일별 비용 추이")
        daily = get_daily_breakdown(days=30)
        if daily:
            df_daily = pd.DataFrame(daily)
            df_daily["day"] = pd.to_datetime(df_daily["day"])
            df_daily = df_daily.set_index("day")
            df_daily = df_daily.rename(columns={"cost": "비용(USD)"})
            if _has_multiple_rows(df_daily):
                _render_bar_chart(df_daily[["비용(USD)"]])
            else:
                st.info("최근 30일 API 비용 데이터가 1건뿐입니다.")
                _render_dataframe(df_daily.reset_index(), hide_index=True)
        else:
            st.info("최근 30일 API 비용 데이터가 없습니다.")

    with col_provider:
        st.caption("제공자별 비용")
        providers = get_provider_breakdown(days=30)
        if providers:
            df_prov = pd.DataFrame(providers)
            df_prov = df_prov[["provider", "calls", "tokens", "cost"]]
            df_prov["cost"] = df_prov["cost"].apply(lambda x: round(x, 4))
            df_prov = df_prov.rename(
                columns={
                    "provider": "제공자",
                    "calls": "호출 수",
                    "tokens": "토큰",
                    "cost": "비용(USD)",
                }
            )
            _render_dataframe(df_prov, hide_index=True)
        else:
            st.info("제공자 데이터가 없습니다.")
else:
    st.warning("API 비용 분석에는 api_usage_tracker 모듈이 필요합니다.")


# ══════════════════════════════════════════════════════════════
# SECTION 4: 플랫폼 성과
# ══════════════════════════════════════════════════════════════
st.divider()
st.subheader("📱 플랫폼 성과", anchor=False)

if _RT_OK:
    platform_data = rt_platform_summary()
    if platform_data:
        rows = []
        for p in platform_data:
            total_v = p.get("total_views", 0)
            total_l = p.get("total_likes", 0)
            count = p.get("count", 0)
            engagement = round(total_l / total_v * 100, 2) if total_v > 0 else 0.0
            rows.append(
                {
                    "플랫폼": p.get("platform", "").upper(),
                    "콘텐츠 수": count,
                    "총 조회수": f"{total_v:,}",
                    "총 좋아요": f"{total_l:,}",
                    "총 댓글": f"{p.get('total_comments', 0):,}",
                    "평균 조회수": f"{p.get('avg_views', 0):,.0f}",
                    "참여율": f"{engagement}%",
                }
            )
        df_platform = pd.DataFrame(rows)
        _render_dataframe(df_platform, hide_index=True)
    else:
        st.info("플랫폼 데이터가 아직 없습니다. 결과 대시보드에 콘텐츠를 등록하세요.")
else:
    st.warning("플랫폼 성과에는 result_tracker_db 모듈이 필요합니다.")


# ── Footer ────────────────────────────────────────────────────
st.divider()
st.caption("페이지를 열 때마다 데이터가 새로고침됩니다. 시스템 상태는 사이드바에서 확인하세요.")
