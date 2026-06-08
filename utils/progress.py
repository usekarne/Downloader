#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Progress Display System
INFINITE HYPERNOVA SOVEREIGN NEXUS

Rich progress bars, spinners, multi-progress tracking,
and specialized download progress display with thread-safe updates.

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng
License: MIT
"""

import sys
import time
import threading
import math
from typing import Optional, Dict, List, Callable, Any, Tuple
from dataclasses import dataclass, field
from contextlib import contextmanager
from enum import Enum

from .colors import (
    colorize,
    get_theme,
    supports_color,
    caps,
    strip_ansi,
    ansi_len,
    ESC,
    hide_cursor,
    show_cursor,
    clear_line,
    move_cursor_up,
)


# ==============================================================================
# Formatters
# ==============================================================================

class FileSize:
    """Format file sizes in human-readable form."""

    UNITS = ["B", "KB", "MB", "GB", "TB", "PB"]
    BINARY_UNITS = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]

    @staticmethod
    def format(
        size: float,
        binary: bool = False,
        precision: int = 2,
        unit: Optional[str] = None,
    ) -> str:
        """Format a file size to human-readable string."""
        if size < 0:
            return f"-{FileSize.format(-size, binary, precision, unit)}"
        if size == 0:
            return f"0 {unit or 'B'}"

        base = 1024 if binary else 1000
        units = FileSize.BINARY_UNITS if binary else FileSize.UNITS

        if unit and unit in units:
            idx = units.index(unit)
            value = size / (base ** idx)
            return f"{value:.{precision}f} {unit}"

        for i, u in enumerate(units):
            threshold = base ** (i + 1)
            if size < threshold or i == len(units) - 1:
                value = size / (base ** i)
                return f"{value:.{precision}f} {u}"

        return f"{size:.{precision}f} B"

    @staticmethod
    def parse(size_str: str) -> float:
        """Parse a human-readable size string to bytes."""
        size_str = size_str.strip().upper()
        multipliers = {
            "B": 1, "KB": 1000, "MB": 1000**2, "GB": 1000**3,
            "TB": 1000**4, "PB": 1000**5,
            "KIB": 1024, "MIB": 1024**2, "GIB": 1024**3,
            "TIB": 1024**4, "PIB": 1024**5,
            "K": 1000, "M": 1000**2, "G": 1000**3,
        }
        for suffix, mult in sorted(multipliers.items(), key=lambda x: -len(x[0])):
            if size_str.endswith(suffix):
                try:
                    return float(size_str[:-len(suffix)].strip()) * mult
                except ValueError:
                    break
        try:
            return float(size_str)
        except ValueError:
            return 0.0


class TransferSpeed:
    """Format transfer speeds in human-readable form."""

    @staticmethod
    def format(speed_bps: float, precision: int = 2) -> str:
        """Format a transfer speed (e.g., '1.23 MB/s')."""
        return f"{FileSize.format(speed_bps, precision=precision)}/s"

    @staticmethod
    def from_bytes(downloaded: int, elapsed: float) -> float:
        """Calculate speed from bytes downloaded and elapsed time."""
        if elapsed <= 0:
            return 0.0
        return downloaded / elapsed


class TimeRemaining:
    """Format remaining time estimates."""

    @staticmethod
    def format(seconds: float, compact: bool = False) -> str:
        """Format a duration to human-readable string."""
        if seconds < 0 or math.isinf(seconds) or math.isnan(seconds):
            return "--:--"
        if seconds == 0:
            return "0s" if compact else "0 seconds"

        intervals = [("d", 86400), ("h", 3600), ("m", 60), ("s", 1)]

        if compact:
            parts = []
            for suffix, duration in intervals:
                if seconds >= duration:
                    count = int(seconds // duration)
                    seconds %= duration
                    parts.append(f"{count}{suffix}")
                    if len(parts) >= 2:
                        break
            return " ".join(parts) if parts else "<1s"

        verbose_intervals = [
            ("day", "days", 86400), ("hour", "hours", 3600),
            ("minute", "minutes", 60), ("second", "seconds", 1),
        ]
        parts = []
        for singular, plural, duration in verbose_intervals:
            if seconds >= duration:
                count = int(seconds // duration)
                seconds %= duration
                word = singular if count == 1 else plural
                parts.append(f"{count} {word}")
                if len(parts) >= 2:
                    break
        return ", ".join(parts) if parts else "<1 second"

    @staticmethod
    def estimate(downloaded: int, total: int, speed: float) -> float:
        """Estimate remaining time in seconds."""
        if speed <= 0 or total <= 0:
            return float("inf")
        return (total - downloaded) / speed


# Standalone helper formatters
def format_speed(bytes_per_sec: float, precision: int = 2) -> str:
    """Format speed in human-readable form (color-coded)."""
    return TransferSpeed.format(bytes_per_sec, precision)

def format_size(bytes_val: float, precision: int = 2) -> str:
    """Format size in human-readable form."""
    return FileSize.format(bytes_val, precision=precision)

def format_time(seconds: float, compact: bool = False) -> str:
    """Format time in human-readable form."""
    return TimeRemaining.format(seconds, compact)


# ==============================================================================
# Progress State
# ==============================================================================

class ProgressState(Enum):
    """Progress bar state."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ==============================================================================
