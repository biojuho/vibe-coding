from __future__ import annotations

from unittest.mock import MagicMock, patch


from execution.process_manager import ProcessManager, TrackedProcess


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pm(tmp_path):
    return ProcessManager(process_file=tmp_path / "processes.json")


def _sample_entry(pid=1000, name="TestApp", port=None):
    return {
        "pid": pid,
        "name": name,
        "command": "python app.py",
        "cwd": "/tmp",
        "launched_at": "2026-02-27T10:00:00",
        "port": port,
    }


# ---------------------------------------------------------------------------
# _load / _save
# ---------------------------------------------------------------------------

def test_load_returns_empty_when_file_missing(tmp_path):
    pm = _make_pm(tmp_path)
    assert pm._load() == []


def test_save_and_load_roundtrip(tmp_path):
    pm = _make_pm(tmp_path)
    entry = _sample_entry()
    pm._save([entry])
    loaded = pm._load()
    assert len(loaded) == 1
    assert loaded[0]["pid"] == 1000
    assert loaded[0]["name"] == "TestApp"


def test_load_handles_corrupt_json(tmp_path):
    pm = _make_pm(tmp_path)
    (tmp_path / "processes.json").write_text("{ not valid json }", encoding="utf-8")
    assert pm._load() == []


# ---------------------------------------------------------------------------
# _is_alive
# ---------------------------------------------------------------------------

def test_is_alive_true_for_running_process(tmp_path):
    pm = _make_pm(tmp_path)
    mock_proc = MagicMock()
    mock_proc.is_running.return_value = True
    mock_proc.status.return_value = "running"

    with patch("execution.process_manager.psutil.Process", return_value=mock_proc):
        assert pm._is_alive(1234) is True


def test_is_alive_false_for_zombie(tmp_path):
    pm = _make_pm(tmp_path)
    mock_proc = MagicMock()
    mock_proc.is_running.return_value = True
    mock_proc.status.return_value = "zombie"

    with patch("execution.process_manager.psutil.Process", return_value=mock_proc):
        with patch("execution.process_manager.psutil.STATUS_ZOMBIE", "zombie"):
            assert pm._is_alive(1234) is False


def test_is_alive_false_for_no_such_process(tmp_path):
    pm = _make_pm(tmp_path)
    import psutil as _psutil

    with patch("execution.process_manager.psutil.Process", side_effect=_psutil.NoSuchProcess(9999)):
        assert pm._is_alive(9999) is False


def test_is_alive_false_for_access_denied(tmp_path):
    pm = _make_pm(tmp_path)
    import psutil as _psutil

    with patch("execution.process_manager.psutil.Process", side_effect=_psutil.AccessDenied(9999)):
        assert pm._is_alive(9999) is False


# ---------------------------------------------------------------------------
# register
# ---------------------------------------------------------------------------

def test_register_adds_new_entry(tmp_path):
    pm = _make_pm(tmp_path)

    with patch.object(pm, "_is_alive", return_value=True):
        pm.register(pid=5000, name="Agent", command="python agent.py", cwd="/app", port=8080)

    entries = pm._load()
    assert len(entries) == 1
    assert entries[0]["pid"] == 5000
    assert entries[0]["name"] == "Agent"
    assert entries[0]["port"] == 8080


def test_register_replaces_dead_entry_with_same_name(tmp_path):
    pm = _make_pm(tmp_path)
    old_entry = _sample_entry(pid=100, name="MyApp")
    pm._save([old_entry])

    # 기존 엔트리는 죽었다고 가정
    with patch.object(pm, "_is_alive", side_effect=lambda pid: pid != 100):
        pm.register(pid=200, name="MyApp", command="python app.py", cwd="/app")

    entries = pm._load()
    pids = [e["pid"] for e in entries]
    assert 100 not in pids
    assert 200 in pids


