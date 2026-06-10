import sys
from pathlib import Path

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

import streamlit as st  # noqa: E402

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


def _stretch_button_kwargs() -> dict[str, str]:
    return {"width": "stretch"}


def _format_result_detail(detail: object) -> str:
    if not detail:
        return ""
    return str(detail).replace("`", "\\`")


def _inject_mobile_safe_styles() -> None:
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
}
div.stButton > button {
    min-height: 44px;
    white-space: normal;
}
div[data-testid="stSelectbox"] div[data-baseweb="select"],
div[data-testid="stSelectbox"] div[data-baseweb="select"] > div,
div[data-testid="stSelectbox"] input[role="combobox"] {
    min-height: 44px;
    min-width: 44px;
}
div[data-testid="stMetricValue"],
div[data-testid="stMarkdownContainer"] {
    overflow-wrap: anywhere;
}
</style>
""",
        unsafe_allow_html=True,
    )


def _status_label(status: str) -> str:
    return {
        STATUS_OK: "정상",
        STATUS_WARN: "확인 필요",
        STATUS_FAIL: "즉시 조치",
        STATUS_SKIP: "건너뜀",
    }.get(status, status.upper())


def _detail_has(detail_lower: str, *needles: str) -> bool:
    return any(needle in detail_lower for needle in needles)


def _status_next_action(status: str) -> str | None:
    if status == STATUS_OK:
        return "추가 조치가 필요 없습니다."
    if status == STATUS_SKIP:
        return "최초 실행 전이면 기록만 남기고, 반복 점검에서 계속 건너뛰면 생성 파이프라인을 확인하세요."
    return None


def _env_next_action(detail_lower: str) -> str:
    if _detail_has(detail_lower, "not set", "missing"):
        return ".env와 .env.example을 비교해 누락된 키를 채우고, 선택 provider인지 필수 provider인지 구분하세요."
    if "unexpected format" in detail_lower:
        return "키 prefix와 길이를 provider 콘솔 기준으로 확인하고, 포맷이 맞지 않으면 새 키로 교체하세요."
    return "환경 변수 값을 갱신한 뒤 같은 카테고리만 다시 점검하세요."


def _api_next_action(detail_lower: str) -> str:
    if _detail_has(detail_lower, "401", "unauthorized", "invalid"):
        return "인증 키가 만료되었거나 잘못되었습니다. provider 콘솔에서 재발급 후 .env를 갱신하세요."
    if _detail_has(detail_lower, "403", "forbidden"):
        return "키 권한, 조직, 프로젝트 스코프를 확인한 뒤 최소 권한으로 다시 연결하세요."
    if _detail_has(detail_lower, "429", "rate"):
        return "요청 제한 상태입니다. 재시도 간격을 두고 비용/쿼터 화면에서 한도를 확인하세요."
    if _detail_has(detail_lower, "timeout", "connection"):
        return "네트워크, DNS, 프록시, provider 상태를 확인한 뒤 연결 점검만 재실행하세요."
    if _detail_has(detail_lower, "not set", "missing keys"):
        return "필수 API인지 선택 API인지 판단하고, 필요한 키만 .env에 채운 뒤 재점검하세요."
    return "연결 실패 원문을 기준으로 인증, 권한, provider 상태를 순서대로 분리해 확인하세요."


def _filesystem_next_action(detail_lower: str) -> str:
    if "missing" in detail_lower:
        return "누락 경로를 프로젝트 root 기준으로 복구하고, 임시 산출물은 재생성 가능한지 확인하세요."
    return "경로 권한과 실제 위치를 확인한 뒤 파일시스템 점검만 다시 실행하세요."


def _database_next_action(detail_lower: str) -> str:
    if "not created yet" in detail_lower:
        return "초기화 스크립트나 관련 파이프라인을 실행해 workspace.db를 생성하세요."
    return "SQLite 파일 존재 여부와 integrity를 확인하고, 손상 시 재생성 가능한 백업 경로를 우선 확인하세요."


def _environment_next_action(result: dict) -> str:
    name_lower = str(result.get("name", "")).lower()
    if "venv" in name_lower:
        return "가상환경을 활성화하거나 의존성 설치 상태를 확인한 뒤 동일 점검을 반복하세요."
    if "git" in name_lower:
        return "현재 작업 경로가 Git 저장소 root인지 확인하세요."
    return "실행 환경 차이를 먼저 고정한 뒤 점검을 다시 실행하세요."


def _suggest_next_action(result: dict) -> str:
    status_action = _status_next_action(result.get("status", ""))
    if status_action:
        return status_action

    category = result.get("category", "")
    detail_lower = str(result.get("detail") or "").lower()
    category_handlers = {
        "env": lambda: _env_next_action(detail_lower),
        "api": lambda: _api_next_action(detail_lower),
        "filesystem": lambda: _filesystem_next_action(detail_lower),
        "database": lambda: _database_next_action(detail_lower),
        "environment": lambda: _environment_next_action(result),
    }
    handler = category_handlers.get(category)
    if handler:
        return handler()
    return "실패 원문을 근거로 소유 시스템을 분리하고, 같은 카테고리만 재실행해 복구 여부를 확인하세요."


def _build_action_items(results: list[dict], limit: int = 8) -> list[dict]:
    priority = {STATUS_FAIL: 0, STATUS_WARN: 1}
    actionable = [r for r in results if r.get("status") in priority]
    actionable.sort(
        key=lambda r: (
            priority.get(r.get("status", ""), 99),
            str(r.get("category", "")),
            str(r.get("name", "")),
        )
    )
    return actionable[:limit]


def _category_count_text(results: list[dict]) -> str:
    counts = {STATUS_OK: 0, STATUS_WARN: 0, STATUS_FAIL: 0, STATUS_SKIP: 0}
    for result in results:
        status = result.get("status")
        if status in counts:
            counts[status] += 1
    return (
        f"즉시 조치 {counts[STATUS_FAIL]} · "
        f"확인 필요 {counts[STATUS_WARN]} · "
        f"정상 {counts[STATUS_OK]} · "
        f"건너뜀 {counts[STATUS_SKIP]}"
    )


def _overall_message(summary: dict) -> str:
    counts = summary["counts"]
    if summary["overall"] == STATUS_FAIL:
        return (
            f"실패 {counts[STATUS_FAIL]}건이 있어 현재 환경은 바로 사용 가능한 상태가 아닙니다. "
            "아래 우선 조치부터 처리하세요."
        )
    if summary["overall"] == STATUS_WARN:
        return f"경고 {counts[STATUS_WARN]}건이 있습니다. 핵심 사용 전에 선택 provider와 누락 값을 구분해 정리하세요."
    return "점검한 항목은 바로 사용할 수 있는 상태입니다. 변경 후에는 같은 카테고리로 다시 확인하세요."


def _render_overall_notice(summary: dict) -> None:
    message = _overall_message(summary)
    if summary["overall"] == STATUS_FAIL:
        st.error(message)
    elif summary["overall"] == STATUS_WARN:
        st.warning(message)
    else:
        st.success(message)


def _render_action_items(results: list[dict]) -> None:
    st.subheader("우선 조치")
    action_items = _build_action_items(results)
    if not action_items:
        st.success("즉시 처리할 실패/경고 항목이 없습니다.")
        return

    for item in action_items:
        status = item.get("status", "")
        icon = _ICONS.get(status, "?")
        category = _CAT_LABELS.get(str(item.get("category", "")), str(item.get("category", "")))
        detail = _format_result_detail(item.get("detail"))
        st.markdown(f"{icon} **{_status_label(status)} · {category} · {item.get('name', '-')}**")
        if detail:
            st.caption(f"근거: {detail}")
        st.write(f"권장 조치: {_suggest_next_action(item)}")


st.set_page_config(page_title="Health Check - Joolife", page_icon="🏥", layout="wide")
_inject_mobile_safe_styles()

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
    "governance": "거버넌스",
}

st.title("시스템 상태 점검")
st.caption("실패, 경고, 권장 조치를 한 화면에 정리해 운영자가 바로 복구 순서를 정할 수 있게 합니다.")

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
    run_clicked = st.button("🔍 점검 실행", type="primary", **_stretch_button_kwargs())

# ── 점검 실행 ─────────────────────────────────────
if run_clicked:
    cat_arg = None if selected_cat == "all" else selected_cat
    with st.spinner("점검 중..."):
        results = run_all_checks(category=cat_arg)
    summary = get_summary(results)

    st.divider()
    _render_overall_notice(summary)
    overall_icon = _ICONS.get(summary["overall"], "?")
    c = summary["counts"]
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("판정", f"{overall_icon} {_status_label(summary['overall'])}")
    k2.metric("즉시 조치", c.get(STATUS_FAIL, 0))
    k3.metric("확인 필요", c.get(STATUS_WARN, 0))
    k4.metric("정상", c.get(STATUS_OK, 0))
    k5.metric("건너뜀", c.get(STATUS_SKIP, 0))

    st.divider()
    _render_action_items(results)

    st.divider()
    st.subheader("카테고리별 점검 결과")
    categories_in_results = sorted(set(r["category"] for r in results))
    for cat in categories_in_results:
        cat_results = [r for r in results if r["category"] == cat]
        cat_label = _CAT_LABELS.get(cat, cat)
        count_text = _category_count_text(cat_results)
        with st.expander(f"**{cat_label}** ({len(cat_results)}건 · {count_text})", expanded=True):
            for r in cat_results:
                icon = _ICONS.get(r["status"], "?")
                status_label = _status_label(r.get("status", ""))
                detail = _format_result_detail(r.get("detail"))
                detail_text = f" — `{detail}`" if detail else ""
                st.markdown(f"{icon} **{status_label} · {r['name']}**{detail_text}")

    st.divider()
    st.caption(f"총 {summary['total']}개 항목 점검 완료")
else:
    st.info("카테고리를 선택하고 **점검 실행**을 누르면 판정, 우선 조치, 근거가 함께 표시됩니다.")
