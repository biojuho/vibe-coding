"""
Shorts Manager - YouTube Shorts 콘텐츠 자동 생성 및 관리 대시보드.
"""
import json
import subprocess
import sys
from pathlib import Path

import streamlit as st

# ---------------------------------------------------------------------------
# 경로 설정 + 모듈 import
# ---------------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
_V2_DIR = _ROOT / "shorts-maker-v2"
sys.path.insert(0, str(_ROOT))

_MODULE_OK = False
_MODULE_ERR = ""
try:
    from execution.content_db import (
        add_topic,
        delete_item,
        get_all,
        get_kpis,
        init_db,
        update_job,
    )
    _MODULE_OK = True
except ImportError as e:
    _MODULE_ERR = str(e)

# ---------------------------------------------------------------------------
# 채널 목록 (고정)
# ---------------------------------------------------------------------------
CHANNELS = [
    "심리학",
    "우주/천문학",
    "의학/건강",
    "AI/기술",
    "역사/고고학",
]

# ---------------------------------------------------------------------------
# 페이지 설정
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Shorts Manager", page_icon="🎬", layout="wide")

if not _MODULE_OK:
    st.error(f"content_db 모듈 로드 실패: {_MODULE_ERR}")
    st.stop()

init_db()

# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------

def _status_badge(status: str) -> str:
    colors = {
        "pending": "#6c757d",
        "running": "#fd7e14",
        "success": "#28a745",
        "failed":  "#dc3545",
    }
    labels = {"pending": "대기", "running": "생성중", "success": "완료", "failed": "실패"}
    color = colors.get(status, "#6c757d")
    label = labels.get(status, status)
    return f"<span style='background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem'>{label}</span>"


def _fmt_dur(sec: float) -> str:
    if sec <= 0:
        return "-"
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


def _fmt_cost(usd: float) -> str:
    return f"${usd:.4f}" if usd > 0 else "-"


def _scan_manifests() -> None:
    """v2 output 폴더의 manifest.json을 스캔해서 content_db 업데이트."""
    output_dir = _V2_DIR / "output"
    if not output_dir.exists():
        return
    for mf in output_dir.glob("*_manifest.json"):
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            job_id = data.get("job_id", "")
            if not job_id:
                continue
            # job_id로 content_db에서 matching 항목 검색
            items = get_all()
            for item in items:
                if item.get("job_id") == job_id:
                    update_job(
                        item["id"],
                        status=data.get("status", item["status"]),
                        title=data.get("title", ""),
                        video_path=data.get("output_path", ""),
                        thumbnail_path=data.get("thumbnail_path", ""),
                        cost_usd=data.get("estimated_cost_usd", 0.0),
                        duration_sec=data.get("total_duration_sec", 0.0),
                    )
                    break
        except Exception:
            pass


