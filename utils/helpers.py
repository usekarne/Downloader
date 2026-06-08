#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Helper Utilities
INFINITE HYPERNOVA SOVEREIGN NEXUS

Utility functions for formatting, sanitization, file operations,
decorators, caching, timing, and sorting.

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng
License: MIT
"""

import os
import re
import json
import sys
import time
import uuid
import shutil
import hashlib
import signal
import functools
import threading
from typing import (
    Any, Callable, Dict, Iterable, List, Optional, Tuple, TypeVar, Union
)
from datetime import datetime, timezone
from pathlib import Path
from contextlib import contextmanager


# ==============================================================================
# Type Variables
# ==============================================================================

F = TypeVar("F", bound=Callable)
T = TypeVar("T")


# ==============================================================================
# File Size Formatting
# ==============================================================================

SIZE_UNITS = ["B", "KB", "MB", "GB", "TB", "PB", "EB"]
SIZE_BINARY_UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB"]


def format_filesize(
    size: Union[int, float],
    binary: bool = False,
    precision: int = 2,
    unit: Optional[str] = None,
) -> str:
    """
    Format a file size to human-readable string.

    Args:
        size: Size in bytes.
        binary: Use binary (1024) instead of decimal (1000) units.
        precision: Number of decimal places.
        unit: Force a specific unit.

    Returns:
        Formatted size string (e.g., "1.23 GB").
    """
    if size < 0:
        return f"-{format_filesize(-size, binary, precision, unit)}"

    if size == 0:
        return f"0 {unit or 'B'}"

    base = 1024 if binary else 1000
    units = SIZE_BINARY_UNITS if binary else SIZE_UNITS

    if unit:
        if unit in units:
            idx = units.index(unit)
            value = size / (base ** idx)
            return f"{value:.{precision}f} {unit}"
        return f"{size:.{precision}f} {unit}"

    for i, u in enumerate(units):
        threshold = base ** (i + 1)
        if size < threshold or i == len(units) - 1:
            value = size / (base ** i)
            return f"{value:.{precision}f} {u}"

    return f"{size:.{precision}f} B"


def parse_filesize(size_str: str) -> float:
    """Parse a human-readable size string to bytes."""
    size_str = size_str.strip().upper()
    multipliers: Dict[str, float] = {}
    for i, u in enumerate(SIZE_UNITS):
        multipliers[u] = 1000 ** i
    for i, u in enumerate(SIZE_BINARY_UNITS):
        multipliers[u] = 1024 ** i
    multipliers["K"] = 1000
    multipliers["M"] = 1000 ** 2
    multipliers["G"] = 1000 ** 3

    for suffix in sorted(multipliers.keys(), key=len, reverse=True):
        if size_str.endswith(suffix):
            try:
                return float(size_str[:-len(suffix)].strip()) * multipliers[suffix]
            except ValueError:
                break

    try:
        return float(size_str)
    except ValueError:
        return 0.0


# ==============================================================================
# Duration Formatting
# ==============================================================================

def format_duration(
    seconds: Union[int, float],
    compact: bool = False,
    show_ms: bool = False,
) -> str:
    """
    Format a duration to human-readable string.

    Args:
        seconds: Duration in seconds.
        compact: Use compact format (HH:MM:SS).
        show_ms: Show milliseconds in compact format.

    Returns:
        Formatted duration string.
    """
    if seconds < 0:
        seconds = abs(seconds)

    if compact:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if show_ms:
            ms = int((seconds % 1) * 1000)
            return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    parts = []
    if seconds >= 86400:
        days = int(seconds // 86400)
        seconds %= 86400
        parts.append(f"{days} day{'s' if days != 1 else ''}")

    if seconds >= 3600:
        hours = int(seconds // 3600)
        seconds %= 3600
        parts.append(f"{hours} hour{'s' if hours != 1 else ''}")

    if seconds >= 60:
        minutes = int(seconds // 60)
        seconds %= 60
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")

    if seconds > 0 or not parts:
        secs = int(seconds)
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")

    return ", ".join(parts)


# ==============================================================================
# Speed Formatting
# ==============================================================================

def format_speed(speed_bps: Union[int, float], precision: int = 2) -> str:
    """
    Format a transfer speed to human-readable string.

    Args:
        speed_bps: Speed in bytes per second.
        precision: Number of decimal places.

    Returns:
        Formatted speed string (e.g., "1.23 MB/s").
    """
    if speed_bps < 0:
        speed_bps = abs(speed_bps)
    return f"{format_filesize(speed_bps, precision=precision)}/s"


# ==============================================================================
# Timestamp Formatting
# ==============================================================================

def format_timestamp(
    timestamp: Optional[Union[int, float, datetime]] = None,
    fmt: str = "%Y-%m-%d %H:%M:%S",
    utc: bool = False,
) -> str:
    """
    Format a timestamp to human-readable string.

    Args:
        timestamp: Unix timestamp or datetime object. None for current time.
        fmt: strftime format string.
        utc: Use UTC timezone.

    Returns:
        Formatted timestamp string.
    """
    if timestamp is None:
        dt = datetime.now(timezone.utc) if utc else datetime.now()
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        if utc:
            dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
        else:
            dt = datetime.fromtimestamp(timestamp)

    return dt.strftime(fmt)


def format_timestamp_relative(
    timestamp: Optional[Union[int, float, datetime]] = None,
) -> str:
    """Format a timestamp as relative time (e.g., '2 hours ago')."""
    if timestamp is None:
        dt = datetime.now()
    elif isinstance(timestamp, datetime):
        dt = timestamp
    else:
        dt = datetime.fromtimestamp(timestamp)

    now = datetime.now()
    diff = (now - dt).total_seconds()

    if diff < 0:
        return "just now"

    if diff < 60:
        return f"{int(diff)} second{'s' if int(diff) != 1 else ''} ago"
    if diff < 3600:
        minutes = int(diff // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    if diff < 86400:
        hours = int(diff // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    if diff < 604800:
        days = int(diff // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    if diff < 2592000:
        weeks = int(diff // 604800)
        return f"{weeks} week{'s' if weeks != 1 else ''} ago"
    if diff < 31536000:
        months = int(diff // 2592000)
        return f"{months} month{'s' if months != 1 else ''} ago"

    years = int(diff // 31536000)
    return f"{years} year{'s' if years != 1 else ''} ago"


# ==============================================================================
# Filename Sanitization
# ==============================================================================

_INVALID_FILENAME_RE = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(
    filename: str,
    replacement: str = "_",
    max_length: int = 255,
    preserve_extension: bool = True,
) -> str:
    """
    Sanitize a filename by removing/replacing invalid characters.

    Args:
        filename: The filename to sanitize.
        replacement: Character to replace invalid characters with.
        max_length: Maximum filename length.
        preserve_extension: Preserve file extension when truncating.

    Returns:
        Sanitized filename string.
    """
    if not filename:
        return "untitled"

    sanitized = _INVALID_FILENAME_RE.sub(replacement, filename)
    sanitized = sanitized.strip(" .")
    sanitized = re.sub(r"\s+", " ", sanitized)
    sanitized = re.sub(r"\.+", ".", sanitized)

    name_without_ext = os.path.splitext(sanitized)[0].upper()
    if name_without_ext in _WINDOWS_RESERVED:
        sanitized = f"_{sanitized}"

    if len(sanitized) > max_length:
        if preserve_extension and "." in sanitized:
            name, ext = sanitized.rsplit(".", 1)
            max_name = max_length - len(ext) - 1
            if max_name > 0:
                sanitized = f"{name[:max_name]}.{ext}"
            else:
                sanitized = sanitized[:max_length]
        else:
            sanitized = sanitized[:max_length]

    return sanitized or "untitled"


# ==============================================================================
# ID Generation
# ==============================================================================

def generate_id(prefix: str = "") -> str:
    """Generate a unique identifier (UUID4 hex with optional prefix)."""
    uid = uuid.uuid4().hex[:12]
    return f"{prefix}_{uid}" if prefix else uid


def generate_short_id(length: int = 8) -> str:
    """Generate a short random ID."""
    return uuid.uuid4().hex[:length]


def generate_deterministic_id(*args: str) -> str:
    """Generate a deterministic ID from input arguments using SHA256."""
    data = ":".join(str(a) for a in args)
    return hashlib.sha256(data.encode()).hexdigest()[:16]


# ==============================================================================
# Directory Operations
# ==============================================================================

def ensure_dir(path: Union[str, Path]) -> Path:
    """Ensure a directory exists, creating it if necessary. Returns Path."""
    p = Path(path).expanduser().resolve()
    p.mkdir(parents=True, exist_ok=True)
    return p


def get_free_space(path: Union[str, Path] = ".") -> int:
    """Get free disk space in bytes."""
    try:
        usage = shutil.disk_usage(str(Path(path).expanduser().resolve()))
        return usage.free
    except (OSError, AttributeError):
        return 0


def get_total_space(path: Union[str, Path] = ".") -> int:
    """Get total disk space in bytes."""
    try:
        usage = shutil.disk_usage(str(Path(path).expanduser().resolve()))
        return usage.total
    except (OSError, AttributeError):
        return 0


def get_used_space(path: Union[str, Path] = ".") -> int:
    """Get used disk space in bytes."""
    try:
        usage = shutil.disk_usage(str(Path(path).expanduser().resolve()))
        return usage.used
    except (OSError, AttributeError):
        return 0


def directory_size(path: Union[str, Path]) -> int:
    """Calculate total size of all files in a directory recursively."""
    total = 0
    try:
        for entry in Path(path).expanduser().resolve().rglob("*"):
            if entry.is_file():
                total += entry.stat().st_size
    except (OSError, PermissionError):
        pass
    return total


def clean_directory(
    path: Union[str, Path],
    max_age_days: int = 30,
    pattern: str = "*",
    dry_run: bool = False,
) -> int:
    """Clean old files from a directory. Returns number of files deleted."""
    p = Path(path).expanduser().resolve()
    if not p.is_dir():
        return 0

    now = time.time()
    cutoff = now - (max_age_days * 86400)
    count = 0

    for entry in p.rglob(pattern):
        if entry.is_file():
            try:
                if entry.stat().st_mtime < cutoff:
                    if not dry_run:
                        entry.unlink()
                    count += 1
            except (OSError, PermissionError):
                continue

    return count


# ==============================================================================
# MIME Type Detection
# ==============================================================================

_MIME_MAP: Dict[str, str] = {
    # Video
    ".mp4": "video/mp4", ".mkv": "video/x-matroska", ".avi": "video/x-msvideo",
    ".mov": "video/quicktime", ".wmv": "video/x-ms-wmv", ".flv": "video/x-flv",
    ".webm": "video/webm", ".m4v": "video/mp4", ".3gp": "video/3gpp",
    ".ts": "video/mp2t", ".ogv": "video/ogg",
    # Audio
    ".mp3": "audio/mpeg", ".flac": "audio/flac", ".aac": "audio/aac",
    ".wav": "audio/wav", ".ogg": "audio/ogg", ".opus": "audio/opus",
    ".m4a": "audio/mp4", ".wma": "audio/x-ms-wma", ".aiff": "audio/aiff",
    # Image
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".gif": "image/gif", ".webp": "image/webp", ".svg": "image/svg+xml",
    ".bmp": "image/bmp", ".ico": "image/x-icon", ".tiff": "image/tiff",
    # Document
    ".pdf": "application/pdf", ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain", ".html": "text/html", ".json": "application/json",
    ".xml": "application/xml", ".csv": "text/csv", ".md": "text/markdown",
    # Subtitle
    ".srt": "application/x-subrip", ".ass": "text/x-ssa",
    ".vtt": "text/vtt", ".sub": "text/plain",
    # Archive
    ".zip": "application/zip", ".tar": "application/x-tar",
    ".gz": "application/gzip", ".rar": "application/vnd.rar",
    ".7z": "application/x-7z-compressed",
}


def get_mime_type(filepath: Union[str, Path]) -> str:
    """Get the MIME type for a file based on its extension."""
    ext = Path(filepath).suffix.lower()
    return _MIME_MAP.get(ext, "application/octet-stream")


def get_extension(mime_type: str) -> str:
    """Get file extension from MIME type."""
    reverse_map = {v: k for k, v in _MIME_MAP.items()}
    return reverse_map.get(mime_type, ".bin")


# ==============================================================================
# Iterable Utilities
# ==============================================================================

def chunked(iterable: Iterable[T], size: int) -> Iterable[List[T]]:
    """Split an iterable into chunks of a given size."""
    chunk: List[T] = []
    for item in iterable:
        chunk.append(item)
        if len(chunk) >= size:
            yield chunk
            chunk = []
    if chunk:
        yield chunk


def flatten(nested: Iterable) -> List:
    """Flatten a nested iterable."""
    result = []
    for item in nested:
        if isinstance(item, (list, tuple, set)):
            result.extend(flatten(item))
        else:
            result.append(item)
    return result


def unique(iterable: Iterable[T], key: Optional[Callable] = None) -> List[T]:
    """Return unique items from an iterable, preserving order."""
    seen = set()
    result = []
    for item in iterable:
        k = key(item) if key else item
        if k not in seen:
            seen.add(k)
            result.append(item)
    return result


# ==============================================================================
# Decorators
# ==============================================================================

def rate_limit(calls: int, period: float = 1.0) -> Callable[[F], F]:
    """
    Decorator for rate-limiting function calls.

    Args:
        calls: Maximum number of calls allowed in the period.
        period: Time period in seconds.
    """
    min_interval = period / calls
    lock = threading.Lock()
    last_called: List[float] = [0.0]

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            with lock:
                elapsed = time.time() - last_called[0]
                if elapsed < min_interval:
                    time.sleep(min_interval - elapsed)
                last_called[0] = time.time()
            return func(*args, **kwargs)
        return wrapper  # type: ignore
    return decorator


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple = (Exception,),
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Callable[[F], F]:
    """
    Decorator for retrying a function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts.
        delay: Initial delay between retries in seconds.
        backoff: Backoff multiplier.
        exceptions: Tuple of exception types to catch.
        on_retry: Optional callback called on each retry.
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            current_delay = delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts:
                        if on_retry:
                            on_retry(attempt, e)
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        raise

            if last_exception:
                raise last_exception

        return wrapper  # type: ignore
    return decorator


