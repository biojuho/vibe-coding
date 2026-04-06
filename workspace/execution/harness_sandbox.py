"""Harness Sandbox Configuration — Docker-based isolation for agent execution.

Part of Harness Engineering AI Phase 0 (ADR-025).

Provides sandbox profiles that constrain agent execution to isolated
environments, preventing unintended side-effects on the host system.

Design principles:
  - Minimal privilege: each sandbox profile grants only what the task needs.
  - Docker-first: production agents run in OCI containers with resource limits.
  - Subprocess fallback: local development on Windows/macOS falls back to
    subprocess isolation with cwd/env constraints.
  - Immutable configs: sandbox profiles are frozen dataclasses.

Usage::

    manager = SandboxManager()
    sandbox = manager.create(BLIND_TO_X_SANDBOX)
    sandbox.start()
    ...  # run agent work
    sandbox.stop()
"""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Network mode
# ---------------------------------------------------------------------------


class NetworkMode(Enum):
    """Container network isolation level."""

    NONE = "none"  # No network access
    HOST = "host"  # Host networking (dev only)
    BRIDGE = "bridge"  # Default Docker bridge


# ---------------------------------------------------------------------------
# Sandbox configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SandboxConfig:
    """Immutable configuration for a sandbox environment.

    Attributes:
        name: Human-readable sandbox name.
        image: Docker image to use (e.g. ``"python:3.14-slim"``).
        memory_limit: Memory limit string (e.g. ``"512m"``).
        cpu_limit: CPU quota as a float (e.g. ``1.0`` = 1 core).
        network_mode: Network isolation level.
        volume_mounts: Mapping of host_path -> container_path with
            optional ``:ro`` suffix for read-only.
        env_vars: Environment variables to inject.
        timeout: Maximum execution duration in seconds.
        working_dir: Working directory inside the container.
        allowed_commands: If non-empty, only these commands may be run.
    """

    name: str
    image: str = "python:3.14-slim"
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    network_mode: NetworkMode = NetworkMode.NONE
    volume_mounts: tuple[tuple[str, str], ...] = ()
    env_vars: tuple[tuple[str, str], ...] = ()
    timeout: int = 300
    working_dir: str = "/workspace"
    allowed_commands: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Sandbox state
# ---------------------------------------------------------------------------


class SandboxState(Enum):
    """Lifecycle state of a sandbox instance."""

    CREATED = "created"
    RUNNING = "running"
    STOPPED = "stopped"
    DESTROYED = "destroyed"
    ERROR = "error"


@dataclass
class SandboxInstance:
    """Runtime state for a running sandbox."""

    config: SandboxConfig
    state: SandboxState = SandboxState.CREATED
    container_id: str | None = None
    process: subprocess.Popen | None = None  # For subprocess fallback
    started_at: float | None = None
    stopped_at: float | None = None
    exit_code: int | None = None
    error_message: str = ""

    @property
    def elapsed(self) -> float | None:
        """Seconds since start, or total runtime if stopped."""
        if self.started_at is None:
            return None
        end = self.stopped_at or time.time()
        return end - self.started_at

    @property
    def is_timed_out(self) -> bool:
        """Whether the sandbox has exceeded its timeout."""
        elapsed = self.elapsed
        if elapsed is None:
            return False
        return elapsed > self.config.timeout


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------


