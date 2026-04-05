from __future__ import annotations

import importlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from shorts_maker_v2.config import AppConfig, resolve_runtime_paths
from shorts_maker_v2.growth.feedback_loop import GrowthLoopEngine
from shorts_maker_v2.growth.models import GrowthLoopReport, VariantField, VideoPerformanceSnapshot
from shorts_maker_v2.pipeline.series_engine import SeriesEngine


@dataclass(frozen=True)
class GrowthSyncResult:
    channel: str
    snapshot_count: int
    report_path: Path
    report: GrowthLoopReport
    refresh_summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel": self.channel,
            "snapshot_count": self.snapshot_count,
            "report_path": str(self.report_path),
            "refresh_summary": self.refresh_summary,
            "report": self.report.to_dict(),
        }


def _find_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "workspace" / "execution" / "content_db.py").exists():
            return parent
    raise FileNotFoundError("Could not locate repo root for workspace execution imports.")


def _ensure_repo_root_on_path() -> Path:
    root = _find_repo_root()
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return root


def _load_content_db_module():
    _ensure_repo_root_on_path()
    return importlib.import_module("workspace.execution.content_db")


def _load_youtube_collector_module():
    _ensure_repo_root_on_path()
    return importlib.import_module("workspace.execution.youtube_analytics_collector")


def _parse_datetime(raw: Any) -> datetime | None:
    text = str(raw or "").strip()
    if not text:
        return None

    for candidate in (text, text.replace("Z", "+00:00")):
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue

    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _load_success_manifests(output_dir: Path) -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    if not output_dir.exists():
        return manifests

    for path in sorted(output_dir.glob("*_manifest.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue

        job_id = str(payload.get("job_id", "")).strip()
        if not job_id or payload.get("status") != "success":
            continue
        manifests[job_id] = payload
    return manifests


def _coerce_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _coerce_float(value: Any) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _normalize_variant_metadata(payload: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for key, value in payload.items():
        text = str(value).strip()
        if text:
            result[str(key)] = text
    return result


def _build_snapshot(
    *,
    row: dict[str, Any],
    manifest: dict[str, Any],
) -> VideoPerformanceSnapshot:
    avg_watch_sec = _coerce_float(row.get("yt_avg_watch_sec"))
    duration_sec = _coerce_float(row.get("duration_sec"))
    avg_watch_pct = 0.0
    if avg_watch_sec > 0 and duration_sec > 0:
        avg_watch_pct = min((avg_watch_sec / duration_sec) * 100.0, 100.0)

    published_at = _parse_datetime(row.get("youtube_uploaded_at")) or _parse_datetime(manifest.get("created_at"))
    metadata = _normalize_variant_metadata(manifest.get("ab_variant", {}))

    return VideoPerformanceSnapshot(
        video_id=str(row.get("youtube_video_id") or row.get("job_id") or manifest.get("job_id") or "").strip(),
        channel=str(row.get("channel") or "").strip(),
        topic=str(manifest.get("topic") or row.get("topic") or row.get("title") or "").strip(),
        views=_coerce_int(row.get("yt_views")),
        likes=_coerce_int(row.get("yt_likes")),
        comments=_coerce_int(row.get("yt_comments")),
        average_view_duration_sec=round(avg_watch_sec, 2),
        average_view_percentage=round(avg_watch_pct, 2),
        impressions_ctr=_coerce_float(row.get("yt_ctr")),
        published_at=published_at,
        metadata=metadata,
    )


def _resolve_scope_channel(channel: str, snapshots: list[VideoPerformanceSnapshot]) -> str:
    if channel:
        return channel
    unique_channels = sorted({snapshot.channel for snapshot in snapshots if snapshot.channel})
    if len(unique_channels) == 1:
        return unique_channels[0]
    return "all_channels"


def _build_snapshots(
    *,
    manifests: dict[str, dict[str, Any]],
    rows: list[dict[str, Any]],
    since: datetime | None,
    min_views: int,
) -> list[VideoPerformanceSnapshot]:
    snapshots: list[VideoPerformanceSnapshot] = []

    for row in rows:
        if row.get("youtube_status") != "uploaded":
            continue

        job_id = str(row.get("job_id") or "").strip()
        if not job_id:
            continue

        manifest = manifests.get(job_id)
        if manifest is None:
            continue

        views = _coerce_int(row.get("yt_views"))
        if views < min_views:
            continue

        metric_time = (
            _parse_datetime(row.get("yt_stats_updated_at"))
            or _parse_datetime(row.get("youtube_uploaded_at"))
            or _parse_datetime(row.get("updated_at"))
        )
        if since is not None and metric_time is not None and metric_time < since:
            continue

        snapshots.append(_build_snapshot(row=row, manifest=manifest))

    snapshots.sort(key=lambda item: (item.views, item.likes, item.comments), reverse=True)
    return snapshots


def _default_report_path(base_dir: Path, channel: str) -> Path:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    scope = channel or "all_channels"
    return (base_dir / ".tmp" / "growth_reports" / f"{scope}_{stamp}.json").resolve()


def sync_growth_report(
    *,
    config: AppConfig,
    base_dir: Path,
    channel: str = "",
    since_days: int = 30,
    min_views: int = 0,
    variant_field: VariantField = "caption_combo",
    refresh_metrics: bool = True,
    report_path: Path | None = None,
) -> GrowthSyncResult:
    runtime_paths = resolve_runtime_paths(config, base_dir)
    refresh_summary: dict[str, Any] = {"status": "skipped", "updated": 0, "skipped": 0, "errors": []}

    if refresh_metrics:
        try:
            collector = _load_youtube_collector_module()
            refresh_summary = dict(collector.collect_and_update(channel=channel or None))
            refresh_summary["status"] = "ok"
        except Exception as exc:
            refresh_summary = {
                "status": "failed",
                "updated": 0,
                "skipped": 0,
                "errors": [str(exc)],
            }

    content_db = _load_content_db_module()
    content_db.init_db()
    manifests = _load_success_manifests(runtime_paths.output_dir)
    rows = content_db.get_all(channel=channel or None)

    since = None if since_days <= 0 else datetime.now() - timedelta(days=since_days)
    snapshots = _build_snapshots(
        manifests=manifests,
        rows=rows,
        since=since,
        min_views=max(0, min_views),
    )

    report_channel = _resolve_scope_channel(channel, snapshots)
    growth_engine = GrowthLoopEngine(
        output_dir=runtime_paths.output_dir,
        series_engine=SeriesEngine(output_dir=runtime_paths.output_dir),
    )
    report = growth_engine.generate_report(
        channel=report_channel,
        snapshots=snapshots,
        variant_field=variant_field,
    )

    final_report_path = (report_path or _default_report_path(base_dir, report_channel)).resolve()
    final_report_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now().isoformat(),
        "channel": report_channel,
        "channel_filter": channel,
        "since_days": since_days,
        "min_views": max(0, min_views),
        "variant_field": variant_field,
        "snapshot_count": len(snapshots),
        "refresh_summary": refresh_summary,
        "snapshots": [snapshot.to_dict() for snapshot in snapshots],
        "report": report.to_dict(),
    }
    final_report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return GrowthSyncResult(
        channel=report_channel,
        snapshot_count=len(snapshots),
        report_path=final_report_path,
        report=report,
        refresh_summary=refresh_summary,
    )