def test_register_keeps_alive_entry_with_same_name(tmp_path):
    pm = _make_pm(tmp_path)
    old_entry = _sample_entry(pid=100, name="MyApp")
    pm._save([old_entry])

    # 기존 엔트리도 살아있으면 두 엔트리 모두 보존
    with patch.object(pm, "_is_alive", return_value=True):
        pm.register(pid=200, name="MyApp", command="python app.py", cwd="/app")

    entries = pm._load()
    pids = {e["pid"] for e in entries}
    assert {100, 200} == pids


# ---------------------------------------------------------------------------
# get_alive_processes
# ---------------------------------------------------------------------------

def test_get_alive_processes_returns_only_alive(tmp_path):
    pm = _make_pm(tmp_path)
    pm._save([_sample_entry(pid=10), _sample_entry(pid=20, name="Dead")])

    with patch.object(pm, "_is_alive", side_effect=lambda pid: pid == 10):
        alive = pm.get_alive_processes()

    assert len(alive) == 1
    assert alive[0].pid == 10


def test_get_alive_processes_cleans_dead_entries(tmp_path):
    pm = _make_pm(tmp_path)
    pm._save([_sample_entry(pid=10), _sample_entry(pid=20, name="Dead")])

    with patch.object(pm, "_is_alive", side_effect=lambda pid: pid == 10):
        pm.get_alive_processes()

    # 죽은 엔트리가 파일에서 제거됐는지 확인
    remaining = pm._load()
    assert all(e["pid"] == 10 for e in remaining)


def test_get_alive_processes_empty_when_all_dead(tmp_path):
    pm = _make_pm(tmp_path)
    pm._save([_sample_entry(pid=10)])

    with patch.object(pm, "_is_alive", return_value=False):
        alive = pm.get_alive_processes()

    assert alive == []


# ---------------------------------------------------------------------------
# kill_process
# ---------------------------------------------------------------------------

def test_kill_process_success(tmp_path):
    pm = _make_pm(tmp_path)
    mock_proc = MagicMock()
    mock_proc.children.return_value = []

    with patch("execution.process_manager.psutil.Process", return_value=mock_proc):
        with patch("execution.process_manager.psutil.wait_procs", return_value=([], [])):
            result = pm.kill_process(1234)

    assert result is True
    mock_proc.terminate.assert_called_once()


def test_kill_process_no_such_process(tmp_path):
    pm = _make_pm(tmp_path)
    import psutil as _psutil

    with patch("execution.process_manager.psutil.Process", side_effect=_psutil.NoSuchProcess(9999)):
        result = pm.kill_process(9999)

    assert result is False


def test_kill_process_kills_remaining_alive(tmp_path):
    pm = _make_pm(tmp_path)
    mock_proc = MagicMock()
    mock_child = MagicMock()
    mock_proc.children.return_value = [mock_child]

    with patch("execution.process_manager.psutil.Process", return_value=mock_proc):
        with patch("execution.process_manager.psutil.wait_procs", return_value=([], [mock_proc])):
            pm.kill_process(1234)

    mock_proc.kill.assert_called_once()


# ---------------------------------------------------------------------------
# kill_all
# ---------------------------------------------------------------------------

def test_kill_all_kills_each_alive_process(tmp_path):
    pm = _make_pm(tmp_path)
    fake_alive = [
        TrackedProcess(pid=1, name="A", command="", cwd=".", launched_at="now"),
        TrackedProcess(pid=2, name="B", command="", cwd=".", launched_at="now"),
    ]

    with patch.object(pm, "get_alive_processes", return_value=fake_alive):
        with patch.object(pm, "kill_process", return_value=True) as mock_kill:
            killed = pm.kill_all()

    assert killed == 2
    assert mock_kill.call_count == 2


def test_kill_all_returns_zero_when_no_processes(tmp_path):
    pm = _make_pm(tmp_path)

    with patch.object(pm, "get_alive_processes", return_value=[]):
        killed = pm.kill_all()

    assert killed == 0
    assert pm._load() == []


def test_kill_all_clears_file_afterwards(tmp_path):
    pm = _make_pm(tmp_path)
    pm._save([_sample_entry(pid=99)])

    with patch.object(pm, "get_alive_processes", return_value=[]):
        pm.kill_all()

    assert pm._load() == []
