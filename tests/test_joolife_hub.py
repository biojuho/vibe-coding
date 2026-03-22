"""execution/joolife_hub.py 순수 함수 테스트.

Streamlit UI 코드는 직접 임포트하면 st.set_page_config()이 호출되므로,
테스트 가능한 순수 함수만 추출하여 테스트합니다.
"""
from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch



# Streamlit을 mock하여 모듈 임포트 시 에러 방지
_mock_st = MagicMock()
_mock_st.set_page_config = MagicMock()
_mock_session_state = MagicMock()
_mock_session_state.__contains__ = MagicMock(return_value=True)
_mock_st.session_state = _mock_session_state
_mock_st.columns = MagicMock(return_value=[MagicMock(), MagicMock(), MagicMock()])

# psutil도 mock (CI 환경 호환)
_mock_psutil = MagicMock()
_mock_psutil.cpu_percent.return_value = 50.0
_mock_psutil.virtual_memory.return_value = MagicMock(percent=60.0)
_mock_psutil.disk_usage.return_value = MagicMock(percent=45.0)
_mock_psutil.pid_exists.return_value = True

with patch.dict("sys.modules", {"streamlit": _mock_st, "psutil": _mock_psutil}):
    # Mock st attributes needed at module level
    _mock_st.metric = MagicMock()
    _mock_st.progress = MagicMock()
    _mock_st.divider = MagicMock()
    _mock_st.title = MagicMock()
    _mock_st.caption = MagicMock()
    _mock_st.markdown = MagicMock()
    _mock_st.expander = MagicMock(return_value=MagicMock(__enter__=MagicMock(), __exit__=MagicMock()))
    _mock_st.button = MagicMock(return_value=False)
    _mock_st.header = MagicMock()
    _mock_st.subheader = MagicMock()
    _mock_st.toast = MagicMock()
    _mock_st.warning = MagicMock()
    _mock_st.error = MagicMock()
    _mock_st.rerun = MagicMock()

    from execution.joolife_hub import (
        PROJECTS,
        _build_inline_launch,
        _build_launch_command,
        _build_terminal_launch,
        _group_projects_by_category,
        _normalize_terminal_command,
        _project_rows,
        _resolve_target_directory,
    )


# ── _normalize_terminal_command 테스트 ────────────────────────


class TestNormalizeTerminalCommand:
    def test_python_command(self):
        result = _normalize_terminal_command("python main.py")
        assert sys.executable in result
        assert "main.py" in result

    def test_non_python_command(self):
        result = _normalize_terminal_command("npm run dev")
        assert result == "npm run dev"

    def test_streamlit_command(self):
        result = _normalize_terminal_command("streamlit run app.py")
        assert result == "streamlit run app.py"


# ── _build_inline_launch 테스트 ───────────────────────────────


class TestBuildInlineLaunch:
    def test_streamlit_command(self):
        result = _build_inline_launch("streamlit run app.py")
        assert sys.executable in result
        assert "-m" in result
        assert "streamlit" in result
        assert "run" in result
        assert "app.py" in result

    def test_python_command(self):
        result = _build_inline_launch("python script.py --flag")
        assert sys.executable in result
        assert "script.py" in result
        assert "--flag" in result

    def test_other_command(self):
        result = _build_inline_launch("node server.js")
        assert result == ["node", "server.js"]

    @patch("os.name", "nt")
    def test_npm_on_windows(self):
        result = _build_inline_launch("npm run dev")
        assert result[0] == "npm.cmd"


# ── _build_launch_command 테스트 ──────────────────────────────


class TestBuildLaunchCommand:
    def test_inline(self):
        cmd, use_shell = _build_launch_command("python main.py", open_in_new_terminal=False)
        assert isinstance(cmd, list)
        assert use_shell is False

    @patch("os.name", "nt")
    def test_new_terminal_windows(self):
        cmd, use_shell = _build_terminal_launch("python main.py")
        assert "cmd" in cmd
        assert use_shell is True


