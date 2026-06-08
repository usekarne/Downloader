"""
RS Downloader v10.0.0 - Structured Logging System
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Enterprise-grade structured logging with JSON formatting, rotation,
sensitive data filtering, rate limiting, and remote logging support.
"""

from __future__ import annotations

import gzip
import hashlib
import io
import json
import logging
import logging.handlers
import os
import re
import shutil
import sys
import threading
import time
import traceback
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Deque,
    Dict,
    Iterator,
    List,
    Optional,
    Sequence,
    TextIO,
    Tuple,
    Union,
)


# ---------------------------------------------------------------------------
# Log Format Types
# ---------------------------------------------------------------------------

class LogFormat(Enum):
    """Supported log output formats."""
    PLAIN = "plain"
    JSON = "json"
    STRUCTURED = "structured"
    COLOR = "color"


# ---------------------------------------------------------------------------
# Sensitive Data Filter
# ---------------------------------------------------------------------------

class SensitiveDataFilter(logging.Filter):
    """
    Automatically masks sensitive data in log messages.

    Detects and masks:
    - API keys, tokens, bearer strings
    - Passwords in URLs and auth headers
    - Email addresses
    - Credit card numbers
    - IP addresses (optional)
    - Custom patterns
    """

    # Default patterns that match sensitive data
    DEFAULT_PATTERNS: List[Tuple[str, str]] = [
        # API keys / tokens
        (r'(api[_-]?key\s*[:=]\s*)["\']?(\S{8,})["\']?', r'\1****MASKED****'),
        (r'(token\s*[:=]\s*)["\']?(\S{8,})["\']?', r'\1****MASKED****'),
        (r'(bearer\s+)\S+', r'\1****MASKED****'),
        (r'(authorization\s*[:=]\s*)["\']?\S+["\']?', r'\1****MASKED****'),
        (r'(secret\s*[:=]\s*)["\']?(\S{8,})["\']?', r'\1****MASKED****'),
        # Passwords in URLs
        (r'(://[^:]+:)([^@]+)(@)', r'\1****MASKED****\3'),
        # Password in fields
        (r'(password\s*[:=]\s*)["\']?\S+["\']?', r'\1****MASKED****'),
        (r'(passwd\s*[:=]\s*)["\']?\S+["\']?', r'\1****MASKED****'),
        (r'(pwd\s*[:=]\s*)["\']?\S+["\']?', r'\1****MASKED****'),
        # Email addresses
        (r'([a-zA-Z0-9._%+-])([a-zA-Z0-9._%+-]*)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
         r'\1****@\3'),
        # Credit card numbers (basic pattern)
        (r'\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b',
         r'\1-****-****-\4'),
        # AWS-like keys
        (r'(AKIA[A-Z0-9]{4})[A-Z0-9]{12}', r'\1****MASKED****'),
        # Generic key=value with 'key' in name
        (r'([a-zA-Z_]*key[a-zA-Z_]*\s*[:=]\s*)["\']?(\S{8,})["\']?',
         r'\1****MASKED****'),
    ]

    def __init__(
        self,
        mask_ip: bool = False,
        custom_patterns: Optional[List[Tuple[str, str]]] = None,
        mask_char: str = "****MASKED****",
    ) -> None:
        super().__init__()
        self.mask_ip = mask_ip
        self.mask_char = mask_char
        self._compiled: List[Tuple[re.Pattern, str]] = []
        for pattern, replacement in self.DEFAULT_PATTERNS:
            self._compiled.append((re.compile(pattern, re.IGNORECASE), replacement))
        if custom_patterns:
            for pattern, replacement in custom_patterns:
                self._compiled.append((re.compile(pattern, re.IGNORECASE), replacement))
        if self.mask_ip:
            ip_pattern = (
                r'\b(\d{1,3})\.\d{1,3}\.\d{1,3}\.(\d{1,3})\b',
                r'\1.xxx.xxx.\2',
            )
            self._compiled.append((re.compile(ip_pattern[0]), ip_pattern[1]))

    def filter(self, record: logging.LogRecord) -> bool:
        """Filter (mask) sensitive data from the log record."""
        if record.msg and isinstance(record.msg, str):
            record.msg = self._mask(record.msg)
        if record.args and isinstance(record.args, dict):
            record.args = {
                k: self._mask(str(v)) if isinstance(v, str) else v
                for k, v in record.args.items()
            }
        elif record.args and isinstance(record.args, tuple):
            record.args = tuple(
                self._mask(str(a)) if isinstance(a, str) else a
                for a in record.args
            )
        return True

    def _mask(self, text: str) -> str:
        """Apply all masking patterns to text."""
        for compiled, replacement in self._compiled:
            text = compiled.sub(replacement, text)
        return text


# ---------------------------------------------------------------------------
# Rate-Limiting Filter
# ---------------------------------------------------------------------------

