"""
Shorts Manager - YouTube Shorts 콘텐츠 자동 생성 및 관리 대시보드.
"""

from __future__ import annotations

import html as _html
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

import streamlit as st

WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from path_contract import resolve_project_dir
from execution.youtube_metadata import build_shorts_upload_metadata

# ---------------------------------------------------------------------------
# 경로 설정 + 모듈 import
# ---------------------------------------------------------------------------
_V2_DIR = resolve_project_dir("shorts-maker-v2", required_paths=("config.yaml",))

_MODULE_OK = False
_MODULE_ERR = ""
try:
    from execution.content_db import (
        add_topic,
        delete_item,
        get_all,
        get_channel_settings,
        get_channel_readiness_summary,
        get_manifest_sync_diffs,
        get_kpis,
        get_recent_failure_items,
        get_review_queue_items,
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

_NOTION_OK = False
_NOTION_ERR = ""
try:
    from execution.notion_shorts_sync import (
        is_configured as notion_is_configured,
        sync_all as notion_sync_all,
        sync_item as notion_sync_item,
    )

    _NOTION_OK = True
except ImportError as e:
    _NOTION_ERR = str(e)

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
_DELETE_CONFIRM_KEY = "shorts_manager_pending_delete_id"
_RUN_BLOCKING_OPS_STATUSES = {"setup_required", "critical"}
_ISSUE_LABELS = {
    "channel_settings_missing": "채널 설정 없음",
    "missing_brand_assets": "브랜드 에셋 누락",
    "brand_asset_missing": "브랜드 에셋 누락",
    "missing_bgm": "BGM 누락",
    "bgm_missing": "BGM 누락",
    "failed_jobs_present": "실패 작업 있음",
    "low_disk_space": "디스크 공간 부족",
}
_CHANNEL_LABEL_ALIASES = {
    "ai/tech": "AI/기술",
    "ai-tech": "AI/기술",
    "ai_tech": "AI/기술",
    "space": "우주/천문학",
    "history": "역사/고고학",
    "psychology": "심리학",
    "health": "의학/건강",
}
_OPS_STATUS_PRIORITY = {"critical": 0, "setup_required": 1, "warning": 2, "healthy": 3}
_CHANNEL_READINESS_COUNT_FIELDS = (
    "total_count",
    "pending_count",
    "running_count",
    "failed_count",
    "success_count",
)

# ---------------------------------------------------------------------------
# 페이지 설정
# ---------------------------------------------------------------------------
st.set_page_config(page_title="Shorts Manager", page_icon="🎬", layout="wide")

if not _MODULE_OK:
    st.error(f"content_db 모듈 로드 실패: {_MODULE_ERR}")
    st.stop()

init_db()


def _inject_mobile_touch_target_styles() -> None:
    st.markdown(
        """
<style>
.shorts-operator-shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin: 0.75rem 0 1rem;
}

.shorts-operator-shortcuts a {
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.6rem 0.85rem;
  border: 1px solid rgba(49, 51, 63, 0.18);
  border-radius: 999px;
  color: inherit;
  text-decoration: none;
  background: rgba(250, 250, 250, 0.72);
  font-weight: 600;
  line-height: 1.2;
}

.shorts-operator-shortcuts a:focus,
.shorts-operator-shortcuts a:hover {
  border-color: rgba(255, 75, 75, 0.58);
  background: rgba(255, 75, 75, 0.08);
}

.shorts-section-anchor {
  display: block;
  height: 0;
  position: relative;
  top: -0.75rem;
  visibility: hidden;
}

.st-key-shorts_delete_confirmation {
  position: fixed;
  top: 4rem;
  left: 50%;
  right: auto;
  width: min(760px, calc(100vw - 2rem));
  transform: translateX(-50%);
  z-index: 1000;
  background: rgb(255, 255, 255);
  border-radius: 8px;
  box-shadow: 0 16px 36px rgba(15, 23, 42, 0.18);
  box-sizing: border-box;
  max-height: min(52vh, 24rem);
  overflow-y: auto;
}

@media (max-width: 640px) {
  div[role='tablist'] {
    flex-wrap: wrap;
    gap: 0.25rem;
    overflow-x: visible;
  }

  div[role='tablist'] button[role='tab'],
  div[data-testid='stButton'] button,
  div[data-testid='stFormSubmitButton'] button,
  div[data-baseweb='select'],
  div[data-baseweb='input'],
  div[data-baseweb='input'] input,
  button[data-testid='stNumberInputStepDown'],
  button[data-testid='stNumberInputStepUp'],
  div[data-testid='stCheckbox'] label {
    min-height: 44px;
  }

  button[data-testid='stNumberInputStepDown'],
  button[data-testid='stNumberInputStepUp'] {
    min-width: 44px;
  }

  div[role='tablist'] button[role='tab'] {
    min-width: 44px;
    flex: 0 0 auto;
  }

  .st-key-shorts_delete_confirmation {
    top: 3.5rem;
    width: calc(100vw - 1.5rem);
    max-height: 48vh;
  }

  .shorts-operator-shortcuts a {
    flex: 1 1 calc(50% - 0.5rem);
  }
}
</style>
""",
        unsafe_allow_html=True,
    )


_inject_mobile_touch_target_styles()


def _section_anchor(anchor: str) -> None:
    safe_anchor = _html.escape(anchor, quote=True)
    st.markdown(
        f'<span id="{safe_anchor}" class="shorts-section-anchor"></span>',
        unsafe_allow_html=True,
    )


def _render_operator_shortcuts() -> None:
    st.markdown(
        """
<nav class="shorts-operator-shortcuts" aria-label="쇼츠 운영 빠른 이동">
  <a href="#shorts-add-topic">새 콘텐츠</a>
  <a href="#shorts-content-list">콘텐츠 목록</a>
  <a href="#shorts-review-queue">검수 큐</a>
  <a href="#shorts-channel-settings">채널 설정</a>
</nav>
""",
        unsafe_allow_html=True,
    )


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


def _get_pending_delete_id() -> int | None:
    pending = st.session_state.get(_DELETE_CONFIRM_KEY)
    if isinstance(pending, int) and not isinstance(pending, bool):
        return pending
    return None


def _request_delete_confirmation(item_id: int) -> None:
    st.session_state[_DELETE_CONFIRM_KEY] = item_id
    _set_flash("warning", "삭제 확인 대기: 항목을 지우려면 삭제 확인을 누르세요.")


def _cancel_delete_confirmation(item_id: int | None = None) -> None:
    pending = _get_pending_delete_id()
    if item_id is None or pending == item_id:
        st.session_state.pop(_DELETE_CONFIRM_KEY, None)


def _delete_item_with_confirmation(item_id: int) -> None:
    delete_item(item_id)
    _cancel_delete_confirmation(item_id)
    _set_flash("success", "항목 삭제 완료")


def _clear_stale_delete_confirmation(visible_item_ids: set[int]) -> None:
    pending = _get_pending_delete_id()
    if pending is not None and pending not in visible_item_ids:
        _cancel_delete_confirmation(pending)


def _render_global_delete_confirmation(all_items: list[dict[str, Any]]) -> None:
    pending = _get_pending_delete_id()
    if pending is None:
        return

    item = next((row for row in all_items if int(row["id"]) == pending), None)
    if item is None:
        _cancel_delete_confirmation(pending)
        return

    title = item.get("title") or item.get("topic") or f"ID {pending}"
    channel = _display_channel_label(item.get("channel", ""))
    with st.container(border=True, key="shorts_delete_confirmation"):
        st.warning("삭제 확인 대기")
        st.caption(f"[{channel}] {title}")
        confirm_col, cancel_col = st.columns(2)
        with confirm_col:
            if st.button(
                "삭제 확인",
                key=f"global_del_confirm_{pending}",
                help="현재 삭제 대기 중인 항목을 영구 삭제합니다.",
                type="primary",
                **_stretch_button_kwargs(),
            ):
                _delete_item_with_confirmation(pending)
                st.rerun()
        with cancel_col:
            if st.button(
                "취소",
                key=f"global_del_cancel_{pending}",
                help="삭제 확인을 취소합니다.",
                **_stretch_button_kwargs(),
            ):
                _cancel_delete_confirmation(pending)
                _set_flash("info", "삭제 취소됨")
                st.rerun()


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
    return f"<span style='background:{color};color:white;padding:2px 8px;border-radius:10px;font-size:0.75rem'>{label}</span>"  # noqa: E501


def _fmt_dur(sec: float) -> str:
    if sec <= 0:
        return "-"
    m, s = divmod(int(sec), 60)
    return f"{m}:{s:02d}"


def _fmt_cost(usd: float) -> str:
    return f"${usd:.4f}" if usd > 0 else "-"


def _fmt_youtube_upload_metric(uploaded: int, awaiting: int) -> str:
    return f"{uploaded} / {awaiting} 대기"


def _stretch_button_kwargs() -> dict[str, str]:
    return {"width": "stretch"}


def _render_wrapped_code(value: object) -> None:
    st.code(str(value), language=None, wrap_lines=True)


def _youtube_badge(yt_status: str, yt_url: str = "") -> str:
    if yt_status == "uploaded" and yt_url:
        safe_url = _html.escape(yt_url, quote=True)
        _style = (
            "background:#ff0000;color:white;padding:2px 8px;border-radius:10px;font-size:0.7rem;text-decoration:none"  # noqa: E501
        )
        return f"<a href='{safe_url}' target='_blank' style='{_style}'>▶ YT</a>"
    if yt_status == "uploaded":
        return "<span style='background:#ff0000;color:white;padding:2px 8px;border-radius:10px;font-size:0.7rem'>▶ YT</span>"  # noqa: E501
    if yt_status == "failed":
        return "<span style='background:#6c757d;color:white;padding:2px 8px;border-radius:10px;font-size:0.7rem'>YT 실패</span>"  # noqa: E501
    return ""


def _ops_badge(status: str) -> str:
    colors = {
        "healthy": "#28a745",
        "warning": "#fd7e14",
        "critical": "#dc3545",
        "setup_required": "#6f42c1",
    }
    labels = {
        "healthy": "정상",
        "warning": "주의",
        "critical": "중요",
        "setup_required": "설정 필요",
    }
    color = colors.get(status, "#6c757d")
    label = labels.get(status, status)
    return (
        f"<span style='background:{color};color:white;padding:2px 8px;"
        f"border-radius:10px;font-size:0.75rem'>{label}</span>"
    )


def _format_issue_labels(issues: list[str]) -> list[str]:
    labels = []
    for issue in issues:
        label = issue.split(":", 1)[1] if ":" in issue else issue
        labels.append(_ISSUE_LABELS.get(label, label.replace("_", " ")))
    return labels


def _canonical_channel_label(channel: object) -> str:
    value = str(channel or "").strip()
    if not value:
        return ""
    return _CHANNEL_LABEL_ALIASES.get(value.lower(), value)


def _display_channel_label(channel: object) -> str:
    return _canonical_channel_label(channel) or "-"


def _item_matches_channel(item: dict[str, Any], channel: str) -> bool:
    return _canonical_channel_label(item.get("channel", "")) == channel


def _derive_display_ops_status(issues: list[str]) -> str:
    if any(issue.startswith("setup:") for issue in issues):
        return "setup_required"
    if any(issue.startswith("critical:") for issue in issues):
        return "critical"
    if issues:
        return "warning"
    return "healthy"


def _derive_display_next_action(issues: list[str], fallback: str) -> str:
    if not issues:
        return "렌더 실행 가능"
    if any(issue.startswith("setup:") for issue in issues):
        return "채널 설정 저장"
    if any("brand_asset_missing" in issue or "missing_brand_assets" in issue for issue in issues):
        return "브랜드 에셋 생성"
    if any("bgm_missing" in issue or "missing_bgm" in issue for issue in issues):
        return "BGM 추가 또는 스킵 확인"
    if any("failed_jobs" in issue for issue in issues):
        return "실패 건 확인"
    return fallback or "운영 상태 점검"


def _readiness_display_issue_allowed(
    issue: str,
    *,
    raw_channel: str,
    display_channel: str,
    has_display_channel_item: bool,
) -> bool:
    if raw_channel == display_channel:
        return True
    if has_display_channel_item and issue in {
        "setup:channel_settings_missing",
        "warning:brand_asset_missing",
    }:
        return False
    return True


def _channel_readiness_for_display(summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in summary:
        display_channel = _display_channel_label(item.get("channel", ""))
        grouped.setdefault(display_channel, []).append(item)

    merged_summary: list[dict[str, Any]] = []
    for display_channel, items in grouped.items():
        preferred = next(
            (item for item in items if str(item.get("channel", "")).strip() == display_channel),
            items[0],
        )
        has_display_channel_item = any(str(item.get("channel", "")).strip() == display_channel for item in items)
        merged = dict(preferred)
        merged["channel"] = display_channel
        for field in _CHANNEL_READINESS_COUNT_FIELDS:
            merged[field] = sum(int(item.get(field, 0) or 0) for item in items)

        issues: list[str] = []
        for item in items:
            raw_channel = str(item.get("channel", "")).strip()
            for issue in list(item.get("issues") or []):
                if not _readiness_display_issue_allowed(
                    str(issue),
                    raw_channel=raw_channel,
                    display_channel=display_channel,
                    has_display_channel_item=has_display_channel_item,
                ):
                    continue
                if issue not in issues:
                    issues.append(str(issue))

        merged["issues"] = issues
        merged["status"] = _derive_display_ops_status(issues)
        merged["next_action"] = _derive_display_next_action(
            issues,
            str(preferred.get("next_action") or ""),
        )
        for field in ("voice", "style_preset", "font_color", "image_style_prefix"):
            if not merged.get(field):
                merged[field] = next((item.get(field, "") for item in items if item.get(field)), "")
        merged_summary.append(merged)

    return merged_summary


def _build_generation_run_blockers(readiness_summary: list[dict[str, Any]]) -> dict[str, str]:
    blockers: dict[str, str] = {}
    for item in readiness_summary:
        channel = str(item.get("channel", "")).strip()
        if not channel or str(item.get("status", "")) not in _RUN_BLOCKING_OPS_STATUSES:
            continue

        next_action = str(item.get("next_action") or "채널 준비 상태를 먼저 해결하세요.").strip()
        issue_labels = _format_issue_labels(list(item.get("issues") or []))
        reason = f"{next_action} 후 실행 가능"
        if issue_labels:
            reason = f"{reason}: {', '.join(issue_labels)}"
        blockers[channel] = reason
    return blockers


def _generation_run_block_reason(
    item: dict[str, Any],
    readiness_blockers: dict[str, str],
    *,
    v2_available: bool,
) -> str:
    if item.get("status") not in ("pending", "failed"):
        return ""
    if not v2_available:
        return "shorts-maker-v2 엔진 경로를 확인하세요."
    channel = str(item.get("channel", "")).strip()
    if not channel:
        return "채널을 지정해야 실행할 수 있습니다."
    canonical_channel = _canonical_channel_label(channel)
    if canonical_channel != channel:
        return readiness_blockers.get(canonical_channel, "")
    return readiness_blockers.get(channel, "")


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


def _resolve_v2_python() -> str:
    """Return the interpreter that can run the shorts-maker-v2 package."""
    candidates = [
        _V2_DIR / ".venv" / "Scripts" / "python.exe",
        _V2_DIR / "venv" / "Scripts" / "python.exe",
        _V2_DIR / ".venv" / "bin" / "python",
        _V2_DIR / "venv" / "bin" / "python",
    ]
    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)
    return sys.executable


def _launch_v2(item_id: int, topic: str, channel: str = "") -> str | None:
    """v2 파이프라인을 백그라운드로 실행. job_id 반환."""
    if not _V2_DIR.exists():
        return None
    cmd = [
        _resolve_v2_python(),
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
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
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


def _youtube_upload_setup_block_reason(auth_status: dict[str, Any]) -> str:
    if not _YT_OK:
        return str(auth_status.get("reason") or _YT_ERR or "YouTube 업로더 사용 불가")
    if not auth_status.get("has_credentials_file"):
        return "credentials.json 설정 필요"
    return ""


def _youtube_item_upload_block_reason(
    item: dict[str, Any],
    auth_status: dict[str, Any],
    *,
    retry: bool,
) -> str:
    if item.get("status") != "success":
        return "영상 생성 완료 후 업로드 가능"
    if not item.get("video_path"):
        return "영상 파일 경로가 있어야 업로드 가능"

    youtube_status = str(item.get("youtube_status") or "")
    if retry:
        if youtube_status != "failed":
            return "업로드 실패 항목만 재시도 가능"
    elif youtube_status:
        return "업로드 전 항목만 신규 업로드 가능"

    setup_reason = _youtube_upload_setup_block_reason(auth_status)
    if setup_reason:
        return f"YouTube 업로드 설정 필요: {setup_reason}"
    return ""


def _notion_sync_block_reason() -> str:
    if not _NOTION_OK:
        return f"Notion 동기화 모듈 로드 실패: {_NOTION_ERR}" if _NOTION_ERR else "Notion 동기화 사용 불가"
    if not notion_is_configured():
        return "NOTION_API_KEY 및 NOTION_SHORTS_DATABASE_ID 설정 필요"
    return ""


def _card_external_action_reasons(item: dict[str, Any], auth_status: dict[str, Any]) -> list[str]:
    reasons: list[str] = []
    youtube_status = str(item.get("youtube_status") or "")
    if item.get("status") == "success" and item.get("video_path") and youtube_status in ("", "failed"):
        retry = youtube_status == "failed"
        youtube_reason = _youtube_item_upload_block_reason(item, auth_status, retry=retry)
        if youtube_reason:
            label = "YT 재시도 잠금" if retry else "YT 업로드 잠금"
            reasons.append(f"{label}: {youtube_reason}")

    notion_reason = _notion_sync_block_reason()
    if notion_reason:
        reasons.append(f"Notion 동기화 잠금: {notion_reason}")
    return reasons


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
    return build_shorts_upload_metadata(item)


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
    if not result.get("video_id"):
        raise RuntimeError(result.get("error", "업로드 실패: video_id 없음"))
    update_job(
        item["id"],
        youtube_video_id=result["video_id"],
        youtube_status="uploaded",
        youtube_url=result.get("youtube_url", ""),
        youtube_uploaded_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        youtube_error="",
    )
    return result


def _render_item_action_buttons(
    item: dict[str, Any],
    key_prefix: str,
    *,
    generation_run_blockers: dict[str, str],
    v2_available: bool,
    auth_status: dict[str, Any],
) -> None:
    """실행·업로드·재시도·Notion·삭제 버튼 영역을 렌더링한다."""
    btn_col1, btn_col2, btn_col3, btn_col4, btn_col5 = st.columns(5)
    with btn_col1:
        run_block_reason = _generation_run_block_reason(
            item,
            generation_run_blockers,
            v2_available=v2_available,
        )
        can_run = item["status"] in ("pending", "failed") and not run_block_reason
        if st.button(
            "실행",
            key=f"run_{key_prefix}_{item['id']}",
            disabled=not can_run,
            help=run_block_reason or "v2 파이프라인 실행",
            **_stretch_button_kwargs(),
        ):
            pid = _launch_v2(
                item["id"],
                item["topic"],
                _canonical_channel_label(item.get("channel", "")),
            )
            if pid:
                _set_flash("success", f"실행됨 (PID {pid})")
            else:
                _set_flash("error", "실행 실패")
            st.rerun()
        if run_block_reason:
            st.caption(f"생성 잠금: {run_block_reason}")
    with btn_col2:
        upload_block_reason = _youtube_item_upload_block_reason(item, auth_status, retry=False)
        can_upload = not upload_block_reason
        if st.button(
            "YT 업로드",
            key=f"yt_{key_prefix}_{item['id']}",
            disabled=not can_upload,
            help=upload_block_reason or "YouTube 업로드",
            **_stretch_button_kwargs(),
        ):
            try:
                result = _upload_single(item, retry=False)
                _set_flash("success", f"업로드 완료: {result['youtube_url']}")
            except Exception as exc:
                update_job(item["id"], youtube_status="failed", youtube_error=str(exc)[:300])
                _set_flash("error", f"업로드 실패: {exc}")
            st.rerun()
    with btn_col3:
        retry_block_reason = _youtube_item_upload_block_reason(item, auth_status, retry=True)
        can_retry = not retry_block_reason
        if st.button(
            "YT 재시도",
            key=f"ytretry_{key_prefix}_{item['id']}",
            disabled=not can_retry,
            help=retry_block_reason or "업로드 실패 건 재시도",
            **_stretch_button_kwargs(),
        ):
            try:
                result = _upload_single(item, retry=True)
                _set_flash("success", f"재업로드 완료: {result['youtube_url']}")
            except Exception as exc:
                update_job(item["id"], youtube_status="failed", youtube_error=str(exc)[:300])
                _set_flash("error", f"재업로드 실패: {exc}")
            st.rerun()
    with btn_col4:
        notion_synced = bool(item.get("notion_page_id", ""))
        notion_btn_label = "📋 Notion↑" if not notion_synced else "📋 Notion↻"
        item_notion_block_reason = _notion_sync_block_reason()
        if st.button(
            notion_btn_label,
            key=f"notion_{key_prefix}_{item['id']}",
            disabled=bool(item_notion_block_reason),
            help=item_notion_block_reason or ("Notion에 동기화" if not notion_synced else "Notion 업데이트"),
            **_stretch_button_kwargs(),
        ):
            result = notion_sync_item(item["id"])
            action = result["action"]
            if action in ("created", "updated"):
                _set_flash("success", f"Notion {action}: {result.get('page_id', '')[:8]}")
            else:
                _set_flash("error", f"Notion 오류: {result.get('error', '')}")
            st.rerun()
    with btn_col5:
        if _get_pending_delete_id() == item["id"]:
            st.caption("삭제 확인 필요")
            if st.button(
                "삭제 확인",
                key=f"del_confirm_{key_prefix}_{item['id']}",
                help="이 항목을 영구 삭제합니다",
                type="primary",
                **_stretch_button_kwargs(),
            ):
                _delete_item_with_confirmation(item["id"])
                st.rerun()
            if st.button(
                "취소",
                key=f"del_cancel_{key_prefix}_{item['id']}",
                help="삭제 확인을 취소합니다",
                **_stretch_button_kwargs(),
            ):
                _cancel_delete_confirmation(item["id"])
                _set_flash("info", "삭제 취소됨")
                st.rerun()
        elif st.button(
            "삭제",
            key=f"del_{key_prefix}_{item['id']}",
            help="삭제 확인을 엽니다",
            **_stretch_button_kwargs(),
        ):
            _request_delete_confirmation(item["id"])
            st.rerun()

    for reason in _card_external_action_reasons(item, auth_status):
        st.caption(reason)


def _voice_index(settings: dict[str, Any] | None) -> int:
    voice = (settings or {}).get("voice", "alloy")
    return VOICE_OPTIONS.index(voice) if voice in VOICE_OPTIONS else 0


def _style_index(settings: dict[str, Any] | None) -> int:
    style = (settings or {}).get("style_preset", "default")
    return STYLE_OPTIONS.index(style) if style in STYLE_OPTIONS else 0


# ---------------------------------------------------------------------------
# UI 시작
# ---------------------------------------------------------------------------
def _render_channel_readiness(channels: list[str], summary: list[dict[str, Any]] | None = None) -> None:
    st.subheader("채널 준비 상태")
    summary = summary if summary is not None else get_channel_readiness_summary(channels=channels)
    if not summary:
        st.info("표시할 채널 상태가 없습니다.")
        return

    display_summary = sorted(
        _channel_readiness_for_display(summary),
        key=lambda item: (
            _OPS_STATUS_PRIORITY.get(str(item.get("status")), 99),
            -int(item.get("failed_count", 0)),
            str(item.get("channel", "")),
        ),
    )

    for item in display_summary:
        with st.container(border=True):
            top_col, meta_col = st.columns([2, 3])
            with top_col:
                st.markdown(
                    f"**{item['channel']}** {_ops_badge(item['status'])}",
                    unsafe_allow_html=True,
                )
                st.caption(f"음성: `{item['voice'] or '-'}` | 스타일: `{item['style_preset'] or '-'}`")
            with meta_col:
                st.caption(
                    "BGM: "
                    f"{'준비됨' if item['bgm_ready'] else '부족'} | "
                    "브랜드 에셋: "
                    f"{'준비됨' if item['brand_assets_ready'] else '부족'} | "
                    f"실패 {item['failed_count']} / 실행중 {item['running_count']} / 대기 {item['pending_count']}"
                )
                st.caption(f"다음 액션: {item['next_action']}")
            if item["issues"]:
                issue_labels = _format_issue_labels(item["issues"])
                st.caption("이슈: " + ", ".join(issue_labels))


def _render_failure_triage(limit: int = 6) -> None:
    st.subheader("실패 triage")
    failures = get_recent_failure_items(limit=limit)
    if not failures:
        st.info("최근 실패 건이 없습니다.")
        return

    for item in failures:
        with st.container(border=True):
            display_channel = _display_channel_label(item.get("channel", ""))
            st.markdown(
                f"**{display_channel}** {_status_badge('failed')} "
                f"&nbsp; **{item.get('title') or item.get('topic') or '-'}**",
                unsafe_allow_html=True,
            )
            st.caption(
                f"실패 시각: {item.get('updated_at', '-')[:16]} | "
                f"재시도 권장: {'예' if item.get('retry_recommended') else '아니오'}"
            )
            st.caption(f"실패 원인: {item.get('failure_reason', '-')}")
            if item.get("issues"):
                issue_labels = _format_issue_labels(item["issues"])
                st.caption("사전 점검: " + ", ".join(issue_labels))
            st.caption(f"다음 액션: {item.get('next_action', '-')}")


def _render_manifest_sync_panel() -> None:
    st.subheader("Manifest sync 점검")
    diff = get_manifest_sync_diffs(limit=5)
    summary = diff["summary"]
    metric_cols = st.columns(4)
    metric_cols[0].metric("DB 누락", summary["missing_in_db_count"])
    metric_cols[1].metric("동기화 필요", summary["pending_sync_count"])
    metric_cols[2].metric("영상 파일 누락", summary["missing_output_file_count"])
    metric_cols[3].metric("manifest 누락", summary["missing_manifest_count"])

    if not any(summary.values()):
        st.success("현재 확인된 manifest 불일치가 없습니다.")
        return

    if diff["pending_sync"]:
        st.caption("동기화 필요")
        for item in diff["pending_sync"]:
            st.caption(
                f"- [{_display_channel_label(item['channel'])}] {item['topic']} / {', '.join(item['mismatches'])}"
            )
    if diff["missing_in_db"]:
        st.caption("DB 누락")
        for item in diff["missing_in_db"]:
            st.caption(f"- {item['job_id']} / {item['title'] or '-'}")
    if diff["missing_output_file"]:
        st.caption("영상 파일 누락")
        for item in diff["missing_output_file"]:
            st.caption(f"- [{_display_channel_label(item['channel'])}] {item['topic']}")
    if diff["missing_manifest"]:
        st.caption("manifest 누락")
        for item in diff["missing_manifest"]:
            st.caption(f"- [{_display_channel_label(item['channel'])}] {item['topic']} / {item['status']}")


def _render_manual_review_queue(
    limit: int = 6,
    *,
    generation_run_blockers: dict[str, str] | None = None,
    v2_available: bool = False,
    auth_status: dict[str, Any] | None = None,
) -> None:
    st.subheader("수동 검수 큐")
    review_items = get_review_queue_items(limit=limit)
    if not review_items:
        st.info("검수할 완료 결과가 없습니다.")
        return

    for item in review_items:
        with st.container(border=True):
            display_channel = _display_channel_label(item.get("channel", ""))
            st.markdown(
                f"**{display_channel}** {_ops_badge(item['review_status'])} "
                f"&nbsp; **{item.get('title') or item.get('topic') or '-'}**",
                unsafe_allow_html=True,
            )
            if generation_run_blockers is not None and auth_status is not None:
                _render_item_action_buttons(
                    item,
                    key_prefix=f"review_{item['id']}",
                    generation_run_blockers=generation_run_blockers,
                    v2_available=v2_available,
                    auth_status=auth_status,
                )
            st.caption(
                f"생성: {item.get('updated_at', '-')[:16]} | "
                f"영상: {'있음' if item.get('video_exists') else '없음'} | "
                f"썸네일: {'있음' if item.get('thumbnail_exists') else '없음'}"
            )
            if item.get("notes"):
                st.caption(f"메모: {item['notes']}")
            if item.get("youtube_error"):
                st.caption(f"업로드 오류: {item['youtube_error']}")
            st.caption(f"다음 액션: {item.get('next_action', '-')}")


def _render_thumbnail_preview(thumbnail_path: str) -> None:
    if not thumbnail_path:
        return
    if not Path(thumbnail_path).exists():
        return

    with st.expander("썸네일 미리보기"):
        try:
            st.image(thumbnail_path, width=320)
        except Exception:
            st.warning("썸네일 미리보기를 표시할 수 없습니다.")
            st.caption(f"파일 경로: {thumbnail_path}")


all_items = get_all()

st.title("🎬 쇼츠 운영")
st.caption("생성 · 검수 · 업로드 관리")
_render_flash()
_clear_stale_delete_confirmation({int(item["id"]) for item in all_items})
_render_global_delete_confirmation(all_items)
_render_operator_shortcuts()
channel_readiness_summary = get_channel_readiness_summary(channels=CHANNELS)
generation_run_blockers = _build_generation_run_blockers(channel_readiness_summary)
_render_channel_readiness(CHANNELS, summary=channel_readiness_summary)

auth_status = _default_auth_status()
v2_ok = _V2_DIR.exists()

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
            **_stretch_button_kwargs(),
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

sync_col, notion_col, sync_spacer = st.columns([1, 1, 4])
with sync_col:
    if st.button("↻ 결과 동기화", help="v2 output 폴더에서 완료된 작업을 가져옵니다", **_stretch_button_kwargs()):
        _scan_manifests()
        _set_flash("success", "manifest 동기화 완료")
        st.rerun()
with notion_col:
    notion_block_reason = _notion_sync_block_reason()
    notion_ready = not notion_block_reason
    if st.button(
        "📋 전체 Notion 동기화",
        help="모든 항목을 Notion DB에 동기화합니다" if notion_ready else notion_block_reason,
        disabled=not notion_ready,
        **_stretch_button_kwargs(),
    ):
        results = notion_sync_all()
        created = sum(1 for r in results if r["action"] == "created")
        updated = sum(1 for r in results if r["action"] == "updated")
        errors = sum(1 for r in results if r["action"] == "error")
        level = "success" if errors == 0 else "warning"
        _set_flash(level, f"Notion 동기화 완료: 생성 {created} / 업데이트 {updated} / 오류 {errors}")
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
c6.metric("YT 업로드", _fmt_youtube_upload_metric(yt_stats["uploaded"], yt_stats["awaiting"]))

st.divider()

# ---------------------------------------------------------------------------
# 레이아웃: 좌측 폼 | 우측 채널 탭 콘텐츠 목록
# ---------------------------------------------------------------------------
triage_col, manifest_col, review_col = st.columns(3)
with triage_col:
    _render_failure_triage()
with manifest_col:
    _render_manifest_sync_panel()
with review_col:
    _section_anchor("shorts-review-queue")
    _render_manual_review_queue(
        generation_run_blockers=generation_run_blockers,
        v2_available=v2_ok,
        auth_status=auth_status,
    )

left, right = st.columns([1, 3])

with left:
    _section_anchor("shorts-add-topic")
    st.subheader("새 콘텐츠 추가")
    with st.form("add_topic_form", clear_on_submit=True):
        channel_input = st.selectbox("채널", options=CHANNELS)
        topic_input = st.text_area("주제", placeholder="예: 블랙홀의 미스터리 5가지", height=80)
        notes_input = st.text_input("메모 (선택)", placeholder="태그, 참고사항 등")
        submitted = st.form_submit_button("큐에 추가", type="primary", **_stretch_button_kwargs())
        if submitted:
            if topic_input.strip():
                add_topic(topic_input.strip(), notes_input.strip(), channel=channel_input)
                _set_flash("success", f"[{channel_input}] 주제 추가 완료")
                st.rerun()
            else:
                st.warning("주제를 입력해주세요.")

    st.divider()

    _section_anchor("shorts-channel-settings")
    st.subheader("채널 설정")
    settings_channel = st.selectbox("설정 채널", options=CHANNELS, key="settings_channel")
    channel_settings = get_channel_settings(settings_channel) or {}
    with st.form(f"channel_settings_form_{settings_channel}"):
        voice = st.selectbox("음성", options=VOICE_OPTIONS, index=_voice_index(channel_settings))
        style_preset = st.selectbox("스타일 프리셋", options=STYLE_OPTIONS, index=_style_index(channel_settings))
        font_color = st.text_input("자막 색상", value=channel_settings.get("font_color", "#FFD700"))
        image_prefix = st.text_area(
            "이미지 스타일 프롬프트",
            value=channel_settings.get("image_style_prefix", ""),
            height=80,
            placeholder="예: cinematic documentary lighting, high contrast",
        )
        settings_submit = st.form_submit_button("채널 설정 저장", **_stretch_button_kwargs())
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
        ch_items_for_status = [item for item in all_items if _item_matches_channel(item, ch)]
        total = len(ch_items_for_status)
        success = len([item for item in ch_items_for_status if item.get("status") == "success"])
        pending = len([item for item in ch_items_for_status if item.get("status") == "pending"])
        if total > 0:
            st.caption(f"**{ch}**: 전체 {total} | 완료 {success} | 대기 {pending}")
        else:
            st.caption(f"**{ch}**: 주제 없음")

    st.divider()
    st.caption("**파이프라인 설정 경로**")
    _render_wrapped_code(_V2_DIR / "config.yaml")
    if v2_ok:
        st.success("shorts-maker-v2 엔진 감지됨")
        st.caption("**실행 Python**")
        _render_wrapped_code(_resolve_v2_python())
    else:
        st.error("shorts-maker-v2 디렉토리 없음")

with right:
    _section_anchor("shorts-content-list")
    st.subheader("콘텐츠 목록")
    tab_labels = [f"전체 ({len(all_items)})"] + CHANNELS
    tabs = st.tabs(tab_labels)

    def _render_item_header(item: dict[str, Any]) -> None:
        """항목 제목·배지·메타 정보 영역을 렌더링한다."""
        status_html = _status_badge(item["status"])
        yt_html = _youtube_badge(item.get("youtube_status", ""), item.get("youtube_url", ""))
        title_display = _html.escape(item.get("title") or item["topic"])
        ch_tag = ""
        if item.get("channel"):
            safe_ch = _html.escape(_display_channel_label(item["channel"]))
            ch_tag = (
                f"<span style='background:#0d6efd;color:white;padding:2px 6px;"
                f"border-radius:8px;font-size:0.7rem'>{safe_ch}</span> "
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

    def _render_items(items_to_show: list[dict[str, Any]], key_prefix: str = "all") -> None:
        if not items_to_show:
            st.info("항목이 없습니다.")
            return
        for item in items_to_show:
            with st.container():
                _render_item_header(item)
                _render_item_action_buttons(
                    item,
                    key_prefix,
                    generation_run_blockers=generation_run_blockers,
                    v2_available=v2_ok,
                    auth_status=auth_status,
                )

                thumb = item.get("thumbnail_path", "")
                _render_thumbnail_preview(thumb)

                video = item.get("video_path", "")
                if video and Path(video).exists():
                    with st.expander("영상 경로"):
                        _render_wrapped_code(video)

                st.divider()

    with tabs[0]:
        _render_items(all_items, key_prefix="all")

    for i, ch in enumerate(CHANNELS):
        with tabs[i + 1]:
            ch_items = [item for item in all_items if _item_matches_channel(item, ch)]
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