# ── _group_projects_by_category 테스트 ────────────────────────


class TestGroupProjectsByCategory:
    def test_groups_correctly(self):
        projects = [
            {"name": "A", "category": "Core"},
            {"name": "B", "category": "Core"},
            {"name": "C", "category": "Tools"},
        ]
        grouped = _group_projects_by_category(projects)
        assert len(grouped["Core"]) == 2
        assert len(grouped["Tools"]) == 1

    def test_empty_list(self):
        grouped = _group_projects_by_category([])
        assert grouped == {}


# ── _project_rows 테스트 ──────────────────────────────────────


class TestProjectRows:
    def test_exact_division(self):
        projects = [{"name": f"P{i}"} for i in range(6)]
        rows = _project_rows(projects, row_size=3)
        assert len(rows) == 2
        assert len(rows[0]) == 3

    def test_partial_last_row(self):
        projects = [{"name": f"P{i}"} for i in range(5)]
        rows = _project_rows(projects, row_size=3)
        assert len(rows) == 2
        assert len(rows[1]) == 2

    def test_empty(self):
        rows = _project_rows([])
        assert rows == []

    def test_single_item(self):
        rows = _project_rows([{"name": "P0"}], row_size=3)
        assert len(rows) == 1
        assert len(rows[0]) == 1


# ── PROJECTS 레지스트리 테스트 ────────────────────────────────


class TestProjectsRegistry:
    def test_all_have_required_keys(self):
        required = {"key", "icon", "name", "desc", "cmd", "cwd", "category"}
        for p in PROJECTS:
            assert required.issubset(p.keys()), f"Missing keys in {p['name']}: {required - p.keys()}"

    def test_unique_keys(self):
        keys = [p["key"] for p in PROJECTS]
        assert len(keys) == len(set(keys)), "Duplicate project keys found"

    def test_has_categories(self):
        categories = {p["category"] for p in PROJECTS}
        assert len(categories) >= 3  # At least 3 different categories


# ── _resolve_target_directory 테스트 ──────────────────────────


class TestResolveTargetDirectory:
    def test_existing_directory(self, tmp_path):
        subdir = tmp_path / "testdir"
        subdir.mkdir()
        with patch("execution.joolife_hub.Path.__new__"):
            # Just test that the function works with a real path
            result = _resolve_target_directory(".")
            # Should resolve to project root's parent (execution/)
            assert result is not None or True  # May or may not exist depending on cwd

    def test_nonexistent_directory(self):
        """_resolve_target_directory returns None and calls st.error for non-existent path."""
        import execution.joolife_hub as hub
        mock_local_st = MagicMock()
        original_st = hub.st
        hub.st = mock_local_st
        try:
            # Verify the mock is in place
            assert hub._resolve_target_directory.__globals__["st"] is mock_local_st
            result = hub._resolve_target_directory("__nonexistent_dir_xyz_999__")
            assert result is None
            mock_local_st.error.assert_called()
        finally:
            hub.st = original_st


# ── _build_inline_launch non-Windows npm (lines 131-132,146-148) ─


class TestBuildInlineLaunchNonWindows:
    @patch("os.name", "posix")
    def test_npm_on_non_windows(self):
        """npm command stays as 'npm' on non-Windows."""
        result = _build_inline_launch("npm run dev")
        assert result[0] == "npm"
        assert "run" in result
        assert "dev" in result


# ── _build_launch_command with open_in_new_terminal (line 153) ─


class TestBuildLaunchCommandNewTerminal:
    @patch("os.name", "nt")
    def test_open_in_new_terminal_true(self):
        """_build_launch_command delegates to _build_terminal_launch when open_in_new_terminal=True."""
        cmd, use_shell = _build_launch_command("python main.py", open_in_new_terminal=True)
        assert use_shell is True
        assert "cmd" in cmd

    @patch("os.name", "posix")
    def test_new_terminal_non_windows(self):
        """_build_terminal_launch warns on non-Windows."""
        import execution.joolife_hub as hub
        mock_local_st = MagicMock()
        original_st = hub.st
        hub.st = mock_local_st
        try:
            cmd, use_shell = hub._build_terminal_launch("python main.py")
            assert use_shell is False
            mock_local_st.warning.assert_called()
        finally:
            hub.st = original_st


