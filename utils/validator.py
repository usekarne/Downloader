#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Input Validation System
INFINITE HYPERNOVA SOVEREIGN NEXUS

Comprehensive input validation for URLs, proxies, formats, quality,
paths, emails, magnet links, cron expressions, API keys, and
platform-specific URL detection with 15+ platform detectors.

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng
License: MIT
"""

import os
import re
from typing import Optional, Tuple, List, Dict
from urllib.parse import urlparse
from dataclasses import dataclass


# ==============================================================================
# Validation Result
# ==============================================================================

@dataclass
class ValidationResult:
    """Result of a validation check."""
    valid: bool
    value: Optional[str] = None
    error: Optional[str] = None
    warnings: List[str] = None  # type: ignore[assignment]

    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []

    def __bool__(self) -> bool:
        return self.valid

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def _ok(value: Optional[str] = None, warnings: Optional[List[str]] = None) -> ValidationResult:
    """Create a successful validation result."""
    return ValidationResult(valid=True, value=value, warnings=warnings or [])


def _fail(error: str, value: Optional[str] = None) -> ValidationResult:
    """Create a failed validation result."""
    return ValidationResult(valid=False, value=value, error=error)


# ==============================================================================
# URL Validation
# ==============================================================================

_URL_PATTERN = re.compile(
    r"^https?://"
    r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"
    r"localhost|"
    r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"
    r"(?::\d+)?"
    r"(?:/?|[/?]\S+)$",
    re.IGNORECASE,
)

SUPPORTED_PROTOCOLS = {"http", "https", "ftp", "ftps", "rtmp", "rtmps", "mms", "rtsp"}

_DANGEROUS_TLDS = {"tk", "ml", "ga", "cf", "gq", "xyz", "top", "buzz", "icu"}

_PRIVATE_IP_RANGES = [
    (re.compile(r"^10\."), "Class A private"),
    (re.compile(r"^172\.(1[6-9]|2[0-9]|3[01])\."), "Class B private"),
    (re.compile(r"^192\.168\."), "Class C private"),
    (re.compile(r"^127\."), "Loopback"),
    (re.compile(r"^0\."), "Current network"),
]


def validate_url(url: str, allow_private: bool = False) -> ValidationResult:
    """
    Validate a URL format, protocol, and domain.

    Args:
        url: The URL to validate.
        allow_private: Allow private/reserved IP addresses.

    Returns:
        ValidationResult with (is_valid, error_message).
    """
    if not url or not isinstance(url, str):
        return _fail("URL cannot be empty")

    url = url.strip()
    warnings: List[str] = []

    try:
        parsed = urlparse(url)
    except Exception as e:
        return _fail(f"Invalid URL format: {e}")

    if not parsed.scheme:
        return _fail("URL must include a protocol (http:// or https://)")

    if parsed.scheme.lower() not in SUPPORTED_PROTOCOLS:
        return _fail(
            f"Unsupported protocol '{parsed.scheme}'. "
            f"Supported: {', '.join(sorted(SUPPORTED_PROTOCOLS))}"
        )

    if not parsed.hostname:
        return _fail("URL must include a hostname")

    hostname = parsed.hostname

    # IP address check
    if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
        if not allow_private:
            for pattern, name in _PRIVATE_IP_RANGES:
                if pattern.match(hostname):
                    return _fail(f"Private/reserved IP address ({name}) not allowed")
        # Validate IP octets
        for octet in hostname.split("."):
            val = int(octet)
            if val < 0 or val > 255:
                return _fail(f"Invalid IP address octet: {octet}")

    # Domain validation
    if not re.match(r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?$", hostname.split(".")[-1] if "." in hostname else hostname):
        if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname):
            return _fail(f"Invalid hostname: {hostname}")

    # TLD warning
    if "." in hostname:
        tld = hostname.rsplit(".", 1)[-1].lower()
        if tld in _DANGEROUS_TLDS:
            warnings.append(f"Suspicious TLD '.{tld}' - exercise caution")

    # Port validation
    if parsed.port is not None:
        if parsed.port < 1 or parsed.port > 65535:
            return _fail(f"Invalid port number: {parsed.port}")
        if parsed.port in (22, 23, 25, 445, 3389):
            warnings.append(f"Unusual port {parsed.port} for web content")

    # Path traversal check
    if ".." in parsed.path:
        warnings.append("Path traversal pattern detected (..)")

    return _ok(value=url, warnings=warnings)


# ==============================================================================
# Proxy Validation
# ==============================================================================

_PROXY_AUTH_WITH_CREDS = re.compile(
    r"^(https?|socks[45]h?)://([^:]+):([^@]+)@([\w.-]+):(\d+)$", re.IGNORECASE
)
_PROXY_AUTH_PATTERN = re.compile(
    r"^(https?|socks[45]h?)://([\w.-]+):(\d+)$", re.IGNORECASE
)
_PROXY_PATTERNS = {
    "http": re.compile(r"^https?://[\w.-]+:\d+$", re.IGNORECASE),
    "https": re.compile(r"^https://[\w.-]+:\d+$", re.IGNORECASE),
    "socks4": re.compile(r"^socks4://[\w.-]+:\d+$", re.IGNORECASE),
    "socks5": re.compile(r"^socks5://[\w.-]+:\d+$", re.IGNORECASE),
    "socks5h": re.compile(r"^socks5h://[\w.-]+:\d+$", re.IGNORECASE),
}


def validate_proxy(proxy: str) -> ValidationResult:
    """
    Validate a proxy URL.
    Supports HTTP, HTTPS, SOCKS4, SOCKS5, SOCKS5H with optional authentication.

    Returns:
        ValidationResult with (is_valid, error_message).
    """
    if not proxy or not isinstance(proxy, str):
        return _fail("Proxy cannot be empty")

    proxy = proxy.strip()

    # Try with credentials first
    match = _PROXY_AUTH_WITH_CREDS.match(proxy)
    if match:
        proto, user, passwd, host, port = match.groups()
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            return _fail(f"Invalid proxy port: {port}")
        if not user or not passwd:
            return _fail("Proxy credentials incomplete")
        return _ok(value=proxy)

    # Try without credentials
    match = _PROXY_AUTH_PATTERN.match(proxy)
    if match:
        proto, host, port = match.groups()
        port_num = int(port)
        if port_num < 1 or port_num > 65535:
            return _fail(f"Invalid proxy port: {port}")
        return _ok(value=proxy)

    # Check if it has a known protocol but wrong format
    for proto_name in _PROXY_PATTERNS:
        if proxy.lower().startswith(f"{proto_name}://"):
            return _fail(f"Proxy format invalid. Expected: {proto_name}://host:port or {proto_name}://user:pass@host:port")

    if "://" not in proxy:
        return _fail("Proxy must include protocol (http://, https://, socks4://, socks5://)")

    return _fail("Invalid proxy format. Expected: protocol://host:port or protocol://user:pass@host:port")


# ==============================================================================
# Format Validation
# ==============================================================================

VIDEO_FORMATS = {
    "mp4", "mkv", "avi", "mov", "wmv", "flv", "webm", "m4v",
    "mpg", "mpeg", "3gp", "ogv", "ts", "mts", "vob", "asf",
}

AUDIO_FORMATS = {
    "mp3", "flac", "aac", "wav", "ogg", "opus", "m4a", "wma",
    "aiff", "alac", "ape", "ac3", "dts", "amr",
}

IMAGE_FORMATS = {
    "jpg", "jpeg", "png", "gif", "bmp", "webp", "svg", "ico",
    "tiff", "tif", "avif", "heic", "heif", "raw", "psd",
}

DOCUMENT_FORMATS = {
    "pdf", "doc", "docx", "txt", "rtf", "odt", "epub",
    "mobi", "azw3", "html", "md", "json", "xml", "csv",
}

SUBTITLE_FORMATS = {
    "srt", "ass", "ssa", "vtt", "sub", "sbv", "dfxp", "ttml",
    "stl", "lrc",
}

ALL_FORMATS = VIDEO_FORMATS | AUDIO_FORMATS | IMAGE_FORMATS | DOCUMENT_FORMATS | SUBTITLE_FORMATS


def validate_format(fmt: str, category: Optional[str] = None) -> ValidationResult:
    """
    Validate a media format string.

    Args:
        fmt: Format string (e.g., "mp4", "flac").
        category: Optional category filter ("video", "audio", "image", "document", "subtitle").

    Returns:
        ValidationResult with (is_valid, error_message).
    """
    if not fmt or not isinstance(fmt, str):
        return _fail("Format cannot be empty")

    fmt = fmt.strip().lower().lstrip(".")

    if fmt not in ALL_FORMATS:
        return _fail(f"Unknown format '{fmt}'. Supported: {', '.join(sorted(ALL_FORMATS))}")

    if category:
        category_map = {
            "video": VIDEO_FORMATS, "audio": AUDIO_FORMATS,
            "image": IMAGE_FORMATS, "document": DOCUMENT_FORMATS,
            "subtitle": SUBTITLE_FORMATS,
        }
        if category not in category_map:
            return _fail(f"Unknown format category: {category}")
        if fmt not in category_map[category]:
            valid = ", ".join(sorted(category_map[category]))
            return _fail(f"Format '{fmt}' is not a valid {category} format. Valid: {valid}")

    return _ok(value=fmt)


# ==============================================================================
# Quality Validation
# ==============================================================================

QUALITY_MAP = {
    "240p": (426, 240), "360p": (640, 360), "480p": (854, 480),
    "540p": (960, 540), "720p": (1280, 720), "1080p": (1920, 1080),
    "1440p": (2560, 1440), "2k": (2560, 1440), "4k": (3840, 2160),
    "2160p": (3840, 2160), "5k": (5120, 2880), "2880p": (5120, 2880),
    "8k": (7680, 4320), "4320p": (7680, 4320),
}

AUDIO_QUALITY_MAP = {
    "64k": 64, "96k": 96, "128k": 128, "160k": 160,
    "192k": 192, "256k": 256, "320k": 320, "lossless": 1411,
}

AUDIO_QUALITY_PATTERN = re.compile(r"^(\d+)k$", re.IGNORECASE)


def validate_quality(quality: str, media_type: str = "video") -> ValidationResult:
    """
    Validate a quality string.

    Args:
        quality: Quality string (e.g., "1080p", "4k", "320k").
        media_type: "video" or "audio".

    Returns:
        ValidationResult with (is_valid, error_message).
    """
    if not quality or not isinstance(quality, str):
        return _fail("Quality cannot be empty")

    quality = quality.strip().lower()

    if media_type == "audio":
        if quality in AUDIO_QUALITY_MAP:
            return _ok(value=quality)
        if AUDIO_QUALITY_PATTERN.match(quality):
            return _ok(value=quality)
        valid = ", ".join(sorted(AUDIO_QUALITY_MAP.keys()))
        return _fail(f"Invalid audio quality '{quality}'. Valid: {valid}")

    # Video quality
    if quality in QUALITY_MAP:
        return _ok(value=quality)

    # Custom resolution (e.g., "1920x1080")
    if re.match(r"^\d+x\d+$", quality):
        return _ok(value=quality)

    # Bitrate-based quality (e.g., "5000k")
    if re.match(r"^\d+k$", quality):
        return _ok(value=quality)

    valid = ", ".join(sorted(QUALITY_MAP.keys()))
    return _fail(f"Invalid video quality '{quality}'. Valid: {valid}, or WxH, or bitrate (e.g., 5000k)")


# ==============================================================================
# Path Validation
# ==============================================================================

_INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def validate_path(
    path: str,
    must_exist: bool = False,
    must_be_dir: bool = False,
    must_be_file: bool = False,
    must_be_writable: bool = False,
    allow_relative: bool = True,
) -> ValidationResult:
    """
    Validate a file path.

    Args:
        path: The path to validate.
        must_exist: Path must already exist.
        must_be_dir: Path must be a directory.
        must_be_file: Path must be a file.
        must_be_writable: Path must be writable.
        allow_relative: Allow relative paths.

    Returns:
        ValidationResult with (is_valid, error_message).
    """
    if not path or not isinstance(path, str):
        return _fail("Path cannot be empty")

    path = path.strip()
    expanded = os.path.expanduser(path)
    expanded = os.path.expandvars(expanded)

    if not allow_relative and not os.path.isabs(expanded):
        return _fail("Path must be absolute")

    if _INVALID_FILENAME_CHARS.search(os.path.basename(expanded)):
        invalid_chars = set(_INVALID_FILENAME_CHARS.findall(os.path.basename(expanded)))
        return _fail(f"Path contains invalid characters: {', '.join(repr(c) for c in invalid_chars)}")

    name_without_ext = os.path.splitext(os.path.basename(expanded))[0].upper()
    if name_without_ext in _WINDOWS_RESERVED:
        return _fail(f"Reserved filename: {name_without_ext}")

    if ".." in expanded.split(os.sep):
        return _fail("Path traversal (..) not allowed")

    if must_exist and not os.path.exists(expanded):
        return _fail(f"Path does not exist: {expanded}")

    if must_be_dir and os.path.exists(expanded) and not os.path.isdir(expanded):
        return _fail(f"Path is not a directory: {expanded}")

    if must_be_file and os.path.exists(expanded) and not os.path.isfile(expanded):
        return _fail(f"Path is not a file: {expanded}")

    if must_be_writable:
        if os.path.exists(expanded):
            if not os.access(expanded, os.W_OK):
                return _fail(f"Path is not writable: {expanded}")
        else:
            parent = os.path.dirname(expanded)
            if parent and not os.access(parent, os.W_OK):
                return _fail(f"Parent directory is not writable: {parent}")

    return _ok(value=expanded)


# ==============================================================================
# Email Validation
# ==============================================================================

_EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?"
    r"(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$"
)

_DISPOSABLE_DOMAINS = {
    "mailinator.com", "guerrillamail.com", "throwaway.email",
    "tempmail.com", "yopmail.com", "sharklasers.com",
    "guerrillamailblock.com", "grr.la", "dispostable.com",
}


def validate_email(email: str, allow_disposable: bool = False) -> ValidationResult:
    """Validate an email address."""
    if not email or not isinstance(email, str):
        return _fail("Email cannot be empty")

    email = email.strip().lower()

    if not _EMAIL_PATTERN.match(email):
        return _fail("Invalid email format")

    local, domain = email.rsplit("@", 1)
    if len(local) > 64:
        return _fail("Email local part exceeds 64 characters")
    if len(email) > 254:
        return _fail("Email exceeds 254 characters")

    if not re.match(r"^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*$", domain):
        return _fail("Invalid email domain")

    warnings: List[str] = []
    if not allow_disposable and domain in _DISPOSABLE_DOMAINS:
        warnings.append(f"Disposable email domain: {domain}")

    return _ok(value=email, warnings=warnings)


# ==============================================================================
# Magnet Link Validation
# ==============================================================================

_MAGNET_PATTERN = re.compile(
    r"^magnet:\?xt=urn:(btih|sha1|ed2k|aich|kzhash|md5|tree:tiger):[a-zA-Z0-9]+",
    re.IGNORECASE,
)

_MAGNET_BTIH_PATTERN = re.compile(
    r"^magnet:\?xt=urn:btih:([a-fA-F0-9]{40}|[A-Z2-7]{32})", re.IGNORECASE,
)


def validate_magnet(magnet: str) -> ValidationResult:
    """Validate a magnet link."""
    if not magnet or not isinstance(magnet, str):
        return _fail("Magnet link cannot be empty")

    magnet = magnet.strip()

    if not magnet.startswith("magnet:?"):
        return _fail("Magnet link must start with 'magnet:?'")

    if not _MAGNET_PATTERN.match(magnet):
        return _fail("Invalid magnet link format - missing or invalid xt parameter")

    # Parse parameters
    params: Dict[str, str] = {}
    try:
        query = magnet[8:]
        for part in query.split("&"):
            if "=" in part:
                key, value = part.split("=", 1)
                params[key.lower()] = value
    except Exception:
        return _fail("Failed to parse magnet link parameters")

    if "xt" not in params:
        return _fail("Magnet link must contain xt (exact topic) parameter")

    xt = params["xt"]
    if not xt.startswith("urn:"):
        return _fail("xt parameter must use URN notation")

    warnings: List[str] = []

    if "btih" in xt.lower():
        if not _MAGNET_BTIH_PATTERN.match(magnet):
            return _fail("Invalid BitTorrent info hash in magnet link")

    if "dn" not in params:
        warnings.append("No display name (dn) parameter - filename may be unknown")
    if "tr" not in params:
        warnings.append("No tracker (tr) parameter - may reduce download speed")
    if "xl" not in params:
        warnings.append("No exact length (xl) parameter - file size unknown")

    return _ok(value=magnet, warnings=warnings)


# ==============================================================================
# Cron Expression Validation
# ==============================================================================

def validate_cron(expression: str) -> ValidationResult:
    """
    Validate a cron expression (5-field format: min hour day month weekday).

    Returns:
        ValidationResult with (is_valid, error_message).
    """
    if not expression or not isinstance(expression, str):
        return _fail("Cron expression cannot be empty")

    expression = expression.strip()
    parts = expression.split()

    if len(parts) != 5:
        return _fail(f"Cron expression must have 5 fields (min hour day month weekday), got {len(parts)}")

    field_names = ["minute", "hour", "day of month", "month", "day of week"]
    field_ranges = [(0, 59), (0, 23), (1, 31), (1, 12), (0, 6)]
    month_names = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
                   "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12}
    dow_names = {"sun": 0, "mon": 1, "tue": 2, "wed": 3, "thu": 4, "fri": 5, "sat": 6}

    for i, (part, (min_val, max_val)) in enumerate(zip(parts, field_ranges)):
        field_name = field_names[i]

        # Handle step values
        if "/" in part:
            range_part, step = part.split("/", 1)
            try:
                step_val = int(step)
                if step_val <= 0:
                    return _fail(f"Step value must be positive in {field_name}: {step}")
            except ValueError:
                return _fail(f"Invalid step value in {field_name}: {step}")
            if range_part == "*":
                continue
            part = range_part

        if part == "*":
            continue

        # Handle ranges
        if "-" in part:
            range_parts = part.split("-")
            if len(range_parts) != 2:
                return _fail(f"Invalid range in {field_name}: {part}")
            for rp in range_parts:
                if i == 3 and rp.lower() in month_names:
                    continue
                if i == 4 and rp.lower() in dow_names:
                    continue
                try:
                    val = int(rp)
                    if val < min_val or val > max_val:
                        return _fail(f"Value {val} out of range ({min_val}-{max_val}) in {field_name}")
                except ValueError:
                    return _fail(f"Invalid value in {field_name}: {rp}")
            continue

        # Handle lists
        if "," in part:
            for item in part.split(","):
                if i == 3 and item.lower() in month_names:
                    continue
                if i == 4 and item.lower() in dow_names:
                    continue
                try:
                    val = int(item)
                    if val < min_val or val > max_val:
                        return _fail(f"Value {val} out of range ({min_val}-{max_val}) in {field_name}")
                except ValueError:
                    return _fail(f"Invalid value in {field_name}: {item}")
            continue

        # Single values
        if i == 3 and part.lower() in month_names:
            continue
        if i == 4 and part.lower() in dow_names:
            continue
        try:
            val = int(part)
            if val < min_val or val > max_val:
                return _fail(f"Value {val} out of range ({min_val}-{max_val}) in {field_name}")
        except ValueError:
            return _fail(f"Invalid value in {field_name}: {part}")

    return _ok(value=expression)


# ==============================================================================
# API Key Validation
# ==============================================================================

_API_KEY_PATTERNS = {
    "generic": re.compile(r"^[a-zA-Z0-9_-]{16,}$"),
    "openai": re.compile(r"^sk-[a-zA-Z0-9]{20,}$"),
    "google": re.compile(r"^AIza[a-zA-Z0-9_-]{35}$"),
    "github": re.compile(r"^(ghp|gho|ghu|ghs|ghr)_[a-zA-Z0-9]{36,}$"),
    "aws": re.compile(r"^(AKIA|ASIA)[A-Z0-9]{16}$"),
    "stripe": re.compile(r"^(sk_test|sk_live)_[a-zA-Z0-9]{24,}$"),
}


def validate_api_key(key: str, key_type: str = "generic") -> ValidationResult:
    """Validate an API key format."""
    if not key or not isinstance(key, str):
        return _fail("API key cannot be empty")

    key = key.strip()

    if key_type in _API_KEY_PATTERNS:
        if _API_KEY_PATTERNS[key_type].match(key):
            return _ok(value=key)
        return _fail(f"Invalid {key_type} API key format")

    if len(key) < 16:
        return _fail("API key is too short (minimum 16 characters)")

    if not re.match(r"^[a-zA-Z0-9._-]+$", key):
        return _fail("API key contains invalid characters")

    warnings: List[str] = []
    if key.startswith("Bearer "):
        warnings.append("API key should not include 'Bearer ' prefix")
    if " " in key:
        warnings.append("API key should not contain spaces")

    return _ok(value=key, warnings=warnings)


# ==============================================================================
# Platform URL Detection
# ==============================================================================

@dataclass
class PlatformInfo:
    """Information about a detected platform."""
    name: str
    platform_id: str
    url_type: str  # "video", "audio", "playlist", "live", "post", "story", "image"
    confidence: float  # 0.0 to 1.0


_PLATFORM_PATTERNS: Dict[str, List[Tuple[re.Pattern, str, float]]] = {
    "youtube": [
        (re.compile(r"(https?://)?(www\.)?youtube\.com/watch\?v=", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?youtube\.com/playlist\?list=", re.I), "playlist", 0.99),
        (re.compile(r"(https?://)?(www\.)?youtube\.com/shorts/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?youtube\.com/live/", re.I), "live", 0.99),
        (re.compile(r"(https?://)?(www\.)?youtube\.com/@[\w.-]+", re.I), "video", 0.85),
        (re.compile(r"(https?://)?youtu\.be/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?youtube\.com/embed/", re.I), "video", 0.99),
    ],
    "instagram": [
        (re.compile(r"(https?://)?(www\.)?instagram\.com/p/", re.I), "post", 0.99),
        (re.compile(r"(https?://)?(www\.)?instagram\.com/reel/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?instagram\.com/stories/", re.I), "story", 0.99),
        (re.compile(r"(https?://)?(www\.)?instagram\.com/tv/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?instagram\.com/[\w.]+/?$", re.I), "post", 0.70),
    ],
    "tiktok": [
        (re.compile(r"(https?://)?(www\.)?tiktok\.com/@[\w.-]+/video/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?tiktok\.com/@[\w.-]+", re.I), "video", 0.85),
        (re.compile(r"(https?://)?vm\.tiktok\.com/", re.I), "video", 0.99),
    ],
    "twitter": [
        (re.compile(r"(https?://)?(www\.)?(twitter|x)\.com/\w+/status/", re.I), "post", 0.99),
        (re.compile(r"(https?://)?(www\.)?(twitter|x)\.com/\w+/live/", re.I), "live", 0.90),
        (re.compile(r"(https?://)?(www\.)?(twitter|x)\.com/i/spaces/", re.I), "audio", 0.90),
        (re.compile(r"(https?://)?(www\.)?(twitter|x)\.com/\w+$", re.I), "post", 0.60),
    ],
    "reddit": [
        (re.compile(r"(https?://)?(www\.)?reddit\.com/r/\w+/comments/", re.I), "post", 0.99),
        (re.compile(r"(https?://)?(www\.)?reddit\.com/r/\w+/?$", re.I), "post", 0.80),
        (re.compile(r"(https?://)?v\.redd\.it/", re.I), "video", 0.99),
    ],
    "facebook": [
        (re.compile(r"(https?://)?(www\.)?facebook\.com/.*/videos/", re.I), "video", 0.95),
        (re.compile(r"(https?://)?(www\.)?facebook\.com/watch/", re.I), "video", 0.90),
        (re.compile(r"(https?://)?(www\.)?facebook\.com/.*/posts/", re.I), "post", 0.90),
        (re.compile(r"(https?://)?fb\.watch/", re.I), "video", 0.99),
    ],
    "twitch": [
        (re.compile(r"(https?://)?(www\.)?twitch\.tv/\w+/clip/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?twitch\.tv/videos/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?(www\.)?twitch\.tv/\w+$", re.I), "live", 0.85),
    ],
    "soundcloud": [
        (re.compile(r"(https?://)?soundcloud\.com/[\w-]+/[\w-]+", re.I), "audio", 0.95),
        (re.compile(r"(https?://)?soundcloud\.com/[\w-]+/sets/", re.I), "playlist", 0.95),
    ],
    "spotify": [
        (re.compile(r"(https?://)?open\.spotify\.com/track/", re.I), "audio", 0.99),
        (re.compile(r"(https?://)?open\.spotify\.com/album/", re.I), "playlist", 0.99),
        (re.compile(r"(https?://)?open\.spotify\.com/playlist/", re.I), "playlist", 0.99),
        (re.compile(r"(https?://)?open\.spotify\.com/episode/", re.I), "audio", 0.99),
    ],
    "bandcamp": [
        (re.compile(r"(https?://)?[\w-]+\.bandcamp\.com/track/", re.I), "audio", 0.99),
        (re.compile(r"(https?://)?[\w-]+\.bandcamp\.com/album/", re.I), "playlist", 0.99),
    ],
    "vimeo": [
        (re.compile(r"(https?://)?(www\.)?vimeo\.com/\d+", re.I), "video", 0.99),
        (re.compile(r"(https?://)?player\.vimeo\.com/video/", re.I), "video", 0.99),
    ],
    "dailymotion": [
        (re.compile(r"(https?://)?(www\.)?dailymotion\.com/video/", re.I), "video", 0.99),
        (re.compile(r"(https?://)?dai\.ly/", re.I), "video", 0.99),
    ],
    "tumblr": [
        (re.compile(r"(https?://)?[\w-]+\.tumblr\.com/post/", re.I), "post", 0.90),
    ],
    "pinterest": [
        (re.compile(r"(https?://)?(www\.)?pinterest\.com/pin/", re.I), "image", 0.95),
    ],
    "snapchat": [
        (re.compile(r"(https?://)?(www\.)?snapchat\.com/", re.I), "video", 0.80),
    ],
    "discord": [
        (re.compile(r"(https?://)?(cdn\.)?discordapp\.com/", re.I), "image", 0.85),
        (re.compile(r"(https?://)?(cdn\.)?discord\.com/", re.I), "image", 0.85),
    ],
}


def detect_platform(url: str) -> Optional[PlatformInfo]:
    """
    Auto-detect the platform from a URL.

    Args:
        url: URL to analyze.

    Returns:
        PlatformInfo if detected, None otherwise.
    """
    if not url:
        return None

    best_match: Optional[PlatformInfo] = None
    best_confidence = 0.0

    for platform_name, patterns in _PLATFORM_PATTERNS.items():
        for pattern, url_type, confidence in patterns:
            if pattern.match(url):
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = PlatformInfo(
                        name=platform_name.capitalize(),
                        platform_id=platform_name,
                        url_type=url_type,
                        confidence=confidence,
                    )

    return best_match


# ==============================================================================
# Platform Detector Functions (15+)
# ==============================================================================

def is_youtube_url(url: str) -> bool:
    """Check if URL is a YouTube URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "youtube"