# Spinner
# ==============================================================================

class Spinner:
    """Animated spinner with customizable frames."""

    FRAMES = {
        "dots": ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"],
        "line": ["-", "\\", "|", "/"],
        "arrow": ["←", "↖", "↑", "↗", "→", "↘", "↓", "↙"],
        "bouncing": ["[    ]", "[=   ]", "[==  ]", "[=== ]", "[ ===]", "[  ==]", "[   =]", "[    ]"],
        "pulse": ["●", "◉", "○"],
        "wave": ["▁", "▂", "▃", "▄", "▅", "▆", "▇", "█", "▇", "▆", "▅", "▄", "▃", "▂"],
        "braille": ["⠁", "⠃", "⠇", "⡇", "⡗", "⡷", "⣷", "⣯", "⣟", "⡿", "⢿", "⣻", "⣽", "⣾"],
    }

    def __init__(
        self,
        message: str = "",
        frames: Optional[List[str]] = None,
        interval: float = 0.1,
        style: str = "dots",
        color: Optional[str] = None,
    ):
        self.message = message
        self.frames = frames or self.FRAMES.get(style, self.FRAMES["dots"])
        self.interval = interval
        self.color = color or get_theme().accent
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._frame_idx = 0
        self._lock = threading.Lock()

    def start(self) -> "Spinner":
        """Start the spinner animation."""
        if self._running:
            return self
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def stop(self, final_message: Optional[str] = None) -> None:
        """Stop the spinner animation."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if sys.stdout.isatty():
            sys.stdout.write("\r" + " " * 80 + "\r")
            if final_message:
                theme = get_theme()
                print(colorize(f"  ✓ {final_message}", fg=theme.success))
            sys.stdout.flush()

    def update(self, message: str) -> None:
        """Update the spinner message."""
        with self._lock:
            self.message = message

    def succeed(self, message: Optional[str] = None) -> None:
        """Stop spinner with success indication."""
        self.stop(final_message=message or self.message)

    def fail(self, message: Optional[str] = None) -> None:
        """Stop spinner with failure indication."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        theme = get_theme()
        msg = message or self.message
        if sys.stdout.isatty():
            sys.stdout.write("\r" + " " * 80 + "\r")
            print(colorize(f"  ✗ {msg}", fg=theme.error))
            sys.stdout.flush()

    def _spin(self) -> None:
        """Animation loop."""
        while self._running:
            frame = self.frames[self._frame_idx % len(self.frames)]
            self._frame_idx += 1
            if sys.stdout.isatty():
                with self._lock:
                    msg = self.message
                line = f"  {colorize(frame, fg=self.color)} {msg}"
                sys.stdout.write(f"\r{line}")
                sys.stdout.flush()
            time.sleep(self.interval)

    def __enter__(self) -> "Spinner":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.succeed()
        else:
            self.fail()


# ==============================================================================
# Progress Bar
# ==============================================================================