def timeout(seconds: float) -> Callable[[F], F]:
    """
    Decorator for adding a timeout to a function.
    Uses signal on Unix, threading on Windows.
    """
    class TimeoutError(Exception):
        def __init__(self, msg: str = f"Function timed out after {seconds}s"):
            super().__init__(msg)

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            if os.name == "nt":
                # Windows: use threading
                result_container: List[Any] = [None]
                exception_container: List[Optional[Exception]] = [None]

                def target():
                    try:
                        result_container[0] = func(*args, **kwargs)
                    except Exception as e:
                        exception_container[0] = e

                thread = threading.Thread(target=target, daemon=True)
                thread.start()
                thread.join(timeout=seconds)

                if thread.is_alive():
                    raise TimeoutError()

                if exception_container[0]:
                    raise exception_container[0]
                return result_container[0]
            else:
                # Unix: use signal
                def handler(signum: int, frame: Any) -> None:
                    raise TimeoutError()

                old_handler = signal.signal(signal.SIGALRM, handler)
                signal.setitimer(signal.ITIMER_REAL, seconds)
                try:
                    return func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)

        wrapper.timeout_seconds = seconds  # type: ignore
        return wrapper  # type: ignore
    return decorator


def singleton(cls: type) -> Callable:
    """Decorator for implementing the singleton pattern."""
    instances: Dict[type, Any] = {}
    lock = threading.Lock()

    @functools.wraps(cls)
    def get_instance(*args: Any, **kwargs: Any) -> Any:
        if cls not in instances:
            with lock:
                if cls not in instances:
                    instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    get_instance._singleton_cls = cls  # type: ignore
    get_instance._reset = lambda: instances.pop(cls, None)  # type: ignore
    return get_instance


