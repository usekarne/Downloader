"""
RS Downloader v10.0.0 - Download Engine Base
==============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

The HEART of the project. Contains all core download engine classes:
exceptions, enums, data models, queue, speed tracker, scheduler,
lifecycle, agent system, event emitter, checkpoint manager,
concurrent manager, bandwidth monitor, orchestrator, and abstract base.
"""

from __future__ import annotations

import abc
import asyncio
import copy
import hashlib
import heapq
import json
import os
import re
import threading
import time
import uuid
from collections import defaultdict, deque, OrderedDict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum, IntEnum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    FrozenSet,
    Iterator,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Union,
)

from core.logger import get_logger
from core.network import (
    ChecksumAlgorithm,
    HeadInfo,
    DownloadSession,
    SyncHTTPClient,
    verify_checksum,
    detect_content_length,
    download_chunk,
    parallel_download,
)

logger = get_logger("downloader_base", enable_file=False)


# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

VERSION = "10.0.0"


# ---------------------------------------------------------------------------
# Custom Exceptions
# ---------------------------------------------------------------------------

class QueueFullError(Exception):
    """Raised when attempting to add to a full download queue."""
    pass


class QueueEmptyError(Exception):
    """Raised when attempting to get from an empty download queue."""
    pass


class LifecycleError(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


class DownloadError(Exception):
    """General download error."""
    pass


class AgentNotFoundError(Exception):
    """Raised when no suitable agent is found for a download task."""
    pass


class CheckpointCorruptedError(Exception):
    """Raised when checkpoint data is corrupted or invalid."""
    pass


# ---------------------------------------------------------------------------
# DownloadPriority
# ---------------------------------------------------------------------------

class DownloadPriority(IntEnum):
    """Download priority levels. Lower value = higher priority."""
    CRITICAL = 0
    HIGH = 1
    NORMAL = 5
    LOW = 10
    BACKGROUND = 20
    STREAMING = 15
    REALTIME = 0


# ---------------------------------------------------------------------------
# DownloadStatus
# ---------------------------------------------------------------------------

class DownloadStatus(Enum):
    """Download lifecycle states."""
    PENDING = "pending"
    SCHEDULING = "scheduling"
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PAUSED = "paused"
    VERIFYING = "verifying"
    EXTRACTING = "extracting"
    CONVERTING = "converting"
    UPLOADING = "uploading"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


# ---------------------------------------------------------------------------
# DownloadResult
# ---------------------------------------------------------------------------

@dataclass
class DownloadResult:
    """Result of a completed download operation."""
    task_id: str = ""
    url: str = ""
    filename: str = ""
    output_path: str = ""
    file_size: int = 0
    elapsed: float = 0.0
    average_speed: float = 0.0
    status: DownloadStatus = DownloadStatus.PENDING
    error: str = ""
    checksum_verified: bool = False
    checksum_algorithm: str = "sha256"
    resume_used: bool = False
    content_type: str = ""
    platform: str = ""
    agent_name: str = ""
    quality: str = ""
    format: str = ""
    duration: float = 0.0
    thumbnail_url: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    retry_count: int = 0
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    speed_samples: List[float] = field(default_factory=list)
    source_url: str = ""
    download_method: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadResult":
        """Create from dictionary."""
        if "status" in data and isinstance(data["status"], str):
            data["status"] = DownloadStatus(data["status"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ---------------------------------------------------------------------------
# DownloadTask
# ---------------------------------------------------------------------------

@dataclass(order=True)
class DownloadTask:
    """A download task with priority ordering."""
    sort_key: Tuple[int, float] = field(init=False, repr=False)
    priority: int = DownloadPriority.NORMAL
    priority_boost: int = 0
    enqueued_at: float = field(default_factory=time.monotonic)

    task_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    url: str = ""
    output_path: str = ""
    filename: str = ""
    headers: Dict[str, str] = field(default_factory=dict)
    resume_from: int = 0
    checksum: str = ""
    checksum_algo: str = "sha256"
    session: Optional[str] = None
    _status: DownloadStatus = DownloadStatus.PENDING
    platform_hint: str = ""
    agent_hint: str = ""
    scheduled_at: Optional[str] = None
    max_retries: int = 3
    retry_delay: float = 2.0
    tags: List[str] = field(default_factory=list)
    callback_url: str = ""
    chunk_ranges: List[Tuple[int, int]] = field(default_factory=list)
    etag: str = ""
    last_modified: str = ""

    def __post_init__(self) -> None:
        """Calculate the sort key from priority and enqueue time."""
        effective_priority = max(0, self.priority - self.priority_boost)
        self.sort_key = (effective_priority, self.enqueued_at)

    @property
    def status(self) -> DownloadStatus:
        """Get the task status."""
        return self._status

    @status.setter
    def status(self, value: DownloadStatus) -> None:
        """Set the task status."""
        self._status = value

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (excluding non-serializable fields)."""
        return {
            "task_id": self.task_id,
            "url": self.url,
            "output_path": self.output_path,
            "filename": self.filename,
            "headers": self.headers,
            "resume_from": self.resume_from,
            "checksum": self.checksum,
            "checksum_algo": self.checksum_algo,
            "priority": self.priority,
            "priority_boost": self.priority_boost,
            "status": self._status.value,
            "platform_hint": self.platform_hint,
            "agent_hint": self.agent_hint,
            "scheduled_at": self.scheduled_at,
            "max_retries": self.max_retries,
            "retry_delay": self.retry_delay,
            "tags": self.tags,
            "callback_url": self.callback_url,
            "etag": self.etag,
            "last_modified": self.last_modified,
        }


# ---------------------------------------------------------------------------
# ProgressCallback Protocol
# ---------------------------------------------------------------------------

class ProgressCallback(Protocol):
    """Protocol for download progress callbacks."""
    def __call__(self, task_id: str, downloaded: int, total: int, speed: float, eta: float) -> None:
        ...


# ---------------------------------------------------------------------------
# MIME type / extension maps
# ---------------------------------------------------------------------------

_MIME_TO_EXT: Dict[str, str] = {
    "application/octet-stream": ".bin",
    "application/pdf": ".pdf",
    "application/zip": ".zip",
    "application/x-rar-compressed": ".rar",
    "application/x-7z-compressed": ".7z",
    "application/x-tar": ".tar",
    "application/gzip": ".gz",
    "application/x-bzip2": ".bz2",
    "application/x-xz": ".xz",
    "application/json": ".json",
    "application/xml": ".xml",
    "application/javascript": ".js",
    "application/xhtml+xml": ".xhtml",
    "application/atom+xml": ".atom",
    "application/rss+xml": ".rss",
    "application/vnd.ms-excel": ".xls",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
    "application/vnd.ms-powerpoint": ".ppt",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/x-shockwave-flash": ".swf",
    "application/java-archive": ".jar",
    "application/x-android-dex": ".dex",
    "application/vnd.android.package-archive": ".apk",
    "application/x-apple-diskimage": ".dmg",
    "application/x-debian-package": ".deb",
    "application/x-redhat-package-manager": ".rpm",
    "application/x-iso9660-image": ".iso",
    "text/html": ".html",
    "text/plain": ".txt",
    "text/css": ".css",
    "text/csv": ".csv",
    "text/xml": ".xml",
    "text/markdown": ".md",
    "text/javascript": ".js",
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/svg+xml": ".svg",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/x-icon": ".ico",
    "image/avif": ".avif",
    "image/heic": ".heic",
    "image/heif": ".heif",
    "audio/mpeg": ".mp3",
    "audio/ogg": ".ogg",
    "audio/wav": ".wav",
    "audio/flac": ".flac",
    "audio/aac": ".aac",
    "audio/mp4": ".m4a",
    "audio/webm": ".weba",
    "audio/x-m4a": ".m4a",
    "audio/x-wav": ".wav",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
    "video/x-msvideo": ".avi",
    "video/x-matroska": ".mkv",
    "video/quicktime": ".mov",
    "video/x-ms-wmv": ".wmv",
    "video/x-flv": ".flv",
    "video/mpeg": ".mpeg",
    "video/3gpp": ".3gp",
    "video/mp2t": ".ts",
    "video/x-m4v": ".m4v",
    "font/woff": ".woff",
    "font/woff2": ".woff2",
    "font/ttf": ".ttf",
    "font/otf": ".otf",
}

_EXT_TO_MIME: Dict[str, str] = {v: k for k, v in _MIME_TO_EXT.items()}


def detect_content_type(
    url: str = "",
    filename: str = "",
    headers: Optional[Dict[str, str]] = None,
    content: Optional[bytes] = None,
) -> str:
    """
    Detect content type from URL, filename, headers, or content magic bytes.

    Args:
        url: URL to extract extension from.
        filename: Filename to extract extension from.
        headers: HTTP headers (checks Content-Type).
        content: First bytes of content for magic detection.

    Returns:
        MIME type string.
    """
    # 1. Check headers
    if headers:
        ct = headers.get("Content-Type", "").split(";")[0].strip().lower()
        if ct and ct != "application/octet-stream":
            return ct

    # 2. Check filename extension
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in _EXT_TO_MIME:
            return _EXT_TO_MIME[ext]

    # 3. Check URL path extension
    if url:
        from urllib.parse import urlparse
        path = urlparse(url).path
        ext = Path(path).suffix.lower()
        if ext in _EXT_TO_MIME:
            return _EXT_TO_MIME[ext]

    # 4. Magic bytes detection
    if content and len(content) >= 4:
        magic_signatures = {
            b"\x89PNG": "image/png",
            b"\xff\xd8\xff": "image/jpeg",
            b"GIF8": "image/gif",
            b"PK\x03\x04": "application/zip",
            b"\x1f\x8b": "application/gzip",
            b"Rar!": "application/x-rar-compressed",
            b"\x7fELF": "application/octet-stream",
            b"ID3": "audio/mpeg",
            b"\xff\xfb": "audio/mpeg",
            b"\x00\x00\x00\x1c": "video/mp4",
            b"\x00\x00\x00\x20": "video/mp4",
            b"ftyp": "video/mp4",  # MP4 ftyp box (offset varies)
        }
        for magic, mime in magic_signatures.items():
            if content.startswith(magic):
                return mime
        # Check for ftyp in first 12 bytes (MP4/MOV)
        if len(content) >= 12 and b"ftyp" in content[:12]:
            return "video/mp4"

    return "application/octet-stream"


def suggest_filename(
    url: str = "",
    content_type: str = "",
    content_disposition: str = "",
    default_name: str = "download",
) -> str:
    """
    Suggest a filename from URL, Content-Type, or Content-Disposition.

    Args:
        url: URL to extract filename from.
        content_type: MIME type to suggest extension.
        content_disposition: Content-Disposition header value.
        default_name: Default name if nothing can be determined.

    Returns:
        Suggested filename string.
    """
    # 1. Try Content-Disposition
    if content_disposition:
        # Parse filename from Content-Disposition
        patterns = [
            r'filename\*?=(?:UTF-8\'\')?["\']?([^;"\'\n]+)["\']?',
            r'filename\s*=\s*["\']([^"\']+)["\']',
            r'filename\s*=\s*([^\s;]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, content_disposition, re.IGNORECASE)
            if match:
                name = match.group(1).strip()
                # URL-decode if needed
                if "%" in name:
                    try:
                        from urllib.parse import unquote
                        name = unquote(name)
                    except Exception:
                        pass
                if name:
                    # Sanitize
                    name = re.sub(r'[<>:"|?*\\]', '_', name)
                    return name

    # 2. Try URL path
    if url:
        from urllib.parse import urlparse, unquote
        path = unquote(urlparse(url).path)
        if path and "/" in path:
            name = path.rsplit("/", 1)[-1]
            if name and "." in name:
                return re.sub(r'[<>:"|?*\\]', '_', name)

    # 3. Use content type to add extension
    ext = _MIME_TO_EXT.get(content_type, "")
    return f"{default_name}{ext}"


# ---------------------------------------------------------------------------
# DownloadQueue
# ---------------------------------------------------------------------------

class DownloadQueue:
    """
    Thread-safe priority queue for download tasks.

    Uses a heap internally for efficient priority ordering.
    Supports put, get, peek, drain, size_by_priority, cancel_all,
    remove, clear, reorder, get_by_tag, get_by_platform.
    """

    def __init__(self, max_size: int = 0) -> None:
        """
        Args:
            max_size: Maximum queue size (0 = unlimited).
        """
        self.max_size = max_size
        self._heap: List[DownloadTask] = []
        self._tasks: Dict[str, DownloadTask] = {}
        self._lock = threading.Lock()
        self._not_empty = threading.Condition(self._lock)
        self._not_full = threading.Condition(self._lock)

    def put(self, task: DownloadTask, block: bool = True, timeout: float = 0.0) -> None:
        """
        Add a task to the priority queue.

        Args:
            task: DownloadTask to add.
            block: Whether to block if queue is full.
            timeout: Timeout for blocking.

        Raises:
            QueueFullError: If queue is full and block=False.
        """
        with self._not_full:
            if self.max_size > 0:
                if len(self._heap) >= self.max_size:
                    if not block:
                        raise QueueFullError(f"Queue is full (max_size={self.max_size})")
                    self._not_full.wait(timeout)
                    if len(self._heap) >= self.max_size:
                        raise QueueFullError(f"Queue is full after waiting")
            self._heap.append(task)
            heapq.heapify(self._heap)
            self._tasks[task.task_id] = task
            task.status = DownloadStatus.QUEUED
            self._not_empty.notify()

    def get(self, block: bool = True, timeout: float = 0.0) -> DownloadTask:
        """
        Get the highest-priority task from the queue.

        Args:
            block: Whether to block if queue is empty.
            timeout: Timeout for blocking.

        Returns:
            The highest-priority DownloadTask.

        Raises:
            QueueEmptyError: If queue is empty and block=False.
        """
        with self._not_empty:
            if not self._heap:
                if not block:
                    raise QueueEmptyError("Queue is empty")
                self._not_empty.wait(timeout)
                if not self._heap:
                    raise QueueEmptyError("Queue is empty after waiting")
            task = heapq.heappop(self._heap)
            self._tasks.pop(task.task_id, None)
            return task

    def peek(self) -> Optional[DownloadTask]:
        """Peek at the highest-priority task without removing it."""
        with self._lock:
            return self._heap[0] if self._heap else None

    def peek_priority(self) -> Optional[int]:
        """Peek at the priority of the highest-priority task."""
        with self._lock:
            if self._heap:
                return self._heap[0].priority
            return None

    def drain(self, max_count: int = 0) -> List[DownloadTask]:
        """
        Drain all tasks from the queue.

        Args:
            max_count: Maximum number of tasks to drain (0 = all).

        Returns:
            List of drained tasks in priority order.
        """
        with self._lock:
            count = min(max_count, len(self._heap)) if max_count > 0 else len(self._heap)
            tasks = []
            for _ in range(count):
                if self._heap:
                    task = heapq.heappop(self._heap)
                    self._tasks.pop(task.task_id, None)
                    tasks.append(task)
            return tasks

    def size_by_priority(self, priority: int) -> int:
        """Count tasks with a specific priority level."""
        with self._lock:
            return sum(1 for t in self._heap if t.priority == priority)

    def cancel_all(self) -> int:
        """Cancel all tasks in the queue. Returns count cancelled."""
        with self._lock:
            count = len(self._heap)
            for task in self._heap:
                task.status = DownloadStatus.CANCELLED
            self._heap.clear()
            self._tasks.clear()
            return count

    def remove(self, task_id: str) -> bool:
        """Remove a specific task by task_id."""
        with self._lock:
            if task_id not in self._tasks:
                return False
            task = self._tasks.pop(task_id)
            try:
                self._heap.remove(task)
                heapq.heapify(self._heap)
            except ValueError:
                pass
            task.status = DownloadStatus.CANCELLED
            return True

    @property
    def size(self) -> int:
        """Current queue size."""
        with self._lock:
            return len(self._heap)

    def clear(self) -> int:
        """Clear all tasks. Returns count cleared."""
        with self._lock:
            count = len(self._heap)
            self._heap.clear()
            self._tasks.clear()
            return count

    def reorder(self) -> None:
        """Re-sort the queue (e.g., after priority changes)."""
        with self._lock:
            for task in self._heap:
                task.__post_init__()
            heapq.heapify(self._heap)

    def get_by_tag(self, tag: str) -> List[DownloadTask]:
        """Get all tasks with a specific tag."""
        with self._lock:
            return [t for t in self._heap if tag in t.tags]

    def get_by_platform(self, platform: str) -> List[DownloadTask]:
        """Get all tasks with a specific platform hint."""
        with self._lock:
            return [t for t in self._heap if t.platform_hint == platform]

    def __len__(self) -> int:
        return self.size

    def __contains__(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._tasks


# ---------------------------------------------------------------------------
# DownloadSpeedTracker
# ---------------------------------------------------------------------------

class DownloadSpeedTracker:
    """
    Thread-safe download speed tracker with moving average,
    min, max, current, median, p95, p99 speeds.
    Uses window-based sampling.
    """

    def __init__(
        self,
        window_size: int = 100,
        sample_interval: float = 0.5,
    ) -> None:
        self.window_size = window_size
        self.sample_interval = sample_interval
        self._samples: Deque[Tuple[float, int]] = deque(maxlen=window_size)
        self._speeds: Deque[float] = deque(maxlen=window_size)
        self._lock = threading.Lock()
        self._last_sample_time = 0.0
        self._last_bytes = 0
        self._total_bytes = 0
        self._start_time = 0.0

    def start(self) -> None:
        """Start tracking."""
        with self._lock:
            self._start_time = time.monotonic()
            self._last_sample_time = self._start_time
            self._last_bytes = 0
            self._total_bytes = 0
            self._samples.clear()
            self._speeds.clear()

    def update(self, downloaded_bytes: int) -> None:
        """
        Update with current downloaded bytes.

        Calculates speed from the delta since last sample.
        """
        now = time.monotonic()
        with self._lock:
            elapsed = now - self._last_sample_time
            if elapsed < self.sample_interval:
                return
            delta_bytes = downloaded_bytes - self._last_bytes
            speed = delta_bytes / elapsed if elapsed > 0 else 0.0
            self._speeds.append(speed)
            self._samples.append((now, downloaded_bytes))
            self._last_sample_time = now
            self._last_bytes = downloaded_bytes
            self._total_bytes = downloaded_bytes

    @property
    def current_speed(self) -> float:
        """Get the most recent speed sample (bytes/sec)."""
        with self._lock:
            return self._speeds[-1] if self._speeds else 0.0

    @property
    def average_speed(self) -> float:
        """Get the moving average speed (bytes/sec)."""
        with self._lock:
            if not self._speeds:
                return 0.0
            return sum(self._speeds) / len(self._speeds)

    @property
    def min_speed(self) -> float:
        """Get the minimum recorded speed."""
        with self._lock:
            return min(self._speeds) if self._speeds else 0.0

    @property
    def max_speed(self) -> float:
        """Get the maximum recorded speed."""
        with self._lock:
            return max(self._speeds) if self._speeds else 0.0

    @property
    def median_speed(self) -> float:
        """Get the median speed."""
        with self._lock:
            return self._percentile(list(self._speeds), 0.5)

    @property
    def p95_speed(self) -> float:
        """Get the 95th percentile speed."""
        with self._lock:
            return self._percentile(list(self._speeds), 0.95)

    @property
    def p99_speed(self) -> float:
        """Get the 99th percentile speed."""
        with self._lock:
            return self._percentile(list(self._speeds), 0.99)

    @property
    def total_bytes(self) -> int:
        """Total bytes downloaded."""
        return self._total_bytes

    def _percentile(self, data: List[float], pct: float) -> float:
        """Calculate percentile from data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * pct)
        idx = min(idx, len(sorted_data) - 1)
        return sorted_data[idx]

    def get_stats(self) -> Dict[str, float]:
        """Get all speed statistics."""
        return {
            "current_kbps": self.current_speed / 1024,
            "average_kbps": self.average_speed / 1024,
            "min_kbps": self.min_speed / 1024,
            "max_kbps": self.max_speed / 1024,
            "median_kbps": self.median_speed / 1024,
            "p95_kbps": self.p95_speed / 1024,
            "p99_kbps": self.p99_speed / 1024,
            "total_bytes": self._total_bytes,
            "sample_count": len(self._speeds),
        }

    def reset(self) -> None:
        """Reset the tracker."""
        with self._lock:
            self._samples.clear()
            self._speeds.clear()
            self._total_bytes = 0
            self._last_bytes = 0
            self._start_time = 0.0


# ---------------------------------------------------------------------------
# DownloadScheduler
# ---------------------------------------------------------------------------

class DownloadScheduler:
    """
    Cron-based download scheduler with one-off and recurring tasks.

    Parses cron expressions and dispatches tasks to a queue on schedule.
    Runs a background thread for timing.
    """

    # Cron field names
    FIELDS = ["minute", "hour", "day_of_month", "month", "day_of_week"]

    def __init__(
        self,
        queue: Optional[DownloadQueue] = None,
        check_interval: float = 60.0,
    ) -> None:
        self.queue = queue
        self.check_interval = check_interval
        self._schedules: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def parse_cron(self, expr: str) -> Dict[str, List[int]]:
        """
        Parse a cron expression into a dict of field → list of values.

        Format: minute hour day_of_month month day_of_week
        Supports: *, */n, n-m, n,m,o

        Args:
            expr: Cron expression string.

        Returns:
            Dict mapping field names to lists of integer values.
        """
        parts = expr.strip().split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron expression (expected 5 fields): {expr}")

        ranges = {
            "minute": (0, 59),
            "hour": (0, 23),
            "day_of_month": (1, 31),
            "month": (1, 12),
            "day_of_week": (0, 6),
        }

        result: Dict[str, List[int]] = {}
        for i, field_name in enumerate(self.FIELDS):
            low, high = ranges[field_name]
            result[field_name] = self._parse_field(parts[i], low, high)
        return result

    def _parse_field(self, field: str, low: int, high: int) -> List[int]:
        """Parse a single cron field."""
        values: Set[int] = set()
        for part in field.split(","):
            if part == "*":
                values.update(range(low, high + 1))
            elif part.startswith("*/"):
                step = int(part[2:])
                values.update(range(low, high + 1, step))
            elif "-" in part:
                parts = part.split("-")
                start, end = int(parts[0]), int(parts[1])
                values.update(range(start, end + 1))
            else:
                values.add(int(part))
        return sorted(v for v in values if low <= v <= high)

    def should_run(self, cron_dict: Dict[str, List[int]], dt: Optional[datetime] = None) -> bool:
        """Check if the current time matches the cron schedule."""
        now = dt or datetime.now()
        return (
            now.minute in cron_dict["minute"]
            and now.hour in cron_dict["hour"]
            and now.day in cron_dict["day_of_month"]
            and now.month in cron_dict["month"]
            and now.weekday() in cron_dict["day_of_week"]
        )

    def add_schedule(
        self,
        name: str,
        cron_expr: str,
        url: str,
        agent_hint: str = "",
        platform_hint: str = "",
        priority: int = DownloadPriority.NORMAL,
        tags: Optional[List[str]] = None,
        enabled: bool = True,
    ) -> str:
        """Add a recurring schedule."""
        cron_dict = self.parse_cron(cron_expr)
        schedule_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._schedules[schedule_id] = {
                "id": schedule_id,
                "name": name,
                "cron_expr": cron_expr,
                "cron_dict": cron_dict,
                "url": url,
                "agent_hint": agent_hint,
                "platform_hint": platform_hint,
                "priority": priority,
                "tags": tags or [],
                "enabled": enabled,
                "type": "recurring",
                "last_run": None,
                "next_run": None,
                "run_count": 0,
            }
        logger.info("Schedule added: %s (%s) - %s", name, schedule_id, cron_expr)
        return schedule_id

    def add_one_off(
        self,
        name: str,
        run_at: datetime,
        url: str,
        agent_hint: str = "",
        platform_hint: str = "",
        priority: int = DownloadPriority.HIGH,
        tags: Optional[List[str]] = None,
    ) -> str:
        """Add a one-off scheduled download."""
        schedule_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._schedules[schedule_id] = {
                "id": schedule_id,
                "name": name,
                "cron_expr": "",
                "cron_dict": None,
                "run_at": run_at.isoformat(),
                "url": url,
                "agent_hint": agent_hint,
                "platform_hint": platform_hint,
                "priority": priority,
                "tags": tags or [],
                "enabled": True,
                "type": "one_off",
                "last_run": None,
                "next_run": run_at.isoformat(),
                "run_count": 0,
            }
        return schedule_id

    def remove_schedule(self, schedule_id: str) -> bool:
        """Remove a schedule."""
        with self._lock:
            return self._schedules.pop(schedule_id, None) is not None

    def enable_schedule(self, schedule_id: str) -> bool:
        """Enable a schedule."""
        with self._lock:
            if schedule_id in self._schedules:
                self._schedules[schedule_id]["enabled"] = True
                return True
            return False

    def disable_schedule(self, schedule_id: str) -> bool:
        """Disable a schedule."""
        with self._lock:
            if schedule_id in self._schedules:
                self._schedules[schedule_id]["enabled"] = False
                return True
            return False

    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all schedules."""
        with self._lock:
            return [
                {k: v for k, v in s.items() if k != "cron_dict"}
                for s in self._schedules.values()
            ]

    def _dispatch_task(self, schedule: Dict[str, Any]) -> None:
        """Create a DownloadTask from a schedule and add it to the queue."""
        task = DownloadTask(
            url=schedule["url"],
            platform_hint=schedule.get("platform_hint", ""),
            agent_hint=schedule.get("agent_hint", ""),
            priority=schedule.get("priority", DownloadPriority.NORMAL),
            tags=schedule.get("tags", []),
        )
        if self.queue:
            self.queue.put(task)
            logger.info("Scheduled task dispatched: %s (%s)", schedule["name"], task.task_id)

    def start(self) -> None:
        """Start the scheduler background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._scheduler_loop,
            name="download_scheduler",
            daemon=True,
        )
        self._thread.start()
        logger.info("Download scheduler started")

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10.0)
        logger.info("Download scheduler stopped")

    def _scheduler_loop(self) -> None:
        """Main scheduler loop."""
        last_minute = -1
        while self._running:
            now = datetime.now()
            current_minute = now.minute

            if current_minute != last_minute:
                last_minute = current_minute
                with self._lock:
                    for sid, schedule in self._schedules.items():
                        if not schedule["enabled"]:
                            continue
                        if schedule["type"] == "recurring" and schedule.get("cron_dict"):
                            if self.should_run(schedule["cron_dict"], now):
                                self._dispatch_task(schedule)
                                schedule["last_run"] = now.isoformat()
                                schedule["run_count"] = schedule.get("run_count", 0) + 1
                        elif schedule["type"] == "one_off":
                            run_at_str = schedule.get("run_at")
                            if run_at_str:
                                try:
                                    run_at = datetime.fromisoformat(run_at_str)
                                    if now >= run_at and schedule.get("run_count", 0) == 0:
                                        self._dispatch_task(schedule)
                                        schedule["last_run"] = now.isoformat()
                                        schedule["run_count"] = 1
                                except (ValueError, TypeError):
                                    pass

            time.sleep(self.check_interval)


