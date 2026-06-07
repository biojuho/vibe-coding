"""
QA/QC status dashboard.

Usage:
    streamlit run workspace/execution/pages/qaqc_status.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import resolve_project_dir

try:
    import streamlit as st
except ImportError:
    print("streamlit is not installed. Run: pip install streamlit")
    sys.exit(1)


_PAGE_TITLE = "검증 현황 - Joolife"
_RESULT_RELATIVE_PATH = ".tmp/project_qc_runner_latest.json"
_KNOWLEDGE_DATA_RESULT_RELATIVE_PATH = "projects/knowledge-dashboard/data/qaqc_result.json"
_FALLBACK_RESULT_RELATIVE_PATH = "projects/knowledge-dashboard/public/qaqc_result.json"
_STALE_RESULT_DAYS = 7
_SHORTS_QC_COMMAND = "python execution\\project_qc_runner.py --project shorts-maker-v2 --json --timeout-seconds 300"
_FULL_QC_COMMAND = "python execution\\project_qc_runner.py --json --timeout-seconds 700"
_PLOTLY_CHART_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "responsive": True,
}


def _inject_qaqc_mobile_css() -> None:
    st.markdown(
        """
        <style>
        @media (max-width: 640px) {
          h1 {
            font-size: 2rem !important;
            line-height: 1.15 !important;
          }
          div[data-testid="stToolbar"] button,
          div[data-testid="stToolbar"] a,
          div[data-testid="stToolbar"] [role="button"],
          div[data-testid="stStatusWidget"] button,
          button[kind],
          div[data-testid="stButton"] button {
            min-height: 44px !important;
            min-width: 44px !important;
          }
          div[data-testid="stMetric"] {
            min-width: 0 !important;
          }
          div[data-testid="stMetric"] label,
          div[data-testid="stMarkdownContainer"],
          div[data-testid="stCaptionContainer"] {
            overflow-wrap: anywhere;
            word-break: keep-all;
          }
          div[data-testid="stDataFrame"] {
            max-width: 100% !important;
          }
          div[data-testid="stExpander"] summary {
            min-height: 44px !important;
            align-items: center !important;
          }
          a[aria-label="Link to heading"] {
            display: inline-flex !important;
            min-height: 44px !important;
            min-width: 44px !important;
            align-items: center !important;
            justify-content: center !important;
          }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _candidate_result_paths() -> list[Path]:
    project_dir = resolve_project_dir("knowledge-dashboard")
    return [
        WORKSPACE_ROOT.parent / ".tmp" / "project_qc_runner_latest.json",
        project_dir / "data" / "qaqc_result.json",
        project_dir / "public" / "qaqc_result.json",
    ]


def load_latest_result() -> dict[str, Any] | None:
    for result_path in _candidate_result_paths():
        if not result_path.exists():
            continue
        try:
            return json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _parse_timestamp(timestamp: str | None) -> datetime | None:
    if not timestamp:
        return None
    normalized = timestamp.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _result_verdict(result: dict[str, Any]) -> str:
    verdict = str(result.get("verdict") or "").strip().upper()
    if verdict:
        return verdict
    status = str(result.get("status") or "").strip().lower()
    if status in {"pass", "passed", "ok", "success", "approved"}:
        return "APPROVED"
    if status in {"warn", "warning", "conditionally_approved"}:
        return "CONDITIONALLY_APPROVED"
    if status in {"fail", "failed", "error", "rejected"}:
        return "REJECTED"
    return "UNKNOWN"


def _result_totals(result: dict[str, Any]) -> dict[str, int]:
    totals = result.get("total")
    if isinstance(totals, dict) and totals:
        return {
            "passed": int(totals.get("passed") or 0),
            "failed": int(totals.get("failed") or 0),
            "errors": int(totals.get("errors") or 0),
            "skipped": int(totals.get("skipped") or 0),
        }
    projects = result.get("projects", {})
    if not isinstance(projects, dict):
        return {"passed": 0, "failed": 0, "errors": 0, "skipped": 0}
    return {
        "passed": sum(int(project.get("passed") or 0) for project in projects.values()),
        "failed": sum(int(project.get("failed") or 0) for project in projects.values()),
        "errors": sum(int(project.get("errors") or 0) for project in projects.values()),
        "skipped": sum(int(project.get("skipped") or 0) for project in projects.values()),
    }


def _quality_warnings(result: dict[str, Any], *, now: datetime | None = None) -> list[str]:
    warnings: list[str] = []
    timestamp = _parse_timestamp(str(result.get("timestamp") or ""))
    if timestamp is None:
        warnings.append("실행 시각이 없어 결과 신선도를 확인할 수 없습니다.")
    else:
        current = now or datetime.now(timezone.utc)
        age_days = max(0, (current.astimezone(timezone.utc) - timestamp).days)
        if age_days > _STALE_RESULT_DAYS:
            warnings.append(f"QA/QC 결과가 {age_days}일 전 데이터입니다. 게시·공유 전 재검증이 필요합니다.")
    projects = result.get("projects", {})
    if not isinstance(projects, dict) or not projects:
        warnings.append("프로젝트별 결과가 비어 있어 전체 워크스페이스 판단에는 부족합니다.")
    return warnings


def load_history() -> list[dict[str, Any]]:
    try:
        from execution.qaqc_history_db import QaQcHistoryDB

        db = QaQcHistoryDB()
        return db.get_trend_data(days=30)
    except Exception:
        return []


def _verdict_label(verdict: str) -> str:
    labels = {
        "APPROVED": "사용 가능",
        "CONDITIONALLY_APPROVED": "조건부 사용",
        "REJECTED": "조치 필요",
    }
    return labels.get(verdict.upper(), "확인 필요")


def _status_label(status: str | None) -> str:
    normalized = (status or "").strip().lower()
    if normalized in {"pass", "passed", "ok", "success", "approved"}:
        return "통과"
    if normalized in {"warn", "warning", "conditionally_approved"}:
        return "확인 필요"
    if normalized in {"fail", "failed", "error", "rejected"}:
        return "실패"
    if normalized in {"skip", "skipped"}:
        return "건너뜀"
    return status or "-"


def _format_elapsed(seconds: int | float | str | None) -> str:
    try:
        numeric = float(seconds or 0)
    except (TypeError, ValueError):
        return "-"
    if numeric < 60:
        return f"{numeric:.1f}초"
    minutes, remainder = divmod(int(numeric), 60)
    return f"{minutes}분 {remainder}초"


def _project_next_action(project_name: str, data: dict[str, Any]) -> str:
    status = _status_label(str(data.get("status", "")))
    failed = int(data.get("failed") or 0)
    errors = int(data.get("errors") or 0)
    if failed or errors or status == "실패":
        return "실패 로그 확인 후 해당 프로젝트 focused gate를 먼저 재실행"
    if project_name == "blind-to-x" and status == "통과":
        return "초안 게시 전 Notion 리뷰 큐와 X 게시 상태만 최종 확인"
    if project_name == "shorts-maker-v2" and status == "통과":
        return "쇼츠 생성·업로드 전 최신 QC 기준으로 사용 가능"
    if project_name == "hanwoo-dashboard" and status == "통과":
        return "로컬 QC 통과; live Supabase CRUD는 T-251 해소 후 별도 확인"
    if project_name == "knowledge-dashboard" and status == "통과":
        return "배포 전 인증 data route smoke만 유지"
    if status == "확인 필요":
        return "경고 상세 확인 후 결과물 게시 전 재검증"
    return "추가 조치 없음"


def _build_project_rows(projects: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for name, data in projects.items():
        rows.append(
            {
                "프로젝트": name,
                "상태": _status_label(str(data.get("status", "-"))),
                "통과": int(data.get("passed") or 0),
                "실패": int(data.get("failed") or 0),
                "건너뜀": int(data.get("skipped") or 0),
                "다음 조치": _project_next_action(name, data),
            }
        )
    return rows


def _render_action_summary(rows: list[dict[str, Any]]) -> None:
    failed_rows = [row for row in rows if row["상태"] == "실패"]
    warning_rows = [row for row in rows if row["상태"] == "확인 필요"]
    if failed_rows:
        st.error(f"즉시 조치 필요: {len(failed_rows)}개 프로젝트 실패")
    elif warning_rows:
        st.warning(f"확인 필요: {len(warning_rows)}개 프로젝트 경고")
    else:
        st.success("로컬 QC 기준으로 모든 프로젝트가 통과했습니다.")

    st.markdown("**프로젝트별 다음 조치**")
    for row in rows:
        st.markdown(f"- **{row['프로젝트']}**: {row['다음 조치']}")


def _render_empty_state() -> None:
    st.warning("아직 QA/QC 결과 파일이 없습니다.")
    st.markdown("**바로 실행할 검증**")
    st.caption("쇼츠 생성·업로드 판단이 필요하면 Shorts Maker V2 focused QC를 먼저 실행합니다.")
    _render_command(_SHORTS_QC_COMMAND)
    st.caption("릴리스 전 전체 프로젝트 상태를 다시 확인할 때는 전체 QC를 실행합니다.")
    _render_command(_FULL_QC_COMMAND)
    st.caption(f"기본 결과 파일: `{_RESULT_RELATIVE_PATH}`")
    st.caption(f"Knowledge Dashboard 인증 data: `{_KNOWLEDGE_DATA_RESULT_RELATIVE_PATH}`")
    st.caption(f"로컬 러너 fallback: `{_FALLBACK_RESULT_RELATIVE_PATH}`")


def _render_command(command: str) -> None:
    st.code(command, language="powershell", wrap_lines=True, width="stretch")


def _render_verdict(result: dict[str, Any]) -> None:
    verdict = _result_verdict(result)
    message = f"최종 판정: {_verdict_label(verdict)}"
    renderer = {
        "APPROVED": st.success,
        "CONDITIONALLY_APPROVED": st.warning,
        "REJECTED": st.error,
    }.get(verdict.upper(), st.info)
    renderer(message)


def _render_summary_metrics(result: dict[str, Any]) -> None:
    totals = _result_totals(result)
    timestamp = str(result.get("timestamp", ""))
    col_verdict, col_time, col_elapsed, col_passed = st.columns(4)
    with col_verdict:
        st.metric("판정", _verdict_label(_result_verdict(result)))
    with col_time:
        st.metric("실행 시각", timestamp[:19].replace("T", " ") if timestamp else "-")
    with col_elapsed:
        st.metric("소요 시간", _format_elapsed(result.get("elapsed_sec")))
    with col_passed:
        st.metric("통과", totals.get("passed", 0))


def _render_project_results(result: dict[str, Any]) -> None:
    projects = result.get("projects", {})
    rows = _build_project_rows(projects)
    st.subheader("프로젝트별 검증 결과")
    if not rows:
        st.info("프로젝트별 결과가 비어 있습니다.")
        return

    _render_action_summary(rows)
    st.dataframe(
        rows,
        width="stretch",
        hide_index=True,
        column_config={
            "프로젝트": st.column_config.TextColumn("프로젝트", width="medium"),
            "상태": st.column_config.TextColumn("상태", width="small"),
            "통과": st.column_config.NumberColumn("통과", width="small"),
            "실패": st.column_config.NumberColumn("실패", width="small"),
            "건너뜀": st.column_config.NumberColumn("건너뜀", width="small"),
            "다음 조치": st.column_config.TextColumn("다음 조치", width="large"),
        },
    )

    for row in rows:
        with st.expander(f"{row['프로젝트']} · {row['상태']}", expanded=row["상태"] != "통과"):
            st.markdown(f"**다음 조치:** {row['다음 조치']}")
            st.caption(f"통과 {row['통과']} · 실패 {row['실패']} · 건너뜀 {row['건너뜀']}")


def _render_system_checks(result: dict[str, Any]) -> None:
    col_ast, col_security = st.columns(2)

    with col_ast:
        st.subheader("AST 점검")
        ast_data = result.get("ast_check", {})
        st.metric("정상 모듈", f"{ast_data.get('ok', 0)}/{ast_data.get('total', 0)}")
        for failure in ast_data.get("failures", []):
            st.error(f"{failure['file']}: {failure['error']}")

    with col_security:
        st.subheader("보안 스캔")
        security_data = result.get("security_scan", {})
        st.metric("상태", _status_label(str(security_data.get("status", "-"))))
        detail = security_data.get("status_detail")
        if detail:
            st.caption(str(detail))
        for issue in security_data.get("issues", []):
            st.warning(f"{issue['file']}: {issue['pattern']}")


def _render_infrastructure(result: dict[str, Any]) -> None:
    infra = result.get("infrastructure", {})
    st.divider()
    st.subheader("인프라 상태")
    if not infra:
        st.info("인프라 점검 결과가 없습니다.")
        return
    infra_columns = st.columns(4)
    infra_columns[0].metric("Docker", "정상" if infra.get("docker") else "중지")
    infra_columns[1].metric("Ollama", "정상" if infra.get("ollama") else "중지")
    scheduler = infra.get("scheduler", {})
    infra_columns[2].metric("스케줄러", f"{scheduler.get('ready', 0)}/{scheduler.get('total', 0)} 준비")
    infra_columns[3].metric("디스크 여유", f"{infra.get('disk_gb_free', '?')} GB")


def _render_trend(history: list[dict[str, Any]]) -> None:
    if not history:
        return
    try:
        import plotly.express as px
    except ImportError:
        st.caption("검증 추세 차트를 표시하려면 plotly가 필요합니다.")
        return

    if not any("date" in row for row in history):
        return

    columns = [column for column in ["passed", "failed"] if any(column in row for row in history)]
    if not columns:
        return

    st.divider()
    st.subheader("30일 검증 추세")
    chart_rows = [
        {
            "날짜": row.get("date", "-"),
            "통과": row.get("passed", 0),
            "실패": row.get("failed", 0),
        }
        for row in history
    ]
    fig = px.line(chart_rows, x="날짜", y=[{"passed": "통과", "failed": "실패"}[column] for column in columns])
    fig.update_layout(
        legend_title_text="항목",
        xaxis_title="날짜",
        yaxis_title="건수",
        margin={"l": 8, "r": 8, "t": 16, "b": 8},
    )
    st.plotly_chart(fig, width="stretch", config=_PLOTLY_CHART_CONFIG)


def main() -> None:
    st.set_page_config(page_title=_PAGE_TITLE, page_icon="✅", layout="wide")
    _inject_qaqc_mobile_css()
    st.title("✅ 검증 현황")
    st.caption("Shorts Maker V2와 워크스페이스 릴리스 게이트를 한 화면에서 확인합니다.")

    result = load_latest_result()
    if result is None:
        _render_empty_state()
        return

    for warning in _quality_warnings(result):
        st.warning(warning)
    _render_verdict(result)
    _render_summary_metrics(result)
    st.divider()
    _render_project_results(result)
    st.divider()
    _render_system_checks(result)
    _render_infrastructure(result)
    _render_trend(load_history())

    totals = _result_totals(result)
    st.divider()
    st.caption(
        f"합계: 통과 {totals.get('passed', 0)} · 실패 {totals.get('failed', 0)} · "
        f"오류 {totals.get('errors', 0)} · 건너뜀 {totals.get('skipped', 0)}"
    )


if __name__ == "__main__":
    main()
