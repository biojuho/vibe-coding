"""Unit tests for harness_sandbox.py — Harness Phase 0."""

import time

import pytest

from execution.harness_sandbox import (
    BLIND_TO_X_SANDBOX,
    DEVELOPMENT_SANDBOX,
    SHORTS_SANDBOX,
    NetworkMode,
    SandboxConfig,
    SandboxInstance,
    SandboxManager,
    SandboxState,
    build_blind_to_x_sandbox,
    build_development_sandbox,
    build_shorts_sandbox,
)


# ── SandboxConfig ──────────────────────────────────────────────────────


class TestSandboxConfig:
    def test_defaults(self):
        cfg = SandboxConfig(name="test")
        assert cfg.name == "test"
        assert cfg.image == "python:3.14-slim"
        assert cfg.memory_limit == "512m"
        assert cfg.cpu_limit == 1.0
        assert cfg.network_mode == NetworkMode.NONE
        assert cfg.timeout == 300
        assert cfg.volume_mounts == ()
        assert cfg.env_vars == ()

    def test_frozen_immutability(self):
        cfg = SandboxConfig(name="frozen-test")
        with pytest.raises(AttributeError):
            cfg.name = "changed"  # type: ignore[misc]

    def test_custom_values(self):
        cfg = SandboxConfig(
            name="custom",
            image="node:20-slim",
            memory_limit="1g",
            cpu_limit=2.0,
            network_mode=NetworkMode.BRIDGE,
            timeout=600,
        )
        assert cfg.image == "node:20-slim"
        assert cfg.network_mode == NetworkMode.BRIDGE


# ── SandboxInstance ────────────────────────────────────────────────────


class TestSandboxInstance:
    def test_elapsed_none_when_not_started(self):
        inst = SandboxInstance(config=SandboxConfig(name="t"))
        assert inst.elapsed is None
        assert inst.is_timed_out is False

    def test_elapsed_while_running(self):
        inst = SandboxInstance(config=SandboxConfig(name="t", timeout=10))
        inst.started_at = time.time() - 5
        assert inst.elapsed is not None
        assert inst.elapsed >= 4.9
        assert inst.is_timed_out is False

    def test_is_timed_out(self):
        inst = SandboxInstance(config=SandboxConfig(name="t", timeout=1))
        inst.started_at = time.time() - 10
        assert inst.is_timed_out is True


# ── SandboxManager ────────────────────────────────────────────────────


class TestSandboxManager:
    def test_create_and_get(self):
        manager = SandboxManager(docker_available=False)
        cfg = SandboxConfig(name="unit-test")
        inst = manager.create(cfg)
        assert inst.state == SandboxState.CREATED
        assert manager.get("unit-test") is inst

    def test_create_duplicate_running_raises(self):
        manager = SandboxManager(docker_available=False)
        cfg = SandboxConfig(name="dup-test")
        inst = manager.create(cfg)
        inst.state = SandboxState.RUNNING
        manager._instances["dup-test"] = inst
        with pytest.raises(RuntimeError, match="already running"):
            manager.create(cfg)

    def test_start_not_found_raises(self):
        manager = SandboxManager(docker_available=False)
        with pytest.raises(KeyError, match="No sandbox named"):
            manager.start("nonexistent")

    def test_start_subprocess_fallback(self):
        manager = SandboxManager(docker_available=False)
        cfg = SandboxConfig(name="sub-test")
        manager.create(cfg)
        inst = manager.start("sub-test")
        assert inst.state == SandboxState.RUNNING
        assert inst.started_at is not None
        assert "sub-test" in manager.active_sandboxes

    def test_stop_running_sandbox(self):
        manager = SandboxManager(docker_available=False)
        cfg = SandboxConfig(name="stop-test")
        manager.create(cfg)
        manager.start("stop-test")
        inst = manager.stop("stop-test")
        assert inst.state == SandboxState.STOPPED
        assert inst.stopped_at is not None
        assert "stop-test" not in manager.active_sandboxes

    def test_stop_not_running_is_noop(self):
        manager = SandboxManager(docker_available=False)
        cfg = SandboxConfig(name="noop-test")
        manager.create(cfg)
        inst = manager.stop("noop-test")
        assert inst.state == SandboxState.CREATED  # unchanged

    def test_destroy_removes_instance(self):
        manager = SandboxManager(docker_available=False)
        cfg = SandboxConfig(name="destroy-test")
        manager.create(cfg)
        manager.start("destroy-test")
        manager.destroy("destroy-test")
        assert manager.get("destroy-test") is None

    def test_destroy_nonexistent_is_noop(self):
        manager = SandboxManager(docker_available=False)
        manager.destroy("ghost")  # Should not raise


# ── Pre-built profiles ────────────────────────────────────────────────


class TestPrebuiltProfiles:
    def test_blind_to_x_profile(self):
        cfg = build_blind_to_x_sandbox("/test/root")
        assert cfg.name == "blind-to-x"
        assert cfg.network_mode == NetworkMode.NONE
        assert cfg.memory_limit == "512m"
        assert any("blind-to-x" in v[0] for v in cfg.volume_mounts)

    def test_shorts_profile(self):
        cfg = build_shorts_sandbox("/test/root")
        assert cfg.name == "shorts-maker-v2"
        assert cfg.memory_limit == "1g"
        assert cfg.cpu_limit == 2.0

    def test_development_profile(self):
        cfg = build_development_sandbox("/test/root")
        assert cfg.name == "development"
        assert cfg.network_mode == NetworkMode.BRIDGE
        assert cfg.timeout == 1800

    def test_module_level_constants_exist(self):
        assert BLIND_TO_X_SANDBOX.name == "blind-to-x"
        assert SHORTS_SANDBOX.name == "shorts-maker-v2"
        assert DEVELOPMENT_SANDBOX.name == "development"
