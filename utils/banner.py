#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Banner System
INFINITE HYPERNOVA SOVEREIGN NEXUS

ASCII art banners with multiple styles, color customization,
animation support, and system information display.

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng
License: MIT
"""

import os
import random
import sys
import time
import platform
import shutil
from typing import Optional, Dict, List
from datetime import datetime

from .colors import (
    colorize,
    gradient_text,
    rainbow_text,
    strip_ansi,
    ansi_len,
    get_theme,
    supports_color,
    caps,
    ESC,
    clear_line,
    move_cursor_up,
)


# ==============================================================================
# Version Information
# ==============================================================================

VERSION = "10.0.0"
CODENAME = "INFINITE HYPERNOVA SOVEREIGN NEXUS"
AUTHOR = "RAJSARASWATI JATAV (RS) / T3rmuxk1ng"
YEAR = "2025"


# ==============================================================================
# ASCII Art Banners
# ==============================================================================

BANNER_NEXUS = r"""
  ╔══════════════════════════════════════════════════════════════════════╗
  ║                                                                      ║
  ║     ██████╗ ███████╗███████╗██████╗  ██████╗ ███████╗               ║
  ║    ██╔════╝ ██╔════╝██╔════╝██╔══██╗██╔═══██╗██╔════╝               ║
  ║    ██║  ███╗█████╗  █████╗  ██████╔╝██║   ██║███████╗               ║
  ║    ██║   ██║██╔══╝  ██╔══╝  ██╔══██╗██║   ██║╚════██║               ║
  ║    ╚██████╔╝███████╗███████╗██║  ██║╚██████╔╝███████║               ║
  ║     ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝               ║
  ║                                                                      ║
  ║   ██████╗ ██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗           ║
  ║   ██╔══██╗██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗          ║
  ║   ██║  ██║██████╔╝███████║██║     █████╔╝ █████╗  ██║  ██║          ║
  ║   ██║  ██║██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██║  ██║          ║
  ║   ██████╔╝██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██████╔╝          ║
  ║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝           ║
  ║                                                                      ║
  ║          v{version} // {codename}              ║
  ║          by {author}              ║
  ╚══════════════════════════════════════════════════════════════════════╝
"""

BANNER_CYBERPUNK = r"""
  ┌──────────────────────────────────────────────────────────────────────┐
  │                                                                      │
  │   ▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄▄         │
  │   █ ▄▀▀▀▄ █▀▄▀▄█ ▄▀▀▀▄ █  ▄▀▀  ▄▀▀▄ ▄▀▀▄ █▀▄▀▄ ▄▀▀▀▄ █           │
  │   █ ▀▄▄▄▀ █ ▀ █ ▀▄▄▄▀ █  ▀▀▄  █▄▄█ █  █ █ ▀ █ ▀▄▄▄▀ █           │
  │   █▄▄▄▄▄▄▄█▄█ ▀ █▄▄▄▄▄▄█  ▄▄▀  ▄▄▄▄▄█  █ █▄█ ▀█▄▄▄▄▄▄█           │
  │                                                                      │
  │   ▄▀▀▄ ▄▀▀▄ ▄▀▀▀▄ ▄▀▀▀▄ █▀▄▀▄ ▄▀▀  ▄▀▀▄ █  ▄▀▀▀▄ ▄▀▀▄            │
  │   █▄▄█ █  █ █▄▄▄▀ █▄▄▄▀ █ ▀ █ ▀▀▄  █▄▄█ █  █▄▄▄▀ █  █            │
  │   ▄▄▄▄▄█  █ ▄▄▄▄▄▄█ ▄▄▄▄▄▄█▄█ ▀ ▄▄▀  ▄▄▄▄▄█▄▄█ ▄▄▄▄▄▄█  █            │
  │                                                                      │
  │   ╔══ v{version} ══╗                                 │
  │   ║ {codename}  ║                       │
  │   ╚════════════════════════════════╝                                 │
  └──────────────────────────────────────────────────────────────────────┘