class ProgressBar:
    """
    Rich progress bar with percentage, speed, ETA, and file size display.
    Thread-safe for concurrent updates.
    """

    BAR_STYLES = {
        "block": ("█", "░"), "sharp": ("#", "-"), "arrow": ("▸", "·"),
        "pipe": ("▓", "░"), "filled": ("■", "□"), "classic": ("=", "-"),
        "dot": ("●", "○"), "unicode": ("▓", "░"),
    }

    def __init__(
        self,
        total: int = 0,
        desc: str = "",
        unit: str = "B",
        bar_style: str = "block",
        width: int = 30,
        color: Optional[str] = None,
        show_speed: bool = True,
        show_eta: bool = True,
        show_size: bool = True,
        min_interval: float = 0.1,
    ):
        self.total = total
        self.desc = desc
        self.unit = unit
        self.width = width
        self.show_speed = show_speed
        self.show_eta = show_eta
        self.show_size = show_size
        self.min_interval = min_interval

        self._current = 0
        self._state = ProgressState.PENDING
        self._start_time: Optional[float] = None
        self._last_update = 0.0
        self._speed_samples: List[Tuple[float, int]] = []
        self._current_speed = 0.0
        self._lock = threading.Lock()

        style = self.BAR_STYLES.get(bar_style, self.BAR_STYLES["block"])
        self._fill_char = style[0]
        self._empty_char = style[1]
        self._color = color

    @property
    def current(self) -> int:
        return self._current

    @property
    def state(self) -> ProgressState:
        return self._state

    @property
    def percentage(self) -> float:
        if self.total <= 0:
            return 0.0
        return min(100.0, (self._current / self.total) * 100)

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return time.time() - self._start_time

    @property
    def speed(self) -> float:
        return self._current_speed

    @property
    def eta(self) -> float:
        if self.total <= 0 or self._current_speed <= 0:
            return float("inf")
        return (self.total - self._current) / self._current_speed

    def start(self) -> "ProgressBar":
        """Start the progress bar."""
        with self._lock:
            self._state = ProgressState.RUNNING
            self._start_time = time.time()
        self._render()
        return self

    def update(self, n: int = 1) -> None:
        """Update progress by n units."""
        now = time.time()
        with self._lock:
            self._current += n
            self._speed_samples.append((now, self._current))
            if len(self._speed_samples) > 20:
                self._speed_samples = self._speed_samples[-20:]
            self._calculate_speed()

        if now - self._last_update >= self.min_interval or self._current >= self.total:
            self._last_update = now
            self._render()

        if self._current >= self.total and self.total > 0:
            self.complete()

    def set_current(self, value: int) -> None:
        """Set the current progress value directly."""
        now = time.time()
        with self._lock:
            self._current = value
            self._speed_samples.append((now, value))
            if len(self._speed_samples) > 20:
                self._speed_samples = self._speed_samples[-20:]
            self._calculate_speed()

        if now - self._last_update >= self.min_interval:
            self._last_update = now
            self._render()

    def complete(self) -> None:
        """Mark the progress as complete."""
        with self._lock:
            self._state = ProgressState.COMPLETED
            self._current = self.total
        self._render(final=True)

    def finish(self) -> None:
        """Alias for complete()."""
        self.complete()

    def fail(self, message: str = "") -> None:
        """Mark the progress as failed."""
        with self._lock:
            self._state = ProgressState.FAILED
        self._render(final=True, error=message)

    def pause(self) -> None:
        with self._lock:
            self._state = ProgressState.PAUSED

    def resume(self) -> None:
        with self._lock:
            self._state = ProgressState.RUNNING

    def render(self) -> str:
        """Render the progress bar as a string."""
        theme = get_theme()
        bar_color = self._color or self._speed_color(theme)
        parts = []

        if self.desc:
            max_desc = 25
            d = self.desc[:max_desc - 2] + ".." if len(self.desc) > max_desc else self.desc
            parts.append(colorize(d, fg=theme.title, style="bold"))

        if self.total > 0:
            pct = self.percentage / 100.0
            filled = int(self.width * pct)
            empty = self.width - filled
            bar = colorize(self._fill_char * filled, fg=bar_color)
            bar_bg = colorize(self._empty_char * empty, fg=theme.muted)
            parts.append(f"{bar}{bar_bg}")
            parts.append(colorize(f"{self.percentage:5.1f}%", fg=bar_color, style="bold"))
        else:
            pos = int(time.time() * 10) % self.width
            bar_str = self._empty_char * self.width
            bar_str = bar_str[:pos] + self._fill_char + bar_str[pos + 1:]
            parts.append(colorize(bar_str, fg=bar_color))

        if self.show_size and self.total > 0:
            size_str = f"{FileSize.format(self._current)}/{FileSize.format(self.total)}"
            parts.append(colorize(size_str, fg="white"))

        if self.show_speed and self._current_speed > 0:
            parts.append(colorize(TransferSpeed.format(self._current_speed), fg=theme.accent))

        if self.show_eta and self.total > 0 and self._current_speed > 0:
            parts.append(colorize(f"ETA {TimeRemaining.format(self.eta, compact=True)}", fg=theme.muted))

        return " ".join(parts)

    def _calculate_speed(self) -> None:
        if len(self._speed_samples) < 2:
            return
        t1, b1 = self._speed_samples[0]
        t2, b2 = self._speed_samples[-1]
        dt = t2 - t1
        if dt > 0:
            self._current_speed = (b2 - b1) / dt

    def _speed_color(self, theme: Any) -> str:
        """Color-coded speed: green=fast, yellow=medium, red=slow."""
        if self._current_speed <= 0:
            return theme.primary
        if self.unit == "B":
            if self._current_speed > 5 * 1024 * 1024:
                return "green"
            elif self._current_speed > 1 * 1024 * 1024:
                return "yellow"
            else:
                return "red"
        return theme.primary

    def _render(self, final: bool = False, error: str = "") -> None:
        """Render the progress bar to stdout."""
        if not sys.stdout.isatty():
            if final:
                if self._state == ProgressState.COMPLETED:
                    print(f"✓ {self.desc} - Complete")
                elif self._state == ProgressState.FAILED:
                    print(f"✗ {self.desc} - Failed: {error}")
            return

        line = self.render()
        if error:
            line += " " + colorize(f"ERROR: {error}", fg="red")

        if final:
            sys.stdout.write(f"\r{line}\n")
        else:
            sys.stdout.write(f"\r{line}")
        sys.stdout.flush()

    def __enter__(self) -> "ProgressBar":
        return self.start()

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if exc_type is None:
            self.complete()
        else:
            self.fail(str(exc_val))


