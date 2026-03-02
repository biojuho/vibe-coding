"""
Shorts Manager - YouTube Shorts 콘텐츠 자동 생성 및 관리 대시보드.
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

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
        get_channel_settings,
        get_kpis,
        get_youtube_stats,
        init_db,
        update_job,
        upsert_channel_settings,
    )

    _MODULE_OK = True
except ImportError as e:
    _MODULE_ERR = str(e)

_YT_OK = False
_YT_ERR = ""
try:
    from execution.youtube_uploader import (
        get_auth_status as yt_get_auth_status,
        upload_pending_items as yt_upload_pending,
        upload_video as yt_upload,
    )

    _YT_OK = True
except ImportError as e:
    _YT_ERR = str(e)

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
VOICE_OPTIONS = ["alloy", "ash", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer"]
STYLE_OPTIONS = ["default", "bold", "neon", "subtitle", "cta"]
_FLASH_KEY = "shorts_manager_flash"

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
def _set_flash(level: str, message: str) -> None:
    st.session_state[_FLASH_KEY] = {"level": level, "message": message}


def _render_flash() -> None:
    payload = st.session_state.pop(_FLASH_KEY, None)
    if not payload:
        return
    level = payload.get("level", "info")
    message = payload.get("message", "")
    getattr(st, level, st.info)(message)


def _status_badge(status: str) -> str:
    colors = {
        "pending": "#6c757d",
        "running": "#fd7e14",
        "success": "#28a745",
        "failed": "#dc3545",
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


def _youtube_badge(yt_status: str, yt_url: str = "") -> str:
    if yt_status == "uploaded" and yt_url:
        return f"<a href='{yt_url}' target='_blank' style='background:#ff0000;color:white;padding:2px 8px;border-radius:10px;font-size:0.7rem;text-decoration:none'>▶ YT</a>"
    if yt_status == "uploaded":
        return "<span style='background:#ff0000;color:white;padding:2px 8px;border-radius:10px;font-size:0.7rem'>▶ YT</span>"
    if yt_status == "failed":
        return "<span style='background:#6c757d;color:white;padding:2px 8px;border-radius:10px;font-size:0.7rem'>YT 실패</span>"
    return ""


def _scan_manifests() -> None:
    """v2 output 폴더의 manifest.json을 스캔해서 content_db 업데이트."""
    output_dir = _V2_DIR / "output"
    if not output_dir.exists():
        return
    manifests = list(output_dir.glob("*_manifest.json"))
    if not manifests:
        return
    all_items = get_all()
    job_lookup = {item.get("job_id"): item for item in all_items if item.get("job_id")}
    for mf in manifests:
        try:
            data = json.loads(mf.read_text(encoding="utf-8"))
            job_id = data.get("job_id", "")
            if not job_id:
                continue
            item = job_lookup.get(job_id)
            if item:
                update_job(
                    item["id"],
                    status=data.get("status", item["status"]),
                    title=data.get("title", ""),
                    video_path=data.get("output_path", ""),
                    thumbnail_path=data.get("thumbnail_path", ""),
                    cost_usd=data.get("estimated_cost_usd", 0.0),
                    duration_sec=data.get("total_duration_sec", 0.0),
                )
        except Exception:
            continue


def _launch_v2(item_id: int, topic: str, channel: str = "") -> str | None:
    """v2 파이프라인을 백그라운드로 실행. job_id 반환."""
    if not _V2_DIR.exists():
        return None
    cmd = [
        sys.executable,
        "-m",
        "shorts_maker_v2",
        "run",
        "--topic",
        topic,
        "--config",
        str(_V2_DIR / "config.yaml"),
    ]
    if channel:
        cmd.extend(["--channel", channel])
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


def _default_auth_status() -> dict[str, Any]:
    if _YT_OK:
        return yt_get_auth_status()
    return {
        "has_credentials_file": False,
        "has_token_file": False,
        "token_valid_or_refreshable": False,
        "ready": False,
        "reason": f"YouTube 업로더 로드 실패: {_YT_ERR}" if _YT_ERR else "YouTube 업로더 사용 불가",
    }


def _can_attempt_upload(auth_status: dict[str, Any]) -> bool:
    return _YT_OK and bool(auth_status.get("has_credentials_file"))


def _render_auth_status(auth_status: dict[str, Any]) -> None:
    st.subheader("YouTube 인증 상태")
    if not _YT_OK:
        st.error(auth_status["reason"])
        return
    if not auth_status["has_credentials_file"]:
        st.error("credentials.json 없음")
        st.caption("Google Cloud OAuth 클라이언트 파일을 프로젝트 루트에 배치해야 업로드를 시작할 수 있습니다.")
    elif not auth_status["has_token_file"]:
        st.warning("token.json 없음")
        st.caption("첫 업로드 시 브라우저 인증이 열립니다. credentials.json만 있으면 진행 가능합니다.")
    elif auth_status["token_valid_or_refreshable"]:
        st.success("토큰 준비 완료")
        st.caption("YouTube 업로드를 바로 실행할 수 있습니다.")
    else:
        st.warning("refresh 필요")
        st.caption("업로드 시 재인증이 필요할 수 있습니다.")


def _build_upload_metadata(item: dict[str, Any]) -> tuple[str, list[str]]:
    topic = item["topic"]
    channel = item.get("channel", "")
    description = f"#{channel} #{topic}" if channel else f"#{topic}"
    tags = [channel, "shorts"] if channel else ["shorts"]
    return description, tags


def _reset_youtube_fields(item_id: int) -> None:
    update_job(
        item_id,
        youtube_video_id="",
        youtube_status="",
        youtube_url="",
        youtube_uploaded_at="",
        youtube_error="",
    )


def _upload_single(item: dict[str, Any], retry: bool = False) -> dict[str, Any]:
    title = item.get("title") or item["topic"]
    description, tags = _build_upload_metadata(item)
    if retry:
        _reset_youtube_fields(item["id"])
    result = yt_upload(
        video_path=item["video_path"],
        title=title,
        description=description,
        tags=tags,
        privacy_status="private",
    )
    update_job(
        item["id"],
        youtube_video_id=result["video_id"],
        youtube_status="uploaded",
        youtube_url=result["youtube_url"],
        youtube_uploaded_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        youtube_error="",
    )
    return result


def _voice_index(settings: dict[str, Any] | None) -> int:
    voice = (settings or {}).get("voice", "alloy")
    return VOICE_OPTIONS.index(voice) if voice in VOICE_OPTIONS else 0


def _style_index(settings: dict[str, Any] | None) -> int:
    style = (settings or {}).get("style_preset", "default")
    return STYLE_OPTIONS.index(style) if style in STYLE_OPTIONS else 0


# ---------------------------------------------------------------------------
# UI 시작
# ---------------------------------------------------------------------------
st.title("🎬 Shorts Manager")
st.caption("YouTube Shorts 콘텐츠 자동 생성 및 관리")
_render_flash()

auth_status = _default_auth_status()

status_col, batch_col = st.columns([1, 2])
with status_col:
    _render_auth_status(auth_status)

with batch_col:
    st.subheader("일괄 업로드")
    with st.form("youtube_batch_upload"):
        batch_channel = st.selectbox("채널", options=["전체"] + CHANNELS)
        batch_limit = st.number_input("업로드 수", min_value=1, max_value=50, value=5, step=1)
        retry_failed = st.checkbox("기존 업로드 실패 건 재시도 포함")
        batch_submit = st.form_submit_button(
            "업로드 시작",
            disabled=not _can_attempt_upload(auth_status),
            use_container_width=True,
        )
        if batch_submit:
            target_channel = None if batch_channel == "전체" else batch_channel
            results = yt_upload_pending(
                limit=int(batch_limit),
                channel=target_channel,
                retry_failed=retry_failed,
                privacy_status="private",
            )
            uploaded = len([r for r in results if r.get("status") == "uploaded"])
            failed = len(results) - uploaded
            if results:
                level = "success" if failed == 0 else "warning"
                _set_flash(level, f"일괄 업로드 완료: 성공 {uploaded}건 / 실패 {failed}건")
            else:
                _set_flash("info", "업로드할 항목이 없습니다.")
            st.rerun()

sync_col, sync_spacer = st.columns([1, 5])
with sync_col:
    if st.button("↻ 결과 동기화", help="v2 output 폴더에서 완료된 작업을 가져옵니다", use_container_width=True):
        _scan_manifests()
        _set_flash("success", "manifest 동기화 완료")
        st.rerun()

# ---------------------------------------------------------------------------
# KPI 메트릭 (전체)
# ---------------------------------------------------------------------------
kpis = get_kpis()
yt_stats = get_youtube_stats()
c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("총 콘텐츠", kpis.get("total", 0))
c2.metric("완료", kpis.get("success_count", 0))
c3.metric("대기 / 생성중", f"{kpis.get('pending_count', 0)} / {kpis.get('running_count', 0)}")
c4.metric("실패", kpis.get("failed_count", 0))
c5.metric("총 비용", f"${kpis.get('total_cost_usd', 0.0):.4f}")
c6.metric("YT 업로드", f"{yt_stats['uploaded']} / {yt_stats['awaiting']}대기")

st.divider()

# ---------------------------------------------------------------------------
# 레이아웃: 좌측 폼 | 우측 채널 탭 콘텐츠 목록
# ---------------------------------------------------------------------------
left, right = st.columns([1, 3])

v2_ok = _V2_DIR.exists()
upload_allowed = _can_attempt_upload(auth_status)

with left:
    st.subheader("새 콘텐츠 추가")
    with st.form("add_topic_form", clear_on_submit=True):
        channel_input = st.selectbox("채널", options=CHANNELS)
        topic_input = st.text_area("주제", placeholder="예: 블랙홀의 미스터리 5가지", height=80)
        notes_input = st.text_input("메모 (선택)", placeholder="태그, 참고사항 등")
        submitted = st.form_submit_button("큐에 추가", use_container_width=True, type="primary")
        if submitted:
            if topic_input.strip():
                add_topic(topic_input.strip(), notes_input.strip(), channel=channel_input)
                _set_flash("success", f"[{channel_input}] 주제 추가 완료")
                st.rerun()
            else:
                st.warning("주제를 입력해주세요.")

    st.divider()

    st.subheader("채널 설정")
    settings_channel = st.selectbox("설정 채널", options=CHANNELS, key="settings_channel")
    channel_settings = get_channel_settings(settings_channel) or {}
    with st.form(f"channel_settings_form_{settings_channel}"):
        voice = st.selectbox("Voice", options=VOICE_OPTIONS, index=_voice_index(channel_settings))
        style_preset = st.selectbox("Style preset", options=STYLE_OPTIONS, index=_style_index(channel_settings))
        font_color = st.text_input("Font color", value=channel_settings.get("font_color", "#FFD700"))
        image_prefix = st.text_area(
            "Image style prefix",
            value=channel_settings.get("image_style_prefix", ""),
            height=80,
            placeholder="예: cinematic documentary lighting, high contrast",
        )
        settings_submit = st.form_submit_button("채널 설정 저장", use_container_width=True)
        if settings_submit:
            upsert_channel_settings(
                settings_channel,
                voice=voice,
                style_preset=style_preset,
                font_color=font_color.strip() or "#FFD700",
                image_style_prefix=image_prefix.strip(),
            )
            _set_flash("success", f"[{settings_channel}] 채널 설정 저장 완료")
            st.rerun()

    st.divider()

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

with right:
    st.subheader("콘텐츠 목록")
    all_items = get_all()
    tab_labels = [f"전체 ({len(all_items)})"] + CHANNELS
    tabs = st.tabs(tab_labels)

    def _render_items(items_to_show: list[dict[str, Any]], key_prefix: str = "all") -> None:
        if not items_to_show:
            st.info("항목이 없습니다.")
            return
        for item in items_to_show:
            with st.container():
                row1, row2 = st.columns([4, 1.4])
                with row1:
                    status_html = _status_badge(item["status"])
                    yt_html = _youtube_badge(item.get("youtube_status", ""), item.get("youtube_url", ""))
                    title_display = item.get("title") or item["topic"]
                    ch_tag = ""
                    if item.get("channel"):
                        ch_tag = (
                            f"<span style='background:#0d6efd;color:white;padding:2px 6px;"
                            f"border-radius:8px;font-size:0.7rem'>{item['channel']}</span> "
                        )
                    st.markdown(f"{ch_tag}{status_html} {yt_html} &nbsp; **{title_display}**", unsafe_allow_html=True)
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
                    if item.get("youtube_error"):
                        st.caption(f"업로드 오류: {item['youtube_error']}")

                with row2:
                    btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                    with btn_col1:
                        can_run = item["status"] in ("pending", "failed") and v2_ok
                        if st.button(
                            "실행",
                            key=f"run_{key_prefix}_{item['id']}",
                            disabled=not can_run,
                            help="v2 파이프라인 실행",
                            use_container_width=True,
                        ):
                            pid = _launch_v2(item["id"], item["topic"], item.get("channel", ""))
                            if pid:
                                _set_flash("success", f"실행됨 (PID {pid})")
                            else:
                                _set_flash("error", "실행 실패")
                            st.rerun()
                    with btn_col2:
                        can_upload = (
                            upload_allowed
                            and item["status"] == "success"
                            and item.get("video_path", "")
                            and not item.get("youtube_status")
                        )
                        if st.button(
                            "YT 업로드",
                            key=f"yt_{key_prefix}_{item['id']}",
                            disabled=not can_upload,
                            help="YouTube 업로드",
                            use_container_width=True,
                        ):
                            try:
                                result = _upload_single(item, retry=False)
                                _set_flash("success", f"업로드 완료: {result['youtube_url']}")
                            except Exception as exc:
                                update_job(item["id"], youtube_status="failed", youtube_error=str(exc)[:300])
                                _set_flash("error", f"업로드 실패: {exc}")
                            st.rerun()
                    with btn_col3:
                        can_retry = (
                            upload_allowed
                            and item["status"] == "success"
                            and item.get("video_path", "")
                            and item.get("youtube_status") == "failed"
                        )
                        if st.button(
                            "YT 재시도",
                            key=f"ytretry_{key_prefix}_{item['id']}",
                            disabled=not can_retry,
                            help="업로드 실패 건 재시도",
                            use_container_width=True,
                        ):
                            try:
                                result = _upload_single(item, retry=True)
                                _set_flash("success", f"재업로드 완료: {result['youtube_url']}")
                            except Exception as exc:
                                update_job(item["id"], youtube_status="failed", youtube_error=str(exc)[:300])
                                _set_flash("error", f"재업로드 실패: {exc}")
                            st.rerun()
                    with btn_col4:
                        if st.button(
                            "삭제",
                            key=f"del_{key_prefix}_{item['id']}",
                            help="삭제",
                            use_container_width=True,
                        ):
                            delete_item(item["id"])
                            _set_flash("success", "항목 삭제 완료")
                            st.rerun()

                thumb = item.get("thumbnail_path", "")
                if thumb and Path(thumb).exists():
                    with st.expander("썸네일 미리보기"):
                        st.image(thumb, width=320)

                video = item.get("video_path", "")
                if video and Path(video).exists():
                    with st.expander("영상 경로"):
                        st.code(video, language=None)

                st.divider()

    with tabs[0]:
        _render_items(all_items, key_prefix="all")

    for i, ch in enumerate(CHANNELS):
        with tabs[i + 1]:
            ch_items = [item for item in all_items if item.get("channel") == ch]
            sub_tab_all, sub_tab_pending, sub_tab_success, sub_tab_failed = st.tabs(
                [f"전체 ({len(ch_items)})", "대기/생성중", "완료", "실패"]
            )
            with sub_tab_all:
                _render_items(ch_items, key_prefix=f"ch{i}_all")
            with sub_tab_pending:
                _render_items(
                    [it for it in ch_items if it["status"] in ("pending", "running")],
                    key_prefix=f"ch{i}_pend",
                )
            with sub_tab_success:
                _render_items(
                    [it for it in ch_items if it["status"] == "success"],
                    key_prefix=f"ch{i}_ok",
                )
            with sub_tab_failed:
                _render_items(
                    [it for it in ch_items if it["status"] == "failed"],
                    key_prefix=f"ch{i}_fail",
                )