"""

BANNER_MATRIX = r"""
  ╔══════════════════════════════════════════════════════════════╗
  ║                                                              ║
  ║   01010010 01010011                                          ║
  ║   01000100 01001111 01010111 01001110 01001100 01001111    ║
  ║   01000100 01000101 01010010                                ║
  ║                                                              ║
  ║   ██▀███  ▓█████▄▄▓█   █▓ ▓█████  ██▀███                  ║
  ║   ▓██ ▒ ██▒▓█   ▀ ▒██  ██▒▓█   ▀ ▓██ ▒ ██▒                ║
  ║   ▓██ ░▄█ ▒▒███    ▒██ ██░▒███   ▓██ ░▄█ ▒                ║
  ║   ▒██▀▀█▄  ▒▓█  ▄  ░ ▐██▓ ▒▓█  ▄▒██▀▀█▄                  ║
  ║   ░██▓ ▒██▒░▒████▓  ░ ██▒▓░░▒████▒░██▓ ▒██▒               ║
  ║                                                              ║
  ║   v{version} // {codename}        ║
  ║   {author}                    ║
  ╚══════════════════════════════════════════════════════════════╝
"""

BANNER_MINIMAL = r"""
  ┌─────────────────────────────────────────────┐
  │  RS Downloader v{version}                       │
  │  {codename}   │
  │  by {author}                    │
  └─────────────────────────────────────────────┘
"""

BANNER_COMPACT = r"""
  ╔═ RS DOWNLOADER ═══════════════════════════════════════════╗
  ║ v{version} | {codename} ║
  ╚═══════════════════════════════════════════════════════════╝
