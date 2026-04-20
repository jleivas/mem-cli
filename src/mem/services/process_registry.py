from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from ..storage.runtime_state import RuntimeState, RuntimeStateStore
from ..utils.time import utc_now


class ProcessRegistry:
    def __init__(self, state_store: RuntimeStateStore | None = None) -> None:
        self.state_store = state_store or RuntimeStateStore()

    def load_state(self) -> RuntimeState | None:
        state = self.state_store.load()
        if state and state.pid and not self.is_pid_alive(state.pid):
            return RuntimeState(
                running=False,
                pid=state.pid,
                started_at=state.started_at,
                last_updated=utc_now(),
            )
        return state

    def is_running(self) -> bool:
        state = self.load_state()
        return bool(state and state.running)

    def start(self) -> RuntimeState:
        current = self.load_state()
        if current and current.running:
            raise RuntimeError("mem-cli is already running.")

        process = self._spawn_daemon()
        if not self._wait_for_process_ready(process):
            raise RuntimeError("mem-cli daemon exited before becoming ready.")
        state = RuntimeState(
            running=True,
            pid=process.pid,
            started_at=utc_now(),
            last_updated=utc_now(),
        )
        self.state_store.save(state)
        return state

    def stop(self) -> RuntimeState | None:
        state = self.state_store.load()
        if not state:
            return None

        if state.pid and self.is_pid_alive(state.pid):
            self._terminate_pid(state.pid)
            self._wait_for_pid_exit(state.pid)

        self.state_store.clear()
        return RuntimeState(
            running=False,
            pid=state.pid,
            started_at=state.started_at,
            last_updated=utc_now(),
        )

    def _spawn_daemon(self) -> subprocess.Popen[bytes]:
        command = [
            sys.executable,
            "-c",
            "from mem.app import run_daemon; run_daemon()",
        ]
        creationflags = 0
        if os.name == "nt":
            creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
        return subprocess.Popen(
            command,
            cwd=str(Path.cwd()),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
            start_new_session=os.name != "nt",
        )

    @staticmethod
    def is_pid_alive(pid: int) -> bool:
        if pid <= 0:
            return False
        try:
            os.kill(pid, 0)
        except OSError:
            return False
        return True

    @staticmethod
    def _terminate_pid(pid: int) -> None:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return

    @classmethod
    def _wait_for_process_ready(cls, process: subprocess.Popen[bytes], timeout: float = 2.0) -> bool:
        time.sleep(min(timeout, 0.2))
        return process.poll() is None

    @classmethod
    def _wait_for_pid_exit(cls, pid: int, timeout: float = 2.0) -> None:
        deadline = time.time() + timeout
        while time.time() < deadline and cls.is_pid_alive(pid):
            time.sleep(0.05)
