"""
프로세스 생명주기 관리자 - Joolife Hub용.
런칭된 서브프로세스를 JSON 파일로 영속 추적.

Usage (as library):
    from execution.process_manager import ProcessManager
    pm = ProcessManager()
    pm.register(pid=1234, name="Agent", command="streamlit run app.py", cwd="...")
    alive = pm.get_alive_processes()
    pm.kill_process(pid=1234)
    pm.kill_all()
"""

import json
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import psutil

PROCESS_FILE = Path(__file__).resolve().parent.parent / ".tmp" / "hub_processes.json"


@dataclass
class TrackedProcess:
    pid: int
    name: str
    command: str
    cwd: str
    launched_at: str
    port: Optional[int] = None


class ProcessManager:
    def __init__(self, process_file: Path = PROCESS_FILE):
        self.process_file = process_file
        self.process_file.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> List[dict]:
        if not self.process_file.exists():
            return []
        try:
            return json.loads(self.process_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return []

    def _save(self, processes: List[dict]) -> None:
        self.process_file.write_text(json.dumps(processes, indent=2, ensure_ascii=False), encoding="utf-8")

    def _is_alive(self, pid: int) -> bool:
        try:
            proc = psutil.Process(pid)
            return proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def register(
        self,
        pid: int,
        name: str,
        command: str,
        cwd: str,
        port: Optional[int] = None,
    ) -> None:
        processes = self._load()
        entry = TrackedProcess(
            pid=pid,
            name=name,
            command=command,
            cwd=cwd,
            launched_at=datetime.now().isoformat(timespec="seconds"),
            port=port,
        )
        # 같은 이름의 죽은 프로세스 제거
        processes = [p for p in processes if not (p.get("name") == name and not self._is_alive(p["pid"]))]
        processes.append(asdict(entry))
        self._save(processes)

    def get_alive_processes(self) -> List[TrackedProcess]:
        processes = self._load()
        alive = []
        for p in processes:
            if self._is_alive(p["pid"]):
                alive.append(TrackedProcess(**p))
        # 죽은 엔트리 정리
        self._save([asdict(a) for a in alive])
        return alive

    def kill_process(self, pid: int) -> bool:
        try:
            proc = psutil.Process(pid)
            children = proc.children(recursive=True)
            for child in children:
                child.terminate()
            proc.terminate()
            gone, still_alive = psutil.wait_procs([proc] + children, timeout=5)
            for p in still_alive:
                p.kill()
            return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return False

    def kill_all(self) -> int:
        processes = self.get_alive_processes()
        killed = 0
        for p in processes:
            if self.kill_process(p.pid):
                killed += 1
        self._save([])
        return killed