"""


# ==============================================================================
# Banner Style Registry
# ==============================================================================

class BannerStyle:
    """A banner style definition."""

    def __init__(
        self,
        name: str,
        template: str,
        description: str = "",
        primary_color: str = "cyan",
        secondary_color: str = "magenta",
        use_gradient: bool = True,
    ):
        self.name = name
        self.template = template
        self.description = description
        self.primary_color = primary_color
        self.secondary_color = secondary_color
        self.use_gradient = use_gradient

    def render(self, version: Optional[str] = None) -> str:
        """Render the banner with version and codename."""
        v = version or VERSION
        codename_display = CODENAME[:40] if len(CODENAME) > 40 else CODENAME
        author_display = AUTHOR[:40] if len(AUTHOR) > 40 else AUTHOR

        text = self.template.format(
            version=v, codename=codename_display,
            author=author_display, year=YEAR,
        )

        if not supports_color():
            return text

        theme = get_theme()
        if self.use_gradient and theme.banner_primary != theme.banner_secondary:
            return gradient_text(text, self.primary_color, self.secondary_color)
        return colorize(text, fg=self.primary_color)


# Register built-in banner styles
BANNER_STYLES: Dict[str, BannerStyle] = {
    "nexus": BannerStyle(
        name="nexus", template=BANNER_NEXUS,
        description="Full ASCII art with box border",
        primary_color="cyan", secondary_color="magenta", use_gradient=True,
    ),
    "cyberpunk": BannerStyle(
        name="cyberpunk", template=BANNER_CYBERPUNK,
        description="Block character cyberpunk style",
        primary_color="bright_magenta", secondary_color="bright_cyan", use_gradient=True,
    ),
    "matrix": BannerStyle(
        name="matrix", template=BANNER_MATRIX,
        description="Matrix/hacker green theme",
        primary_color="green", secondary_color="bright_green", use_gradient=True,
    ),
    "minimal": BannerStyle(
        name="minimal", template=BANNER_MINIMAL,
        description="Simple bordered text",
        primary_color="white", secondary_color="bright_black", use_gradient=False,
    ),
    "compact": BannerStyle(
        name="compact", template=BANNER_COMPACT,
        description="Single-line compact banner",
        primary_color="cyan", secondary_color="magenta", use_gradient=False,
    ),
}


# ==============================================================================
# System Information
# ==============================================================================

def get_system_info() -> Dict[str, str]:
    """Gather system information for display."""
    info = {
        "Python": platform.python_version(),
        "OS": f"{platform.system()} {platform.release()}",
        "Architecture": platform.machine(),
        "Platform": platform.platform(),
    }

    # Add specific OS details
    try:
        if platform.system() == "Linux":
            if os.path.isfile("/etc/os-release"):
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("PRETTY_NAME="):
                            info["Distro"] = line.split("=", 1)[1].strip().strip('"')
                            break
        elif platform.system() == "Darwin":
            info["macOS"] = platform.mac_ver()[0]
    except (OSError, IOError):
        pass

    # Check for key dependencies
    deps = {}
    for dep in ("yt-dlp", "ffmpeg", "aria2c"):
        path = shutil.which(dep)
        deps[dep] = path or "not found"

    if deps:
        info["Dependencies"] = ", ".join(
            f"{k}={'✓' if v != 'not found' else '✗'}" for k, v in deps.items()
        )

    return info


def format_system_info(info: Optional[Dict[str, str]] = None) -> str:
    """Format system information for display."""
    if info is None:
        info = get_system_info()

    theme = get_theme()
    lines = []
    for key, value in info.items():
        key_str = colorize(f"  {key}:", fg=theme.primary, style="bold")
        val_str = colorize(value, fg="white")
        lines.append(f"{key_str} {val_str}")

    return "\n".join(lines)


# ==============================================================================
# Banner Display
# ==============================================================================

def show_banner(
    style: Optional[str] = None,
    version: Optional[str] = None,
    show_info: bool = True,
    custom_file: Optional[str] = None,
    no_color: bool = False,
    width: Optional[int] = None,
) -> str:
    """
    Display the startup banner.

    Args:
        style: Banner style name (nexus, cyberpunk, matrix, minimal, compact).
        version: Override version string.
        show_info: Whether to display system information.
        custom_file: Path to a custom banner file.
        no_color: Disable color output.
        width: Terminal width override.

    Returns:
        The rendered banner string.
    """
    if custom_file:
        return _load_custom_banner(custom_file, version, no_color)

    if style and style in BANNER_STYLES:
        banner_style = BANNER_STYLES[style]
    else:
        banner_style = random.choice(list(BANNER_STYLES.values()))

    if no_color:
        v = version or VERSION
        codename_display = CODENAME[:40]
        author_display = AUTHOR[:40]
        result = banner_style.template.format(
            version=v, codename=codename_display,
            author=author_display, year=YEAR,
        )
    else:
        result = banner_style.render(version)

    if show_info:
        result += "\n"
        theme = get_theme()
        result += colorize("─" * 60, fg=theme.muted) + "\n"
        result += format_system_info() + "\n"

    return result


def get_random_banner() -> str:
    """Get a random banner style and render it."""
    style_name = random.choice(list(BANNER_STYLES.keys()))
    return show_banner(style=style_name, show_info=False)


def _load_custom_banner(
    filepath: str, version: Optional[str] = None, no_color: bool = False
) -> str:
    """Load and render a custom banner from a file."""
    try:
        with open(filepath, "r") as f:
            template = f.read()
    except (OSError, IOError) as e:
        return colorize(f"Error loading banner: {e}", fg="red", style="bold")

    v = version or VERSION
    codename_display = CODENAME[:40]
    author_display = AUTHOR[:40]

    try:
        text = template.format(
            version=v, codename=codename_display,
            author=author_display, year=YEAR,
        )
    except KeyError:
        text = template

    if no_color or not supports_color():
        return text

    theme = get_theme()
    return gradient_text(text, theme.banner_primary, theme.banner_secondary)


# ==============================================================================
# Animated Banner
# ==============================================================================

def animate_banner(
    style: Optional[str] = None,
    version: Optional[str] = None,
    duration: float = 2.0,
    frames: int = 10,
) -> None:
    """
    Display an animated banner with a typewriter-like reveal effect.
    Only works in TTY terminals.
    """
    if not sys.stdout.isatty():
        print(show_banner(style=style, version=version, show_info=False))
        return

    banner = show_banner(style=style, version=version, show_info=False)
    clean = strip_ansi(banner)
    total_chars = len(clean)

    if total_chars == 0:
        return

    chars_per_frame = max(1, total_chars // frames)
    delay = duration / frames

    try:
        for frame in range(frames + 1):
            reveal_count = min(frame * chars_per_frame, total_chars)
            output = ""
            char_count = 0
            in_escape = False

            for ch in banner:
                if ch == "\033":
                    in_escape = True
                    output += ch
                    continue
                if in_escape:
                    output += ch
                    if ch == "m":
                        in_escape = False
                    continue
                if ch == "\n":
                    output += ch
                    continue
                char_count += 1
                output += ch if char_count <= reveal_count else " "

            sys.stdout.write(clear_line())
            sys.stdout.write(move_cursor_up(100))
            sys.stdout.write(output)
            sys.stdout.flush()
            time.sleep(delay)

        sys.stdout.write(clear_line())
        sys.stdout.write(banner)
        sys.stdout.flush()

    except (KeyboardInterrupt, OSError):
        print(banner)


def animate_rainbow(
    style: Optional[str] = None,
    version: Optional[str] = None,
    cycles: int = 3,
    speed: float = 0.1,
) -> None:
    """Animate banner with cycling rainbow colors."""
    if not sys.stdout.isatty():
        print(show_banner(style=style, version=version, show_info=False))
        return

    v = version or VERSION
    codename_display = CODENAME[:40]
    author_display = AUTHOR[:40]

    if style and style in BANNER_STYLES:
        banner_style = BANNER_STYLES[style]
    else:
        banner_style = random.choice(list(BANNER_STYLES.values()))

    plain = banner_style.template.format(
        version=v, codename=codename_display,
        author=author_display, year=YEAR,
    )
    line_count = plain.count("\n") + 1

    try:
        for _ in range(cycles):
            colored = rainbow_text(plain)
            sys.stdout.write(colored)
            sys.stdout.flush()
            time.sleep(speed)
            sys.stdout.write(move_cursor_up(line_count))

        theme = get_theme()
        final = gradient_text(plain, theme.banner_primary, theme.banner_secondary)
        sys.stdout.write(final)
        sys.stdout.flush()

    except (KeyboardInterrupt, OSError):
        print(plain)


# ==============================================================================
# Loading / Splash Screen
# ==============================================================================

LOADING_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

LOADING_MESSAGES = [
    "Initializing systems...",
    "Loading download engines...",
    "Connecting to the network...",
    "Scanning for dependencies...",
    "Calibrating bandwidth...",
    "Loading platform agents...",
    "Establishing secure channels...",
    "Syncing configuration...",
    "Preparing download queue...",
    "System ready.",
]


class Spinner:
    """Simple banner spinner for loading states."""

    def __init__(self, message: str = "", style: str = "dots"):
        self.message = message
        self.frames = LOADING_FRAMES
        self._running = False
        self._thread = None

    def start(self):
        if not sys.stdout.isatty():
            if self.message:
                print(self.message)
            return self
        import threading
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()
        return self

    def stop(self, final_message: Optional[str] = None):
        self._running = False
        if self._thread:
            self._thread.join(timeout=1.0)
        if sys.stdout.isatty():
            sys.stdout.write("\r" + " " * 80 + "\r")
            if final_message:
                theme = get_theme()
                print(colorize(f"  ✓ {final_message}", fg=theme.success))
            sys.stdout.flush()

    def _spin(self):
        idx = 0
        while self._running:
            frame = self.frames[idx % len(self.frames)]
            idx += 1
            theme = get_theme()
            line = f"  {colorize(frame, fg=theme.accent)} {self.message}"
            if sys.stdout.isatty():
                sys.stdout.write(f"\r{line}")
                sys.stdout.flush()
            time.sleep(0.1)


def show_loading(
    message: Optional[str] = None,
    duration: float = 3.0,
    style: Optional[str] = None,
) -> None:
    """Display an animated loading screen."""
    if not sys.stdout.isatty():
        if message:
            print(message)
        return

    theme = get_theme()
    frame_count = len(LOADING_FRAMES)
    iterations = int(duration / 0.1)
    msg_index = 0

    try:
        for i in range(iterations):
            frame = LOADING_FRAMES[i % frame_count]
            msg = message or LOADING_MESSAGES[min(msg_index, len(LOADING_MESSAGES) - 1)]
            if i > 0 and i % 5 == 0:
                msg_index += 1
                msg = message or LOADING_MESSAGES[min(msg_index, len(LOADING_MESSAGES) - 1)]
            line = f"  {colorize(frame, fg=theme.accent)} {colorize(msg, fg=theme.muted)}"
            sys.stdout.write(f"\r{line}")
            sys.stdout.flush()
            time.sleep(0.1)
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()
    except (KeyboardInterrupt, OSError):
        sys.stdout.write("\r" + " " * 80 + "\r")
        sys.stdout.flush()


# ==============================================================================
# Motd / Status / Footer
# ==============================================================================

MOTD_MESSAGES = [
    "Ready to download the universe!",
    "Your download command center is online.",
    "All systems operational. Let's go!",
    "Hypernova mode: ENGAGED",
    "The nexus awaits your commands.",
    "Sovereign infrastructure: ACTIVE",
    "Download at the speed of light!",
    "Infinite possibilities, one command away.",
    "The sovereign genesis protocol is ready.",
    "Your media, your rules, your way.",
]


def get_motd() -> str:
    """Get a random message of the day."""
    theme = get_theme()
    msg = random.choice(MOTD_MESSAGES)
    return colorize(f"  >> {msg}", fg=theme.accent)


def status_line(
    downloads: int = 0,
    completed: int = 0,
    failed: int = 0,
    speed: str = "",
    uptime: str = "",
) -> str:
    """Generate a status line showing current download statistics."""
    theme = get_theme()
    parts = []

    if downloads > 0:
        parts.append(colorize(f"⬇ {downloads} active", fg=theme.primary))
    if completed > 0:
        parts.append(colorize(f"✓ {completed} done", fg=theme.success))
    if failed > 0:
        parts.append(colorize(f"✗ {failed} failed", fg=theme.error))
    if speed:
        parts.append(colorize(f"⚡ {speed}", fg=theme.accent))
    if uptime:
        parts.append(colorize(f"⏱ {uptime}", fg=theme.muted))

    if not parts:
        return colorize("  Status: Idle", fg=theme.muted)

    return "  " + colorize(" │ ", fg=theme.muted).join(parts)


def footer() -> str:
    """Generate a footer line."""
    theme = get_theme()
    return colorize(
        f"  RS Downloader v{VERSION} │ {CODENAME[:30]} │ MIT License",
        fg=theme.muted,
    )


# ==============================================================================
# Welcome Screen
# ==============================================================================

def welcome_screen(
    style: Optional[str] = None,
    show_info: bool = True,
    animated: bool = False,
    no_color: bool = False,
) -> None:
    """Display the full welcome screen with banner, system info, and MOTD."""
    if animated and sys.stdout.isatty():
        animate_banner(style=style)
    else:
        banner = show_banner(style=style, show_info=show_info, no_color=no_color)
        print(banner)

    if not no_color:
        print(get_motd())
        print()
        print(status_line())
    else:
        print()


# ==============================================================================
# Update Banner
# ==============================================================================

def update_available_banner(current: str, latest: str) -> str:
    """Display an update available notification."""
    lines = [
        colorize("  ┌─────────────────────────────────────────────┐", fg="yellow"),
        colorize("  │  ⬆  UPDATE AVAILABLE                         │", fg="yellow", style="bold"),
        colorize(f"  │  Current: {current:<16} Latest: {latest:<16} │", fg="yellow"),
        colorize("  │  Run: rsdl update                            │", fg="yellow"),
        colorize("  └─────────────────────────────────────────────┘", fg="yellow"),
    ]
    return "\n".join(lines)


# ==============================================================================
# Custom Banner Registration
# ==============================================================================

def register_banner_style(
    name: str,
    template: str,
    description: str = "",
    primary_color: str = "cyan",
    secondary_color: str = "magenta",
    use_gradient: bool = True,
) -> None:
    """Register a custom banner style."""
    BANNER_STYLES[name] = BannerStyle(
        name=name, template=template, description=description,
        primary_color=primary_color, secondary_color=secondary_color,
        use_gradient=use_gradient,
    )


def list_banner_styles() -> List[str]:
    """List available banner style names."""
    return list(BANNER_STYLES.keys())


def get_banner_style(name: str) -> Optional[BannerStyle]:
    """Get a banner style by name."""
    return BANNER_STYLES.get(name)
