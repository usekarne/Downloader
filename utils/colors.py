#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - ANSI Color System
INFINITE HYPERNOVA SOVEREIGN NEXUS

Advanced ANSI color system with true-color support, themes, gradients,
fluent API, and terminal capability detection.

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng
License: MIT
"""

import os
import re
import sys
from typing import Optional, Dict, List, Tuple, Union


# ==============================================================================
# ANSI Escape Code Constants
# ==============================================================================

class ESC:
    """ANSI escape sequence constants."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    ITALIC = "\033[3m"
    UNDERLINE = "\033[4m"
    BLINK = "\033[5m"
    REVERSE = "\033[7m"
    HIDDEN = "\033[8m"
    STRIKETHROUGH = "\033[9m"

    # Foreground - Standard (0-7)
    BLACK = "\033[30m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"
    WHITE = "\033[37m"

    # Foreground - Bright (8-15)
    BRIGHT_BLACK = "\033[90m"
    BRIGHT_RED = "\033[91m"
    BRIGHT_GREEN = "\033[92m"
    BRIGHT_YELLOW = "\033[93m"
    BRIGHT_BLUE = "\033[94m"
    BRIGHT_MAGENTA = "\033[95m"
    BRIGHT_CYAN = "\033[96m"
    BRIGHT_WHITE = "\033[97m"

    # Background - Standard
    BG_BLACK = "\033[40m"
    BG_RED = "\033[41m"
    BG_GREEN = "\033[42m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"
    BG_MAGENTA = "\033[45m"
    BG_CYAN = "\033[46m"
    BG_WHITE = "\033[47m"

    # Background - Bright
    BG_BRIGHT_BLACK = "\033[100m"
    BG_BRIGHT_RED = "\033[101m"
    BG_BRIGHT_GREEN = "\033[102m"
    BG_BRIGHT_YELLOW = "\033[103m"
    BG_BRIGHT_BLUE = "\033[104m"
    BG_BRIGHT_MAGENTA = "\033[105m"
    BG_BRIGHT_CYAN = "\033[106m"
    BG_BRIGHT_WHITE = "\033[107m"

    # 256-color and True-color prefixes
    FG_256 = "\033[38;5;"
    BG_256 = "\033[48;5;"
    FG_RGB = "\033[38;2;"
    BG_RGB = "\033[48;2;"

    # Cursor control
    CURSOR_UP = "\033[A"
    CURSOR_DOWN = "\033[B"
    CURSOR_RIGHT = "\033[C"
    CURSOR_LEFT = "\033[D"
    CURSOR_HOME = "\033[H"
    CLEAR_LINE = "\033[2K"
    CLEAR_SCREEN = "\033[2J"
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"
    ENTER_ALT_SCREEN = "\033[?1049h"
    EXIT_ALT_SCREEN = "\033[?1049l"


# ==============================================================================
# Color Name Mappings
# ==============================================================================

COLOR_MAP: Dict[str, str] = {
    "black": ESC.BLACK, "red": ESC.RED, "green": ESC.GREEN,
    "yellow": ESC.YELLOW, "blue": ESC.BLUE, "magenta": ESC.MAGENTA,
    "cyan": ESC.CYAN, "white": ESC.WHITE,
    "bright_black": ESC.BRIGHT_BLACK, "bright_red": ESC.BRIGHT_RED,
    "bright_green": ESC.BRIGHT_GREEN, "bright_yellow": ESC.BRIGHT_YELLOW,
    "bright_blue": ESC.BRIGHT_BLUE, "bright_magenta": ESC.BRIGHT_MAGENTA,
    "bright_cyan": ESC.BRIGHT_CYAN, "bright_white": ESC.BRIGHT_WHITE,
    "gray": ESC.BRIGHT_BLACK, "grey": ESC.BRIGHT_BLACK,
    "orange": ESC.FG_256 + "208m", "purple": ESC.FG_256 + "93m",
    "pink": ESC.FG_256 + "213m", "lime": ESC.FG_256 + "118m",
    "teal": ESC.FG_256 + "36m", "navy": ESC.FG_256 + "17m",
    "coral": ESC.FG_256 + "203m", "gold": ESC.FG_256 + "220m",
}

BG_COLOR_MAP: Dict[str, str] = {
    "black": ESC.BG_BLACK, "red": ESC.BG_RED, "green": ESC.BG_GREEN,
    "yellow": ESC.BG_YELLOW, "blue": ESC.BG_BLUE, "magenta": ESC.BG_MAGENTA,
    "cyan": ESC.BG_CYAN, "white": ESC.BG_WHITE,
    "bright_black": ESC.BG_BRIGHT_BLACK, "bright_red": ESC.BG_BRIGHT_RED,
    "bright_green": ESC.BG_BRIGHT_GREEN, "bright_yellow": ESC.BG_BRIGHT_YELLOW,
    "bright_blue": ESC.BG_BRIGHT_BLUE, "bright_magenta": ESC.BG_BRIGHT_MAGENTA,
    "bright_cyan": ESC.BG_BRIGHT_CYAN, "bright_white": ESC.BG_BRIGHT_WHITE,
}

STYLE_MAP: Dict[str, str] = {
    "bold": ESC.BOLD, "dim": ESC.DIM, "italic": ESC.ITALIC,
    "underline": ESC.UNDERLINE, "blink": ESC.BLINK,
    "reverse": ESC.REVERSE, "strikethrough": ESC.STRIKETHROUGH,
}


# ==============================================================================
# Terminal Capability Detection
# ==============================================================================

class TerminalCapabilities:
    """Detect terminal color and feature capabilities."""

    _instance: Optional["TerminalCapabilities"] = None
    _detected: bool = False
    _color_level: int = 0  # 0=none, 1=16, 2=256, 3=true-color
    _supports_cursor: bool = False
    _cols: int = 80
    _rows: int = 24

    def __new__(cls) -> "TerminalCapabilities":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def detect(self) -> None:
        if self._detected:
            return
        self._detected = True

        if os.environ.get("NO_COLOR") is not None:
            self._color_level = 0
            return

        term = os.environ.get("TERM", "")
        colorterm = os.environ.get("COLORTERM", "")

        if term == "dumb":
            self._color_level = 0
            return

        if colorterm in ("truecolor", "24bit"):
            self._color_level = 3
        elif "256color" in term or term in ("xterm-256color", "screen-256color"):
            self._color_level = 2
        elif term and term != "dumb":
            self._color_level = 1

        # Modern terminal detection
        term_program = os.environ.get("TERM_PROGRAM", "")
        if term_program in ("iTerm.app", "WezTerm", "vscode"):
            self._color_level = 3
        if "kitty" in term:
            self._color_level = 3
        if os.environ.get("WT_SESSION"):
            self._color_level = 3
        if os.environ.get("KONSOLE_VERSION"):
            self._color_level = 3
        if os.environ.get("GNOME_TERMINAL_SERVICE"):
            self._color_level = 3

        # Windows ANSI support
        if os.name == "nt":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
                handle = kernel32.GetStdHandle(-11)
                mode = ctypes.c_ulong()
                kernel32.GetConsoleMode(handle, ctypes.byref(mode))
                if mode.value & 0x0004:
                    self._color_level = max(self._color_level, 3)
            except (OSError, AttributeError):
                self._color_level = max(self._color_level, 1)

        # Terminal size
        try:
            size = os.get_terminal_size()
            self._cols = size.columns
            self._rows = size.lines
        except OSError:
            self._cols = int(os.environ.get("COLUMNS", "80"))
            self._rows = int(os.environ.get("LINES", "24"))

        self._supports_cursor = sys.stdout.isatty()

    @property
    def color_level(self) -> int:
        if not self._detected:
            self.detect()
        return self._color_level

    @property
    def supports_truecolor(self) -> bool:
        return self.color_level >= 3

    @property
    def supports_256color(self) -> bool:
        return self.color_level >= 2

    @property
    def supports_color(self) -> bool:
        return self.color_level >= 1

    @property
    def columns(self) -> int:
        if not self._detected:
            self.detect()
        return self._cols

    @property
    def rows(self) -> int:
        if not self._detected:
            self.detect()
        return self._rows

    @property
    def supports_cursor(self) -> bool:
        if not self._detected:
            self.detect()
        return self._supports_cursor

    def reset(self) -> None:
        self._detected = False
        self._color_level = 0


caps = TerminalCapabilities()


def supports_color() -> bool:
    """Check if the terminal supports color output."""
    return caps.supports_color


def color_level() -> int:
    """Return the color support level (0=none, 1=16, 2=256, 3=true-color)."""
    return caps.color_level


# ==============================================================================
# Core Color Functions
# ==============================================================================

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


def strip_ansi(text: str) -> str:
    """Remove all ANSI escape sequences from text."""
    return _ANSI_RE.sub("", text)


def ansi_len(text: str) -> int:
    """Return the visible length of text (excluding ANSI codes)."""
    return len(strip_ansi(text))


def colorize(
    text: str,
    fg: Optional[str] = None,
    bg: Optional[str] = None,
    style: Optional[Union[str, List[str]]] = None,
    reset: bool = True,
) -> str:
    """Apply color and styling to text."""
    if not caps.supports_color:
        return text

    result = ""

    if style:
        styles = [style] if isinstance(style, str) else style
        for s in styles:
            if s in STYLE_MAP:
                result += STYLE_MAP[s]

    if fg:
        result += _resolve_fg_color(fg)

    if bg:
        result += _resolve_bg_color(bg)

    result += text
    if reset:
        result += ESC.RESET

    return result


def _resolve_fg_color(color: Union[str, Tuple[int, int, int], int]) -> str:
    """Resolve a foreground color specification to ANSI code."""
    if isinstance(color, tuple):
        r, g, b = color
        if caps.supports_truecolor:
            return f"{ESC.FG_RGB}{r};{g};{b}m"
        return f"{ESC.FG_256}{rgb_to_256(r, g, b)}m"
    elif isinstance(color, int):
        if 0 <= color <= 255:
            return f"{ESC.FG_256}{color}m"
        return ""
    elif isinstance(color, str):
        if color in COLOR_MAP:
            return COLOR_MAP[color]
        if color.startswith("#"):
            r, g, b = hex_to_rgb(color)
            if caps.supports_truecolor:
                return f"{ESC.FG_RGB}{r};{g};{b}m"
            return f"{ESC.FG_256}{rgb_to_256(r, g, b)}m"
        if "," in color:
            parts = color.split(",")
            if len(parts) == 3:
                try:
                    r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    if caps.supports_truecolor:
                        return f"{ESC.FG_RGB}{r};{g};{b}m"
                    return f"{ESC.FG_256}{rgb_to_256(r, g, b)}m"
                except ValueError:
                    pass
    return ""


def _resolve_bg_color(color: Union[str, Tuple[int, int, int], int]) -> str:
    """Resolve a background color specification to ANSI code."""
    if isinstance(color, tuple):
        r, g, b = color
        if caps.supports_truecolor:
            return f"{ESC.BG_RGB}{r};{g};{b}m"
        return f"{ESC.BG_256}{rgb_to_256(r, g, b)}m"
    elif isinstance(color, int):
        if 0 <= color <= 255:
            return f"{ESC.BG_256}{color}m"
        return ""
    elif isinstance(color, str):
        if color in BG_COLOR_MAP:
            return BG_COLOR_MAP[color]
        if color.startswith("#"):
            r, g, b = hex_to_rgb(color)
            if caps.supports_truecolor:
                return f"{ESC.BG_RGB}{r};{g};{b}m"
            return f"{ESC.BG_256}{rgb_to_256(r, g, b)}m"
        if "," in color:
            parts = color.split(",")
            if len(parts) == 3:
                try:
                    r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                    if caps.supports_truecolor:
                        return f"{ESC.BG_RGB}{r};{g};{b}m"
                    return f"{ESC.BG_256}{rgb_to_256(r, g, b)}m"
                except ValueError:
                    pass
    return ""


# ==============================================================================
# Color Conversion Utilities
# ==============================================================================

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """Convert hex color string to RGB tuple."""
    hex_color = hex_color.lstrip("#")
    if len(hex_color) == 3:
        hex_color = "".join(c * 2 for c in hex_color)
    if len(hex_color) != 6:
        return (255, 255, 255)
    try:
        return (int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16))
    except ValueError:
        return (255, 255, 255)