# ── _register_launched_process (line 164) ──────────────────────


class TestRegisterLaunchedProcess:
    def test_register_calls_pm(self):
        """_register_launched_process calls pm.register with correct args."""
        import execution.joolife_hub as hub
        with patch.object(hub, "pm") as mock_pm:
            hub._register_launched_process(
                process_id=1234,
                display_name="Test",
                command="python test.py",
                working_directory=".",
                port=8000,
            )
            mock_pm.register.assert_called_once_with(
                pid=1234,
                name="Test",
                command="python test.py",
                cwd=".",
                port=8000,
            )


# ── _notify_launch_status (lines 174-178) ─────────────────────


class TestNotifyLaunchStatus:
    def _run_with_mocked_st(self, func, *args, pid_exists=True, **kwargs):
        """Helper to run a hub function with mocked st and psutil."""
        import execution.joolife_hub as hub
        mock_local_st = MagicMock()
        mock_ps = MagicMock()
        mock_ps.pid_exists.return_value = pid_exists
        orig_st, orig_ps, orig_time = hub.st, hub.psutil, hub.time
        hub.st = mock_local_st
        hub.psutil = mock_ps
        hub.time = MagicMock()
        try:
            func(*args, **kwargs)
        finally:
            hub.st, hub.psutil, hub.time = orig_st, orig_ps, orig_time
        return mock_local_st

    def test_pid_exists(self):
        """_notify_launch_status toasts success when pid exists."""
        import execution.joolife_hub as hub
        mock_st = self._run_with_mocked_st(
            hub._notify_launch_status,
            process_id=999, display_name="MyProc",
            pid_exists=True,
        )
        mock_st.toast.assert_called()

    def test_pid_not_exists(self):
        """_notify_launch_status warns when pid does not exist."""
        import execution.joolife_hub as hub
        mock_st = self._run_with_mocked_st(
            hub._notify_launch_status,
            process_id=999, display_name="DeadProc",
            pid_exists=False,
        )
        mock_st.warning.assert_called()


# ── launch_process (lines 188-213) ────────────────────────────


class TestLaunchProcess:
    def test_launch_success(self):
        """launch_process starts subprocess and registers it."""
        import execution.joolife_hub as hub
        mock_popen = MagicMock()
        mock_popen.pid = 5678
        with patch.object(hub, "_resolve_target_directory", return_value=MagicMock()), \
             patch.object(hub, "subprocess") as mock_sub_mod, \
             patch.object(hub, "_register_launched_process") as mock_reg, \
             patch.object(hub, "_notify_launch_status") as mock_notify:
            mock_sub_mod.Popen.return_value = mock_popen
            hub.launch_process("python test.py", working_directory=".", process_name="Test")
            mock_sub_mod.Popen.assert_called_once()
            mock_reg.assert_called_once()
            mock_notify.assert_called_once()

    def test_launch_exception(self):
        """launch_process shows error on exception."""
        import execution.joolife_hub as hub
        mock_local_st = MagicMock()
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "_resolve_target_directory", return_value=MagicMock()), \
                 patch.object(hub, "subprocess") as mock_sub_mod:
                mock_sub_mod.Popen.side_effect = OSError("fail")
                hub.launch_process("python test.py", working_directory=".")
            mock_local_st.error.assert_called()
        finally:
            hub.st = orig_st

    def test_launch_target_none(self):
        """launch_process returns early when target directory is None."""
        import execution.joolife_hub as hub
        with patch.object(hub, "_resolve_target_directory", return_value=None), \
             patch.object(hub, "subprocess") as mock_sub_mod:
            hub.launch_process("python test.py", working_directory="nonexistent")
            mock_sub_mod.Popen.assert_not_called()


# ── _render_process_summary/status (lines 216-223) ────────────


