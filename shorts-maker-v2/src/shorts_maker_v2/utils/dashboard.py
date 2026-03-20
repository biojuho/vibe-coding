import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


def generate_dashboard(logs_dir: str | Path, output_file: str | Path = "dashboard.html") -> Path:
    """logs 디렉토리의 모든 .jsonl 파일을 파싱하여 HTML 대시보드를 생성합니다."""
    logs_dir = Path(logs_dir).resolve()
    out_path = Path(output_file).resolve()

    # costs.jsonl + 개별 job .jsonl 모두 스캔
    jsonl_files = sorted(logs_dir.glob("*.jsonl"))
    if not jsonl_files:
        html = "<html><body><h1>데이터가 없습니다.</h1><p>.jsonl 파일을 찾을 수 없습니다.</p></body></html>"
        out_path.write_text(html, encoding="utf-8")
        return out_path

    total_jobs = 0
    success_jobs = 0
    failed_jobs = 0
    total_cost = 0.0
    seen_job_ids: set[str] = set()

    daily_stats = defaultdict(lambda: {"total": 0, "success": 0, "failed": 0, "cost": 0.0})

    for jsonl_file in jsonl_files:
        job_status = None
        job_cost = 0.0
        job_ts = ""
        job_id = jsonl_file.stem  # e.g. "20260304-100550-8bfd2bc3"

        try:
            with jsonl_file.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except Exception:
                        continue

                    # costs.jsonl 형태: {"timestamp":..., "status":..., "cost_usd":...}
                    if "cost_usd" in record and "status" in record:
                        rec_id = record.get("job_id", jsonl_file.stem)
                        if rec_id not in seen_job_ids:
                            seen_job_ids.add(rec_id)
                            ts = record.get("timestamp", "")
                            status = record.get("status", "success")
                            cost = record.get("cost_usd", 0.0)
                            try:
                                dt = datetime.fromisoformat(ts)
                                date_str = dt.strftime("%Y-%m-%d")
                            except Exception:
                                date_str = "Unknown"
                            total_jobs += 1
                            total_cost += cost
                            daily_stats[date_str]["total"] += 1
                            daily_stats[date_str]["cost"] += cost
                            if status == "success":
                                success_jobs += 1
                                daily_stats[date_str]["success"] += 1
                            else:
                                failed_jobs += 1
                                daily_stats[date_str]["failed"] += 1
                        continue

                    # 개별 job .jsonl: job_finished / job_error 이벤트에서 추출
                    ev = record.get("event", "")
                    if not job_ts:
                        job_ts = record.get("timestamp", "")
                    if ev == "job_finished":
                        job_status = "success"
                    elif ev == "pipeline_complete":
                        job_status = record.get("status", "success")
                        job_cost = record.get("estimated_cost_usd", job_cost)
                    elif ev in ("pipeline_error", "pipeline_failed", "job_error"):
                        job_status = "failed"
                    elif ev == "render_done":
                        job_cost = record.get("estimated_cost_usd", job_cost)
        except Exception:
            continue

        # 개별 job 파일에서 추출된 데이터 집계 (costs.jsonl 엔트리가 아닌 경우)
        if job_id not in seen_job_ids and job_status is not None:
            seen_job_ids.add(job_id)
            try:
                dt = datetime.fromisoformat(job_ts)
                date_str = dt.strftime("%Y-%m-%d")
            except Exception:
                date_str = "Unknown"
            total_jobs += 1
            total_cost += job_cost
            daily_stats[date_str]["total"] += 1
            daily_stats[date_str]["cost"] += job_cost
            if job_status == "success":
                success_jobs += 1
                daily_stats[date_str]["success"] += 1
            else:
                failed_jobs += 1
                daily_stats[date_str]["failed"] += 1

    fail_rate = (failed_jobs / total_jobs * 100) if total_jobs > 0 else 0

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <title>Shorts Maker V2 Dashboard</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 2rem; background: #f8f9fa; color: #333; }}
        h1 {{ border-bottom: 2px solid #ddd; padding-bottom: 0.5rem; }}
        .summary {{ display: flex; gap: 1rem; margin-bottom: 2rem; }}
        .card {{ background: white; padding: 1.5rem; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); flex: 1; text-align: center; }}
        .card h2 {{ font-size: 1rem; color: #666; margin: 0 0 0.5rem 0; }}
        .card .value {{ font-size: 2rem; font-weight: bold; margin: 0; }}
        .fail-rate {{ color: {"red" if fail_rate > 10 else "green"}; }}
        table {{ width: 100%; border-collapse: collapse; background: white; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 1rem; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #f1f3f5; font-weight: bold; }}
        tr:last-child td {{ border-bottom: none; }}
    </style>
</head>
<body>
    <h1>Shorts Maker V2 통계 대시보드</h1>
    <p>업데이트: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")} (UTC)</p>

    <div class="summary">
        <div class="card">
            <h2>총 시도 (건)</h2>
            <p class="value">{total_jobs}</p>
        </div>
        <div class="card">
            <h2>성공 (건)</h2>
            <p class="value" style="color: green;">{success_jobs}</p>
        </div>
        <div class="card">
            <h2>실패 (건)</h2>
            <p class="value" style="color: red;">{failed_jobs}</p>
        </div>
        <div class="card">
            <h2>전체 실패율 (%)</h2>
            <p class="value fail-rate">{fail_rate:.1f}%</p>
        </div>
        <div class="card">
            <h2>총 누적 비용 (USD)</h2>
            <p class="value">${total_cost:.4f}</p>
        </div>
    </div>

    <h2>일별 통계</h2>
    <table>
        <thead>
            <tr>
                <th>날짜</th>
                <th>총 시도</th>
                <th>성공</th>
                <th>실패</th>
                <th>비용 (USD)</th>
                <th>실패율 (%)</th>
            </tr>
        </thead>
        <tbody>
"""
    for date_str, stats in sorted(daily_stats.items(), reverse=True):
        f_rate = (stats["failed"] / stats["total"] * 100) if stats["total"] > 0 else 0
        html += f"""
            <tr>
                <td>{date_str}</td>
                <td>{stats["total"]}</td>
                <td style="color: green;">{stats["success"]}</td>
                <td style="color: red;">{stats["failed"]}</td>
                <td>${stats["cost"]:.4f}</td>
                <td style="color: {"red" if f_rate > 10 else "inherit"};">{f_rate:.1f}%</td>
            </tr>
"""
    html += """
        </tbody>
    </table>
</body>
</html>
"""
    out_path.write_text(html, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        generate_dashboard(sys.argv[1])
    else:
        print("Usage: python dashboard.py /path/to/logs_dir")