def rgb_to_hex(r: int, g: int, b: int) -> str:
    """Convert RGB values to hex color string."""
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_to_256(r: int, g: int, b: int) -> int:
    """Convert RGB values to the nearest 256-color index."""
    def scale(v: int) -> int:
        if v < 48:
            return 0
        elif v < 115:
            return 1
        else:
            return round((v - 55) / 40)

    cube_idx = 16 + (scale(r) * 36) + (scale(g) * 6) + scale(b)
    gray = round(r * 0.299 + g * 0.587 + b * 0.114)
    gray_idx = 232 + round((gray - 8) / 10) if 8 <= gray <= 248 else (16 if gray < 8 else 231)

    # Choose closer match
    def color_distance(idx: int) -> float:
        if idx < 16:
            standard = [
                (0, 0, 0), (128, 0, 0), (0, 128, 0), (128, 128, 0),
                (0, 0, 128), (128, 0, 128), (0, 128, 128), (192, 192, 192),
                (128, 128, 128), (255, 0, 0), (0, 255, 0), (255, 255, 0),
                (0, 0, 255), (255, 0, 255), (0, 255, 255), (255, 255, 255),
            ]
            cr, cg, cb = standard[idx]
        elif idx < 232:
            i = idx - 16
            cr = (i // 36) * 40 + 55 if (i // 36) > 0 else 0
            cg = ((i % 36) // 6) * 40 + 55 if ((i % 36) // 6) > 0 else 0
            cb = (i % 6) * 40 + 55 if (i % 6) > 0 else 0
        else:
            v = 8 + (idx - 232) * 10
            cr, cg, cb = v, v, v
        return ((r - cr) ** 2 + (g - cg) ** 2 + (b - cb) ** 2) ** 0.5

    return cube_idx if color_distance(cube_idx) <= color_distance(gray_idx) else gray_idx


def rgb_to_hsl(r: int, g: int, b: int) -> Tuple[float, float, float]:
    """Convert RGB to HSL."""
    r1, g1, b1 = r / 255.0, g / 255.0, b / 255.0
    cmax, cmin = max(r1, g1, b1), min(r1, g1, b1)
    delta = cmax - cmin
    l = (cmax + cmin) / 2.0

    if delta == 0:
        return (0.0, 0.0, l)

    s = delta / (1.0 - abs(2.0 * l - 1.0)) if (1.0 - abs(2.0 * l - 1.0)) != 0 else 0.0
    if cmax == r1:
        h = ((g1 - b1) / delta) % 6
    elif cmax == g1:
        h = (b1 - r1) / delta + 2
    else:
        h = (r1 - g1) / delta + 4
    h *= 60
    if h < 0:
        h += 360

    return (h, s, l)


def hsl_to_rgb(h: float, s: float, l: float) -> Tuple[int, int, int]:
    """Convert HSL to RGB."""
    if s == 0:
        v = round(l * 255)
        return (v, v, v)

    def hue_to_rgb(p: float, q: float, t: float) -> float:
        if t < 0: t += 1
        if t > 1: t -= 1
        if t < 1/6: return p + (q - p) * 6 * t
        if t < 1/2: return q
        if t < 2/3: return p + (q - p) * (2/3 - t) * 6
        return p

    q = l * (1 + s) if l < 0.5 else l + s - l * s
    p = 2 * l - q
    r = hue_to_rgb(p, q, h / 360 + 1/3)
    g = hue_to_rgb(p, q, h / 360)
    b = hue_to_rgb(p, q, h / 360 - 1/3)
    return (round(r * 255), round(g * 255), round(b * 255))


def lerp_color(
    color1: Tuple[int, int, int],
    color2: Tuple[int, int, int],
    factor: float,
) -> Tuple[int, int, int]:
    """Linearly interpolate between two RGB colors."""
    return (
        max(0, min(255, round(color1[0] + (color2[0] - color1[0]) * factor))),
        max(0, min(255, round(color1[1] + (color2[1] - color1[1]) * factor))),
        max(0, min(255, round(color1[2] + (color2[2] - color1[2]) * factor))),
    )


def _named_to_rgb(name: str) -> Tuple[int, int, int]:
    """Resolve a named color to RGB (approximation)."""
    named_rgb: Dict[str, Tuple[int, int, int]] = {
        "black": (0, 0, 0), "red": (170, 0, 0), "green": (0, 170, 0),
        "yellow": (170, 170, 0), "blue": (0, 0, 170), "magenta": (170, 0, 170),
        "cyan": (0, 170, 170), "white": (170, 170, 170),
        "bright_black": (85, 85, 85), "bright_red": (255, 85, 85),
        "bright_green": (85, 255, 85), "bright_yellow": (255, 255, 85),
        "bright_blue": (85, 85, 255), "bright_magenta": (255, 85, 255),
        "bright_cyan": (85, 255, 255), "bright_white": (255, 255, 255),
        "gray": (128, 128, 128), "orange": (255, 135, 0),
        "purple": (128, 0, 255), "pink": (255, 105, 180),
    }
    return named_rgb.get(name, (255, 255, 255))


# ==============================================================================
# Gradient Text
# ==============================================================================

def gradient_text(
    text: str,
    start_color: Union[str, Tuple[int, int, int]],
    end_color: Union[str, Tuple[int, int, int]],
    style: Optional[str] = None,
) -> str:
    """Create gradient text that transitions between two colors."""
    if not caps.supports_color:
        return text

    def _to_rgb(c: Union[str, Tuple[int, int, int]]) -> Tuple[int, int, int]:
        if isinstance(c, tuple):
            return c
        if isinstance(c, str):
            if c.startswith("#"):
                return hex_to_rgb(c)
            if c in COLOR_MAP:
                return _named_to_rgb(c)
        return (255, 255, 255)

    start_rgb = _to_rgb(start_color)
    end_rgb = _to_rgb(end_color)
    clean = strip_ansi(text)
    length = len(clean)

    if length == 0:
        return ""

    result = ""
    style_prefix = STYLE_MAP.get(style, "") if style else ""

    for i, ch in enumerate(clean):
        factor = i / max(length - 1, 1)
        r, g, b = lerp_color(start_rgb, end_rgb, factor)
        if caps.supports_truecolor:
            result += f"{style_prefix}{ESC.FG_RGB}{r};{g};{b}m{ch}"
        else:
            idx = rgb_to_256(r, g, b)
            result += f"{style_prefix}{ESC.FG_256}{idx}m{ch}"

    result += ESC.RESET
    return result


def rainbow_text(text: str) -> str:
    """Apply rainbow gradient to text."""
    if not caps.supports_color:
        return text

    colors: List[Tuple[int, int, int]] = [
        (255, 0, 0), (255, 127, 0), (255, 255, 0), (0, 255, 0),
        (0, 0, 255), (75, 0, 130), (148, 0, 211),
    ]

    clean = strip_ansi(text)
    length = len(clean)
    if length == 0:
        return ""

    result = ""
    for i, ch in enumerate(clean):
        segment = (i / max(length - 1, 1)) * (len(colors) - 1)
        idx = int(segment)
        frac = segment - idx
        if idx >= len(colors) - 1:
            color = colors[-1]
        else:
            color = lerp_color(colors[idx], colors[idx + 1], frac)
        if caps.supports_truecolor:
            result += f"{ESC.FG_RGB}{color[0]};{color[1]};{color[2]}m{ch}"
        else:
            cidx = rgb_to_256(*color)
            result += f"{ESC.FG_256}{cidx}m{ch}"

    result += ESC.RESET
    return result


# ==============================================================================
# Color Class - Fluent API
# ==============================================================================

class Color:
    """
    Fluent API for text coloring.

    Usage:
        Color.red.bold("Hello")        # Bold red text
        Color.blue.underline("World")  # Underlined blue text
        Color("#ff5500")("Custom")     # Custom hex color
        Color.rgb(255, 100, 0)("RGB")  # RGB color
    """

    def __init__(self, fg: Optional[str] = None, _styles: Optional[List[str]] = None):
        self._fg = fg
        self._bg: Optional[str] = None
        self._styles: List[str] = _styles or []

    def __call__(self, text: str) -> str:
        """Apply the configured colors and styles to text."""
        return colorize(text, fg=self._fg, bg=self._bg, style=self._styles)

    def _with_fg(self, fg: str) -> "Color":
        c = _ColorClass(fg=fg, _styles=self._styles.copy())
        c._bg = self._bg
        return c

    def _with_style(self, style: str) -> "Color":
        styles = self._styles.copy()
        styles.append(style)
        c = _ColorClass(fg=self._fg, _styles=styles)
        c._bg = self._bg
        return c

    # --- Standard Colors ---
    @property
    def black(self) -> "Color": return self._with_fg("black")
    @property
    def red(self) -> "Color": return self._with_fg("red")
    @property
    def green(self) -> "Color": return self._with_fg("green")
    @property
    def yellow(self) -> "Color": return self._with_fg("yellow")
    @property
    def blue(self) -> "Color": return self._with_fg("blue")
    @property
    def magenta(self) -> "Color": return self._with_fg("magenta")
    @property
    def cyan(self) -> "Color": return self._with_fg("cyan")
    @property
    def white(self) -> "Color": return self._with_fg("white")

    # --- Bright Colors ---
    @property
    def bright_black(self) -> "Color": return self._with_fg("bright_black")
    @property
    def bright_red(self) -> "Color": return self._with_fg("bright_red")
    @property
    def bright_green(self) -> "Color": return self._with_fg("bright_green")
    @property
    def bright_yellow(self) -> "Color": return self._with_fg("bright_yellow")
    @property
    def bright_blue(self) -> "Color": return self._with_fg("bright_blue")
    @property
    def bright_magenta(self) -> "Color": return self._with_fg("bright_magenta")
    @property
    def bright_cyan(self) -> "Color": return self._with_fg("bright_cyan")
    @property
    def bright_white(self) -> "Color": return self._with_fg("bright_white")

    # --- Aliases ---
    @property
    def gray(self) -> "Color": return self._with_fg("gray")
    @property
    def grey(self) -> "Color": return self._with_fg("grey")
    @property
    def orange(self) -> "Color": return self._with_fg("orange")
    @property
    def purple(self) -> "Color": return self._with_fg("purple")
    @property
    def pink(self) -> "Color": return self._with_fg("pink")

    # --- Styles ---
    @property
    def bold(self) -> "Color": return self._with_style("bold")
    @property
    def dim(self) -> "Color": return self._with_style("dim")
    @property
    def italic(self) -> "Color": return self._with_style("italic")
    @property
    def underline(self) -> "Color": return self._with_style("underline")
    @property
    def blink(self) -> "Color": return self._with_style("blink")
    @property
    def reverse(self) -> "Color": return self._with_style("reverse")
    @property
    def strikethrough(self) -> "Color": return self._with_style("strikethrough")

    # --- Background ---
    def bg(self, color: str) -> "Color":
        c = _ColorClass(fg=self._fg, _styles=self._styles.copy())
        c._bg = color
        return c

    # --- Factory Methods ---
    @staticmethod
    def rgb(r: int, g: int, b: int) -> "Color":
        return _ColorClass(fg=f"{r},{g},{b}")

    @staticmethod
    def hex(hex_color: str) -> "Color":
        return _ColorClass(fg=hex_color)

    @staticmethod
    def idx(index: int) -> "Color":
        return _ColorClass(fg=str(index))


# Keep reference to the class before overwriting the name
_ColorClass = Color

# Module-level Color instance for fluent access
Color = _ColorClass()


# ==============================================================================
# Theme System
# ==============================================================================

class Theme:
    """A color theme configuration."""

    def __init__(
        self,
        name: str,
        primary: str = "cyan",
        secondary: str = "magenta",
        success: str = "green",
        warning: str = "yellow",
        error: str = "red",
        info: str = "blue",
        accent: str = "bright_cyan",
        muted: str = "bright_black",
        highlight: str = "bright_white",
        banner_primary: str = "cyan",
        banner_secondary: str = "magenta",
        progress_bar: str = "cyan",
        progress_bg: str = "bright_black",
        prompt: str = "bright_green",
        title: str = "bright_white",
        subtitle: str = "bright_cyan",
    ):
        self.name = name
        self.primary = primary
        self.secondary = secondary
        self.success = success
        self.warning = warning
        self.error = error
        self.info = info
        self.accent = accent
        self.muted = muted
        self.highlight = highlight
        self.banner_primary = banner_primary
        self.banner_secondary = banner_secondary
        self.progress_bar = progress_bar
        self.progress_bg = progress_bg
        self.prompt = prompt
        self.title = title
        self.subtitle = subtitle

    def apply(self, text: str, role: str) -> str:
        return colorize(text, fg=getattr(self, role, self.primary))

    def primary_text(self, text: str) -> str:
        return colorize(text, fg=self.primary)

    def secondary_text(self, text: str) -> str:
        return colorize(text, fg=self.secondary)

    def success_text(self, text: str) -> str:
        return colorize(text, fg=self.success, style="bold")

    def warning_text(self, text: str) -> str:
        return colorize(text, fg=self.warning, style="bold")

    def error_text(self, text: str) -> str:
        return colorize(text, fg=self.error, style="bold")

    def info_text(self, text: str) -> str:
        return colorize(text, fg=self.info)

    def muted_text(self, text: str) -> str:
        return colorize(text, fg=self.muted)

    def accent_text(self, text: str) -> str:
        return colorize(text, fg=self.accent, style="bold")

    def highlight_text(self, text: str) -> str:
        return colorize(text, fg=self.highlight, style="bold")

    def title_text(self, text: str) -> str:
        return colorize(text, fg=self.title, style="bold")

    def subtitle_text(self, text: str) -> str:
        return colorize(text, fg=self.subtitle)

    def prompt_text(self, text: str) -> str:
        return colorize(text, fg=self.prompt, style="bold")

    def banner_gradient(self, text: str) -> str:
        return gradient_text(text, self.banner_primary, self.banner_secondary)


# ==============================================================================
# Preset Themes
# ==============================================================================

THEMES: Dict[str, Theme] = {
    "nexus": Theme(
        name="nexus",
        primary="cyan", secondary="magenta",
        banner_primary="cyan", banner_secondary="magenta",
        progress_bar="cyan", progress_bg="bright_black",
        prompt="bright_green", title="bright_white", subtitle="bright_cyan",
    ),
    "cyberpunk": Theme(
        name="cyberpunk",
        primary="bright_magenta", secondary="bright_yellow",
        success="bright_green", warning="bright_yellow", error="bright_red",
        info="bright_cyan", accent="bright_magenta",
        banner_primary="bright_magenta", banner_secondary="bright_cyan",
        progress_bar="bright_magenta", progress_bg="bright_black",
        prompt="bright_yellow", title="bright_magenta", subtitle="bright_cyan",
    ),
    "matrix": Theme(
        name="matrix",
        primary="green", secondary="bright_green",
        success="bright_green", info="green", accent="bright_green",
        highlight="bright_green",
        banner_primary="green", banner_secondary="bright_green",
        progress_bar="green", progress_bg="bright_black",
        prompt="bright_green", title="bright_green", subtitle="green",
    ),
    "minimal": Theme(
        name="minimal",
        primary="white", secondary="bright_black",
        accent="white", info="white",
        banner_primary="white", banner_secondary="bright_black",
        progress_bar="white", progress_bg="bright_black",
        prompt="white", title="bright_white", subtitle="white",
    ),
    "ocean": Theme(
        name="ocean",
        primary="cyan", secondary="blue",
        success="bright_cyan", info="blue", accent="bright_blue",
        banner_primary="cyan", banner_secondary="blue",
        progress_bar="cyan", progress_bg="bright_black",
        prompt="bright_cyan", title="bright_white", subtitle="cyan",
    ),
}

_current_theme: Optional[Theme] = None


def get_theme(name: Optional[str] = None) -> Theme:
    """Get a theme by name, or the current theme."""
    global _current_theme
    if name:
        if name in THEMES:
            return THEMES[name]
        raise ValueError(f"Unknown theme: {name}. Available: {', '.join(THEMES.keys())}")
    if _current_theme is None:
        _current_theme = THEMES["nexus"]
    return _current_theme


def set_theme(name: str) -> None:
    """Set the active theme."""
    global _current_theme
    if name not in THEMES:
        raise ValueError(f"Unknown theme: {name}. Available: {', '.join(THEMES.keys())}")
    _current_theme = THEMES[name]


def list_themes() -> List[str]:
    """List available theme names."""
    return list(THEMES.keys())


def register_theme(theme: Theme) -> None:
    """Register a custom theme."""
    THEMES[theme.name] = theme


# ==============================================================================
# Convenience Functions (using current theme)
# ==============================================================================

def success(text: str) -> str:
    return get_theme().success_text(text)

def warning(text: str) -> str:
    return get_theme().warning_text(text)

def error(text: str) -> str:
    return get_theme().error_text(text)

def info(text: str) -> str:
    return get_theme().info_text(text)

def primary(text: str) -> str:
    return get_theme().primary_text(text)

def secondary(text: str) -> str:
    return get_theme().secondary_text(text)

def muted(text: str) -> str:
    return get_theme().muted_text(text)

def accent(text: str) -> str:
    return get_theme().accent_text(text)

def highlight(text: str) -> str:
    return get_theme().highlight_text(text)

def title(text: str) -> str:
    return get_theme().title_text(text)

def subtitle(text: str) -> str:
    return get_theme().subtitle_text(text)


# ==============================================================================
# Status Indicators
# ==============================================================================

def status_ok(text: str = "OK") -> str:
    return colorize(f"[✓] {text}", fg="green", style="bold")

def status_fail(text: str = "FAIL") -> str:
    return colorize(f"[✗] {text}", fg="red", style="bold")

def status_warn(text: str = "WARN") -> str:
    return colorize(f"[!] {text}", fg="yellow", style="bold")

def status_info(text: str) -> str:
    return colorize(f"[i] {text}", fg="blue")

def status_arrow(text: str) -> str:
    return colorize("→ ", fg="cyan") + text

def status_bullet(text: str) -> str:
    return colorize("• ", fg="cyan") + text

def status_star(text: str) -> str:
    return colorize("★ ", fg="yellow") + text


# ==============================================================================
# Box Drawing / Formatting
# ==============================================================================

def box(
    text: str,
    border_color: Optional[str] = None,
    padding: int = 1,
    width: Optional[int] = None,
) -> str:
    """Draw a box around text."""
    theme = get_theme()
    bc = border_color or theme.primary
    lines = text.split("\n")
    content_width = width or max(len(strip_ansi(line)) for line in lines)
    content_width = max(content_width, max(len(strip_ansi(line)) for line in lines))

    horiz = "─" * (content_width + padding * 2)
    pad_str = " " * padding
    result = colorize(f"┌{horiz}┐", fg=bc) + "\n"

    for line in lines:
        visible_len = len(strip_ansi(line))
        padding_right = content_width - visible_len + padding
        result += colorize("│", fg=bc) + pad_str + line + " " * padding_right + colorize("│", fg=bc) + "\n"

    result += colorize(f"└{horiz}┘", fg=bc)
    return result


def divider(width: int = 60, char: str = "─", color: Optional[str] = None) -> str:
    """Draw a horizontal divider line."""
    theme = get_theme()
    return colorize(char * width, fg=color or theme.muted)


def key_value(key: str, value: str, key_color: Optional[str] = None, value_color: Optional[str] = None) -> str:
    """Format a key-value pair."""
    theme = get_theme()
    kc = key_color or theme.primary
    vc = value_color or "white"
    return f"{colorize(key + ':', fg=kc, style='bold')} {colorize(value, fg=vc)}"


# ==============================================================================
# Cursor Control Helpers
# ==============================================================================

def move_cursor_up(n: int = 1) -> str:
    return f"\033[{n}A"

def move_cursor_down(n: int = 1) -> str:
    return f"\033[{n}B"

def clear_line() -> str:
    return "\033[2K\r"

def hide_cursor() -> str:
    return "\033[?25l"

def show_cursor() -> str:
    return "\033[?25h"


# ==============================================================================
# Init
# ==============================================================================

def init_colors() -> None:
    """Initialize the color system. Call once at startup."""
    caps.detect()