def cached(ttl: float = 300.0, max_size: int = 128) -> Callable[[F], F]:
    """
    Simple TTL cache decorator.

    Args:
        ttl: Time-to-live in seconds.
        max_size: Maximum number of cached results.
    """
    def decorator(func: F) -> F:
        cache: Dict[Tuple, Tuple[float, Any]] = {}
        lock = threading.Lock()

        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            key = (args, tuple(sorted(kwargs.items())))

            with lock:
                if key in cache:
                    cached_time, cached_value = cache[key]
                    if time.time() - cached_time < ttl:
                        return cached_value

                value = func(*args, **kwargs)
                cache[key] = (time.time(), value)

                if len(cache) > max_size:
                    oldest_key = min(cache.keys(), key=lambda k: cache[k][0])
                    del cache[oldest_key]

            return value

        wrapper.cache_clear = lambda: cache.clear()  # type: ignore
        wrapper.cache_info = lambda: {  # type: ignore
            "size": len(cache), "max_size": max_size, "ttl": ttl,
        }
        return wrapper  # type: ignore
    return decorator


# ==============================================================================
# Timing Context Manager
# ==============================================================================

@contextmanager
def measure_time(label: str = "Operation", log_func: Optional[Callable] = None):
    """
    Context manager for measuring execution time.

    Args:
        label: Label for the operation.
        log_func: Custom logging function. Defaults to print.

    Yields:
        Dictionary with timing information.
    """
    timing: Dict[str, Any] = {"label": label}
    start = time.perf_counter()
    timing["start"] = start

    try:
        yield timing
    finally:
        end = time.perf_counter()
        elapsed = end - start
        timing["end"] = end
        timing["elapsed"] = elapsed
        timing["elapsed_formatted"] = format_duration(elapsed, compact=True)

        if log_func:
            log_func(f"{label} took {timing['elapsed_formatted']}")