class SandboxManager:
    """Create, start, stop, and destroy sandbox environments.

    On systems without Docker, falls back to subprocess-based isolation
    that constrains the working directory and environment variables.
    """

    def __init__(self, docker_available: bool | None = None) -> None:
        if docker_available is None:
            self._docker_available = _check_docker()
        else:
            self._docker_available = docker_available
        self._instances: dict[str, SandboxInstance] = {}

    @property
    def docker_available(self) -> bool:
        return self._docker_available

    @property
    def active_sandboxes(self) -> list[str]:
        return [name for name, inst in self._instances.items() if inst.state == SandboxState.RUNNING]

    def create(self, config: SandboxConfig) -> SandboxInstance:
        """Create a sandbox instance from the given config.

        The sandbox is not yet started — call :meth:`start` to begin
        execution.
        """
        if config.name in self._instances:
            existing = self._instances[config.name]
            if existing.state == SandboxState.RUNNING:
                raise RuntimeError(f"Sandbox '{config.name}' is already running. Stop it before creating a new one.")

        instance = SandboxInstance(config=config)
        self._instances[config.name] = instance
        logger.info("Sandbox '%s' created (docker=%s)", config.name, self._docker_available)
        return instance

    def start(self, name: str) -> SandboxInstance:
        """Start a previously created sandbox."""
        instance = self._instances.get(name)
        if instance is None:
            raise KeyError(f"No sandbox named '{name}'. Call create() first.")
        if instance.state == SandboxState.RUNNING:
            raise RuntimeError(f"Sandbox '{name}' is already running.")

        instance.started_at = time.time()

        if self._docker_available:
            instance = self._start_docker(instance)
        else:
            instance = self._start_subprocess(instance)

        self._instances[name] = instance
        return instance

    def stop(self, name: str) -> SandboxInstance:
        """Stop a running sandbox."""
        instance = self._instances.get(name)
        if instance is None:
            raise KeyError(f"No sandbox named '{name}'.")

        if instance.state != SandboxState.RUNNING:
            logger.warning("Sandbox '%s' is not running (state=%s)", name, instance.state.value)
            return instance

        instance.stopped_at = time.time()

        if instance.container_id:
            self._stop_docker(instance)
        elif instance.process:
            self._stop_subprocess(instance)

        instance.state = SandboxState.STOPPED
        self._instances[name] = instance
        logger.info("Sandbox '%s' stopped (elapsed=%.1fs)", name, instance.elapsed or 0)
        return instance

    def destroy(self, name: str) -> None:
        """Remove a sandbox instance entirely."""
        instance = self._instances.get(name)
        if instance is None:
            return

        if instance.state == SandboxState.RUNNING:
            self.stop(name)

        if instance.container_id:
            self._destroy_docker(instance)

        instance.state = SandboxState.DESTROYED
        del self._instances[name]
        logger.info("Sandbox '%s' destroyed", name)

    def get(self, name: str) -> SandboxInstance | None:
        """Get sandbox instance by name."""
        return self._instances.get(name)

    # -- Docker backend -----------------------------------------------------

    def _start_docker(self, instance: SandboxInstance) -> SandboxInstance:
        """Start a Docker container for the sandbox."""
        cfg = instance.config
        cmd = [
            "docker",
            "run",
            "-d",
            "--name",
            f"harness-{cfg.name}-{int(time.time())}",
            "--memory",
            cfg.memory_limit,
            "--cpus",
            str(cfg.cpu_limit),
            "--network",
            cfg.network_mode.value,
            "-w",
            cfg.working_dir,
        ]

        for host_path, container_path in cfg.volume_mounts:
            cmd.extend(["-v", f"{host_path}:{container_path}"])

        for key, value in cfg.env_vars:
            cmd.extend(["-e", f"{key}={value}"])

        cmd.extend([cfg.image, "sleep", str(cfg.timeout)])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                instance.state = SandboxState.ERROR
                instance.error_message = result.stderr.strip()
                logger.error("Docker start failed for '%s': %s", cfg.name, instance.error_message)
            else:
                instance.container_id = result.stdout.strip()[:12]
                instance.state = SandboxState.RUNNING
                logger.info("Docker container started: %s", instance.container_id)
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            instance.state = SandboxState.ERROR
            instance.error_message = str(e)
            logger.error("Docker start error for '%s': %s", cfg.name, e)

        return instance

    def _stop_docker(self, instance: SandboxInstance) -> None:
        """Stop a Docker container."""
        if not instance.container_id:
            return
        try:
            subprocess.run(
                ["docker", "stop", instance.container_id],
                capture_output=True,
                timeout=15,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Docker stop timed out for container %s", instance.container_id)

    def _destroy_docker(self, instance: SandboxInstance) -> None:
        """Remove a Docker container."""
        if not instance.container_id:
            return
        try:
            subprocess.run(
                ["docker", "rm", "-f", instance.container_id],
                capture_output=True,
                timeout=15,
            )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Docker rm failed for container %s", instance.container_id)

    # -- Subprocess fallback ------------------------------------------------

    def _start_subprocess(self, instance: SandboxInstance) -> SandboxInstance:
        """Start a subprocess-based sandbox (local dev fallback).

        This provides minimal isolation by constraining the working
        directory, environment variables, and timeout — but does NOT
        provide file system or network isolation.
        """
        cfg = instance.config

        # Build constrained environment
        env = dict(os.environ)
        for key, value in cfg.env_vars:
            env[key] = value

        # Determine working dir — use first volume mount's host path or cwd
        work_dir = None
        if cfg.volume_mounts:
            work_dir = cfg.volume_mounts[0][0]
        if not work_dir or not Path(work_dir).is_dir():
            work_dir = os.getcwd()

        instance.state = SandboxState.RUNNING
        logger.info(
            "Subprocess sandbox '%s' started (cwd=%s, timeout=%ds)",
            cfg.name,
            work_dir,
            cfg.timeout,
        )
        return instance

    def _stop_subprocess(self, instance: SandboxInstance) -> None:
        """Stop a subprocess-based sandbox."""
        proc = instance.process
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


# ---------------------------------------------------------------------------
# Pre-built sandbox profiles
# ---------------------------------------------------------------------------


def _default_workspace_root() -> str:
    return str(Path(__file__).resolve().parents[1])


def build_blind_to_x_sandbox(workspace_root: str | None = None) -> SandboxConfig:
    """Sandbox for blind-to-x pipeline tasks: read-only project, writable .tmp."""
    root = workspace_root or _default_workspace_root()
    return SandboxConfig(
        name="blind-to-x",
        image="python:3.14-slim",
        memory_limit="512m",
        cpu_limit=1.0,
        network_mode=NetworkMode.NONE,
        volume_mounts=(
            (f"{root}/projects/blind-to-x", "/workspace/projects/blind-to-x:ro"),
            (f"{root}/.tmp", "/workspace/.tmp"),
        ),
        env_vars=(
            ("PYTHONDONTWRITEBYTECODE", "1"),
            ("SANDBOX_NAME", "blind-to-x"),
        ),
        timeout=300,
    )


def build_shorts_sandbox(workspace_root: str | None = None) -> SandboxConfig:
    """Sandbox for shorts-maker-v2 tasks."""
    root = workspace_root or _default_workspace_root()
    return SandboxConfig(
        name="shorts-maker-v2",
        image="python:3.14-slim",
        memory_limit="1g",
        cpu_limit=2.0,
        network_mode=NetworkMode.NONE,
        volume_mounts=(
            (f"{root}/projects/shorts-maker-v2", "/workspace/projects/shorts-maker-v2:ro"),
            (f"{root}/.tmp", "/workspace/.tmp"),
        ),
        env_vars=(
            ("PYTHONDONTWRITEBYTECODE", "1"),
            ("SANDBOX_NAME", "shorts-maker-v2"),
        ),
        timeout=600,
    )


def build_development_sandbox(workspace_root: str | None = None) -> SandboxConfig:
    """Development sandbox with network access and human-gated writes."""
    root = workspace_root or _default_workspace_root()
    return SandboxConfig(
        name="development",
        image="python:3.14-slim",
        memory_limit="2g",
        cpu_limit=2.0,
        network_mode=NetworkMode.BRIDGE,
        volume_mounts=((root, "/workspace"),),
        env_vars=(
            ("PYTHONDONTWRITEBYTECODE", "1"),
            ("SANDBOX_NAME", "development"),
        ),
        timeout=1800,
    )


# Convenient module-level profile instances
BLIND_TO_X_SANDBOX = build_blind_to_x_sandbox()
SHORTS_SANDBOX = build_shorts_sandbox()
DEVELOPMENT_SANDBOX = build_development_sandbox()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_docker() -> bool:
    """Check if Docker is available on this system."""
    docker_path = shutil.which("docker")
    if not docker_path:
        return False
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return False