# ==============================================================================
# Download Progress (Specialized)
# ==============================================================================

class DownloadProgress:
    """
    Specialized progress tracker for downloads.
    Tracks file name, URL, size, speed, ETA, and download state.
    """

    def __init__(
        self,
        filename: str = "",
        url: str = "",
        total_size: int = 0,
        chunk_size: int = 8192,
        bar_width: int = 25,
        show_bar: bool = True,
    ):
        self.filename = filename
        self.url = url
        self.total_size = total_size
        self.chunk_size = chunk_size
        self.bar_width = bar_width
        self.show_bar = show_bar

        self._downloaded = 0
        self._state = ProgressState.PENDING
        self._start_time: Optional[float] = None
        self._end_time: Optional[float] = None
        self._speed = 0.0
        self._peak_speed = 0.0
        self._speed_samples: List[Tuple[float, int]] = []
        self._lock = threading.Lock()
        self._last_render = 0.0
        self._callback: Optional[Callable[[int, int, float], None]] = None

    @property
    def downloaded(self) -> int:
        return self._downloaded

    @property
    def state(self) -> ProgressState:
        return self._state

    @property
    def percentage(self) -> float:
        if self.total_size <= 0:
            return 0.0
        return min(100.0, (self._downloaded / self.total_size) * 100)

    @property
    def speed(self) -> float:
        return self._speed

    @property
    def eta(self) -> float:
        if self._speed <= 0 or self.total_size <= 0:
            return float("inf")
        return (self.total_size - self._downloaded) / self._speed

    @property
    def elapsed(self) -> float:
        if self._start_time is None:
            return 0.0
        return (self._end_time or time.time()) - self._start_time

    def on_progress(self, callback: Callable[[int, int, float], None]) -> None:
        """Register a progress callback: callback(downloaded, total, speed)."""
        self._callback = callback

    def start(self) -> "DownloadProgress":
        """Start tracking download progress."""
        with self._lock:
            self._state = ProgressState.RUNNING
            self._start_time = time.time()
        self._render()
        return self

    def update(self, chunk_size: int) -> None:
        """Update with a downloaded chunk."""
        now = time.time()
        with self._lock:
            self._downloaded += chunk_size
            self._speed_samples.append((now, self._downloaded))
            if len(self._speed_samples) > 30:
                self._speed_samples = self._speed_samples[-30:]
            self._calculate_speed()
            dl = self._downloaded
            spd = self._speed

        if self._callback:
            try:
                self._callback(dl, self.total_size, spd)
            except Exception:
                pass

        if now - self._last_render >= 0.1 or dl >= self.total_size:
            self._last_render = now
            self._render()

        if dl >= self.total_size and self.total_size > 0:
            self.complete()

    def set_downloaded(self, value: int) -> None:
        """Set downloaded amount directly."""
        now = time.time()
        with self._lock:
            self._downloaded = value
            self._speed_samples.append((now, value))
            if len(self._speed_samples) > 30:
                self._speed_samples = self._speed_samples[-30:]
            self._calculate_speed()

        if now - self._last_render >= 0.1:
            self._last_render = now
            self._render()

    def complete(self) -> None:
        """Mark download as complete."""
        with self._lock:
            self._state = ProgressState.COMPLETED
            self._downloaded = self.total_size
            self._end_time = time.time()
        self._render(final=True)

    def fail(self, error: str = "") -> None:
        """Mark download as failed."""
        with self._lock:
            self._state = ProgressState.FAILED
            self._end_time = time.time()
        self._render(final=True, error=error)

    def pause(self) -> None:
        with self._lock:
            self._state = ProgressState.PAUSED

    def resume(self) -> None:
        with self._lock:
            self._state = ProgressState.RUNNING

    def _calculate_speed(self) -> None:
        if len(self._speed_samples) < 2:
            return
        t1, b1 = self._speed_samples[0]
        t2, b2 = self._speed_samples[-1]
        dt = t2 - t1
        if dt > 0:
            self._speed = (b2 - b1) / dt
            self._peak_speed = max(self._peak_speed, self._speed)

    def _speed_to_color(self) -> str:
        """Map speed to color: green=fast, yellow=medium, red=slow."""
        if self._speed <= 0:
            return "cyan"
        if self._speed > 10 * 1024 * 1024:
            return "green"
        elif self._speed > 2 * 1024 * 1024:
            return "yellow"
        else:
            return "red"

    def _render(self, final: bool = False, error: str = "") -> None:
        """Render the download progress line."""
        theme = get_theme()

        if not sys.stdout.isatty():
            if final:
                if self._state == ProgressState.COMPLETED:
                    print(f"✓ {self.filename} - {FileSize.format(self.total_size)}")
                elif self._state == ProgressState.FAILED:
                    print(f"✗ {self.filename} - Failed: {error}")
            return

        parts = []

        # Status icon
        if self._state == ProgressState.COMPLETED:
            icon = colorize("✓", fg=theme.success)
        elif self._state == ProgressState.FAILED:
            icon = colorize("✗", fg=theme.error)
        elif self._state == ProgressState.PAUSED:
            icon = colorize("⏸", fg=theme.warning)
        else:
            icon = colorize("⬇", fg=theme.primary)
        parts.append(icon)

        # Filename
        name = self.filename[:30] + ".." if len(self.filename) > 32 else self.filename
        parts.append(colorize(name, fg="white", style="bold"))

        # Progress bar
        if self.show_bar and self.total_size > 0:
            pct = self.percentage / 100.0
            filled = int(self.bar_width * pct)
            empty = self.bar_width - filled
            bar_color = self._speed_to_color()
            bar = colorize("█" * filled, fg=bar_color) + colorize("░" * empty, fg=theme.muted)
            parts.append(bar)
            parts.append(colorize(f"{self.percentage:5.1f}%", fg=bar_color, style="bold"))

        # Size
        if self.total_size > 0:
            parts.append(colorize(f"{FileSize.format(self._downloaded)}/{FileSize.format(self.total_size)}", fg="white"))

        # Speed (color-coded)
        if self._speed > 0:
            speed_color = self._speed_to_color()
            parts.append(colorize(TransferSpeed.format(self._speed), fg=speed_color))

        # ETA
        if self.total_size > 0 and self._speed > 0 and self._state == ProgressState.RUNNING:
            parts.append(colorize(f"ETA {TimeRemaining.format(self.eta, compact=True)}", fg=theme.muted))

        if error:
            parts.append(colorize(error, fg=theme.error))

        line = " ".join(parts)
        if final:
            sys.stdout.write(f"\r{line}\n")
        else:
            sys.stdout.write(f"\r{line}")
        sys.stdout.flush()

    def summary(self) -> Dict[str, Any]:
        """Return a summary dictionary of the download."""
        return {
            "filename": self.filename, "url": self.url,
            "total_size": self.total_size, "downloaded": self._downloaded,
            "percentage": self.percentage, "speed": self._speed,
            "peak_speed": self._peak_speed, "elapsed": self.elapsed,
            "state": self._state.value,
        }