# ---------------------------------------------------------------------------
# DownloadLifecycle
# ---------------------------------------------------------------------------

class DownloadLifecycle:
    """
    State machine for download lifecycle with 13 states.

    Validates all state transitions and tracks history
    with timestamps and time-in-state metrics.
    """

    # Valid state transitions
    TRANSITIONS: Dict[DownloadStatus, Set[DownloadStatus]] = {
        DownloadStatus.PENDING: {DownloadStatus.SCHEDULING, DownloadStatus.CANCELLED},
        DownloadStatus.SCHEDULING: {DownloadStatus.QUEUED, DownloadStatus.FAILED, DownloadStatus.CANCELLED},
        DownloadStatus.QUEUED: {DownloadStatus.DOWNLOADING, DownloadStatus.CANCELLED, DownloadStatus.FAILED},
        DownloadStatus.DOWNLOADING: {
            DownloadStatus.PAUSED, DownloadStatus.VERIFYING,
            DownloadStatus.FAILED, DownloadStatus.CANCELLED, DownloadStatus.RETRYING,
        },
        DownloadStatus.PAUSED: {DownloadStatus.DOWNLOADING, DownloadStatus.CANCELLED, DownloadStatus.FAILED},
        DownloadStatus.VERIFYING: {
            DownloadStatus.EXTRACTING, DownloadStatus.COMPLETED,
            DownloadStatus.FAILED, DownloadStatus.RETRYING,
        },
        DownloadStatus.EXTRACTING: {
            DownloadStatus.CONVERTING, DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
        },
        DownloadStatus.CONVERTING: {DownloadStatus.UPLOADING, DownloadStatus.COMPLETED, DownloadStatus.FAILED},
        DownloadStatus.UPLOADING: {DownloadStatus.COMPLETED, DownloadStatus.FAILED},
        DownloadStatus.COMPLETED: set(),  # Terminal state
        DownloadStatus.FAILED: {DownloadStatus.RETRYING, DownloadStatus.CANCELLED},
        DownloadStatus.CANCELLED: set(),  # Terminal state
        DownloadStatus.RETRYING: {DownloadStatus.QUEUED, DownloadStatus.FAILED, DownloadStatus.CANCELLED},
    }

    def __init__(self, task_id: str = "") -> None:
        self.task_id = task_id
        self._current = DownloadStatus.PENDING
        self._history: List[Dict[str, Any]] = [
            {"state": DownloadStatus.PENDING.value, "entered_at": time.monotonic(), "timestamp": datetime.now(tz=timezone.utc).isoformat()}
        ]
        self._lock = threading.Lock()

    @property
    def current(self) -> DownloadStatus:
        """Current state."""
        return self._current

    def transition(self, new_state: DownloadStatus) -> None:
        """
        Transition to a new state.

        Args:
            new_state: Target state.

        Raises:
            LifecycleError: If the transition is not valid.
        """
        with self._lock:
            if new_state not in self.TRANSITIONS.get(self._current, set()):
                raise LifecycleError(
                    f"Invalid transition: {self._current.value} → {new_state.value} "
                    f"(task: {self.task_id})"
                )
            now_mono = time.monotonic()
            now_iso = datetime.now(tz=timezone.utc).isoformat()

            # Record exit from current state
            if self._history:
                last = self._history[-1]
                last["exited_at"] = now_mono
                last["duration"] = now_mono - last["entered_at"]

            self._current = new_state
            self._history.append({
                "state": new_state.value,
                "entered_at": now_mono,
                "timestamp": now_iso,
            })

    def can_transition(self, new_state: DownloadStatus) -> bool:
        """Check if a transition to new_state is valid."""
        return new_state in self.TRANSITIONS.get(self._current, set())

    def get_history(self) -> List[Dict[str, Any]]:
        """Get full state transition history."""
        with self._lock:
            return list(self._history)

    def time_in_state(self, state: DownloadStatus) -> float:
        """Get total time spent in a specific state (seconds)."""
        with self._lock:
            total = 0.0
            for entry in self._history:
                if entry["state"] == state.value:
                    duration = entry.get("duration", 0.0)
                    if duration == 0.0 and "exited_at" not in entry:
                        # Still in this state
                        duration = time.monotonic() - entry["entered_at"]
                    total += duration
            return total

    def time_in_current_state(self) -> float:
        """Get time spent in the current state."""
        with self._lock:
            if self._history:
                last = self._history[-1]
                return time.monotonic() - last["entered_at"]
            return 0.0

    @property
    def is_terminal(self) -> bool:
        """Check if the current state is terminal (COMPLETED, FAILED, CANCELLED)."""
        return self._current in (DownloadStatus.COMPLETED, DownloadStatus.FAILED, DownloadStatus.CANCELLED)

    def reset(self) -> None:
        """Reset the lifecycle to PENDING."""
        with self._lock:
            self._current = DownloadStatus.PENDING
            self._history = [
                {"state": DownloadStatus.PENDING.value, "entered_at": time.monotonic(),
                 "timestamp": datetime.now(tz=timezone.utc).isoformat()}
            ]


