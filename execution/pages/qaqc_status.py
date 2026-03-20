"""
QA/QC 현황 대시보드 (Streamlit).

QA/QC 러너의 실행 결과를 시각화합니다.
히스토리 DB에서 트렌드 데이터를 읽어 30일 추이를 표시합니다.

Usage:
    streamlit run execution/pages/qaqc_status.py
"""

import json
import sys
from pathlib import Path

# 경로 설정
ROOT_DIR = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT_DIR / "execution"))

try:
    import streamlit as st
except ImportError:
    print("streamlit이 설치되어 있지 않습니다: pip install streamlit")
    sys.exit(1)

# ── 페이지 설정 ──────────────────────────────────────────
st.set_page_config(
    page_title="QA/QC 현황",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ QA/QC 현황 대시보드")
st.caption("통합 테스트 · AST 검증 · 보안 스캔 · 인프라 헬스")


def load_latest_result() -> dict | None:
    """가장 최근 QA/QC 결과 JSON을 로드합니다."""
    result_path = ROOT_DIR / "knowledge-dashboard" / "public" / "qaqc_result.json"
    if not result_path.exists():
        return None
    try:
        with open(result_path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None


def load_history() -> list[dict]:
    """히스토리 DB에서 트렌드 데이터를 가져옵니다."""
    try:
        from qaqc_history_db import QaQcHistoryDB

        db = QaQcHistoryDB()
        return db.get_trend_data(days=30)
    except ImportError:
        return []


# ── 데이터 로드 ──────────────────────────────────────────
result = load_latest_result()
history = load_history()

if result is None:
    st.warning("아직 QA/QC 실행 결과가 없습니다. `python execution/qaqc_runner.py`를 먼저 실행하세요.")
    st.stop()

# ── 판정 배너 ───────────────────────────────────────────
verdict = result.get("verdict", "UNKNOWN")
verdict_map = {
    "APPROVED": ("✅ 승인 (APPROVED)", "success"),
    "CONDITIONALLY_APPROVED": ("⚠️ 조건부 승인", "warning"),
    "REJECTED": ("❌ 반려 (REJECTED)", "error"),
}
label, color = verdict_map.get(verdict, (f"❓ {verdict}", "info"))

col_verdict, col_time, col_duration = st.columns([2, 2, 1])
with col_verdict:
    if color == "success":
        st.success(f"**최종 판정: {label}**")
    elif color == "warning":
        st.warning(f"**최종 판정: {label}**")
    elif color == "error":
        st.error(f"**최종 판정: {label}**")
    else:
        st.info(f"**최종 판정: {label}**")

with col_time:
    ts = result.get("timestamp", "")
    st.metric("실행 시각", ts[:19].replace("T", " ") if ts else "—")

with col_duration:
    st.metric("소요 시간", f"{result.get('elapsed_sec', 0)}s")

st.divider()

# ── 테스트 요약 ──────────────────────────────────────────
st.subheader("📦 프로젝트별 테스트 결과")

projects = result.get("projects", {})
cols = st.columns(len(projects) if projects else 1)

for i, (name, data) in enumerate(projects.items()):
    with cols[i]:
        passed = data.get("passed", 0)
        failed = data.get("failed", 0)
        skipped = data.get("skipped", 0)
        status = data.get("status", "?")
        icon = "✅" if status == "PASS" else "❌"

        st.markdown(f"### {icon} {name}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Passed", passed)
        c2.metric("Failed", failed)
        c3.metric("Skipped", skipped)

st.divider()

# ── AST + 보안 ──────────────────────────────────────────
col_ast, col_sec = st.columns(2)

with col_ast:
    st.subheader("🔍 AST 구문 검증")
    ast_data = result.get("ast_check", {})
    ok = ast_data.get("ok", 0)
    total = ast_data.get("total", 0)
    st.metric("통과", f"{ok}/{total}")
    failures = ast_data.get("failures", [])
    if failures:
        for f in failures:
            st.error(f"❌ `{f['file']}`: {f['error']}")

with col_sec:
    st.subheader("🛡️ 보안 스캔")
    sec_data = result.get("security_scan", {})
    st.metric("상태", sec_data.get("status", "?"))
    issues = sec_data.get("issues", [])
    if issues:
        for iss in issues:
            st.warning(f"⚠️ `{iss['file']}`: {iss['pattern']}")

st.divider()

# ── 인프라 헬스 ─────────────────────────────────────────
infra = result.get("infrastructure", {})
if infra:
    st.subheader("🏗️ 인프라 헬스")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Docker", "🟢 Up" if infra.get("docker") else "🔴 Down")
    c2.metric("Ollama", "🟢 Up" if infra.get("ollama") else "🔴 Down")
    sched = infra.get("scheduler", {})
    c3.metric("Scheduler", f"{sched.get('ready', 0)}/{sched.get('total', 0)} Ready")
    c4.metric("디스크 여유", f"{infra.get('disk_gb_free', '?')} GB")

st.divider()

# ── 30일 추이 ───────────────────────────────────────────
if history:
    st.subheader("📈 30일 테스트 추이")
    import pandas as pd

    df = pd.DataFrame(history)
    if not df.empty:
        st.line_chart(df.set_index("date")[["passed", "failed"]])
else:
    st.info("트렌드 데이터가 아직 없습니다. QA/QC를 여러 번 실행하면 추이가 표시됩니다.")

# ── 총 테스트 수 ──────────────────────────────────────────
total = result.get("total", {})
st.markdown(f"**총 테스트: {total.get('passed', 0)} passed, {total.get('failed', 0)} failed**")