# ==============================================================================
# Multi-Progress
# ==============================================================================

class MultiProgress:
    """
    Track and display multiple concurrent progress bars.
    Each progress item gets its own line. Thread-safe.
    """

    def __init__(self, max_concurrent: int = 5, bar_width: int = 20):
        self.max_concurrent = max_concurrent
        self.bar_width = bar_width
        self._items: Dict[str, DownloadProgress] = {}
        self._lock = threading.Lock()
        self._running = False
        self._render_thread: Optional[threading.Thread] = None
        self._last_line_count = 0

    def add(
        self, item_id: str, filename: str = "",
        url: str = "", total_size: int = 0,
    ) -> DownloadProgress:
        """Add a new download progress tracker."""
        with self._lock:
            progress = DownloadProgress(
                filename=filename, url=url,
                total_size=total_size, bar_width=self.bar_width,
            )
            self._items[item_id] = progress
        return progress

    def remove(self, item_id: str) -> None:
        """Remove a progress tracker."""
        with self._lock:
            if item_id in self._items:
                del self._items[item_id]

    def get(self, item_id: str) -> Optional[DownloadProgress]:
        """Get a progress tracker by ID."""
        return self._items.get(item_id)

    def start(self) -> "MultiProgress":
        """Start the multi-progress display."""
        self._running = True
        if sys.stdout.isatty():
            self._render_thread = threading.Thread(target=self._render_loop, daemon=True)
            self._render_thread.start()
        return self

    def stop(self) -> None:
        """Stop the multi-progress display."""
        self._running = False
        if self._render_thread:
            self._render_thread.join(timeout=2.0)

    def _render_loop(self) -> None:
        while self._running:
            self._render_all()
            time.sleep(0.2)

    def _render_all(self) -> None:
        if not sys.stdout.isatty():
            return

        theme = get_theme()
        with self._lock:
            items = list(self._items.items())

        for _ in range(self._last_line_count):
            sys.stdout.write(move_cursor_up(1))
            sys.stdout.write(clear_line())

        lines = []

        # Header
        active = sum(1 for _, p in items if p.state == ProgressState.RUNNING)
        completed = sum(1 for _, p in items if p.state == ProgressState.COMPLETED)
        failed = sum(1 for _, p in items if p.state == ProgressState.FAILED)

        header_parts = []
        if active > 0:
            header_parts.append(colorize(f"⬇ {active} active", fg=theme.primary))
        if completed > 0:
            header_parts.append(colorize(f"✓ {completed} done", fg=theme.success))
        if failed > 0:
            header_parts.append(colorize(f"✗ {failed} failed", fg=theme.error))
        header = " │ ".join(header_parts) if header_parts else colorize("No downloads", fg=theme.muted)
        lines.append(header)

        for item_id, progress in items:
            lines.append(self._format_item(progress))

        self._last_line_count = len(lines)
        for line in lines:
            sys.stdout.write(line + "\n")
        sys.stdout.flush()

    def _format_item(self, progress: DownloadProgress) -> str:
        """Format a single progress item line."""
        theme = get_theme()
        parts = []

        state_icons = {
            ProgressState.PENDING: ("⏳", theme.muted),
            ProgressState.RUNNING: ("⬇", theme.primary),
            ProgressState.PAUSED: ("⏸", theme.warning),
            ProgressState.COMPLETED: ("✓", theme.success),
            ProgressState.FAILED: ("✗", theme.error),
            ProgressState.CANCELLED: ("⊘", theme.warning),
        }
        icon, icon_color = state_icons.get(progress.state, ("?", theme.muted))
        parts.append(colorize(icon, fg=icon_color))

        name = progress.filename[:25] + ".." if len(progress.filename) > 27 else progress.filename
        parts.append(colorize(name, fg="white"))

        if progress.total_size > 0:
            pct = progress.percentage / 100.0
            filled = int(self.bar_width * pct)
            empty = self.bar_width - filled
            bar = colorize("█" * filled, fg=icon_color) + colorize("░" * empty, fg=theme.muted)
            parts.append(bar)
            parts.append(colorize(f"{progress.percentage:4.0f}%", fg=icon_color))

        if progress.speed > 0:
            parts.append(colorize(TransferSpeed.format(progress.speed), fg=theme.accent))

        return " ".join(parts)

    def summary(self) -> List[Dict[str, Any]]:
        """Get summary of all items."""
        with self._lock:
            return [p.summary() for p in self._items.values()]