# ---------------------------------------------------------------------------
# AgentSkill
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AgentSkill:
    """Describes an agent's capabilities.

    Supports both core field names and common aliases:
    - name → mapped to platform (for backward compatibility)
    - supported_formats → mapped to formats
    - supported_qualities → mapped to qualities
    """
    platform: str = ""
    formats: Tuple[str, ...] = ()
    qualities: Tuple[str, ...] = ()
    features: Tuple[str, ...] = ()
    max_concurrent: int = 3
    priority: int = 5
    version: str = "1.0.0"
    description: str = ""

    def __init__(self, platform: str = "", formats: Tuple[str, ...] = (),
                 qualities: Tuple[str, ...] = (), features: Tuple[str, ...] = (),
                 max_concurrent: int = 3, priority: int = 5,
                 version: str = "1.0.0", description: str = "",
                 # Aliases for backward compatibility with agents
                 name: str = "",
                 supported_formats = None,
                 supported_qualities = None) -> None:
        # Map aliases to canonical fields
        effective_platform = platform or name
        effective_formats = formats if supported_formats is None else tuple(supported_formats) if not isinstance(supported_formats, tuple) else supported_formats
        effective_qualities = qualities if supported_qualities is None else tuple(supported_qualities) if not isinstance(supported_qualities, tuple) else supported_qualities

        object.__setattr__(self, 'platform', effective_platform)
        object.__setattr__(self, 'formats', effective_formats)
        object.__setattr__(self, 'qualities', effective_qualities)
        object.__setattr__(self, 'features', features)
        object.__setattr__(self, 'max_concurrent', max_concurrent)
        object.__setattr__(self, 'priority', priority)
        object.__setattr__(self, 'version', version)
        object.__setattr__(self, 'description', description)