def _launch_v2(item_id: int, topic: str) -> str | None:
    """v2 파이프라인을 백그라운드로 실행. job_id 반환."""
    if not _V2_DIR.exists():
        return None
    cmd = [
        sys.executable, "-m", "shorts_maker_v2",
        "run",
        "--topic", topic,
        "--config", str(_V2_DIR / "config.yaml"),
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=str(_V2_DIR),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        update_job(item_id, status="running")
        return str(proc.pid)
    except Exception as exc:
        update_job(item_id, status="failed", notes=str(exc))
        return None


# ---------------------------------------------------------------------------
# UI 시작
# ---------------------------------------------------------------------------
st.title("🎬 Shorts Manager")
st.caption("YouTube Shorts 콘텐츠 자동 생성 및 관리")

# 동기화 버튼
col_sync, col_spacer = st.columns([1, 5])
with col_sync:
    if st.button("↻ 결과 동기화", help="v2 output 폴더에서 완료된 작업을 가져옵니다"):
        _scan_manifests()
        st.rerun()

# ---------------------------------------------------------------------------
# KPI 메트릭 (전체)
# ---------------------------------------------------------------------------
kpis = get_kpis()
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("총 콘텐츠", kpis.get("total", 0))
c2.metric("완료", kpis.get("success_count", 0))
c3.metric("대기 / 생성중", f"{kpis.get('pending_count', 0)} / {kpis.get('running_count', 0)}")
c4.metric("실패", kpis.get("failed_count", 0))
c5.metric("총 비용", f"${kpis.get('total_cost_usd', 0.0):.4f}")

st.divider()

# ---------------------------------------------------------------------------
# 레이아웃: 좌측 폼 | 우측 채널 탭 콘텐츠 목록
# ---------------------------------------------------------------------------
left, right = st.columns([1, 3])

v2_ok = _V2_DIR.exists()

# --- 좌측: 주제 추가 폼 ---
with left:
    st.subheader("새 콘텐츠 추가")
    with st.form("add_topic_form", clear_on_submit=True):
        channel_input = st.selectbox("채널", options=CHANNELS)
        topic_input = st.text_area(
            "주제", placeholder="예: 블랙홀의 미스터리 5가지", height=80
        )
        notes_input = st.text_input("메모 (선택)", placeholder="태그, 참고사항 등")
        submitted = st.form_submit_button("큐에 추가", width="stretch", type="primary")
        if submitted:
            if topic_input.strip():
                add_topic(topic_input.strip(), notes_input.strip(), channel=channel_input)
                st.success(f"[{channel_input}] 추가 완료!")
                st.rerun()
            else:
                st.warning("주제를 입력해주세요.")

    st.divider()

    # 채널별 KPI 요약
    st.caption("**채널별 현황**")
    for ch in CHANNELS:
        ch_kpis = get_kpis(channel=ch)
        total = ch_kpis.get("total", 0)
        success = ch_kpis.get("success_count", 0)
        pending = ch_kpis.get("pending_count", 0)
        if total > 0:
            st.caption(f"**{ch}**: 전체 {total} | 완료 {success} | 대기 {pending}")
        else:
            st.caption(f"**{ch}**: 주제 없음")

    st.divider()
    st.caption("**파이프라인 설정 경로**")
    st.code(str(_V2_DIR / "config.yaml"), language=None)
    if v2_ok:
        st.success("shorts-maker-v2 엔진 감지됨")
    else:
        st.error("shorts-maker-v2 디렉토리 없음")

# --- 우측: 채널 탭 콘텐츠 목록 ---
with right:
    st.subheader("콘텐츠 목록")
    all_items = get_all()

    # 탭: 전체 + 5개 채널
    tab_labels = [f"전체 ({len(all_items)})"] + CHANNELS
    tabs = st.tabs(tab_labels)

    def _render_items(items_to_show: list, key_prefix: str = "all") -> None:
        if not items_to_show:
            st.info("항목이 없습니다.")
            return
        for item in items_to_show:
            with st.container():
                row1, row2 = st.columns([4, 1])
                with row1:
                    status_html = _status_badge(item["status"])
                    title_display = item.get("title") or item["topic"]
                    ch_tag = f"<span style='background:#0d6efd;color:white;padding:2px 6px;border-radius:8px;font-size:0.7rem'>{item.get('channel','')}</span> " if item.get("channel") else ""
                    st.markdown(
                        f"{ch_tag}{status_html} &nbsp; **{title_display}**",
                        unsafe_allow_html=True,
                    )
                    if item.get("title") and item["title"] != item["topic"]:
                        st.caption(f"주제: {item['topic']}")
                    meta_parts = []
                    dur = _fmt_dur(item.get("duration_sec", 0))
                    cost = _fmt_cost(item.get("cost_usd", 0))
                    if dur != "-":
                        meta_parts.append(f"길이: {dur}")
                    if cost != "-":
                        meta_parts.append(f"비용: {cost}")
                    if item.get("created_at"):
                        meta_parts.append(f"생성: {item['created_at'][:16]}")
                    if meta_parts:
                        st.caption("  |  ".join(meta_parts))
                    if item.get("notes"):
                        st.caption(f"메모: {item['notes']}")

                with row2:
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        can_run = item["status"] in ("pending", "failed") and v2_ok
                        if st.button(
                            "▶ 실행",
                            key=f"run_{key_prefix}_{item['id']}",
                            disabled=not can_run,
                            help="v2 파이프라인 실행",
                        ):
                            pid = _launch_v2(item["id"], item["topic"])
                            if pid:
                                st.success(f"실행됨 (PID {pid})")
                            else:
                                st.error("실행 실패")
                            st.rerun()
                    with btn_col2:
                        if st.button("🗑", key=f"del_{key_prefix}_{item['id']}", help="삭제"):
                            delete_item(item["id"])
                            st.rerun()

                # 썸네일 미리보기
                thumb = item.get("thumbnail_path", "")
                if thumb and Path(thumb).exists():
                    with st.expander("썸네일 미리보기"):
                        st.image(thumb, width=320)

                # 비디오 경로
                video = item.get("video_path", "")
                if video and Path(video).exists():
                    with st.expander("영상 경로"):
                        st.code(video, language=None)

                st.divider()

    # 전체 탭
    with tabs[0]:
        _render_items(all_items, key_prefix="all")

    # 채널별 탭
    for i, ch in enumerate(CHANNELS):
        with tabs[i + 1]:
            ch_items = [item for item in all_items if item.get("channel") == ch]

            # 채널 탭 내 상태 필터
            sub_tab_all, sub_tab_pending, sub_tab_success, sub_tab_failed = st.tabs(
                [f"전체 ({len(ch_items)})", "대기/생성중", "완료", "실패"]
            )
            with sub_tab_all:
                _render_items(ch_items, key_prefix=f"ch{i}_all")
            with sub_tab_pending:
                _render_items([it for it in ch_items if it["status"] in ("pending", "running")], key_prefix=f"ch{i}_pend")
            with sub_tab_success:
                _render_items([it for it in ch_items if it["status"] == "success"], key_prefix=f"ch{i}_ok")
            with sub_tab_failed:
                _render_items([it for it in ch_items if it["status"] == "failed"], key_prefix=f"ch{i}_fail")