class Timer:
    """A simple timer class for measuring elapsed time."""

    def __init__(self, label: str = ""):
        self.label = label
        self._start: Optional[float] = None
        self._end: Optional[float] = None

    def start(self) -> "Timer":
        self._start = time.perf_counter()
        return self

    def stop(self) -> "Timer":
        self._end = time.perf_counter()
        return self

    @property
    def elapsed(self) -> float:
        if self._start is None:
            return 0.0
        end = self._end or time.perf_counter()
        return end - self._start

    @property
    def elapsed_formatted(self) -> str:
        return format_duration(self.elapsed, compact=True)

    def __enter__(self) -> "Timer":
        return self.start()

    def __exit__(self, *args: Any) -> None:
        self.stop()

    def __repr__(self) -> str:
        if self.label:
            return f"Timer({self.label!r}, elapsed={self.elapsed_formatted})"
        return f"Timer(elapsed={self.elapsed_formatted})"


# ==============================================================================
# JSON Utilities
# ==============================================================================

def safe_json_loads(
    text: str,
    default: Any = None,
    strict: bool = False,
) -> Any:
    """
    Safely parse JSON with fallback.

    Args:
        text: JSON string to parse.
        default: Default value if parsing fails.
        strict: If True, raise on parse error.

    Returns:
        Parsed JSON or default value.
    """
    if not text or not isinstance(text, str):
        return default

    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        if strict:
            raise

        # Try to fix common JSON issues
        try:
            cleaned = re.sub(r",\s*([}\]])", r"\1", text)
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        try:
            cleaned = text.replace("'", '"')
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        return default