# ==============================================================================
# Convenience Functions
# ==============================================================================

def progress_bar(total: int, desc: str = "", unit: str = "B", **kwargs) -> ProgressBar:
    """Create and start a new progress bar."""
    return ProgressBar(total=total, desc=desc, unit=unit, **kwargs).start()


def spinner(message: str = "", style: str = "dots", **kwargs) -> Spinner:
    """Create and start a new spinner."""
    return Spinner(message=message, style=style, **kwargs).start()


def download_progress(filename: str = "", url: str = "", total_size: int = 0, **kwargs) -> DownloadProgress:
    """Create and start a new download progress tracker."""
    return DownloadProgress(filename=filename, url=url, total_size=total_size, **kwargs).start()


def multi_progress(max_concurrent: int = 5, **kwargs) -> MultiProgress:
    """Create a new multi-progress display."""
    return MultiProgress(max_concurrent=max_concurrent, **kwargs)


# ==============================================================================
# Context Managers
# ==============================================================================

@contextmanager
def track_progress(total: int, desc: str = "", unit: str = "B"):
    """Context manager for tracking progress."""
    bar = ProgressBar(total=total, desc=desc, unit=unit).start()
    try:
        yield bar
    except Exception as e:
        bar.fail(str(e))
        raise
    else:
        bar.complete()