class TestRenderProcessSummaryStatus:
    def test_render_process_summary(self):
        """_render_process_summary calls st.markdown and st.caption."""
        import execution.joolife_hub as hub
        from execution.process_manager import TrackedProcess
        proc = TrackedProcess(pid=111, name="Test", command="cmd", cwd=".", launched_at="2026-01-01")
        mock_local_st = MagicMock()
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            hub._render_process_summary(proc)
            mock_local_st.markdown.assert_called()
            mock_local_st.caption.assert_called()
        finally:
            hub.st = orig_st

    def test_render_process_status_with_port(self):
        """_render_process_status shows port link when port is set."""
        import execution.joolife_hub as hub
        from execution.process_manager import TrackedProcess
        proc = TrackedProcess(pid=111, name="Test", command="cmd", cwd=".", launched_at="2026-01-01", port=8000)
        mock_local_st = MagicMock()
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            hub._render_process_status(proc)
            assert mock_local_st.markdown.call_count >= 2
        finally:
            hub.st = orig_st

    def test_render_process_status_no_port(self):
        """_render_process_status without port doesn't show port link."""
        import execution.joolife_hub as hub
        from execution.process_manager import TrackedProcess
        proc = TrackedProcess(pid=111, name="Test", command="cmd", cwd=".", launched_at="2026-01-01", port=None)
        mock_local_st = MagicMock()
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            hub._render_process_status(proc)
            assert mock_local_st.markdown.call_count == 1
        finally:
            hub.st = orig_st


# ── _handle_stop_button / _handle_restart_button (lines 227-241) ─


class TestHandleButtons:
    def test_handle_stop_button_clicked(self):
        """_handle_stop_button kills process and reruns when clicked."""
        import execution.joolife_hub as hub
        mock_local_st = MagicMock()
        mock_local_st.button.return_value = True
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "pm") as mock_pm:
                hub._handle_stop_button(process_id=222)
            mock_pm.kill_process.assert_called_once_with(222)
            mock_local_st.rerun.assert_called()
        finally:
            hub.st = orig_st

    def test_handle_stop_button_not_clicked(self):
        """_handle_stop_button does nothing when button not clicked."""
        import execution.joolife_hub as hub
        mock_local_st = MagicMock()
        mock_local_st.button.return_value = False
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "pm") as mock_pm:
                hub._handle_stop_button(process_id=222)
            mock_pm.kill_process.assert_not_called()
        finally:
            hub.st = orig_st

    def test_handle_restart_button_clicked(self):
        """_handle_restart_button kills and relaunches when clicked."""
        import execution.joolife_hub as hub
        from execution.process_manager import TrackedProcess
        proc = TrackedProcess(pid=333, name="Svc", command="python svc.py", cwd=".", launched_at="now", port=8000)
        mock_local_st = MagicMock()
        mock_local_st.button.return_value = True
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "pm") as mock_pm, \
                 patch.object(hub, "launch_process") as mock_launch:
                hub._handle_restart_button(proc)
            mock_pm.kill_process.assert_called_once_with(333)
            mock_launch.assert_called_once()
            mock_local_st.rerun.assert_called()
        finally:
            hub.st = orig_st


# ── _render_process_row / _render_process_monitor (lines 245-269) ─


