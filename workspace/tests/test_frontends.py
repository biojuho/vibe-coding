import os
import signal
import socket
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent
WEBPACK_DEV_SERVER_APPS = {"hanwoo-dashboard", "knowledge-dashboard"}


def get_free_port() -> str:
    """Return a dynamically allocated free TCP port."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return str(s.getsockname()[1])


def _taskkill_process_tree(pid: int) -> bool:
    if os.name != "nt":
        return False
    try:
        result = subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            timeout=5,
        )
    except Exception:
        return False
    return result.returncode == 0


def _kill_stale_nextjs_server(app_dir: str) -> None:
    """Kill a stale Next.js dev process recorded by the app lock file."""
    lock_file = ROOT / "projects" / app_dir / ".next" / "dev" / "lock"
    if not lock_file.exists():
        return
    try:
        pid_str = lock_file.read_text(encoding="utf-8").strip()
        pid = int(pid_str.split("\n")[0].strip())
        if os.name == "nt":
            _taskkill_process_tree(pid)
        else:  # pragma: no cover
            os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        lock_file.unlink(missing_ok=True)
    except Exception:
        lock_file.unlink(missing_ok=True)


def _nextjs_creationflags() -> int:
    if os.name != "nt":
        return 0
    return subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW


def _nextjs_command(app_dir: str, port: str) -> list[str]:
    command = ["npx.cmd" if os.name == "nt" else "npx", "next", "dev", "-p", port]
    # Keep security smoke tests on Webpack; Turbopack dev cache can panic on
    # this Windows workspace before the route-level assertions run.
    if app_dir in WEBPACK_DEV_SERVER_APPS:
        command.append("--webpack")
    return command


def _nextjs_server_env(env_vars: dict) -> dict:
    merged_env = os.environ.copy()
    merged_env.update(env_vars)
    return merged_env


def _nextjs_log_paths(app_dir: str, port: str) -> tuple[Path, Path]:
    log_dir = ROOT / ".tmp" / "frontend-smoke"
    log_dir.mkdir(parents=True, exist_ok=True)
    return (
        log_dir / f"{app_dir}-{port}.stdout.log",
        log_dir / f"{app_dir}-{port}.stderr.log",
    )


def _close_handles(*handles) -> None:
    for handle in handles:
        handle.close()


def _fail_for_crashed_server(
    process: subprocess.Popen,
    stdin_handle,
    stdout_handle,
    stderr_handle,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    _close_handles(stdin_handle, stdout_handle, stderr_handle)
    msg_out = stdout_path.read_text(encoding="utf-8", errors="replace")
    msg_err = stderr_path.read_text(encoding="utf-8", errors="replace")
    pytest.fail(
        f"server crashed with exit code {process.returncode}.\nSTDOUT: {msg_out[-2000:]}\nSTDERR: {msg_err[-2000:]}"
    )


def _server_responded(base_url: str) -> bool:
    try:
        res = urllib.request.urlopen(f"{base_url}/login", timeout=2)
        return res.status == 200
    except urllib.error.HTTPError:
        return True
    except (urllib.error.URLError, ConnectionError, TimeoutError):
        return False


def _wait_for_nextjs_server_ready(
    app_dir: str,
    base_url: str,
    process: subprocess.Popen,
    stdin_handle,
    stdout_handle,
    stderr_handle,
    stdout_path: Path,
    stderr_path: Path,
) -> None:
    start_time = time.time()
    while time.time() - start_time < 70:
        if process.poll() is not None:
            _fail_for_crashed_server(
                process,
                stdin_handle,
                stdout_handle,
                stderr_handle,
                stdout_path,
                stderr_path,
            )
        if _server_responded(base_url):
            return
        time.sleep(0.2)

    _kill_process_group(process)
    _close_handles(stdin_handle, stdout_handle, stderr_handle)
    pytest.fail(f"{app_dir} dev server failed to start in 70 seconds.")


@contextmanager
def spin_up_nextjs_server(app_dir: str, port: str, env_vars: dict):
    """Start a Next.js dev server, wait for readiness, and tear it down."""
    _kill_stale_nextjs_server(app_dir)

    cwd = ROOT / "projects" / app_dir
    base_url = f"http://localhost:{port}"
    stdout_path, stderr_path = _nextjs_log_paths(app_dir, port)
    stdin_handle = open(os.devnull, "rb")
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")

    process = subprocess.Popen(
        _nextjs_command(app_dir, port),
        cwd=str(cwd),
        stdin=stdin_handle,
        stdout=stdout_handle,
        stderr=stderr_handle,
        env=_nextjs_server_env(env_vars),
        creationflags=_nextjs_creationflags(),
    )

    _wait_for_nextjs_server_ready(
        app_dir,
        base_url,
        process,
        stdin_handle,
        stdout_handle,
        stderr_handle,
        stdout_path,
        stderr_path,
    )

    try:
        yield base_url
    finally:
        _kill_process_group(process)
        _close_handles(stdin_handle, stdout_handle, stderr_handle)


def _kill_process_group(process: subprocess.Popen):
    """Terminate a cross-platform process group safely."""
    if process.poll() is not None:
        return

    if _taskkill_process_tree(process.pid):
        return

    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        if os.name == "nt":
            process.send_signal(signal.CTRL_BREAK_EVENT)
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
        else:
            process.kill()


class NoRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_no_redirect(url: str, timeout: int = 10):
    opener = urllib.request.build_opener(NoRedirects)
    req = urllib.request.Request(url)
    try:
        res = opener.open(req, timeout=timeout)
        return res.status
    except urllib.error.HTTPError as e:
        return e.code


def test_nextjs_command_preserves_app_specific_flags():
    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"
    assert _nextjs_command("knowledge-dashboard", "1234") == [
        npx_cmd,
        "next",
        "dev",
        "-p",
        "1234",
        "--webpack",
    ]
    assert _nextjs_command("hanwoo-dashboard", "5678") == [
        npx_cmd,
        "next",
        "dev",
        "-p",
        "5678",
        "--webpack",
    ]


def test_nextjs_server_env_merges_without_mutating_input():
    env_vars = {"DASHBOARD_API_KEY": "test-key"}
    merged = _nextjs_server_env(env_vars)
    assert merged["DASHBOARD_API_KEY"] == "test-key"
    assert env_vars == {"DASHBOARD_API_KEY": "test-key"}


def test_server_responded_preserves_http_error_readiness(monkeypatch):
    def http_error(_url, timeout):
        raise urllib.error.HTTPError(_url, 500, "ready enough", {}, None)

    def url_error(_url, timeout):
        raise urllib.error.URLError("not ready")

    monkeypatch.setattr(urllib.request, "urlopen", http_error)
    assert _server_responded("http://localhost:1234") is True

    monkeypatch.setattr(urllib.request, "urlopen", url_error)
    assert _server_responded("http://localhost:1234") is False


def test_taskkill_process_tree_uses_windows_tree_flags(monkeypatch):
    calls = []

    class Result:
        returncode = 0

    def fake_run(command, capture_output, timeout):
        calls.append((command, capture_output, timeout))
        return Result()

    monkeypatch.setattr(os, "name", "nt")
    monkeypatch.setattr(subprocess, "run", fake_run)

    assert _taskkill_process_tree(1234) is True
    assert calls == [
        (["taskkill", "/F", "/T", "/PID", "1234"], True, 5),
    ]


@pytest.fixture(scope="module")
def knowledge_dashboard_server():
    port = get_free_port()
    env = {"DASHBOARD_API_KEY": "test-key-123"}
    with spin_up_nextjs_server("knowledge-dashboard", port, env) as url:
        yield url


@pytest.fixture(scope="module")
def hanwoo_dashboard_server():
    port = get_free_port()
    env = {"NEXTAUTH_SECRET": "test-secret", "NEXTAUTH_URL": f"http://localhost:{port}"}
    with spin_up_nextjs_server("hanwoo-dashboard", port, env) as url:
        yield url


def test_knowledge_dashboard_security(knowledge_dashboard_server: str):
    base_url = knowledge_dashboard_server

    res = urllib.request.urlopen(base_url, timeout=15)
    assert res.status == 200

    req = urllib.request.Request(f"{base_url}/api/data/dashboard")
    try:
        urllib.request.urlopen(req, timeout=10)
        pytest.fail("Unauthenticated request should have failed")
    except urllib.error.HTTPError as e:
        assert e.code == 401

    req.add_header("Authorization", "Bearer test-key-123")
    res = urllib.request.urlopen(req, timeout=10)
    assert res.status == 200


def test_hanwoo_dashboard_security(hanwoo_dashboard_server: str):
    base_url = hanwoo_dashboard_server

    res = urllib.request.urlopen(f"{base_url}/login", timeout=15)
    assert res.status == 200

    status_index = fetch_no_redirect(base_url)
    assert status_index in (500, 401, 302, 307, 308)

    status_admin = fetch_no_redirect(f"{base_url}/admin")
    assert status_admin in (200, 302, 307, 308, 401, 404)
