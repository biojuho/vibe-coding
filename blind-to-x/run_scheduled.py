"""Blind-to-X scheduled runner.

Windows Task Scheduler에서 직접 실행되는 Python 스크립트.
bat 파일의 한국어 경로 chcp/cd 이슈를 우회합니다.
"""
import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path

# 절대 경로로 작업 디렉토리 설정
WORK_DIR = Path(r"C:\Users\박주호\Desktop\Vibe coding\blind-to-x")
PYTHON = sys.executable
LOG_DIR = WORK_DIR / ".tmp" / "logs"

def main():
    os.chdir(WORK_DIR)
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    
    now = datetime.now()
    log_file = LOG_DIR / f"scheduled_{now.strftime('%Y%m%d_%H%M')}.log"
    
    with open(log_file, "w", encoding="utf-8") as log:
        def write_log(msg):
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log.write(f"[{ts}] {msg}\n")
            log.flush()
        
        write_log("=" * 50)
        write_log(f"Starting Blind-to-X Scheduled Tasks")
        write_log(f"Working Directory: {WORK_DIR}")
        write_log(f"Python: {PYTHON}")
        write_log(f"CWD: {os.getcwd()}")
        write_log("=" * 50)
        
        fail_count = 0
        
        tasks = [
            ("Trending Scrape", [PYTHON, "main.py", "--trending"]),
            ("Popular Scrape", [PYTHON, "main.py", "--popular"]),
        ]
        
        for task_name, cmd in tasks:
            write_log(f"Running {task_name}...")
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=600,  # 10 minute timeout per task
                    cwd=str(WORK_DIR),
                )
                log.write(result.stdout)
                if result.stderr:
                    log.write(result.stderr)
                log.flush()
                
                if result.returncode != 0:
                    write_log(f"ERROR: {task_name} failed with exit code {result.returncode}")
                    fail_count += 1
                else:
                    write_log(f"OK: {task_name} completed successfully")
            except subprocess.TimeoutExpired:
                write_log(f"ERROR: {task_name} timed out (600s)")
                fail_count += 1
            except Exception as e:
                write_log(f"ERROR: {task_name} exception: {e}")
                fail_count += 1
        
        write_log("=" * 50)
        write_log(f"Pipeline finished. Failures: {fail_count}")
        write_log("=" * 50)
        
        # ── 파이프라인 후속 작업 (실패해도 메인 exit code에 영향 없음) ──
        VIBE_ROOT = WORK_DIR.parent  # Vibe coding/
        
        # 1) Watchdog 실행 — 시스템 상태 점검 + 이상 시 Telegram 알림
        write_log("Running Watchdog health check...")
        try:
            wd_result = subprocess.run(
                [PYTHON, str(VIBE_ROOT / "execution" / "pipeline_watchdog.py")],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=60,
                cwd=str(VIBE_ROOT),
            )
            log.write(wd_result.stdout)
            if wd_result.stderr:
                log.write(wd_result.stderr)
            log.flush()
            write_log(f"Watchdog exit code: {wd_result.returncode}")
        except Exception as e:
            write_log(f"Watchdog error (non-fatal): {e}")
        
        # 2) OneDrive 백업 실행
        write_log("Running OneDrive backup...")
        try:
            bk_result = subprocess.run(
                [PYTHON, str(VIBE_ROOT / "execution" / "backup_to_onedrive.py")],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=300,  # 5 minutes max for backup
                cwd=str(VIBE_ROOT),
            )
            log.write(bk_result.stdout)
            if bk_result.stderr:
                log.write(bk_result.stderr)
            log.flush()
            write_log(f"Backup exit code: {bk_result.returncode}")
        except Exception as e:
            write_log(f"Backup error (non-fatal): {e}")
        
        write_log("=" * 50)
        write_log("All tasks complete.")
        write_log("=" * 50)
    
    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()