# ---------------------------------------------------------------------------
# AgentMemory
# ---------------------------------------------------------------------------

class AgentMemory:
    """
    Per-agent persistent JSON store with CRUD operations.
    Thread-safe with auto-persist to disk.
    """

    def __init__(
        self,
        agent_name: str,
        memory_dir: Union[str, Path] = "agent_memory",
        auto_persist: bool = True,
    ) -> None:
        self.agent_name = agent_name
        self.memory_dir = Path(memory_dir)
        self.auto_persist = auto_persist
        self._data: Dict[str, Any] = {}
        self._instructions: Dict[str, str] = {}
        self._lock = threading.Lock()
        self._memory_file = self.memory_dir / f"{agent_name}_memory.json"
        self._load()

    def _load(self) -> None:
        """Load memory from disk."""
        if self._memory_file.exists():
            try:
                with open(self._memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._data = data.get("data", {})
                self._instructions = data.get("instructions", {})
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load agent memory for %s: %s", self.agent_name, e)

    def _persist(self) -> None:
        """Persist memory to disk."""
        if not self.auto_persist:
            return
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        try:
            with open(self._memory_file, "w", encoding="utf-8") as f:
                json.dump({
                    "agent": self.agent_name,
                    "data": self._data,
                    "instructions": self._instructions,
                    "updated_at": datetime.now(tz=timezone.utc).isoformat(),
                }, f, indent=2, ensure_ascii=False, default=str)
        except OSError as e:
            logger.error("Failed to persist agent memory for %s: %s", self.agent_name, e)

    # Data CRUD

    def get(self, key: str, default: Any = None) -> Any:
        """Get a data value by key."""
        with self._lock:
            return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a data value."""
        with self._lock:
            self._data[key] = value
            self._persist()

    def delete(self, key: str) -> bool:
        """Delete a data key."""
        with self._lock:
            if key in self._data:
                del self._data[key]
                self._persist()
                return True
            return False

    def get_all_data(self) -> Dict[str, Any]:
        """Get all stored data."""
        with self._lock:
            return dict(self._data)

    def clear_data(self) -> None:
        """Clear all data."""
        with self._lock:
            self._data.clear()
            self._persist()

    # Instructions CRUD

    def get_instruction(self, key: str, default: str = "") -> str:
        """Get an instruction by key."""
        with self._lock:
            return self._instructions.get(key, default)

    def set_instruction(self, key: str, value: str) -> None:
        """Set an instruction."""
        with self._lock:
            self._instructions[key] = value
            self._persist()

    def delete_instruction(self, key: str) -> bool:
        """Delete an instruction."""
        with self._lock:
            if key in self._instructions:
                del self._instructions[key]
                self._persist()
                return True
            return False

    def get_all_instructions(self) -> Dict[str, str]:
        """Get all instructions."""
        with self._lock:
            return dict(self._instructions)


# ---------------------------------------------------------------------------
# AgentRegistry
# ---------------------------------------------------------------------------

class AgentRegistry:
    """
    Registry for download agents.

    Register/unregister agents, find by platform/format/feature/quality,
    best-for-task selection, and agent listing.
    """

    def __init__(self) -> None:
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    def register(
        self,
        name: str,
        skill: AgentSkill,
        downloader: Optional[Any] = None,
    ) -> None:
        """Register an agent with its skill description and optional downloader instance."""
        with self._lock:
            self._agents[name] = {
                "name": name,
                "skill": skill,
                "downloader": downloader,
                "registered_at": datetime.now(tz=timezone.utc).isoformat(),
            }
        logger.info("Agent registered: %s (platform: %s)", name, skill.platform)

    def unregister(self, name: str) -> bool:
        """Unregister an agent."""
        with self._lock:
            if name in self._agents:
                del self._agents[name]
                logger.info("Agent unregistered: %s", name)
                return True
            return False

    def get(self, name: str) -> Optional[Dict[str, Any]]:
        """Get agent info by name."""
        with self._lock:
            return self._agents.get(name)

    def find_by_platform(self, platform: str) -> List[Dict[str, Any]]:
        """Find all agents supporting a platform."""
        with self._lock:
            return [
                info for info in self._agents.values()
                if info["skill"].platform.lower() == platform.lower()
            ]

    def find_by_format(self, fmt: str) -> List[Dict[str, Any]]:
        """Find all agents supporting a format."""
        with self._lock:
            fmt_lower = fmt.lower()
            return [
                info for info in self._agents.values()
                if fmt_lower in [f.lower() for f in info["skill"].formats]
            ]

    def find_by_feature(self, feature: str) -> List[Dict[str, Any]]:
        """Find all agents with a specific feature."""
        with self._lock:
            feature_lower = feature.lower()
            return [
                info for info in self._agents.values()
                if feature_lower in [f.lower() for f in info["skill"].features]
            ]

    def find_by_quality(self, quality: str) -> List[Dict[str, Any]]:
        """Find all agents supporting a quality level."""
        with self._lock:
            quality_lower = quality.lower()
            return [
                info for info in self._agents.values()
                if quality_lower in [q.lower() for q in info["skill"].qualities]
            ]

    def find_best_for_task(self, task: DownloadTask) -> Optional[Dict[str, Any]]:
        """
        Find the best agent for a given download task.

        Selection criteria:
        1. Platform match
        2. Agent hint match (if provided)
        3. Priority (lower = better)
        4. Feature coverage

        Args:
            task: DownloadTask to find an agent for.

        Returns:
            Best matching agent info, or None.
        """
        with self._lock:
            candidates = list(self._agents.values())

            # Filter by agent hint
            if task.agent_hint:
                hinted = [a for a in candidates if a["name"] == task.agent_hint]
                if hinted:
                    return hinted[0]

            # Filter by platform
            if task.platform_hint:
                platform_matches = [
                    a for a in candidates
                    if a["skill"].platform.lower() == task.platform_hint.lower()
                ]
                if platform_matches:
                    candidates = platform_matches

            if not candidates:
                return None

            # Sort by priority (lower = better)
            candidates.sort(key=lambda a: a["skill"].priority)
            return candidates[0]

    @property
    def agent_count(self) -> int:
        """Number of registered agents."""
        return len(self._agents)

    def list_all(self) -> List[Dict[str, Any]]:
        """List all registered agents."""
        with self._lock:
            return [
                {
                    "name": info["name"],
                    "platform": info["skill"].platform,
                    "formats": list(info["skill"].formats),
                    "qualities": list(info["skill"].qualities),
                    "features": list(info["skill"].features),
                    "max_concurrent": info["skill"].max_concurrent,
                    "priority": info["skill"].priority,
                    "version": info["skill"].version,
                }
                for info in self._agents.values()
            ]


# ---------------------------------------------------------------------------
# DownloadEventEmitter
# ---------------------------------------------------------------------------

class DownloadEventEmitter:
    """
    Event system for download lifecycle notifications.

    Supports 15+ event types, wildcard listeners, and async emit.
    """

    EVENT_TYPES = [
        "on_start", "on_progress", "on_complete", "on_error",
        "on_pause", "on_resume", "on_cancel", "on_scheduled",
        "on_verify", "on_extract", "on_convert", "on_upload",
        "on_retry", "on_speed_change", "on_bandwidth_limit",
    ]

    def __init__(self) -> None:
        self._listeners: Dict[str, List[Callable[..., Any]]] = defaultdict(list)
        self._wildcard_listeners: List[Callable[..., Any]] = []
        self._lock = threading.Lock()

    def on(self, event: str, callback: Callable[..., Any]) -> None:
        """
        Register a listener for an event.

        Args:
            event: Event name (e.g., 'on_complete') or '*' for all events.
            callback: Callback function.
        """
        with self._lock:
            if event == "*":
                self._wildcard_listeners.append(callback)
            else:
                self._listeners[event].append(callback)

    def off(self, event: str, callback: Callable[..., Any]) -> None:
        """Remove a listener."""
        with self._lock:
            if event == "*":
                if callback in self._wildcard_listeners:
                    self._wildcard_listeners.remove(callback)
            elif event in self._listeners and callback in self._listeners[event]:
                self._listeners[event].remove(callback)

    def once(self, event: str, callback: Callable[..., Any]) -> None:
        """Register a one-time listener."""
        def wrapper(*args: Any, **kwargs: Any) -> None:
            self.off(event, wrapper)
            callback(*args, **kwargs)
        self.on(event, wrapper)

    def emit(self, event: str, *args: Any, **kwargs: Any) -> int:
        """
        Emit an event to all registered listeners.

        Args:
            event: Event name.
            *args: Positional arguments for callbacks.
            **kwargs: Keyword arguments for callbacks.

        Returns:
            Number of listeners called.
        """
        with self._lock:
            listeners = self._listeners.get(event, [])[:]
            wildcards = self._wildcard_listeners[:]

        count = 0
        for callback in listeners + wildcards:
            try:
                callback(event, *args, **kwargs)
                count += 1
            except Exception as e:
                logger.error("Event listener error for %s: %s", event, e)
        return count

    async def emit_async(self, event: str, *args: Any, **kwargs: Any) -> int:
        """
        Async version of emit. Calls listeners as coroutines if possible.

        Returns:
            Number of listeners called.
        """
        with self._lock:
            listeners = self._listeners.get(event, [])[:]
            wildcards = self._wildcard_listeners[:]

        count = 0
        for callback in listeners + wildcards:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event, *args, **kwargs)
                else:
                    callback(event, *args, **kwargs)
                count += 1
            except Exception as e:
                logger.error("Async event listener error for %s: %s", event, e)
        return count

    def listener_count(self, event: str) -> int:
        """Get the number of listeners for an event."""
        with self._lock:
            return len(self._listeners.get(event, [])) + len(self._wildcard_listeners)

    def remove_all_listeners(self, event: Optional[str] = None) -> None:
        """Remove all listeners for an event, or all events if None."""
        with self._lock:
            if event:
                self._listeners.pop(event, None)
            else:
                self._listeners.clear()
                self._wildcard_listeners.clear()


# ---------------------------------------------------------------------------
# CheckpointManager
# ---------------------------------------------------------------------------

class CheckpointManager:
    """
    Resume-from-checkpoint persistence.

    Saves/loads checkpoint data for download resume support.
    Includes integrity verification and auto-cleanup of old checkpoints.
    """

    def __init__(
        self,
        checkpoint_dir: Union[str, Path] = "checkpoints",
        max_age_days: int = 30,
    ) -> None:
        self.checkpoint_dir = Path(checkpoint_dir)
        self.max_age_days = max_age_days
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _checkpoint_path(self, task_id: str) -> Path:
        """Get the checkpoint file path for a task."""
        return self.checkpoint_dir / f"{task_id}.json"

    def save(
        self,
        task_id: str,
        url: str,
        output_path: str,
        downloaded_bytes: int,
        total_bytes: int,
        etag: str = "",
        last_modified: str = "",
        checksum: str = "",
        headers: Optional[Dict[str, str]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Save checkpoint data for a download task.

        Args:
            task_id: Download task ID.
            url: Download URL.
            output_path: Output file path.
            downloaded_bytes: Bytes downloaded so far.
            total_bytes: Total bytes expected.
            etag: ETag header value.
            last_modified: Last-Modified header value.
            checksum: Expected checksum.
            headers: Request headers.
            extra: Extra data to store.
        """
        checkpoint = {
            "task_id": task_id,
            "url": url,
            "output_path": output_path,
            "downloaded_bytes": downloaded_bytes,
            "total_bytes": total_bytes,
            "etag": etag,
            "last_modified": last_modified,
            "checksum": checksum,
            "headers": headers or {},
            "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            "version": VERSION,
            "extra": extra or {},
        }
        # Add integrity hash
        checkpoint_data = json.dumps(checkpoint, sort_keys=True, default=str)
        checkpoint["integrity_hash"] = hashlib.sha256(checkpoint_data.encode()).hexdigest()

        path = self._checkpoint_path(task_id)
        with self._lock:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(checkpoint, f, indent=2, ensure_ascii=False, default=str)
            except OSError as e:
                logger.error("Failed to save checkpoint for %s: %s", task_id, e)

    def load(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        Load checkpoint data for a download task.

        Args:
            task_id: Download task ID.

        Returns:
            Checkpoint data dict, or None if not found.

        Raises:
            CheckpointCorruptedError: If integrity check fails.
        """
        path = self._checkpoint_path(task_id)
        if not path.exists():
            return None
        with self._lock:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError) as e:
                logger.error("Failed to load checkpoint for %s: %s", task_id, e)
                raise CheckpointCorruptedError(f"Checkpoint load failed: {e}")

        # Verify integrity
        stored_hash = data.get("integrity_hash")
        if stored_hash:
            data_copy = {k: v for k, v in data.items() if k != "integrity_hash"}
            computed_hash = hashlib.sha256(
                json.dumps(data_copy, sort_keys=True, default=str).encode()
            ).hexdigest()
            if computed_hash != stored_hash:
                raise CheckpointCorruptedError(
                    f"Checkpoint integrity check failed for task {task_id}"
                )
        return data

    def delete(self, task_id: str) -> bool:
        """Delete a checkpoint."""
        path = self._checkpoint_path(task_id)
        with self._lock:
            try:
                if path.exists():
                    path.unlink()
                    return True
                return False
            except OSError as e:
                logger.error("Failed to delete checkpoint for %s: %s", task_id, e)
                return False

    def exists(self, task_id: str) -> bool:
        """Check if a checkpoint exists."""
        return self._checkpoint_path(task_id).exists()

    def cleanup_old(self) -> int:
        """Remove checkpoints older than max_age_days."""
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=self.max_age_days)
        cleaned = 0
        with self._lock:
            for path in self.checkpoint_dir.glob("*.json"):
                try:
                    mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
                    if mtime < cutoff:
                        path.unlink()
                        cleaned += 1
                except OSError:
                    pass
        if cleaned > 0:
            logger.info("Cleaned up %d old checkpoints", cleaned)
        return cleaned

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """List all checkpoint summaries."""
        checkpoints = []
        for path in self.checkpoint_dir.glob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                checkpoints.append({
                    "task_id": data.get("task_id", path.stem),
                    "url": data.get("url", ""),
                    "downloaded_bytes": data.get("downloaded_bytes", 0),
                    "total_bytes": data.get("total_bytes", 0),
                    "saved_at": data.get("saved_at", ""),
                })
            except (json.JSONDecodeError, OSError):
                pass
        return checkpoints


# ---------------------------------------------------------------------------
# ConcurrentDownloadManager
# ---------------------------------------------------------------------------

class ConcurrentDownloadManager:
    """
    Semaphore-limited concurrent download pool.

    Submits tasks, cancels running downloads, aggregates progress,
    and reports status of all active downloads.
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        queue: Optional[DownloadQueue] = None,
    ) -> None:
        self.max_concurrent = max_concurrent
        self.queue = queue or DownloadQueue()
        self._semaphore = threading.Semaphore(max_concurrent)
        self._active: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._worker_threads: Dict[str, threading.Thread] = {}
        self._cancel_flags: Dict[str, threading.Event] = {}

    def submit(
        self,
        task: DownloadTask,
        download_func: Callable[[DownloadTask, threading.Event], DownloadResult],
    ) -> str:
        """
        Submit a download task for concurrent execution.

        Args:
            task: DownloadTask to execute.
            download_func: Function that performs the download.

        Returns:
            Task ID.
        """
        task_id = task.task_id
        cancel_event = threading.Event()
        with self._lock:
            self._cancel_flags[task_id] = cancel_event
            self._active[task_id] = {
                "task": task,
                "status": "waiting",
                "progress": 0.0,
                "started_at": None,
            }

        def worker() -> None:
            self._semaphore.acquire()
            try:
                with self._lock:
                    if task_id in self._active:
                        self._active[task_id]["status"] = "running"
                        self._active[task_id]["started_at"] = time.monotonic()
                result = download_func(task, cancel_event)
                with self._lock:
                    if task_id in self._active:
                        self._active[task_id]["status"] = "completed"
                        self._active[task_id]["result"] = result
            except Exception as e:
                with self._lock:
                    if task_id in self._active:
                        self._active[task_id]["status"] = "failed"
                        self._active[task_id]["error"] = str(e)
            finally:
                self._semaphore.release()

        thread = threading.Thread(
            target=worker,
            name=f"download_worker_{task_id[:8]}",
            daemon=True,
        )
        with self._lock:
            self._worker_threads[task_id] = thread
        thread.start()
        return task_id

    def cancel(self, task_id: str) -> bool:
        """Cancel a running download."""
        with self._lock:
            if task_id in self._cancel_flags:
                self._cancel_flags[task_id].set()
                if task_id in self._active:
                    self._active[task_id]["status"] = "cancelling"
                return True
            return False

    def update_progress(self, task_id: str, progress: float, downloaded: int = 0, total: int = 0) -> None:
        """Update progress for an active download."""
        with self._lock:
            if task_id in self._active:
                self._active[task_id]["progress"] = progress
                self._active[task_id]["downloaded"] = downloaded
                self._active[task_id]["total"] = total

    def get_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific download."""
        with self._lock:
            return self._active.get(task_id)

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all active downloads."""
        with self._lock:
            return dict(self._active)

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get aggregated progress across all active downloads."""
        with self._lock:
            total_downloads = len(self._active)
            running = sum(1 for a in self._active.values() if a["status"] == "running")
            completed = sum(1 for a in self._active.values() if a["status"] == "completed")
            failed = sum(1 for a in self._active.values() if a["status"] == "failed")
            total_downloaded = sum(a.get("downloaded", 0) for a in self._active.values())
            total_size = sum(a.get("total", 0) for a in self._active.values())
            avg_progress = (
                sum(a["progress"] for a in self._active.values()) / total_downloads
                if total_downloads > 0 else 0.0
            )
            return {
                "total_active": total_downloads,
                "running": running,
                "completed": completed,
                "failed": failed,
                "total_downloaded_bytes": total_downloaded,
                "total_expected_bytes": total_size,
                "average_progress": round(avg_progress, 1),
            }

    def wait_all(self, timeout: float = 0.0) -> None:
        """Wait for all active downloads to complete."""
        deadline = time.monotonic() + timeout if timeout > 0 else float("inf")
        while True:
            with self._lock:
                running = [a for a in self._active.values() if a["status"] in ("running", "waiting")]
                if not running:
                    break
            if time.monotonic() > deadline:
                break
            time.sleep(0.5)

    def cleanup_completed(self) -> int:
        """Remove completed/failed downloads from tracking. Returns count removed."""
        with self._lock:
            to_remove = [
                tid for tid, info in self._active.items()
                if info["status"] in ("completed", "failed", "cancelled")
            ]
            for tid in to_remove:
                del self._active[tid]
                self._cancel_flags.pop(tid, None)
                self._worker_threads.pop(tid, None)
            return len(to_remove)


# ---------------------------------------------------------------------------
# BandwidthMonitor
# ---------------------------------------------------------------------------

class BandwidthMonitor:
    """
    Real-time bandwidth monitoring across all downloads.

    Tracks per-agent bandwidth, global limits, and priority-based allocation.
    """

    def __init__(
        self,
        global_limit_kbps: float = 0.0,
        check_interval: float = 1.0,
    ) -> None:
        self.global_limit_kbps = global_limit_kbps
        self.check_interval = check_interval
        self._per_download: Dict[str, Dict[str, Any]] = {}
        self._per_agent: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._total_downloaded = 0
        self._start_time = 0.0

    def start(self) -> None:
        """Start monitoring."""
        self._running = True
        self._start_time = time.monotonic()
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="bandwidth_monitor",
            daemon=True,
        )
        self._monitor_thread.start()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self._running:
            try:
                self._sample_bandwidth()
            except Exception as e:
                logger.error("Bandwidth monitor error: %s", e)
            time.sleep(self.check_interval)

    def _sample_bandwidth(self) -> None:
        """Sample current bandwidth usage."""
        now = time.monotonic()
        with self._lock:
            for task_id, info in self._per_download.items():
                elapsed = now - info.get("last_sample_time", now)
                if elapsed > 0:
                    delta = info.get("current_bytes", 0) - info.get("last_sampled_bytes", 0)
                    speed = delta / elapsed
                    info["current_speed"] = speed
                    info["last_sampled_bytes"] = info.get("current_bytes", 0)
                    info["last_sample_time"] = now

            # Aggregate per-agent
            agent_bandwidth: Dict[str, float] = defaultdict(float)
            for info in self._per_download.values():
                agent = info.get("agent", "unknown")
                agent_bandwidth[agent] += info.get("current_speed", 0.0)
            for agent, bw in agent_bandwidth.items():
                if agent not in self._per_agent:
                    self._per_agent[agent] = {}
                self._per_agent[agent]["current_speed"] = bw

    def register_download(self, task_id: str, agent: str = "") -> None:
        """Register a download for bandwidth tracking."""
        now = time.monotonic()
        with self._lock:
            self._per_download[task_id] = {
                "agent": agent,
                "current_bytes": 0,
                "last_sampled_bytes": 0,
                "current_speed": 0.0,
                "last_sample_time": now,
                "started_at": now,
            }

    def update_download(self, task_id: str, downloaded_bytes: int) -> None:
        """Update download progress for bandwidth calculation."""
        with self._lock:
            if task_id in self._per_download:
                self._per_download[task_id]["current_bytes"] = downloaded_bytes
                self._total_downloaded = sum(
                    info.get("current_bytes", 0) for info in self._per_download.values()
                )

    def unregister_download(self, task_id: str) -> None:
        """Unregister a download from tracking."""
        with self._lock:
            self._per_download.pop(task_id, None)

    def get_global_bandwidth(self) -> float:
        """Get current total bandwidth usage (bytes/sec)."""
        with self._lock:
            return sum(info.get("current_speed", 0.0) for info in self._per_download.values())

    def get_agent_bandwidth(self, agent: str) -> float:
        """Get current bandwidth for an agent (bytes/sec)."""
        with self._lock:
            info = self._per_agent.get(agent, {})
            return info.get("current_speed", 0.0)

    def get_all_agent_bandwidth(self) -> Dict[str, float]:
        """Get bandwidth per agent."""
        with self._lock:
            return {
                agent: info.get("current_speed", 0.0)
                for agent, info in self._per_agent.items()
            }

    def allocate_bandwidth(self, task_id: str, priority: int = 5) -> float:
        """
        Calculate allocated bandwidth for a download based on priority.

        Higher priority (lower number) gets more bandwidth.
        """
        with self._lock:
            if self.global_limit_kbps <= 0:
                return 0.0  # unlimited
            limit_bps = self.global_limit_kbps * 1024
            active_count = len(self._per_download)
            if active_count == 0:
                return limit_bps
            # Priority-based weighting
            total_weight = sum(
                1.0 / (info.get("priority", 5) + 1)
                for info in self._per_download.values()
            )
            task_weight = 1.0 / (priority + 1)
            if total_weight > 0:
                return limit_bps * (task_weight / total_weight)
            return limit_bps / active_count

    def get_stats(self) -> Dict[str, Any]:
        """Get bandwidth statistics."""
        elapsed = time.monotonic() - self._start_time if self._start_time > 0 else 1.0
        return {
            "global_bandwidth_kbps": self.get_global_bandwidth() / 1024,
            "global_limit_kbps": self.global_limit_kbps,
            "total_downloaded_bytes": self._total_downloaded,
            "active_downloads": len(self._per_download),
            "avg_speed_kbps": (self._total_downloaded / elapsed / 1024) if elapsed > 0 else 0.0,
            "per_agent_kbps": {
                agent: bw / 1024
                for agent, bw in self.get_all_agent_bandwidth().items()
            },
        }


# ---------------------------------------------------------------------------
# DownloadOrchestrator
# ---------------------------------------------------------------------------

class DownloadOrchestrator:
    """
    Top-level coordinator for the download pipeline.

    Manages the queue, agents, lifecycle, events, and the full pipeline:
    Submit URL → auto-detect → select agent → download → verify → notify.
    """

    def __init__(
        self,
        max_concurrent: int = 3,
        global_bandwidth_kbps: float = 0.0,
        checkpoint_dir: Union[str, Path] = "checkpoints",
        agent_memory_dir: Union[str, Path] = "agent_memory",
    ) -> None:
        self.queue = DownloadQueue()
        self.registry = AgentRegistry()
        self.events = DownloadEventEmitter()
        self.lifecycle: Dict[str, DownloadLifecycle] = {}
        self.checkpoint = CheckpointManager(checkpoint_dir)
        self.concurrent = ConcurrentDownloadManager(max_concurrent, self.queue)
        self.bandwidth = BandwidthMonitor(global_bandwidth_kbps)
        self.scheduler = DownloadScheduler(self.queue)
        self._results: Dict[str, DownloadResult] = {}
        self._lock = threading.Lock()
        self._running = False

    def submit(
        self,
        url: str,
        output_path: str = "",
        filename: str = "",
        platform_hint: str = "",
        agent_hint: str = "",
        priority: int = DownloadPriority.NORMAL,
        headers: Optional[Dict[str, str]] = None,
        checksum: str = "",
        checksum_algo: str = "sha256",
        tags: Optional[List[str]] = None,
        callback_url: str = "",
    ) -> str:
        """
        Submit a URL for download.

        Creates a DownloadTask, adds it to the queue, and triggers the pipeline.

        Args:
            url: URL to download.
            output_path: Output directory.
            filename: Desired filename.
            platform_hint: Platform hint for agent selection.
            agent_hint: Specific agent to use.
            priority: Download priority.
            headers: Request headers.
            checksum: Expected checksum.
            checksum_algo: Checksum algorithm.
            tags: Tags for the download.
            callback_url: Callback URL on completion.

        Returns:
            Task ID.
        """
        task = DownloadTask(
            url=url,
            output_path=output_path,
            filename=filename,
            platform_hint=platform_hint,
            agent_hint=agent_hint,
            priority=priority,
            headers=headers or {},
            checksum=checksum,
            checksum_algo=checksum_algo,
            tags=tags or [],
            callback_url=callback_url,
        )

        with self._lock:
            self.lifecycle[task.task_id] = DownloadLifecycle(task_id=task.task_id)

        self.queue.put(task)
        self.events.emit("on_start", task.task_id, url)
        self.lifecycle[task.task_id].transition(DownloadStatus.SCHEDULING)
        self.lifecycle[task.task_id].transition(DownloadStatus.QUEUED)

        logger.info("Task submitted: %s → %s", task.task_id[:8], url)
        return task.task_id

    def _auto_detect_platform(self, url: str) -> str:
        """Auto-detect platform from URL."""
        from urllib.parse import urlparse
        domain = urlparse(url).netloc.lower()
        platform_map = {
            "youtube.com": "youtube",
            "youtu.be": "youtube",
            "twitter.com": "twitter",
            "x.com": "twitter",
            "instagram.com": "instagram",
            "facebook.com": "facebook",
            "tiktok.com": "tiktok",
            "reddit.com": "reddit",
            "twitch.tv": "twitch",
            "vimeo.com": "vimeo",
            "dailymotion.com": "dailymotion",
            "soundcloud.com": "soundcloud",
            "spotify.com": "spotify",
            "pinterest.com": "pinterest",
            "tumblr.com": "tumblr",
        }
        for domain_key, platform in platform_map.items():
            if domain_key in domain:
                return platform
        return "generic"

    def _select_agent(self, task: DownloadTask) -> Optional[Dict[str, Any]]:
        """Select the best agent for a task."""
        # Auto-detect platform if not hinted
        if not task.platform_hint:
            task.platform_hint = self._auto_detect_platform(task.url)
        return self.registry.find_best_for_task(task)

    def process_task(self, task: DownloadTask) -> DownloadResult:
        """
        Process a download task through the full pipeline.

        Pipeline: select agent → download → verify → notify

        Args:
            task: DownloadTask to process.

        Returns:
            DownloadResult with outcome.
        """
        lifecycle = self.lifecycle.get(task.task_id)
        result = DownloadResult(
            task_id=task.task_id,
            url=task.url,
            filename=task.filename,
            output_path=task.output_path,
        )
        start_time = time.monotonic()

        try:
            # Transition to DOWNLOADING
            if lifecycle:
                lifecycle.transition(DownloadStatus.DOWNLOADING)
            self.events.emit("on_progress", task.task_id, 0, 0, 0.0, 0.0)

            # Select agent
            agent_info = self._select_agent(task)
            if agent_info:
                result.agent_name = agent_info["name"]
                task.agent_hint = agent_info["name"]
            else:
                result.platform = task.platform_hint or self._auto_detect_platform(task.url)

            # Check for resume checkpoint
            checkpoint_data = None
            if self.checkpoint.exists(task.task_id):
                try:
                    checkpoint_data = self.checkpoint.load(task.task_id)
                    if checkpoint_data:
                        task.resume_from = checkpoint_data.get("downloaded_bytes", 0)
                        result.resume_used = True
                except CheckpointCorruptedError:
                    logger.warning("Corrupted checkpoint for %s, starting fresh", task.task_id)

            # Perform the download
            downloader = None
            if agent_info and agent_info.get("downloader"):
                downloader = agent_info["downloader"]
                download_result = downloader.download(task)
                result.file_size = download_result.file_size if hasattr(download_result, 'file_size') else 0
                result.output_path = download_result.output_path if hasattr(download_result, 'output_path') else task.output_path
            else:
                # Use default HTTP download
                result = self._default_download(task, result)

            # Verify checksum
            if task.checksum and result.output_path:
                if lifecycle:
                    lifecycle.transition(DownloadStatus.VERIFYING)
                self.events.emit("on_verify", task.task_id)
                try:
                    algo = ChecksumAlgorithm(task.checksum_algo)
                    verified = verify_checksum(result.output_path, task.checksum, algo)
                    result.checksum_verified = verified
                    result.checksum_algorithm = task.checksum_algo
                    if not verified:
                        result.error = "Checksum verification failed"
                        result.status = DownloadStatus.FAILED
                except Exception as e:
                    result.checksum_verified = False
                    result.error = f"Checksum verification error: {e}"

            # Mark complete
            if result.status != DownloadStatus.FAILED:
                if lifecycle:
                    lifecycle.transition(DownloadStatus.COMPLETED)
                result.status = DownloadStatus.COMPLETED
                self.events.emit("on_complete", task.task_id, result)
                # Cleanup checkpoint
                if self.checkpoint.exists(task.task_id):
                    self.checkpoint.delete(task.task_id)

        except Exception as e:
            result.status = DownloadStatus.FAILED
            result.error = str(e)
            if lifecycle and lifecycle.can_transition(DownloadStatus.FAILED):
                lifecycle.transition(DownloadStatus.FAILED)
            self.events.emit("on_error", task.task_id, str(e))
            logger.error("Task %s failed: %s", task.task_id[:8], e)

        # Finalize result
        result.elapsed = time.monotonic() - start_time
        result.started_at = datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat()
        result.completed_at = datetime.now(tz=timezone.utc).isoformat()
        if result.file_size > 0 and result.elapsed > 0:
            result.average_speed = result.file_size / result.elapsed

        with self._lock:
            self._results[task.task_id] = result

        return result

    def _default_download(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        """Perform a default HTTP download using SyncHTTPClient."""
        client = SyncHTTPClient()
        try:
            output_path = Path(task.output_path) / task.filename if task.output_path else Path(task.filename)
            if not task.filename:
                # Detect filename from URL
                head_resp = client.head(task.url)
                cd = head_resp.headers.get("Content-Disposition", "")
                ct = head_resp.headers.get("Content-Type", "")
                task.filename = suggest_filename(
                    url=task.url,
                    content_type=ct,
                    content_disposition=cd,
                )
                output_path = Path(task.output_path) / task.filename if task.output_path else Path(task.filename)

            speed_tracker = DownloadSpeedTracker()
            speed_tracker.start()

            def progress_cb(
                tid: str,
                downloaded: int,
                total: int,
                speed: float,
                eta: float,
            ) -> None:
                speed_tracker.update(downloaded)
                self.events.emit("on_progress", task.task_id, downloaded, total, speed, eta)
                # Save checkpoint periodically
                if downloaded % (1024 * 1024) < 8192:  # Roughly every MB
                    self.checkpoint.save(
                        task_id=task.task_id,
                        url=task.url,
                        output_path=str(output_path),
                        downloaded_bytes=downloaded,
                        total_bytes=total,
                    )

            final_path = client.streaming_download(
                url=task.url,
                output_path=output_path,
                headers=task.headers,
                resume_from=task.resume_from,
                progress_callback=progress_cb,
            )

            result.output_path = str(final_path)
            result.filename = final_path.name
            if final_path.exists():
                result.file_size = final_path.stat().st_size
            result.average_speed = speed_tracker.average_speed
            result.speed_samples = list(speed_tracker._speeds)

        finally:
            client.close()
        return result

    def get_result(self, task_id: str) -> Optional[DownloadResult]:
        """Get the result of a completed download."""
        with self._lock:
            return self._results.get(task_id)

    def get_lifecycle(self, task_id: str) -> Optional[DownloadLifecycle]:
        """Get the lifecycle for a task."""
        with self._lock:
            return self.lifecycle.get(task_id)

    def cancel(self, task_id: str) -> bool:
        """Cancel a download task."""
        lifecycle = self.lifecycle.get(task_id)
        if lifecycle and lifecycle.can_transition(DownloadStatus.CANCELLED):
            lifecycle.transition(DownloadStatus.CANCELLED)
        self.concurrent.cancel(task_id)
        self.queue.remove(task_id)
        self.events.emit("on_cancel", task_id)
        return True

    def pause(self, task_id: str) -> bool:
        """Pause a download task."""
        lifecycle = self.lifecycle.get(task_id)
        if lifecycle and lifecycle.can_transition(DownloadStatus.PAUSED):
            lifecycle.transition(DownloadStatus.PAUSED)
            self.events.emit("on_pause", task_id)
            return True
        return False

    def resume(self, task_id: str) -> bool:
        """Resume a paused download task."""
        lifecycle = self.lifecycle.get(task_id)
        if lifecycle and lifecycle.can_transition(DownloadStatus.DOWNLOADING):
            lifecycle.transition(DownloadStatus.DOWNLOADING)
            self.events.emit("on_resume", task_id)
            return True
        return False

    def retry(self, task_id: str) -> bool:
        """Retry a failed download task."""
        lifecycle = self.lifecycle.get(task_id)
        if lifecycle and lifecycle.can_transition(DownloadStatus.RETRYING):
            lifecycle.transition(DownloadStatus.RETRYING)
            lifecycle.transition(DownloadStatus.QUEUED)
            self.events.emit("on_retry", task_id)
            return True
        return False

    def start(self) -> None:
        """Start the orchestrator and all subsystems."""
        self._running = True
        self.bandwidth.start()
        self.scheduler.start()
        logger.info("DownloadOrchestrator started (v%s)", VERSION)

    def stop(self) -> None:
        """Stop the orchestrator and all subsystems."""
        self._running = False
        self.bandwidth.stop()
        self.scheduler.stop()
        self.concurrent.wait_all(timeout=10.0)
        logger.info("DownloadOrchestrator stopped")

    def get_stats(self) -> Dict[str, Any]:
        """Get orchestrator statistics."""
        return {
            "queue_size": self.queue.size,
            "active_downloads": len(self.concurrent._active),
            "completed_downloads": len(self._results),
            "registered_agents": self.registry.agent_count,
            "bandwidth_stats": self.bandwidth.get_stats(),
            "scheduled_jobs": len(self.scheduler._schedules),
        }


# ---------------------------------------------------------------------------
# DownloaderBase (ABC)
# ---------------------------------------------------------------------------

class DownloaderBase(abc.ABC):
    """
    Abstract base class for download agents using the template method pattern.

    Subclasses must implement:
    - validate_url(): Check if URL is valid for this agent.
    - get_available_formats(): Get available download formats.
    - get_metadata(): Get metadata for a URL.

    The download() method orchestrates the full lifecycle using
    hook methods that subclasses can override:
    - on_prepare(): Pre-download setup.
    - on_download(): Core download logic.
    - on_verify(): Post-download verification.
    - on_post_process(): Post-processing (extract, convert, etc.).
    - on_cleanup(): Cleanup after download.
    """

    def __init__(
        self,
        name: str = "base",
        platform: str = "generic",
        formats: Tuple[str, ...] = (),
        qualities: Tuple[str, ...] = (),
        features: Tuple[str, ...] = (),
        max_concurrent: int = 3,
        priority: int = 5,
        **kwargs,
    ) -> None:
        self.name = name
        self.platform = platform
        self.formats = formats
        self.qualities = qualities
        self.features = features
        self.max_concurrent = max_concurrent
        self.priority = priority
        # Store any extra kwargs for agent-specific config
        self._extra = kwargs
        # Common agent attributes that agents may access
        self.headers = kwargs.get('headers', {})
        self.proxy = kwargs.get('proxy', '')
        self.timeout = kwargs.get('timeout', 30)
        self.output_dir = kwargs.get('output_dir', '.')
        self.memory = kwargs.get('memory', AgentMemory(name))
        self.skill = AgentSkill(
            platform=platform or name,
            formats=formats,
            qualities=qualities,
            features=features,
            max_concurrent=max_concurrent,
            priority=priority,
        )
        self._lifecycle: Dict[str, DownloadLifecycle] = {}
        self._lock = threading.Lock()

    @abc.abstractmethod
    def validate_url(self, url: str) -> bool:
        """Check if a URL is valid for this downloader agent."""
        ...

    @abc.abstractmethod
    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Get available download formats for a URL."""
        ...

    @abc.abstractmethod
    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Get metadata for a URL."""
        ...

    def on_prepare(self, task: DownloadTask) -> DownloadTask:
        """
        Pre-download preparation hook.

        Override to add custom preparation logic (e.g., authentication,
        URL transformation, setting headers).

        Args:
            task: The download task.

        Returns:
            Modified task.
        """
        return task

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """
        Core download logic hook.

        Override to implement the actual download for the specific platform.

        Args:
            task: The download task.

        Returns:
            DownloadResult with outcome.
        """
        # Default implementation: use SyncHTTPClient
        client = SyncHTTPClient()
        result = DownloadResult(
            task_id=task.task_id,
            url=task.url,
            filename=task.filename,
        )
        try:
            output_path = Path(task.output_path) / task.filename if task.output_path else Path(task.filename)
            if not task.filename:
                head_resp = client.head(task.url)
                cd = head_resp.headers.get("Content-Disposition", "")
                ct = head_resp.headers.get("Content-Type", "")
                task.filename = suggest_filename(url=task.url, content_type=ct, content_disposition=cd)
                output_path = Path(task.output_path) / task.filename if task.output_path else Path(task.filename)

            final_path = client.streaming_download(
                url=task.url,
                output_path=output_path,
                headers=task.headers,
                resume_from=task.resume_from,
            )
            result.output_path = str(final_path)
            result.filename = final_path.name
            if final_path.exists():
                result.file_size = final_path.stat().st_size
            result.status = DownloadStatus.COMPLETED
        except Exception as e:
            result.status = DownloadStatus.FAILED
            result.error = str(e)
        finally:
            client.close()
        return result

    def on_verify(self, task: DownloadTask = None, result: DownloadResult = None) -> DownloadResult:
        """
        Post-download verification hook.

        Override to add custom verification logic.
        Supports both (self, task, result) and (self, result) signatures.

        Args:
            task: The download task (optional for backward compatibility).
            result: The download result so far (optional for backward compatibility).

        Returns:
            Updated result (or True/bool if agent returns bool).
        """
        # Handle (self, result) calls from agents that don't pass task
        if task is None and result is not None:
            # Agent called on_verify(self, result) — return result directly
            return result
        if result is None:
            return DownloadResult()
        if task and task.checksum and result.output_path:
            try:
                algo = ChecksumAlgorithm(task.checksum_algo)
                result.checksum_verified = verify_checksum(result.output_path, task.checksum, algo)
                result.checksum_algorithm = task.checksum_algo
            except Exception as e:
                result.checksum_verified = False
                result.error = f"Verification error: {e}"
        return result

    def on_post_process(self, task: DownloadTask = None, result: DownloadResult = None) -> DownloadResult:
        """
        Post-processing hook (extraction, conversion, etc.).

        Override to add custom post-processing.
        Supports both (self, task, result) and (self, result) signatures.

        Args:
            task: The download task (optional for backward compatibility).
            result: The download result (optional for backward compatibility).

        Returns:
            Updated result (or None if agent returns None).
        """
        # Handle (self, result) calls from agents
        if task is None and result is not None:
            return result
        if result is None:
            return DownloadResult()
        return result

    def on_cleanup(self, task: DownloadTask = None, result: DownloadResult = None) -> None:
        """
        Cleanup hook after download.

        Override to add custom cleanup logic.
        Supports flexible argument signatures.

        Args:
            task: The download task (optional).
            result: The download result (optional).
        """
        pass

    def download(self, task: DownloadTask) -> DownloadResult:
        """
        Template method that orchestrates the full download lifecycle.

        Calls hooks in order: on_prepare → on_download → on_verify →
        on_post_process → on_cleanup.

        Args:
            task: The download task to execute.

        Returns:
            DownloadResult with the final outcome.
        """
        start_time = time.monotonic()
        lifecycle = DownloadLifecycle(task_id=task.task_id)
        with self._lock:
            self._lifecycle[task.task_id] = lifecycle

        result = DownloadResult(
            task_id=task.task_id,
            url=task.url,
            filename=task.filename,
            output_path=task.output_path,
            agent_name=self.name,
            platform=self.skill.platform,
        )

        try:
            # 1. Prepare
            task = self.on_prepare(task)

            # 2. Download
            lifecycle.transition(DownloadStatus.DOWNLOADING)
            result = self.on_download(task)

            # 3. Verify (only if download succeeded)
            if result.status == DownloadStatus.COMPLETED:
                lifecycle.transition(DownloadStatus.VERIFYING)
                result = self.on_verify(task, result)

                # 4. Post-process
                lifecycle.transition(DownloadStatus.EXTRACTING)
                result = self.on_post_process(task, result)

                # 5. Complete
                lifecycle.transition(DownloadStatus.COMPLETED)
            elif result.status != DownloadStatus.FAILED:
                result.status = DownloadStatus.FAILED

        except Exception as e:
            result.status = DownloadStatus.FAILED
            result.error = str(e)
            if lifecycle.can_transition(DownloadStatus.FAILED):
                lifecycle.transition(DownloadStatus.FAILED)

        finally:
            # 6. Cleanup
            self.on_cleanup(task, result)
            result.elapsed = time.monotonic() - start_time
            result.started_at = datetime.fromtimestamp(start_time, tz=timezone.utc).isoformat()
            result.completed_at = datetime.now(tz=timezone.utc).isoformat()
            if result.file_size > 0 and result.elapsed > 0:
                result.average_speed = result.file_size / result.elapsed

        return result

    def get_skill(self) -> AgentSkill:
        """Get this agent's skill description."""
        return self.skill

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name={self.name!r}, platform={self.skill.platform!r})"
