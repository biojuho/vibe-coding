from pipeline.trend_monitor import TrendMonitor


def teardown_function():
    TrendMonitor.shutdown_shared_executor()
    TrendMonitor._executor_shutdown_registered = False


def test_trend_monitor_reuses_shared_executor():
    first = TrendMonitor({"trends.naver_enabled": False})
    second = TrendMonitor({"trends.naver_enabled": False})

    assert first._executor is second._executor


def test_trend_monitor_shutdown_shared_executor_resets_instance():
    monitor = TrendMonitor({"trends.naver_enabled": False})
    executor = monitor._executor

    TrendMonitor.shutdown_shared_executor()

    assert TrendMonitor._shared_executor is None
    assert getattr(executor, "_shutdown", False) is True