def is_instagram_url(url: str) -> bool:
    """Check if URL is an Instagram URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "instagram"

def is_tiktok_url(url: str) -> bool:
    """Check if URL is a TikTok URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "tiktok"

def is_twitter_url(url: str) -> bool:
    """Check if URL is a Twitter/X URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "twitter"

def is_reddit_url(url: str) -> bool:
    """Check if URL is a Reddit URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "reddit"

def is_facebook_url(url: str) -> bool:
    """Check if URL is a Facebook URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "facebook"

def is_twitch_url(url: str) -> bool:
    """Check if URL is a Twitch URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "twitch"

def is_soundcloud_url(url: str) -> bool:
    """Check if URL is a SoundCloud URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "soundcloud"

def is_spotify_url(url: str) -> bool:
    """Check if URL is a Spotify URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "spotify"

def is_bandcamp_url(url: str) -> bool:
    """Check if URL is a Bandcamp URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "bandcamp"

def is_vimeo_url(url: str) -> bool:
    """Check if URL is a Vimeo URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "vimeo"

def is_dailymotion_url(url: str) -> bool:
    """Check if URL is a Dailymotion URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "dailymotion"

def is_tumblr_url(url: str) -> bool:
    """Check if URL is a Tumblr URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "tumblr"