class RateLimitFilter(logging.Filter):
    """
    Rate-limits log messages to prevent log flooding.

    Only allows N messages per key per time window.
    """

    def __init__(
        self,
        max_messages: int = 100,
        window_seconds: float = 60.0,
        key_func: Optional[Callable[[logging.LogRecord], str]] = None,
    ) -> None:
        super().__init__()
        self.max_messages = max_messages
        self.window_seconds = window_seconds
        self.key_func = key_func or (lambda r: r.getMessage()[:128])
        self._counts: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()
        self._dropped = 0

    def filter(self, record: logging.LogRecord) -> bool:
        """Rate-limit log messages."""
        key = self.key_func(record)
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            if key not in self._counts:
                self._counts[key] = deque()
            q = self._counts[key]
            while q and q[0] < cutoff:
                q.popleft()
            if len(q) >= self.max_messages:
                self._dropped += 1
                return False
            q.append(now)
            return True

    @property
    def dropped_count(self) -> int:
        """Return count of dropped messages."""
        return self._dropped


# ---------------------------------------------------------------------------
# Log Rotation Handler
# ---------------------------------------------------------------------------

class LogRotation:
    """
    Advanced log rotation supporting size-based and time-based rotation
    with compression of old log files.
    """

    def __init__(
        self,
        log_dir: Union[str, Path],
        base_name: str = "rs_downloader",
        max_bytes: int = 10 * 1024 * 1024,  # 10 MB
        backup_count: int = 30,
        when: str = "midnight",
        compress: bool = True,
        encoding: str = "utf-8",
    ) -> None:
        self.log_dir = Path(log_dir)
        self.base_name = base_name
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.when = when
        self.compress = compress
        self.encoding = encoding
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def get_log_path(self) -> Path:
        """Return the current log file path."""
        return self.log_dir / f"{self.base_name}.log"

    def create_handler(self) -> logging.Handler:
        """Create the appropriate rotating handler."""
        log_path = self.get_log_path()
        if self.when and self.when != "none":
            handler = logging.handlers.TimedRotatingFileHandler(
                filename=str(log_path),
                when=self.when,
                backupCount=self.backup_count,
                encoding=self.encoding,
            )
            handler.namer = self._namer
            handler.rotator = self._rotator
        else:
            handler = logging.handlers.RotatingFileHandler(
                filename=str(log_path),
                maxBytes=self.max_bytes,
                backupCount=self.backup_count,
                encoding=self.encoding,
            )
            handler.namer = self._namer
            handler.rotator = self._rotator
        return handler

    def _namer(self, default_name: str) -> str:
        """Custom namer for rotated log files."""
        base = default_name.rstrip(".gz")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        parts = base.rsplit(".", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return f"{parts[0]}_{timestamp}.{parts[1]}"
        return f"{base}_{timestamp}"

    def _rotator(self, source: str, dest: str) -> None:
        """Rotate and optionally compress old log files."""
        if self.compress and not dest.endswith(".gz"):
            dest += ".gz"
            with open(source, "rb") as f_in:
                with gzip.open(dest, "wb") as f_out:
                    shutil.copyfileobj(f_in, f_out)
            os.remove(source)
        else:
            shutil.move(source, dest)
        self._cleanup_old_files()

    def _cleanup_old_files(self) -> None:
        """Remove log files beyond backup_count."""
        pattern = f"{self.base_name}*.log*"
        files = sorted(
            self.log_dir.glob(pattern),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for old_file in files[self.backup_count:]:
            try:
                old_file.unlink()
            except OSError:
                pass


# ---------------------------------------------------------------------------
# JSON Formatter
# ---------------------------------------------------------------------------

class JSONFormatter(logging.Formatter):
    """
    Formats log records as JSON objects for structured logging.
    """

    def __init__(
        self,
        include_extras: bool = True,
        timestamp_format: str = "iso",
        ensure_ascii: bool = False,
    ) -> None:
        super().__init__()
        self.include_extras = include_extras
        self.timestamp_format = timestamp_format
        self.ensure_ascii = ensure_ascii

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_obj: Dict[str, Any] = {
            "timestamp": self._format_timestamp(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info and record.exc_info[0] is not None:
            log_obj["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            log_obj["stack_trace"] = self.formatStack(record.stack_info)
        if self.include_extras:
            standard_attrs = {
                "name", "msg", "args", "created", "relativeCreated",
                "exc_info", "exc_text", "stack_info", "lineno", "funcName",
                "pathname", "filename", "module", "levelno", "levelname",
                "thread", "threadName", "process", "processName", "msecs",
                "message", "taskName",
            }
            extras = {
                k: v for k, v in record.__dict__.items()
                if k not in standard_attrs and not k.startswith("_")
            }
            if extras:
                log_obj["extras"] = extras
        log_obj["source"] = {
            "file": record.pathname,
            "line": record.lineno,
            "function": record.funcName,
        }
        log_obj["thread_id"] = record.thread
        log_obj["thread_name"] = record.threadName
        log_obj["process_id"] = record.process
        try:
            return json.dumps(log_obj, ensure_ascii=self.ensure_ascii, default=str)
        except (TypeError, ValueError):
            return json.dumps(
                {"message": record.getMessage(), "error": "serialization_failed"},
                ensure_ascii=self.ensure_ascii,
            )

    def _format_timestamp(self, record: logging.LogRecord) -> str:
        """Format the timestamp according to configuration."""
        dt = datetime.fromtimestamp(record.created, tz=timezone.utc)
        if self.timestamp_format == "iso":
            return dt.isoformat()
        elif self.timestamp_format == "epoch":
            return str(record.created)
        elif self.timestamp_format == "unix_ms":
            return str(int(record.created * 1000))
        else:
            return dt.strftime(self.timestamp_format)


# ---------------------------------------------------------------------------
# Structured Key-Value Formatter
# ---------------------------------------------------------------------------

class StructuredFormatter(logging.Formatter):
    """
    Formats log records as structured key=value pairs.
    """

    def __init__(
        self,
        colorize: bool = False,
        timestamp_format: str = "%Y-%m-%d %H:%M:%S.%f",
    ) -> None:
        super().__init__()
        self.colorize = colorize
        self.timestamp_format = timestamp_format
        self._level_colors: Dict[int, str] = {
            logging.DEBUG: "\033[36m",     # cyan
            logging.INFO: "\033[32m",      # green
            logging.WARNING: "\033[33m",   # yellow
            logging.ERROR: "\033[31m",     # red
            logging.CRITICAL: "\033[35m",  # magenta
        }
        self._reset = "\033[0m"

    def format(self, record: logging.LogRecord) -> str:
        """Format as structured key=value."""
        ts = datetime.fromtimestamp(record.created).strftime(self.timestamp_format)
        level = record.levelname
        msg = record.getMessage()
        parts = [f"ts={ts}", f"level={level}", f"logger={record.name}", f'msg="{msg}"']
        if record.thread and record.threadName != "MainThread":
            parts.append(f"thread={record.threadName}")
        standard_attrs = {
            "name", "msg", "args", "created", "relativeCreated",
            "exc_info", "exc_text", "stack_info", "lineno", "funcName",
            "pathname", "filename", "module", "levelno", "levelname",
            "thread", "threadName", "process", "processName", "msecs",
            "message", "taskName",
        }
        extras = {
            k: v for k, v in record.__dict__.items()
            if k not in standard_attrs and not k.startswith("_")
        }
        for k, v in extras.items():
            parts.append(f"{k}={v}")
        result = " ".join(parts)
        if record.exc_info and record.exc_info[0] is not None:
            result += "\n" + self.formatException(record.exc_info)
        if self.colorize:
            color = self._level_colors.get(record.levelno, "")
            result = f"{color}{result}{self._reset}"
        return result


# ---------------------------------------------------------------------------
# Color Formatter (for console)
# ---------------------------------------------------------------------------

class ColorFormatter(logging.Formatter):
    """
    Console formatter with colorized output.
    """

    COLORS: Dict[int, str] = {
        logging.DEBUG: "\033[36m",
        logging.INFO: "\033[32m",
        logging.WARNING: "\033[33m",
        logging.ERROR: "\033[31m",
        logging.CRITICAL: "\033[1;31m",
    }
    RESET = "\033[0m"
    GREY = "\033[90m"
    CYAN = "\033[36m"

    def __init__(
        self,
        fmt: str = "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
        datefmt: str = "%H:%M:%S",
    ) -> None:
        super().__init__(fmt=fmt, datefmt=datefmt)

    def format(self, record: logging.LogRecord) -> str:
        """Colorize the log output."""
        color = self.COLORS.get(record.levelno, "")
        record.levelname = f"{color}{record.levelname:<8}{self.RESET}"
        record.name = f"{self.CYAN}{record.name}{self.RESET}"
        record.asctime = f"{self.GREY}{record.asctime}{self.RESET}"
        result = super().format(record)
        if record.exc_info and record.exc_info[0] is not None:
            result += "\n" + self.formatException(record.exc_info)
        return result


# ---------------------------------------------------------------------------
# Remote Logging Handler
# ---------------------------------------------------------------------------

class SyslogHandler(logging.Handler):
    """
    Sends log messages to a syslog server over UDP/TCP.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 514,
        protocol: str = "udp",
        facility: int = 1,  # user
        app_name: str = "rs-downloader",
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.protocol = protocol
        self.facility = facility
        self.app_name = app_name
        self._socket: Any = None
        self._lock_socket = threading.Lock()

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record to syslog."""
        try:
            import socket
            msg = self.format(record)
            pri = (self.facility * 8) + self._syslog_severity(record.levelno)
            hostname = socket.gethostname()
            timestamp = datetime.now().strftime("%b %d %H:%M:%S")
            syslog_msg = f"<{pri}>{timestamp} {hostname} {self.app_name}: {msg}"
            data = syslog_msg.encode("utf-8")[:8192]
            with self._lock_socket:
                if self.protocol == "udp":
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    try:
                        sock.sendto(data, (self.host, self.port))
                    finally:
                        sock.close()
                else:
                    if self._socket is None:
                        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        self._socket.connect((self.host, self.port))
                    self._socket.sendall(data + b"\n")
        except Exception:
            self.handleError(record)

    def _syslog_severity(self, levelno: int) -> int:
        """Map Python log level to syslog severity."""
        mapping = {
            logging.DEBUG: 7,
            logging.INFO: 6,
            logging.WARNING: 4,
            logging.ERROR: 3,
            logging.CRITICAL: 2,
        }
        return mapping.get(levelno, 6)

    def close(self) -> None:
        """Close the syslog socket."""
        with self._lock_socket:
            if self._socket:
                try:
                    self._socket.close()
                except Exception:
                    pass
                self._socket = None
        super().close()


class WebhookHandler(logging.Handler):
    """
    Sends log messages to an HTTP webhook endpoint.
    """

    def __init__(
        self,
        url: str,
        min_level: int = logging.ERROR,
        headers: Optional[Dict[str, str]] = None,
        batch_size: int = 10,
        flush_interval: float = 5.0,
        timeout: float = 10.0,
    ) -> None:
        super().__init__()
        self.url = url
        self.min_level = min_level
        self.headers = headers or {"Content-Type": "application/json"}
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.timeout = timeout
        self._buffer: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._last_flush = time.monotonic()
        self._flush_thread: Optional[threading.Thread] = None

    def emit(self, record: logging.LogRecord) -> None:
        """Buffer log record for batch sending."""
        if record.levelno < self.min_level:
            return
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "source": f"{record.pathname}:{record.lineno}",
        }
        if record.exc_info and record.exc_info[0] is not None:
            entry["exception"] = self.formatException(record.exc_info)
        with self._lock:
            self._buffer.append(entry)
            should_flush = (
                len(self._buffer) >= self.batch_size
                or (time.monotonic() - self._last_flush) >= self.flush_interval
            )
        if should_flush:
            self.flush()

    def flush(self) -> None:
        """Send buffered log entries to the webhook."""
        with self._lock:
            if not self._buffer:
                return
            batch = self._buffer[:]
            self._buffer.clear()
            self._last_flush = time.monotonic()
        try:
            import urllib.request
            payload = json.dumps({"logs": batch}, default=str).encode("utf-8")
            req = urllib.request.Request(
                self.url,
                data=payload,
                headers=self.headers,
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                _ = resp.read()
        except Exception:
            pass  # silently fail - don't create log loops


# ---------------------------------------------------------------------------
# Audit Logger
# ---------------------------------------------------------------------------

class AuditLogger:
    """
    Dedicated audit logger for security-relevant events.

    Writes to a separate audit log file with tamper-evident chain hashes.
    """

    def __init__(
        self,
        log_dir: Union[str, Path],
        filename: str = "audit.log",
        chain_hash: bool = True,
    ) -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_path = self.log_dir / filename
        self.chain_hash = chain_hash
        self._previous_hash = "GENESIS"
        self._lock = threading.Lock()
        self._logger = logging.getLogger("rs_downloader.audit")
        self._setup_file_handler()

    def _setup_file_handler(self) -> None:
        """Set up the audit file handler."""
        handler = logging.handlers.RotatingFileHandler(
            str(self.log_path),
            maxBytes=50 * 1024 * 1024,
            backupCount=90,
            encoding="utf-8",
        )
        handler.setFormatter(JSONFormatter())
        self._logger.addHandler(handler)
        self._logger.setLevel(logging.INFO)

    def log_event(
        self,
        event_type: str,
        actor: str,
        action: str,
        resource: str = "",
        details: Optional[Dict[str, Any]] = None,
        outcome: str = "success",
    ) -> None:
        """Log an audit event with chain hash integrity."""
        entry = {
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "resource": resource,
            "details": details or {},
            "outcome": outcome,
            "timestamp": datetime.now(tz=timezone.utc).isoformat(),
        }
        if self.chain_hash:
            entry_text = json.dumps(entry, sort_keys=True, default=str)
            current_hash = hashlib.sha256(
                f"{self._previous_hash}:{entry_text}".encode()
            ).hexdigest()
            entry["chain_hash"] = current_hash
            with self._lock:
                self._previous_hash = current_hash
        self._logger.info("AUDIT", extra=entry)

    def log_auth(self, actor: str, success: bool, method: str = "password") -> None:
        """Log authentication event."""
        self.log_event(
            event_type="authentication",
            actor=actor,
            action="login",
            details={"method": method},
            outcome="success" if success else "failure",
        )

    def log_config_change(
        self,
        actor: str,
        key: str,
        old_value: Any,
        new_value: Any,
    ) -> None:
        """Log configuration change."""
        self.log_event(
            event_type="config_change",
            actor=actor,
            action="update",
            resource=key,
            details={"old_value": str(old_value), "new_value": str(new_value)},
        )

    def log_access(self, actor: str, resource: str, action: str = "read") -> None:
        """Log resource access."""
        self.log_event(
            event_type="access",
            actor=actor,
            action=action,
            resource=resource,
        )

    def log_download(
        self,
        actor: str,
        url: str,
        outcome: str = "success",
        file_size: int = 0,
    ) -> None:
        """Log download event."""
        self.log_event(
            event_type="download",
            actor=actor,
            action="download",
            resource=url,
            outcome=outcome,
            details={"file_size": file_size},
        )


# ---------------------------------------------------------------------------
# Performance Logger (Timing Context Manager)
# ---------------------------------------------------------------------------

@dataclass
class TimingResult:
    """Result of a timing measurement."""
    name: str
    elapsed_ms: float
    start_time: float
    end_time: float
    success: bool
    error: Optional[str] = None


class PerformanceLogger:
    """
    Performance logging with timing context manager.
    Tracks operation durations and reports slow operations.
    """

    def __init__(
        self,
        logger: Optional[logging.Logger] = None,
        slow_threshold_ms: float = 5000.0,
        track_percentiles: bool = True,
    ) -> None:
        self.logger = logger or logging.getLogger("rs_downloader.perf")
        self.slow_threshold_ms = slow_threshold_ms
        self.track_percentiles = track_percentiles
        self._timings: Dict[str, List[float]] = {}
        self._lock = threading.Lock()

    @contextmanager
    def measure(
        self,
        name: str,
        level: int = logging.DEBUG,
        threshold_ms: Optional[float] = None,
        **extras: Any,
    ) -> Iterator[TimingResult]:
        """Context manager to measure execution time of a block."""
        start = time.perf_counter()
        result = TimingResult(
            name=name,
            elapsed_ms=0.0,
            start_time=start,
            end_time=0.0,
            success=True,
        )
        try:
            yield result
        except Exception as e:
            result.success = False
            result.error = str(e)
            raise
        finally:
            end = time.perf_counter()
            result.elapsed_ms = (end - start) * 1000.0
            result.end_time = end
            threshold = threshold_ms or self.slow_threshold_ms
            log_level = logging.WARNING if result.elapsed_ms > threshold else level
            extra_data = {
                "operation": name,
                "elapsed_ms": round(result.elapsed_ms, 2),
                "slow": result.elapsed_ms > threshold,
                **extras,
            }
            self.logger.log(
                log_level,
                f"[PERF] {name}: {result.elapsed_ms:.2f}ms"
                + (" (SLOW)" if result.elapsed_ms > threshold else ""),
                extra=extra_data,
            )
            if self.track_percentiles:
                with self._lock:
                    if name not in self._timings:
                        self._timings[name] = []
                    self._timings[name].append(result.elapsed_ms)

    def get_stats(self, name: str) -> Optional[Dict[str, float]]:
        """Get timing statistics for an operation."""
        with self._lock:
            if name not in self._timings or not self._timings[name]:
                return None
            times = sorted(self._timings[name])
            n = len(times)
            return {
                "count": n,
                "min_ms": times[0],
                "max_ms": times[-1],
                "avg_ms": sum(times) / n,
                "p50_ms": times[int(n * 0.5)],
                "p90_ms": times[int(n * 0.9)],
                "p95_ms": times[int(n * 0.95)],
                "p99_ms": times[int(n * 0.99)] if n > 1 else times[-1],
            }

    def get_all_stats(self) -> Dict[str, Dict[str, float]]:
        """Get timing statistics for all tracked operations."""
        with self._lock:
            return {
                name: self.get_stats(name)
                for name in self._timings
                if self._timings[name]
            }

    def reset(self, name: Optional[str] = None) -> None:
        """Reset timing data."""
        with self._lock:
            if name:
                self._timings.pop(name, None)
            else:
                self._timings.clear()


# ---------------------------------------------------------------------------
# Log Aggregator & Search
# ---------------------------------------------------------------------------

class LogAggregator:
    """
    Aggregates and searches log entries across multiple log files.
    """

    def __init__(self, log_dir: Union[str, Path]) -> None:
        self.log_dir = Path(log_dir)
        self._cache: List[Dict[str, Any]] = []
        self._cache_lock = threading.Lock()
        self._last_indexed: float = 0.0

    def search(
        self,
        query: str,
        level: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        logger_name: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Search log entries by query and filters."""
        results: List[Dict[str, Any]] = []
        log_files = sorted(self.log_dir.glob("*.log*"), reverse=True)
        query_lower = query.lower()
        for log_file in log_files:
            if len(results) >= limit:
                break
            try:
                entries = self._parse_file(log_file)
            except Exception:
                continue
            for entry in entries:
                if len(results) >= limit:
                    break
                if not self._matches(entry, query_lower, level, start_time, end_time, logger_name):
                    continue
                results.append(entry)
        return results

    def _matches(
        self,
        entry: Dict[str, Any],
        query_lower: str,
        level: Optional[str],
        start_time: Optional[datetime],
        end_time: Optional[datetime],
        logger_name: Optional[str],
    ) -> bool:
        """Check if entry matches all filter criteria."""
        msg = entry.get("message", "").lower()
        if query_lower and query_lower not in msg:
            return False
        if level and entry.get("level", "").upper() != level.upper():
            return False
        if logger_name and logger_name not in entry.get("logger", ""):
            return False
        ts = entry.get("timestamp")
        if ts:
            try:
                entry_dt = datetime.fromisoformat(ts)
                if start_time and entry_dt < start_time:
                    return False
                if end_time and entry_dt > end_time:
                    return False
            except (ValueError, TypeError):
                pass
        return True

    def _parse_file(self, path: Path) -> List[Dict[str, Any]]:
        """Parse a log file into structured entries."""
        entries: List[Dict[str, Any]] = []
        opener = gzip.open if path.suffix == ".gz" else open
        try:
            with opener(path, "rt", encoding="utf-8", errors="replace") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = self._parse_line(line)
                    if entry:
                        entries.append(entry)
        except Exception:
            pass
        return entries

    def _parse_line(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse a single log line (JSON or plain text)."""
        if line.startswith("{"):
            try:
                return json.loads(line)
            except json.JSONDecodeError:
                pass
        # Try structured format: ts=... level=... logger=... msg="..."
        parts: Dict[str, str] = {}
        for match in re.finditer(r'(\w+)=((?:"[^"]*")|\S+)', line):
            key, value = match.group(1), match.group(2)
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            parts[key] = value
        if parts:
            return parts
        # Fallback: plain text
        return {"message": line, "raw": True}

    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics across all log files."""
        total_size = sum(f.stat().st_size for f in self.log_dir.glob("*.log*") if f.is_file())
        file_count = len(list(self.log_dir.glob("*.log*")))
        return {
            "log_dir": str(self.log_dir),
            "file_count": file_count,
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
        }


# ---------------------------------------------------------------------------
# RSLogger - Main Logger Class
# ---------------------------------------------------------------------------

class RSLogger:
    """
    Custom logger with structured output, JSON formatting, rotation,
    sensitive data filtering, rate limiting, and async logging support.

    Usage:
        logger = RSLogger("my_module", log_dir="/var/log/rs_downloader")
        logger.info("Download started", url="https://example.com/file.zip")
        logger.error("Download failed", error="Connection timeout", retry=3)
    """

    _instances: Dict[str, "RSLogger"] = {}
    _instances_lock = threading.Lock()

    def __init__(
        self,
        name: str,
        level: int = logging.DEBUG,
        log_dir: Union[str, Path] = "logs",
        log_format: LogFormat = LogFormat.COLOR,
        enable_file: bool = True,
        enable_console: bool = True,
        sensitive_filter: bool = True,
        rate_limit: int = 0,
        rotation_max_bytes: int = 10 * 1024 * 1024,
        rotation_backup_count: int = 30,
        rotation_when: str = "midnight",
        compress_rotated: bool = True,
        enable_remote: bool = False,
        remote_url: str = "",
        remote_min_level: int = logging.ERROR,
        json_output: bool = False,
    ) -> None:
        self._name = name
        self._log_dir = Path(log_dir)
        self._log_format = log_format
        self._level = level
        self._logger = logging.getLogger(f"rs_downloader.{name}")
        self._logger.setLevel(level)
        self._logger.propagate = False
        self._handlers: List[logging.Handler] = []
        self._perf = PerformanceLogger(self._logger)
        self._audit: Optional[AuditLogger] = None
        self._async_queue: Optional[queue.Queue] = None
        self._async_thread: Optional[threading.Thread] = None
        self._async_running = False

        if enable_console:
            self._add_console_handler(json_output)
        if enable_file:
            self._add_file_handler(
                rotation_max_bytes, rotation_backup_count,
                rotation_when, compress_rotated, json_output,
            )
        if sensitive_filter:
            self._logger.addFilter(SensitiveDataFilter())
        if rate_limit > 0:
            self._logger.addFilter(RateLimitFilter(max_messages=rate_limit))
        if enable_remote and remote_url:
            self._add_remote_handler(remote_url, remote_min_level)

    def _add_console_handler(self, json_output: bool = False) -> None:
        """Add console (stdout) handler."""
        handler = logging.StreamHandler(sys.stdout)
        if json_output:
            handler.setFormatter(JSONFormatter())
        elif self._log_format == LogFormat.STRUCTURED:
            handler.setFormatter(StructuredFormatter(colorize=sys.stdout.isatty()))
        elif self._log_format == LogFormat.JSON:
            handler.setFormatter(JSONFormatter())
        elif self._log_format == LogFormat.COLOR and sys.stdout.isatty():
            handler.setFormatter(ColorFormatter())
        else:
            handler.setFormatter(
                logging.Formatter("%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s")
            )
        handler.setLevel(self._level)
        self._logger.addHandler(handler)
        self._handlers.append(handler)

    def _add_file_handler(
        self,
        max_bytes: int,
        backup_count: int,
        when: str,
        compress: bool,
        json_output: bool,
    ) -> None:
        """Add rotating file handler."""
        self._log_dir.mkdir(parents=True, exist_ok=True)
        rotation = LogRotation(
            self._log_dir,
            base_name=self._name,
            max_bytes=max_bytes,
            backup_count=backup_count,
            when=when,
            compress=compress,
        )
        handler = rotation.create_handler()
        if json_output or self._log_format == LogFormat.JSON:
            handler.setFormatter(JSONFormatter())
        elif self._log_format == LogFormat.STRUCTURED:
            handler.setFormatter(StructuredFormatter())
        else:
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s │ %(levelname)-8s │ %(name)s │ %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
        handler.setLevel(self._level)
        self._logger.addHandler(handler)
        self._handlers.append(handler)

    def _add_remote_handler(self, url: str, min_level: int) -> None:
        """Add webhook remote logging handler."""
        handler = WebhookHandler(url=url, min_level=min_level)
        handler.setFormatter(JSONFormatter())
        self._logger.addHandler(handler)
        self._handlers.append(handler)

    # -- Standard logging methods --

    def debug(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log debug message."""
        self._logger.debug(msg, *args, extra=kwargs)

    def info(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log info message."""
        self._logger.info(msg, *args, extra=kwargs)

    def warning(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log warning message."""
        self._logger.warning(msg, *args, extra=kwargs)

    def error(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log error message."""
        self._logger.error(msg, *args, extra=kwargs)

    def critical(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log critical message."""
        self._logger.critical(msg, *args, extra=kwargs)

    def exception(self, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log exception with traceback."""
        self._logger.exception(msg, *args, extra=kwargs)

    def log(self, level: int, msg: str, *args: Any, **kwargs: Any) -> None:
        """Log at specified level."""
        self._logger.log(level, msg, *args, extra=kwargs)

    # -- Structured logging shortcuts --

    def download_start(self, url: str, filename: str = "", **kwargs: Any) -> None:
        """Log download start event."""
        self.info("Download started", url=url, filename=filename, event="download_start", **kwargs)

    def download_progress(
        self,
        url: str,
        downloaded: int,
        total: int,
        speed: float = 0.0,
        **kwargs: Any,
    ) -> None:
        """Log download progress event."""
        pct = (downloaded / total * 100) if total > 0 else 0.0
        self.debug(
            "Download progress",
            url=url,
            downloaded=downloaded,
            total=total,
            percent=round(pct, 1),
            speed_kbps=round(speed / 1024, 1),
            event="download_progress",
            **kwargs,
        )

    def download_complete(self, url: str, path: str, size: int, elapsed: float, **kwargs: Any) -> None:
        """Log download completion."""
        speed = size / elapsed if elapsed > 0 else 0.0
        self.info(
            "Download complete",
            url=url,
            path=path,
            size_bytes=size,
            elapsed_seconds=round(elapsed, 2),
            speed_kbps=round(speed / 1024, 1),
            event="download_complete",
            **kwargs,
        )

    def download_error(self, url: str, error: str, **kwargs: Any) -> None:
        """Log download error."""
        self.error("Download failed", url=url, error=error, event="download_error", **kwargs)

    # -- Performance logging --

    @property
    def perf(self) -> PerformanceLogger:
        """Access the performance logger."""
        return self._perf

    @contextmanager
    def timer(self, name: str, **kwargs: Any) -> Iterator[TimingResult]:
        """Context manager for timing code blocks."""
        with self._perf.measure(name, **kwargs) as result:
            yield result

    # -- Audit logging --

    @property
    def audit(self) -> AuditLogger:
        """Access the audit logger (lazy initialization)."""
        if self._audit is None:
            self._audit = AuditLogger(self._log_dir)
        return self._audit

    # -- Async logging --

    def start_async(self, max_queue_size: int = 10000) -> None:
        """Start async logging thread for non-blocking log writes."""
        import queue as q
        self._async_queue = q.Queue(maxsize=max_queue_size)
        self._async_running = True
        self._async_thread = threading.Thread(
            target=self._async_worker,
            name=f"rs_logger_async_{self._name}",
            daemon=True,
        )
        self._async_thread.start()

    def stop_async(self, timeout: float = 5.0) -> None:
        """Stop async logging thread."""
        self._async_running = False
        if self._async_queue:
            self._async_queue.put(None)  # sentinel
        if self._async_thread and self._async_thread.is_alive():
            self._async_thread.join(timeout=timeout)

    def async_log(self, level: int, msg: str, **kwargs: Any) -> None:
        """Non-blocking async log (drops if queue is full)."""
        if self._async_queue is None:
            self._log(level, msg, **kwargs)
            return
        try:
            self._async_queue.put_nowait((level, msg, kwargs))
        except Exception:
            pass  # drop message if queue is full

    def _async_worker(self) -> None:
        """Worker thread for async logging."""
        while self._async_running:
            if self._async_queue is None:
                break
            try:
                item = self._async_queue.get(timeout=0.5)
                if item is None:
                    break
                level, msg, kwargs = item
                self._logger.log(level, msg, extra=kwargs)
            except Exception:
                continue
        # Drain remaining
        if self._async_queue:
            while not self._async_queue.empty():
                try:
                    item = self._async_queue.get_nowait()
                    if item is None:
                        continue
                    level, msg, kwargs = item
                    self._logger.log(level, msg, extra=kwargs)
                except Exception:
                    break

    # -- Lifecycle --

    def set_level(self, level: int) -> None:
        """Change the logging level."""
        self._level = level
        self._logger.setLevel(level)
        for handler in self._handlers:
            handler.setLevel(level)

    def add_handler(self, handler: logging.Handler) -> None:
        """Add a custom handler."""
        self._logger.addHandler(handler)
        self._handlers.append(handler)

    def remove_handler(self, handler: logging.Handler) -> None:
        """Remove a handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
        self._logger.removeHandler(handler)

    def close(self) -> None:
        """Close all handlers and clean up."""
        self.stop_async()
        for handler in self._handlers[:]:
            handler.close()
            self._logger.removeHandler(handler)
        self._handlers.clear()

    @property
    def name(self) -> str:
        """Logger name."""
        return self._name

    @property
    def effective_level(self) -> int:
        """Effective logging level."""
        return self._logger.getEffectiveLevel()


# ---------------------------------------------------------------------------
# Module-Level Factory Function
# ---------------------------------------------------------------------------

_logger_cache: Dict[str, RSLogger] = {}
_logger_cache_lock = threading.Lock()


def get_logger(
    name: str,
    level: int = logging.DEBUG,
    log_dir: Union[str, Path] = "logs",
    log_format: LogFormat = LogFormat.COLOR,
    enable_file: bool = True,
    enable_console: bool = True,
    sensitive_filter: bool = True,
    rate_limit: int = 0,
    **kwargs: Any,
) -> RSLogger:
    """
    Factory function to get or create a named RSLogger instance.

    Caches loggers by name so only one instance per name exists.

    Args:
        name: Logger name (usually module name).
        level: Logging level (default: DEBUG).
        log_dir: Directory for log files.
        log_format: Output format (PLAIN, JSON, STRUCTURED, COLOR).
        enable_file: Enable file logging.
        enable_console: Enable console logging.
        sensitive_filter: Filter sensitive data.
        rate_limit: Max messages per key per minute (0=unlimited).
        **kwargs: Additional RSLogger arguments.

    Returns:
        RSLogger instance.
    """
    with _logger_cache_lock:
        if name in _logger_cache:
            existing = _logger_cache[name]
            if level != existing.effective_level:
                existing.set_level(level)
            return existing
        logger = RSLogger(
            name=name,
            level=level,
            log_dir=log_dir,
            log_format=log_format,
            enable_file=enable_file,
            enable_console=enable_console,
            sensitive_filter=sensitive_filter,
            rate_limit=rate_limit,
            **kwargs,
        )
        _logger_cache[name] = logger
        return logger


def reset_logger_cache() -> None:
    """Clear all cached logger instances and close them."""
    with _logger_cache_lock:
        for logger in _logger_cache.values():
            try:
                logger.close()
            except Exception:
                pass
        _logger_cache.clear()


def list_loggers() -> List[str]:
    """List all cached logger names."""
    with _logger_cache_lock:
        return list(_logger_cache.keys())