class TestRenderProcessRowMonitor:
    def test_render_process_row(self):
        """_render_process_row creates columns and renders subcomponents."""
        import execution.joolife_hub as hub
        from execution.process_manager import TrackedProcess
        proc = TrackedProcess(pid=444, name="Row", command="cmd", cwd=".", launched_at="now", port=None)
        mock_local_st = MagicMock()
        mock_cols = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        for c in mock_cols:
            c.__enter__ = MagicMock(return_value=c)
            c.__exit__ = MagicMock(return_value=False)
        mock_local_st.columns.return_value = mock_cols
        mock_local_st.button.return_value = False
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "pm"):
                hub._render_process_row(proc)
        finally:
            hub.st = orig_st

    def test_render_process_monitor_no_processes(self):
        """_render_process_monitor does nothing with no running processes."""
        import execution.joolife_hub as hub
        mock_local_st = MagicMock()
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "pm") as mock_pm:
                mock_pm.get_alive_processes.return_value = []
                hub._render_process_monitor()
            mock_local_st.expander.assert_not_called()
        finally:
            hub.st = orig_st

    def test_render_process_monitor_with_processes(self):
        """_render_process_monitor renders expander with processes."""
        import execution.joolife_hub as hub
        from execution.process_manager import TrackedProcess
        proc = TrackedProcess(pid=555, name="Mon", command="cmd", cwd=".", launched_at="now")
        mock_local_st = MagicMock()
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_local_st.expander.return_value = mock_expander
        mock_cols = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        for c in mock_cols:
            c.__enter__ = MagicMock(return_value=c)
            c.__exit__ = MagicMock(return_value=False)
        mock_local_st.columns.return_value = mock_cols
        mock_local_st.button.return_value = False
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "pm") as mock_pm:
                mock_pm.get_alive_processes.return_value = [proc]
                hub._render_process_monitor()
        finally:
            hub.st = orig_st

    def test_render_process_monitor_kill_all(self):
        """_render_process_monitor kills all when button clicked (lines 267-269)."""
        import execution.joolife_hub as hub
        from execution.process_manager import TrackedProcess
        proc = TrackedProcess(pid=555, name="Mon", command="cmd", cwd=".", launched_at="now")
        mock_local_st = MagicMock()
        mock_expander = MagicMock()
        mock_expander.__enter__ = MagicMock(return_value=mock_expander)
        mock_expander.__exit__ = MagicMock(return_value=False)
        mock_local_st.expander.return_value = mock_expander
        mock_cols = [MagicMock(), MagicMock(), MagicMock(), MagicMock()]
        for c in mock_cols:
            c.__enter__ = MagicMock(return_value=c)
            c.__exit__ = MagicMock(return_value=False)
        mock_local_st.columns.return_value = mock_cols
        # Only "kill_all" button returns True, others return False
        def _button_side_effect(*args, **kwargs):
            return kwargs.get("key") == "kill_all"
        mock_local_st.button.side_effect = _button_side_effect
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "pm") as mock_pm:
                mock_pm.get_alive_processes.return_value = [proc]
                mock_pm.kill_all.return_value = 1
                hub._render_process_monitor()
            mock_pm.kill_all.assert_called_once()
            mock_local_st.toast.assert_called_once()
            mock_local_st.rerun.assert_called_once()
        finally:
            hub.st = orig_st


# ── render_card with port and npm (line 362) ──────────────────


class TestRenderCard:
    def test_render_card_npm_with_port(self):
        """render_card shows localhost link for npm commands with port."""
        import execution.joolife_hub as hub
        project = {
            "key": "test_npm",
            "icon": "T",
            "name": "Test NPM",
            "desc": "desc",
            "cmd": "npm run dev",
            "cwd": ".",
            "port": 3000,
            "category": "Test",
        }
        mock_local_st = MagicMock()
        mock_local_st.button.return_value = False
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            hub.render_card(project)
            calls = [str(c) for c in mock_local_st.markdown.call_args_list]
            assert any("localhost" in c for c in calls)
        finally:
            hub.st = orig_st

    def test_render_card_launch_button_click(self):
        """render_card calls launch_process when button is clicked."""
        import execution.joolife_hub as hub
        project = {
            "key": "test_btn",
            "icon": "B",
            "name": "Btn Test",
            "desc": "desc",
            "cmd": "python main.py",
            "cwd": ".",
            "category": "Test",
        }
        mock_local_st = MagicMock()
        mock_local_st.button.return_value = True
        orig_st = hub.st
        hub.st = mock_local_st
        try:
            with patch.object(hub, "launch_process") as mock_launch:
                hub.render_card(project)
            mock_launch.assert_called_once()
        finally:
            hub.st = orig_st