@contextmanager
def track_download(filename: str, total_size: int = 0, url: str = ""):
    """Context manager for tracking a download."""
    dl = DownloadProgress(filename=filename, url=url, total_size=total_size).start()
    try:
        yield dl
    except Exception as e:
        dl.fail(str(e))
        raise
    else:
        dl.complete()


@contextmanager
def spinning(message: str = "", style: str = "dots"):
    """Context manager for a spinner."""
    sp = Spinner(message=message, style=style).start()
    try:
        yield sp
    except Exception as e:
        sp.fail(str(e))
        raise
    else:
        sp.succeed()


# ==============================================================================
# Non-Interactive (Plain Text) Progress
# ==============================================================================

class PlainProgress:
    """Plain text progress output for non-TTY environments."""

    def __init__(self, total: int = 0, desc: str = "", interval: float = 5.0):
        self.total = total
        self.desc = desc
        self.interval = interval
        self._current = 0
        self._start_time: Optional[float] = None
        self._last_report = 0.0

    def start(self) -> "PlainProgress":
        self._start_time = time.time()
        if self.desc:
            print(f"[START] {self.desc}")
        return self

    def update(self, n: int = 1) -> None:
        self._current += n
        now = time.time()
        if now - self._last_report >= self.interval:
            self._last_report = now
            if self.total > 0:
                pct = (self._current / self.total) * 100
                print(f"[{pct:.1f}%] {self.desc} - {FileSize.format(self._current)}/{FileSize.format(self.total)}")
            else:
                print(f"[...] {self.desc} - {FileSize.format(self._current)} downloaded")

    def complete(self) -> None:
        elapsed = time.time() - (self._start_time or time.time())
        avg_speed = self._current / elapsed if elapsed > 0 else 0
        print(f"[DONE] {self.desc} - {FileSize.format(self._current)} in {TimeRemaining.format(elapsed, compact=True)} (avg {TransferSpeed.format(avg_speed)})")

    def fail(self, error: str = "") -> None:
        print(f"[FAIL] {self.desc} - {error}")
