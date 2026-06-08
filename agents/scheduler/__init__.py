"""
RS Downloader v10.0.0 — Scheduler Agent
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Task scheduling agent for cron-based and one-off scheduled downloads.
"""

from __future__ import annotations

import re
import time
import threading
from datetime import datetime, timezone
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from core.downloader_base import (
    DownloaderBase,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    AgentSkill,
    AgentMemory,
    DownloadPriority,
    DownloadQueue,
)

__all__ = ["SchedulerAgent", "register"]

AGENT_NAME = "scheduler"
PLATFORM = "internal"
SUPPORTED_FORMATS: FrozenSet[str] = frozenset()
SUPPORTED_QUALITIES: FrozenSet[str] = frozenset()

_CRON_PATTERN = re.compile(
    r"^(?P<minute>\*|\d{1,2})\s+"
    r"(?P<hour>\*|\d{1,2})\s+"
    r"(?P<day>\*|\d{1,2})\s+"
    r"(?P<month>\*|\d{1,2})\s+"
    r"(?P<weekday>\*|\d{1,2})$"
)


class SchedulerAgent(DownloaderBase):
    """Task scheduling agent — cron-based and one-off scheduled downloads."""

    AGENT_NAME = AGENT_NAME
    PLATFORM = PLATFORM
    SUPPORTED_FORMATS = SUPPORTED_FORMATS
    SUPPORTED_QUALITIES = SUPPORTED_QUALITIES

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._schedules: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def validate_url(self, url: str) -> bool:
        """Scheduler agent doesn't download from URLs."""
        return True

    def get_available_formats(self, url: str = "") -> List[str]:
        return []

    def get_metadata(self, url: str) -> Dict[str, Any]:
        with self._lock:
            return {
                "scheduled_count": len(self._schedules),
                "schedules": list(self._schedules.keys()),
            }

    def on_prepare(self, task: DownloadTask) -> DownloadTask:
        return task

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Scheduler 'download' returns current schedule status."""
        with self._lock:
            schedules = {
                sid: {
                    "type": s["type"],
                    "cron_expr": s.get("cron_expr", ""),
                    "enabled": s.get("enabled", True),
                    "last_run": s.get("last_run"),
                }
                for sid, s in self._schedules.items()
            }
        return DownloadResult(
            task_id=task.task_id if task else "scheduler-status",
            url=task.url if task else "",
            status=DownloadStatus.COMPLETED,
            metadata={"schedules": schedules},
        )

    def on_verify(self, task: DownloadTask = None, result: DownloadResult = None) -> DownloadResult:
        if result is not None:
            return result
        return DownloadResult(status=DownloadStatus.COMPLETED)

    def on_post_process(self, task: DownloadTask = None, result: DownloadResult = None) -> DownloadResult:
        if result is not None:
            return result
        return DownloadResult(status=DownloadStatus.COMPLETED)

    # -- Scheduling Methods --

    def schedule_once(self, task_id: str, run_at: float, url: str = "",
                      output_path: str = "") -> str:
        """Schedule a one-off download at a specific time."""
        entry = {
            "task_id": task_id,
            "type": "once",
            "run_at": run_at,
            "url": url,
            "output_path": output_path,
            "cron_expr": "",
            "cron_parsed": None,
            "last_run": None,
            "enabled": True,
            "created_at": time.time(),
        }
        with self._lock:
            self._schedules[task_id] = entry
        return task_id

    def schedule_cron(self, task_id: str, cron_expr: str, url: str = "",
                      output_path: str = "") -> str:
        """Schedule a recurring download with cron expression."""
        parsed = self._parse_cron(cron_expr)
        if parsed is None:
            raise ValueError(f"Invalid cron expression: {cron_expr}")
        entry = {
            "task_id": task_id,
            "type": "cron",
            "run_at": None,
            "url": url,
            "output_path": output_path,
            "cron_expr": cron_expr,
            "cron_parsed": parsed,
            "last_run": None,
            "enabled": True,
            "created_at": time.time(),
        }
        with self._lock:
            self._schedules[task_id] = entry
        return task_id

    def unschedule(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        with self._lock:
            return self._schedules.pop(task_id, None) is not None

    def enable(self, task_id: str) -> bool:
        """Enable a scheduled task."""
        with self._lock:
            if task_id in self._schedules:
                self._schedules[task_id]["enabled"] = True
                return True
        return False

    def disable(self, task_id: str) -> bool:
        """Disable a scheduled task."""
        with self._lock:
            if task_id in self._schedules:
                self._schedules[task_id]["enabled"] = False
                return True
        return False

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all scheduled tasks."""
        with self._lock:
            return list(self._schedules.values())

    def start(self, poll_interval: float = 5.0) -> None:
        """Start the scheduler loop in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._running.set()
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            args=(poll_interval,),
            daemon=True,
            name="scheduler-agent",
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler loop."""
        self._running.clear()
        if self._thread:
            self._thread.join(timeout=10.0)
            self._thread = None

    # -- Internal --

    def _parse_cron(self, expr: str) -> Optional[Dict[str, Any]]:
        """Parse a 5-field cron expression."""
        m = _CRON_PATTERN.match(expr.strip())
        if not m:
            return None
        result: Dict[str, Any] = {}
        for key in ("minute", "hour", "day", "month", "weekday"):
            val = m.group(key)
            result[key] = "*" if val == "*" else int(val)
        return result

    def _matches_cron(self, cron: Dict[str, Any], dt: datetime) -> bool:
        """Check if current time matches cron expression."""
        checks = [
            ("minute", dt.minute),
            ("hour", dt.hour),
            ("day", dt.day),
            ("month", dt.month),
            ("weekday", dt.weekday()),
        ]
        for key, actual in checks:
            cron_val = cron.get(key, "*")
            if cron_val != "*" and cron_val != actual:
                return False
        return True

    def _scheduler_loop(self, poll_interval: float) -> None:
        """Background scheduler loop."""
        while self._running.is_set():
            now = time.monotonic()
            now_dt = datetime.now(tz=timezone.utc)
            with self._lock:
                due_tasks: List[str] = []
                for task_id, sched in list(self._schedules.items()):
                    if not sched.get("enabled", True):
                        continue
                    if sched["type"] == "once" and sched.get("run_at") is not None:
                        if now >= sched["run_at"]:
                            due_tasks.append(task_id)
                    elif sched["type"] == "cron" and sched.get("cron_parsed") is not None:
                        last = sched.get("last_run")
                        if self._matches_cron(sched["cron_parsed"], now_dt):
                            if last is None or (now - last) > 60:
                                due_tasks.append(task_id)
                                self._schedules[task_id]["last_run"] = now
            for task_id in due_tasks:
                sched = self._schedules.get(task_id)
                if sched and sched["type"] == "once":
                    del self._schedules[task_id]
            time.sleep(poll_interval)


def register() -> Tuple[str, AgentSkill]:
    """Register the scheduler agent."""
    return (
        AGENT_NAME,
        AgentSkill(
            platform=PLATFORM,
            formats=frozenset(),
            qualities=frozenset(),
            features=frozenset({"cron", "one-off", "recurring", "management"}),
            max_concurrent=1,
            priority=DownloadPriority.BACKGROUND,
        ),
    )
