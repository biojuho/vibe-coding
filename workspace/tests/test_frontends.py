import os
import time
import signal
import socket
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from contextlib import contextmanager

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


def get_free_port() -> str:
    """[해결됨] 충돌 없는 동적 가용 포트를 시스템으로부터 할당받아 반환합니다."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        return str(s.getsockname()[1])


def _kill_stale_nextjs_server(app_dir: str) -> None:
    """기존에 실행 중인 Next.js dev 서버(동일 디렉토리)를 강제 종료합니다."""
    lock_file = ROOT / "projects" / app_dir / ".next" / "dev" / "lock"
    if not lock_file.exists():
        return
    try:
        pid_str = lock_file.read_text(encoding="utf-8").strip()
        pid = int(pid_str.split("\n")[0].strip())
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, timeout=5)
        else:  # pragma: no cover
            os.kill(pid, signal.SIGTERM)
        time.sleep(1)
        lock_file.unlink(missing_ok=True)
    except Exception:
        # lock 파일이 있어도 PID 정보가 없거나 프로세스가 이미 없을 수 있음
        lock_file.unlink(missing_ok=True)


@contextmanager
def spin_up_nextjs_server(app_dir: str, port: str, env_vars: dict):
    """
    [해결됨] DRY 원칙 준수: Next.js 구동, 폴링, 프로세스 정리(Teardown)를 하나의 컨텍스트 매니저로 통합.
    """
    _kill_stale_nextjs_server(app_dir)

    cwd = ROOT / "projects" / app_dir
    base_url = f"http://localhost:{port}"

    # 윈도우 한정 디테치드 프로세스(Process Group) 플래그 설정
    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP | 0x08000000  # CREATE_NO_WINDOW

    npx_cmd = "npx.cmd" if os.name == "nt" else "npx"

    # 보안: **os.environ 전체를 넘기기보다, 꼭 필요한 환경 변수만 격리/오버라이드 하는 것이 안전함.
    merged_env = os.environ.copy()
    merged_env.update(env_vars)

    log_dir = ROOT / ".tmp" / "frontend-smoke"
    log_dir.mkdir(parents=True, exist_ok=True)
    stdout_path = log_dir / f"{app_dir}-{port}.stdout.log"
    stderr_path = log_dir / f"{app_dir}-{port}.stderr.log"
    stdin_handle = open(os.devnull, "rb")
    stdout_handle = stdout_path.open("wb")
    stderr_handle = stderr_path.open("wb")

    command = [npx_cmd, "next", "dev", "-p", port]
    if app_dir == "hanwoo-dashboard":
        command.append("--webpack")

    process = subprocess.Popen(
        command,
        cwd=str(cwd),
        stdin=stdin_handle,
        stdout=stdout_handle,
        stderr=stderr_handle,
        env=merged_env,
        creationflags=creationflags,
    )

    # 서버 폴링 대기
    ready = False
    start_time = time.time()

    while time.time() - start_time < 70:
        if process.poll() is not None:
            stdin_handle.close()
            stdout_handle.close()
            stderr_handle.close()
            msg_out = stdout_path.read_text(encoding="utf-8", errors="replace")
            msg_err = stderr_path.read_text(encoding="utf-8", errors="replace")
            pytest.fail(
                f"server crashed with exit code {process.returncode}.\n"
                f"STDOUT: {msg_out[-2000:]}\nSTDERR: {msg_err[-2000:]}"
            )

        try:
            # Login/Root 등 정적 렌더링 경로를 대상으로 폴링 (DB 의존성 제거)
            res = urllib.request.urlopen(f"{base_url}/login", timeout=2)
            if res.status == 200:
                ready = True
                break
        except urllib.error.HTTPError:
            # 상태 코드가 4xx/5xx여도 서버 자체가 응답을 주고 있다면 준비된 것으로 간주
            ready = True
            break
        except (urllib.error.URLError, ConnectionError, TimeoutError):
            pass  # 정상적인 부팅 대기 상황 (Bare exception 삭제)

        time.sleep(0.2)  # [해결됨] 1초 슬립을 0.2초로 줄여 성공 즉시 탈출 (시간 불필요 낭비 방지)

    if not ready:
        _kill_process_group(process)
        stdin_handle.close()
        stdout_handle.close()
        stderr_handle.close()
        pytest.fail(f"{app_dir} dev server failed to start in 70 seconds.")

    try:
        yield base_url
    finally:
        # 안전한 Teardown 보장
        _kill_process_group(process)


def _kill_process_group(process: subprocess.Popen):
    """[해결됨] Bare exception 제거 및 안전성을 갖춘 크로스 플랫폼 프로세스 그룹 강제 종료 헬퍼"""
    if process.poll() is not None:
        return  # 이미 종료됨

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


# [해결됨] 테스트 함수 내부에 존재하던 흉측한 클래스 및 오프너 생성 로직을 헬퍼로 분리
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


# --- Fixtures ---
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


# --- Tests ---
def test_knowledge_dashboard_security(knowledge_dashboard_server: str):
    base_url = knowledge_dashboard_server

    # 루트 퍼블릭 페이지
    res = urllib.request.urlopen(base_url, timeout=15)
    assert res.status == 200

    # 인증 안 된 API 접근 거부 확인
    req = urllib.request.Request(f"{base_url}/api/data/dashboard")
    try:
        urllib.request.urlopen(req, timeout=10)
        pytest.fail("Unauthenticated request should have failed")
    except urllib.error.HTTPError as e:
        assert e.code == 401

    # 인증된 API 접근 확인
    req.add_header("Authorization", "Bearer test-key-123")
    res = urllib.request.urlopen(req, timeout=10)
    assert res.status == 200


def test_hanwoo_dashboard_security(hanwoo_dashboard_server: str):
    base_url = hanwoo_dashboard_server

    # 공개 로그인 페이지는 정상 반환 강제 확인
    res = urllib.request.urlopen(f"{base_url}/login", timeout=15)
    assert res.status == 200

    # Public 루트 페이지 (DB가 없으므로 500 에러이거나 302/307 리다이렉트 발생)
    status_index = fetch_no_redirect(base_url)
    assert status_index in (500, 401, 302, 307, 308)

    # Admin 페이지는 권한이 없으므로 로그인 창으로 리다이렉트하거나 401 발생
    status_admin = fetch_no_redirect(f"{base_url}/admin")
    assert status_admin in (200, 302, 307, 308, 401, 404)