def safe_json_dumps(
    obj: Any,
    indent: int = 2,
    sort_keys: bool = True,
    default: str = "str",
) -> str:
    """Safely serialize an object to JSON."""
    def _default(o: Any) -> Any:
        if isinstance(o, datetime):
            return o.isoformat()
        if isinstance(o, Path):
            return str(o)
        if isinstance(o, bytes):
            return o.decode("utf-8", errors="replace")
        if default == "str":
            return str(o)
        raise TypeError(f"Object of type {type(o)} is not JSON serializable")

    return json.dumps(obj, indent=indent, sort_keys=sort_keys, default=_default)


# ==============================================================================
# String Utilities
# ==============================================================================

def truncate(text: str, max_length: int = 50, suffix: str = "...") -> str:
    """Truncate text to max_length, adding suffix if truncated."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def pad_right(text: str, width: int, fill: str = " ") -> str:
    """Pad text on the right to a given width, accounting for ANSI codes."""
    visible_len = len(re.sub(r"\033\[[0-9;]*m", "", text))
    if visible_len >= width:
        return text
    return text + fill * (width - visible_len)


def pad_left(text: str, width: int, fill: str = " ") -> str:
    """Pad text on the left to a given width, accounting for ANSI codes."""
    visible_len = len(re.sub(r"\033\[[0-9;]*m", "", text))
    if visible_len >= width:
        return text
    return fill * (width - visible_len) + text


def slugify(text: str) -> str:
    """Convert text to a URL-safe slug."""
    text = text.lower()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[-\s]+", "-", text)
    return text.strip("-")


def camel_to_snake(name: str) -> str:
    """Convert CamelCase to snake_case."""
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def snake_to_camel(name: str) -> str:
    """Convert snake_case to CamelCase."""
    return "".join(word.capitalize() for word in name.split("_"))


# ==============================================================================
# Quality Parsing
# ==============================================================================

_QUALITY_RESOLUTIONS: Dict[str, Tuple[int, int]] = {
    "240p": (426, 240), "360p": (640, 360), "480p": (854, 480),
    "540p": (960, 540), "720p": (1280, 720), "1080p": (1920, 1080),
    "1440p": (2560, 1440), "2k": (2560, 1440), "2160p": (3840, 2160),
    "4k": (3840, 2160), "5k": (5120, 2880), "2880p": (5120, 2880),
    "4320p": (7680, 4320), "8k": (7680, 4320),
}

_QUALITY_ORDER = [
    "240p", "360p", "480p", "540p", "720p", "1080p",
    "1440p", "2k", "2160p", "4k", "5k", "2880p", "4320p", "8k",
]


def parse_quality(quality: str) -> Tuple[int, int]:
    """
    Parse a quality string to a (width, height) resolution tuple.

    Args:
        quality: Quality string (e.g., "1080p", "4k", "1920x1080").

    Returns:
        Tuple of (width, height).
    """
    quality = quality.strip().lower()

    if quality in _QUALITY_RESOLUTIONS:
        return _QUALITY_RESOLUTIONS[quality]

    # WxH format
    match = re.match(r"^(\d+)x(\d+)$", quality)
    if match:
        return (int(match.group(1)), int(match.group(2)))

    # NxP format (e.g., "1080p")
    match = re.match(r"^(\d+)p$", quality)
    if match:
        h = int(match.group(1))
        w = round(h * 16 / 9)
        return (w, h)

    # Nk format (e.g., "4k")
    match = re.match(r"^(\d+)k$", quality)
    if match:
        k = int(match.group(1))
        return (k * 960, k * 540)

    # Default to 1080p
    return (1920, 1080)


def quality_sort_key(quality: str) -> int:
    """Return a sort key for quality strings (lower = lower quality)."""
    quality = quality.strip().lower()
    if quality in _QUALITY_ORDER:
        return _QUALITY_ORDER.index(quality)
    _, h = parse_quality(quality)
    return h


def get_best_quality(available: List[str], max_quality: str = "8k") -> str:
    """Get the best available quality up to max_quality."""
    max_key = quality_sort_key(max_quality)
    valid = [q for q in available if quality_sort_key(q) <= max_key]
    if not valid:
        return available[0] if available else "720p"
    return max(valid, key=quality_sort_key)


# ==============================================================================
# Human Sorting
# ==============================================================================

_NATURAL_SORT_RE = re.compile(r"(\d+)")


def human_sort_key(text: str) -> List[Union[str, int]]:
    """
    Natural/human sorting key function.

    Sorts strings with numbers in natural order:
    ["file1", "file10", "file2"] -> ["file1", "file2", "file10"]

    Args:
        text: String to generate sort key for.

    Returns:
        List of strings and integers for sorting.
    """
    parts = _NATURAL_SORT_RE.split(str(text))
    result = []
    for part in parts:
        if part.isdigit():
            result.append(int(part))
        else:
            result.append(part.lower())
    return result


def human_sort(iterable: Iterable[str], reverse: bool = False) -> List[str]:
    """Sort strings in natural/human order."""
    return sorted(iterable, key=human_sort_key, reverse=reverse)


# ==============================================================================
# Hash Utilities
# ==============================================================================

def file_hash(filepath: Union[str, Path], algorithm: str = "sha256") -> str:
    """Calculate hash of a file."""
    h = hashlib.new(algorithm)
    try:
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(65536)
                if not chunk:
                    break
                h.update(chunk)
        return h.hexdigest()
    except (OSError, IOError):
        return ""


def string_hash(text: str, algorithm: str = "sha256") -> str:
    """Calculate hash of a string."""
    h = hashlib.new(algorithm)
    h.update(text.encode("utf-8"))
    return h.hexdigest()


# ==============================================================================
# Environment Utilities
# ==============================================================================

def is_termux() -> bool:
    """Check if running in Termux environment."""
    return os.path.exists("/data/data/com.termux")


def is_root() -> bool:
    """Check if running with root privileges."""
    return os.geteuid() == 0 if hasattr(os, "geteuid") else False


def is_venv() -> bool:
    """Check if running inside a virtual environment."""
    return (
        os.environ.get("VIRTUAL_ENV") is not None
        or os.environ.get("CONDA_PREFIX") is not None
        or hasattr(sys, "real_prefix")
        or (hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix)
    )


def get_python_version() -> str:
    """Get Python version string."""
    return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"


def get_os_info() -> Dict[str, str]:
    """Get operating system information."""
    import platform
    info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python": get_python_version(),
    }
    if platform.system() == "Linux":
        try:
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        info["distro"] = line.split("=", 1)[1].strip().strip('"')
                        break
        except (OSError, IOError):
            pass
    return info


# ==============================================================================
# Misc Utilities
# ==============================================================================

def clamp(value: Union[int, float], min_val: Union[int, float], max_val: Union[int, float]) -> Union[int, float]:
    """Clamp a value between min and max."""
    return max(min_val, min(max_val, value))


def safe_get(data: Dict, path: str, default: Any = None, separator: str = ".") -> Any:
    """Safely get a nested dictionary value using dot notation."""
    keys = path.split(separator)
    current = data
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current


def merge_dicts(base: Dict, override: Dict) -> Dict:
    """Deep merge two dictionaries. Override values take precedence."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def env_bool(name: str, default: bool = False) -> bool:
    """Get a boolean value from an environment variable."""
    val = os.environ.get(name, "").lower()
    if val in ("1", "true", "yes", "on", "y"):
        return True
    if val in ("0", "false", "no", "off", "n"):
        return False
    return default


def env_int(name: str, default: int = 0) -> int:
    """Get an integer value from an environment variable."""
    try:
        return int(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        return default


def env_float(name: str, default: float = 0.0) -> float:
    """Get a float value from an environment variable."""
    try:
        return float(os.environ.get(name, str(default)))
    except (ValueError, TypeError):
        return default
