#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Utilities Package
INFINITE HYPERNOVA SOVEREIGN NEXUS

Central export point for all utility modules.

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng
License: MIT
"""

# ==============================================================================
# Colors Module
# ==============================================================================
from .colors import (
    ESC, Color, colorize, strip_ansi, ansi_len,
    supports_color, color_level, TerminalCapabilities, caps,
    hex_to_rgb, rgb_to_hex, rgb_to_256, rgb_to_hsl, hsl_to_rgb,
    lerp_color, gradient_text, rainbow_text,
    Theme, THEMES, get_theme, set_theme, list_themes, register_theme,
    success, warning, error, info, primary, secondary, muted,
    accent, highlight, title, subtitle,
    status_ok, status_fail, status_warn, status_info, status_arrow,
    status_bullet, status_star,
    box, divider, key_value,
    move_cursor_up, move_cursor_down, clear_line, hide_cursor, show_cursor,
    init_colors,
)

# ==============================================================================
# Banner Module
# ==============================================================================
from .banner import (
    VERSION as BANNER_VERSION, CODENAME, AUTHOR, YEAR,
    BANNER_NEXUS, BANNER_CYBERPUNK, BANNER_MATRIX,
    BANNER_MINIMAL, BANNER_COMPACT,
    BannerStyle, BANNER_STYLES,
    show_banner, get_system_info, format_system_info,
    animate_banner, animate_rainbow, show_loading, get_motd,
    status_line, footer, welcome_screen,
    update_available_banner, register_banner_style,
    list_banner_styles, get_banner_style, get_random_banner,
    LOADING_FRAMES, LOADING_MESSAGES,
    Spinner as BannerSpinner,
)

# ==============================================================================
# Progress Module
# ==============================================================================
from .progress import (
    FileSize, TransferSpeed, TimeRemaining,
    format_speed, format_size, format_time,
    ProgressState, ProgressBar, Spinner, DownloadProgress,
    MultiProgress, PlainProgress,
    progress_bar, spinner as create_spinner,
    download_progress, multi_progress,
    track_progress, track_download, spinning,
)

# ==============================================================================
# Validator Module
# ==============================================================================
from .validator import (
    ValidationResult, validate_url, SUPPORTED_PROTOCOLS,
    validate_proxy, validate_format,
    VIDEO_FORMATS, AUDIO_FORMATS, IMAGE_FORMATS,
    DOCUMENT_FORMATS, SUBTITLE_FORMATS, ALL_FORMATS,
    validate_quality, QUALITY_MAP, AUDIO_QUALITY_MAP,
    validate_path, validate_email, validate_magnet,
    validate_cron, validate_api_key,
    PlatformInfo, detect_platform,
    is_youtube_url, is_instagram_url, is_tiktok_url,
    is_twitter_url, is_reddit_url, is_facebook_url,
    is_twitch_url, is_soundcloud_url, is_spotify_url,
    is_bandcamp_url, is_vimeo_url, is_dailymotion_url,
    is_tumblr_url, is_pinterest_url, is_snapchat_url,
    is_discord_url, is_magnet_url, is_live_stream_url,
    validate_batch_file, validate_positive_int,
    validate_range, validate_choice,
)

# ==============================================================================
# Helpers Module
# ==============================================================================
from .helpers import (
    format_filesize, parse_filesize, format_duration, format_speed,
    format_timestamp, format_timestamp_relative,
    sanitize_filename, generate_id, generate_short_id,
    generate_deterministic_id, ensure_dir,
    get_free_space, get_total_space, get_used_space,
    directory_size, clean_directory,
    get_mime_type, get_extension,
    chunked, flatten, unique,
    rate_limit, retry, timeout, singleton, cached,
    measure_time, Timer, safe_json_loads, safe_json_dumps,
    truncate, pad_right, pad_left, slugify,
    camel_to_snake, snake_to_camel,
    parse_quality, quality_sort_key, get_best_quality,
    human_sort_key, human_sort,
    file_hash, string_hash,
    is_termux, is_root, is_venv,
    get_python_version, get_os_info,
    clamp, safe_get, merge_dicts,
    env_bool, env_int, env_float,
)


# ==============================================================================
# Version
# ==============================================================================

__version__ = "10.0.0"
__codename__ = "INFINITE HYPERNOVA SOVEREIGN NEXUS"
__author__ = "RAJSARASWATI JATAV (RS) / T3rmuxk1ng"


__all__ = [
    # Colors
    "ESC", "Color", "colorize", "strip_ansi", "ansi_len",
    "supports_color", "color_level", "TerminalCapabilities", "caps",
    "hex_to_rgb", "rgb_to_hex", "rgb_to_256", "rgb_to_hsl", "hsl_to_rgb",
    "lerp_color", "gradient_text", "rainbow_text",
    "Theme", "THEMES", "get_theme", "set_theme", "list_themes", "register_theme",
    "success", "warning", "error", "info", "primary", "secondary", "muted",
    "accent", "highlight", "title", "subtitle",
    "status_ok", "status_fail", "status_warn", "status_info", "status_arrow",
    "status_bullet", "status_star", "box", "divider", "key_value",
    "move_cursor_up", "move_cursor_down", "clear_line", "hide_cursor",
    "show_cursor", "init_colors",
    # Banner
    "show_banner", "get_system_info", "format_system_info",
    "animate_banner", "animate_rainbow", "show_loading", "get_motd",
    "status_line", "footer", "welcome_screen", "update_available_banner",
    "register_banner_style", "list_banner_styles", "get_banner_style",
    "get_random_banner", "BannerStyle", "BANNER_STYLES",
    # Progress
    "FileSize", "TransferSpeed", "TimeRemaining",
    "format_speed", "format_size", "format_time",
    "ProgressState", "ProgressBar", "Spinner", "DownloadProgress",
    "MultiProgress", "PlainProgress", "progress_bar", "create_spinner",
    "download_progress", "multi_progress",
    "track_progress", "track_download", "spinning",
    # Validator
    "ValidationResult", "validate_url", "validate_proxy", "validate_format",
    "validate_quality", "validate_path", "validate_email", "validate_magnet",
    "validate_cron", "validate_api_key", "detect_platform", "PlatformInfo",
    "is_youtube_url", "is_instagram_url", "is_tiktok_url", "is_twitter_url",
    "is_reddit_url", "is_facebook_url", "is_twitch_url", "is_soundcloud_url",
    "is_spotify_url", "is_bandcamp_url", "is_vimeo_url", "is_dailymotion_url",
    "is_tumblr_url", "is_pinterest_url", "is_snapchat_url", "is_discord_url",
    "is_magnet_url", "is_live_stream_url", "validate_batch_file",
    "validate_positive_int", "validate_range", "validate_choice",
    "VIDEO_FORMATS", "AUDIO_FORMATS", "IMAGE_FORMATS",
    "DOCUMENT_FORMATS", "SUBTITLE_FORMATS", "ALL_FORMATS",
    "QUALITY_MAP", "AUDIO_QUALITY_MAP", "SUPPORTED_PROTOCOLS",
    # Helpers
    "format_filesize", "parse_filesize", "format_duration", "format_speed",
    "format_timestamp", "format_timestamp_relative", "sanitize_filename",
    "generate_id", "generate_short_id", "generate_deterministic_id",
    "ensure_dir", "get_free_space", "get_total_space", "get_used_space",
    "directory_size", "clean_directory", "get_mime_type", "get_extension",
    "chunked", "flatten", "unique", "rate_limit", "retry", "timeout",
    "singleton", "cached", "measure_time", "Timer", "safe_json_loads",
    "safe_json_dumps", "truncate", "pad_right", "pad_left", "slugify",
    "camel_to_snake", "snake_to_camel", "parse_quality", "quality_sort_key",
    "get_best_quality", "human_sort_key", "human_sort", "file_hash",
    "string_hash", "is_termux", "is_root", "is_venv", "get_python_version",
    "get_os_info", "clamp", "safe_get", "merge_dicts", "env_bool",
    "env_int", "env_float",
]