def is_pinterest_url(url: str) -> bool:
    """Check if URL is a Pinterest URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "pinterest"

def is_snapchat_url(url: str) -> bool:
    """Check if URL is a Snapchat URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "snapchat"

def is_discord_url(url: str) -> bool:
    """Check if URL is a Discord CDN URL."""
    info = detect_platform(url)
    return info is not None and info.platform_id == "discord"

def is_magnet_url(url: str) -> bool:
    """Check if URL is a magnet link."""
    return bool(url and url.startswith("magnet:?"))

def is_live_stream_url(url: str) -> bool:
    """Check if URL appears to be a live stream."""
    info = detect_platform(url)
    if info and info.url_type == "live":
        return True
    live_keywords = ["/live", "/live_stream", "is_live=1", "livestream"]
    return any(kw in url.lower() for kw in live_keywords)


# ==============================================================================
# Batch Validation
# ==============================================================================

def validate_batch_file(filepath: str) -> ValidationResult:
    """Validate a batch download file."""
    result = validate_path(filepath, must_exist=True, must_be_file=True)
    if not result.valid:
        return result

    try:
        with open(filepath, "r") as f:
            lines = f.readlines()
    except (OSError, IOError) as e:
        return _fail(f"Cannot read batch file: {e}")

    if not lines:
        return _fail("Batch file is empty")

    valid_urls = 0
    invalid_lines = []
    for i, line in enumerate(lines, 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        url_result = validate_url(line)
        if url_result.valid:
            valid_urls += 1
        else:
            invalid_lines.append(f"Line {i}: {url_result.error}")

    if valid_urls == 0:
        return _fail(f"No valid URLs found in batch file. Errors: {'; '.join(invalid_lines[:5])}")

    warnings = []
    if invalid_lines:
        warnings.append(f"{len(invalid_lines)} invalid URLs skipped: {'; '.join(invalid_lines[:3])}")

    return _ok(value=filepath, warnings=warnings)


# ==============================================================================
# General Validation Utilities
# ==============================================================================

def validate_positive_int(value: str, name: str = "value", max_val: int = 1000000) -> ValidationResult:
    """Validate a positive integer."""
    try:
        int_val = int(value)
        if int_val < 1:
            return _fail(f"{name} must be a positive integer")
        if int_val > max_val:
            return _fail(f"{name} must be at most {max_val}")
        return _ok(value=str(int_val))
    except (ValueError, TypeError):
        return _fail(f"{name} must be a valid integer")


def validate_range(value: str, min_val: float, max_val: float, name: str = "value") -> ValidationResult:
    """Validate a number within a range."""
    try:
        num = float(value)
        if num < min_val or num > max_val:
            return _fail(f"{name} must be between {min_val} and {max_val}")
        return _ok(value=str(num))
    except (ValueError, TypeError):
        return _fail(f"{name} must be a valid number")


def validate_choice(value: str, choices: List[str], name: str = "value") -> ValidationResult:
    """Validate a value against a list of choices."""
    if value not in choices:
        return _fail(f"{name} must be one of: {', '.join(choices)}")
    return _ok(value=value)
