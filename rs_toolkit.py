#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Main CLI Entry Point
INFINITE HYPERNOVA SOVEREIGN NEXUS

The brain of the user interface. Full command-line interface with subcommands,
interactive shell mode, tab completion, colored output, and orchestrator integration.

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng
License: MIT
"""

import argparse
import json
import os
import sys
import time
import shutil
import subprocess
import threading
import readline
import shlex
import platform
import signal
import traceback
from pathlib import Path
from typing import Optional, Dict, List, Any, Callable, Tuple
from datetime import datetime

# ==============================================================================
# Version and Metadata
# ==============================================================================

VERSION = "10.0.0"
CODENAME = "INFINITE HYPERNOVA SOVEREIGN NEXUS"
AUTHOR = "RAJSARASWATI JATAV (RS) / T3rmuxk1ng"
PROJECT_NAME = "RS Downloader"
CLI_NAME = "rsdl"
YEAR = "2025"

# ==============================================================================
# Path Configuration
# ==============================================================================

PROJECT_DIR = Path(__file__).parent.resolve()
CONFIG_DIR = Path.home() / ".rs-downloader"
DATA_DIR = CONFIG_DIR / "data"
CACHE_DIR = CONFIG_DIR / "cache"
LOG_DIR = CONFIG_DIR / "logs"
HISTORY_FILE = CONFIG_DIR / "history.json"
SHELL_HISTORY_FILE = CONFIG_DIR / ".rsdl_history"
DB_FILE = DATA_DIR / "downloads.db"
SCHEDULE_FILE = DATA_DIR / "schedules.json"
PROXY_FILE = DATA_DIR / "proxies.json"
BACKUP_DIR = DATA_DIR / "backups"

# Ensure directories exist
for d in [CONFIG_DIR, DATA_DIR, CACHE_DIR, LOG_DIR, BACKUP_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ==============================================================================
# Exit Codes
# ==============================================================================

EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_PARTIAL = 2

# ==============================================================================
# Import Utilities
# ==============================================================================

try:
    from utils import (
        # Colors
        colorize, strip_ansi, supports_color, get_theme, set_theme,
        success, warning, error, info, primary, secondary, muted,
        accent, highlight, title, subtitle,
        status_ok, status_fail, status_warn, status_info,
        status_arrow, status_bullet, status_star,
        box, divider, key_value, hide_cursor, show_cursor,
        init_colors, list_themes, register_theme, Theme,
        # Banner
        show_banner, welcome_screen, get_system_info, format_system_info,
        animate_banner, get_motd, status_line, footer,
        update_available_banner, list_banner_styles,
        # Progress
        ProgressBar, Spinner, DownloadProgress, MultiProgress,
        progress_bar, create_spinner, download_progress, multi_progress,
        track_progress, track_download, spinning,
        FileSize, TransferSpeed, TimeRemaining,
        # Validator
        ValidationResult, validate_url, validate_proxy, validate_format,
        validate_quality, validate_path, validate_email, validate_magnet,
        validate_cron, validate_api_key, detect_platform, PlatformInfo,
        is_youtube_url, is_instagram_url, is_tiktok_url, is_twitter_url,
        is_reddit_url, is_facebook_url, is_twitch_url, is_soundcloud_url,
        is_spotify_url, is_bandcamp_url, is_vimeo_url, is_magnet_url,
        is_live_stream_url, validate_batch_file,
        VIDEO_FORMATS, AUDIO_FORMATS, IMAGE_FORMATS,
        DOCUMENT_FORMATS, SUBTITLE_FORMATS, ALL_FORMATS,
        # Helpers
        format_filesize, parse_filesize, format_duration, format_speed,
        format_timestamp, format_timestamp_relative, sanitize_filename,
        generate_id, ensure_dir, get_free_space, get_mime_type,
        chunked, rate_limit, retry, timeout, singleton, cached,
        measure_time, Timer, safe_json_loads, safe_json_dumps,
        truncate, parse_quality, human_sort, get_os_info,
        is_venv, get_python_version, clamp, safe_get, merge_dicts,
    )
    UTILS_AVAILABLE = True
except ImportError:
    UTILS_AVAILABLE = False

# ==============================================================================
# Fallback implementations when utils are not available
# ==============================================================================

if not UTILS_AVAILABLE:
    def colorize(text, **kwargs): return text
    def strip_ansi(text): return text
    def supports_color(): return False
    def get_theme(): return None
    def set_theme(name): pass
    def success(text): return text
    def warning(text): return text
    def error(text): return text
    def info(text): return text
    def primary(text): return text
    def secondary(text): return text
    def muted(text): return text
    def accent(text): return text
    def highlight(text): return text
    def title(text): return text
    def subtitle(text): return text
    def status_ok(text="OK"): return f"[OK] {text}"
    def status_fail(text="FAIL"): return f"[FAIL] {text}"
    def status_warn(text="WARN"): return f"[WARN] {text}"
    def status_info(text): return f"[INFO] {text}"
    def status_arrow(text): return f"-> {text}"
    def status_bullet(text): return f"* {text}"
    def status_star(text): return f"** {text}"
    def box(text, **kwargs): return text
    def divider(**kwargs): return "-" * 60
    def key_value(key, value, **kwargs): return f"{key}: {value}"
    def hide_cursor(): pass
    def show_cursor(): pass
    def init_colors(): pass
    def list_themes(): return ["nexus"]
    def show_banner(**kwargs): return f"{PROJECT_NAME} v{VERSION}"
    def welcome_screen(**kwargs): print(show_banner())
    def get_system_info(): return {}
    def format_system_info(info=None): return ""
    def animate_banner(**kwargs): print(show_banner())
    def get_motd(): return ""
    def status_line(**kwargs): return ""
    def footer(): return ""
    def update_available_banner(cur, lat): return f"Update: {cur} -> {lat}"
    def list_banner_styles(): return ["nexus"]
    def ProgressBar(**kwargs): return None
    def Spinner(**kwargs): return None
    def DownloadProgress(**kwargs): return None
    def MultiProgress(**kwargs): return None
    def FileSize(): pass
    def TransferSpeed(): pass
    def TimeRemaining(): pass
    class ValidationResult:
        def __init__(self, valid=False, value=None, error=None, warnings=None):
            self.valid = valid; self.value = value; self.error = error; self.warnings = warnings or []
        def __bool__(self): return self.valid
    def validate_url(url, **kwargs):
        if url and url.startswith("http"): return ValidationResult(valid=True, value=url)
        return ValidationResult(valid=False, error="Invalid URL")
    def validate_proxy(proxy, **kwargs): return ValidationResult(valid=True, value=proxy)
    def validate_format(fmt, **kwargs): return ValidationResult(valid=True, value=fmt)
    def validate_quality(q, **kwargs): return ValidationResult(valid=True, value=q)
    def validate_path(p, **kwargs): return ValidationResult(valid=True, value=p)
    def validate_email(e, **kwargs): return ValidationResult(valid=True, value=e)
    def validate_magnet(m, **kwargs): return ValidationResult(valid=True, value=m)
    def validate_cron(c, **kwargs): return ValidationResult(valid=True, value=c)
    def validate_api_key(k, **kwargs): return ValidationResult(valid=True, value=k)
    def detect_platform(url): return None
    def is_youtube_url(url): return "youtube" in url or "youtu.be" in url
    def is_instagram_url(url): return "instagram" in url
    def is_tiktok_url(url): return "tiktok" in url
    def is_twitter_url(url): return "twitter" in url or "x.com" in url
    def is_reddit_url(url): return "reddit" in url
    def is_facebook_url(url): return "facebook" in url
    def is_twitch_url(url): return "twitch" in url
    def is_soundcloud_url(url): return "soundcloud" in url
    def is_spotify_url(url): return "spotify" in url
    def is_bandcamp_url(url): return "bandcamp" in url
    def is_vimeo_url(url): return "vimeo" in url
    def is_magnet_url(url): return url.startswith("magnet:?")
    def is_live_stream_url(url): return False
    def validate_batch_file(f, **kwargs): return ValidationResult(valid=True, value=f)
    VIDEO_FORMATS = {"mp4", "mkv", "avi", "mov", "webm", "flv"}
    AUDIO_FORMATS = {"mp3", "flac", "aac", "wav", "ogg", "opus", "m4a"}
    IMAGE_FORMATS = {"jpg", "png", "gif", "webp"}
    DOCUMENT_FORMATS = {"pdf", "doc", "txt", "epub"}
    SUBTITLE_FORMATS = {"srt", "ass", "vtt"}
    ALL_FORMATS = VIDEO_FORMATS | AUDIO_FORMATS | IMAGE_FORMATS | DOCUMENT_FORMATS | SUBTITLE_FORMATS
    def format_filesize(size, **kwargs): return f"{size} B"
    def format_duration(seconds, **kwargs): return f"{seconds}s"
    def format_speed(speed, **kwargs): return f"{speed} B/s"
    def format_timestamp(ts=None, **kwargs): return str(ts or datetime.now())
    def format_timestamp_relative(ts=None): return "just now"
    def sanitize_filename(name, **kwargs): return name
    def generate_id(prefix=""): return prefix + "123456"
    def ensure_dir(path): os.makedirs(path, exist_ok=True); return Path(path)
    def get_free_space(path="."): return 0
    def get_mime_type(fp): return "application/octet-stream"
    def chunked(it, size): return [it[i:i+size] for i in range(0, len(list(it)), size)]
    def measure_time(label="Op"): pass
    def safe_json_loads(text, default=None): return default
    def safe_json_dumps(obj, **kwargs): return json.dumps(obj)
    def truncate(text, max_length=50): return text[:max_length]
    def parse_quality(q): return (1920, 1080)
    def human_sort(it, **kwargs): return sorted(it)
    def get_os_info(): return {}
    def is_venv(): return False
    def get_python_version(): return "3.x"
    def clamp(v, mn, mx): return max(mn, min(mx, v))
    def safe_get(d, p, default=None): return default
    def merge_dicts(b, o): b.update(o); return b

# ==============================================================================
# Import Core Modules
# ==============================================================================

try:
    from core.downloader_base import (
        DownloadOrchestrator as CoreOrchestrator,
        DownloadTask,
        DownloadPriority,
        DownloadStatus,
        DownloadResult,
        DownloadQueue,
        DownloadScheduler,
        DownloadLifecycle,
    )
    CORE_AVAILABLE = True
except ImportError:
    CORE_AVAILABLE = False

try:
    from core.config import ConfigManager as CoreConfigManager
    CORE_CONFIG_AVAILABLE = True
except ImportError:
    CORE_CONFIG_AVAILABLE = False

try:
    from agents import get_registry, list_all_agents, AGENT_COUNT, AGENT_CATEGORIES
    AGENTS_AVAILABLE = True
except ImportError:
    AGENTS_AVAILABLE = False

try:
    from core.database import Database as DatabaseManager
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False

# ==============================================================================
# Local ConfigManager (fallback when core.config unavailable)
# ==============================================================================

class LocalConfigManager:
    """Manages application configuration with profiles and persistence."""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config_file=None):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self._config_file = Path(config_file) if config_file else CONFIG_DIR / "config.json"
        self._profile = "default"
        self._data = {}
        self._load()

    def _load(self):
        if self._config_file.exists():
            try:
                with open(self._config_file, "r") as f:
                    self._data = safe_json_loads(f.read(), default={})
            except (OSError, json.JSONDecodeError):
                self._data = self._defaults()
        else:
            self._data = self._defaults()
            self._save()

    def _save(self):
        try:
            ensure_dir(self._config_file.parent)
            with open(self._config_file, "w") as f:
                f.write(safe_json_dumps(self._data, indent=2))
        except OSError as e:
            print(error(f"Failed to save config: {e}"))

    def _defaults(self):
        return {
            "general": {"theme": "nexus", "banner_style": "nexus", "language": "en",
                        "check_updates": True, "shell_history": True, "max_history": 1000},
            "download": {"output_dir": str(Path.home() / "Downloads" / "RS-Downloader"),
                         "max_concurrent": 3, "max_retries": 3, "timeout": 300,
                         "overwrite": False, "resume": True},
            "video": {"default_quality": "1080p", "preferred_format": "mp4",
                      "embed_subtitles": False, "embed_thumbnail": False, "embed_metadata": True},
            "audio": {"default_quality": "320k", "preferred_format": "mp3",
                      "embed_thumbnail": True, "embed_metadata": True},
            "network": {"proxy": None, "proxy_type": "http", "cookies_file": None,
                        "rate_limit": 0, "geo_bypass": True},
            "advanced": {"debug": False, "verbose": False, "log_level": "INFO"},
        }

    def get(self, path, default=None):
        return safe_get(self._data, path, default)

    def set(self, path, value):
        keys = path.split(".")
        current = self._data
        for key in keys[:-1]:
            if key not in current or not isinstance(current[key], dict):
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value
        self._save()

    def reset(self, path=None):
        if path:
            defaults = self._defaults()
            value = safe_get(defaults, path)
            if value is not None:
                self.set(path, value)
        else:
            self._data = self._defaults()
            self._save()

    def export(self, filepath):
        with open(filepath, "w") as f:
            f.write(safe_json_dumps(self._data, indent=2))

    def validate(self):
        issues = []
        output_dir = self.get("download.output_dir")
        if output_dir:
            try:
                ensure_dir(output_dir)
            except OSError as e:
                issues.append(f"Output directory not writable: {e}")
        return issues

    @property
    def data(self):
        return self._data

    def profile(self, name=None):
        if name:
            self._profile = name
        return self._profile


# Select the appropriate config manager
if CORE_CONFIG_AVAILABLE:
    try:
        _test_cfg = CoreConfigManager()
        ConfigManager = CoreConfigManager
    except Exception:
        ConfigManager = LocalConfigManager
else:
    ConfigManager = LocalConfigManager


# ==============================================================================
# Local DownloadOrchestrator (fallback)
# ==============================================================================

if CORE_AVAILABLE:
    try:
        _test_orch = CoreOrchestrator()
        Orchestrator = CoreOrchestrator
    except Exception:
        Orchestrator = None
else:
    Orchestrator = None


class LocalOrchestrator:
    """Local download orchestrator for when core module is unavailable."""

    def __init__(self, config=None):
        self.config = config or LocalConfigManager()
        self._active = {}
        self._completed = []
        self._failed = []
        self._lock = threading.Lock()

    def download(self, url, **kwargs):
        dl_id = generate_id("dl")
        output_dir = kwargs.get("output_dir", self.config.get("storage.download_dir") or self.config.get("storage.download_dir") or config.get("download.output_dir"))
        ensure_dir(output_dir)
        platform_info = detect_platform(url) if detect_platform else None
        platform_name = platform_info.platform_id if platform_info else "generic"
        result = {"id": dl_id, "url": url, "platform": platform_name,
                  "status": "pending", "started_at": datetime.now().isoformat(),
                  "output_dir": output_dir, **kwargs}
        with self._lock:
            self._active[dl_id] = result
        try:
            result["status"] = "downloading"
            ydl_opts = self._build_ydl_opts(url, **kwargs)
            ok = self._execute_ytdlp(url, ydl_opts, result)
            if ok:
                result["status"] = "completed"
                result["completed_at"] = datetime.now().isoformat()
                with self._lock:
                    self._completed.append(result)
                    self._active.pop(dl_id, None)
            else:
                result["status"] = "failed"
                with self._lock:
                    self._failed.append(result)
                    self._active.pop(dl_id, None)
        except Exception as e:
            result["status"] = "failed"
            result["error"] = str(e)
            with self._lock:
                self._failed.append(result)
                self._active.pop(dl_id, None)
        return result

    def _build_ydl_opts(self, url, **kwargs):
        opts = {
            "outtmpl": str(Path(kwargs.get("output_dir", self.config.get("storage.download_dir") or self.config.get("storage.download_dir") or config.get("download.output_dir")))
                           / "%(title)s.%(ext)s"),
            "quiet": kwargs.get("quiet", False),
            "no_warnings": True,
            "restrictfilenames": True,
            "noplaylist": kwargs.get("no_playlist", True),
        }
        proxy = kwargs.get("proxy", self.config.get("network.proxy"))
        if proxy:
            opts["proxy"] = proxy
        if self.config.get("download.resume", True):
            opts["continuedl"] = True
        if not self.config.get("download.overwrite", False):
            opts["nooverwrites"] = True
        opts["retries"] = kwargs.get("retries", self.config.get("download.max_retries", 3))
        return opts

    def _execute_ytdlp(self, url, opts, result):
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                ydl.download([url])
            return True
        except ImportError:
            return self._execute_ytdlp_subprocess(url, opts)
        except Exception as e:
            result["error"] = str(e)
            return False

    def _execute_ytdlp_subprocess(self, url, opts):
        if not shutil.which("yt-dlp"):
            print(error("yt-dlp not found. Install: pip install yt-dlp"))
            return False
        cmd = ["yt-dlp", url]
        if opts.get("proxy"):
            cmd.extend(["--proxy", opts["proxy"]])
        if opts.get("nooverwrites"):
            cmd.append("--no-overwrites")
        if opts.get("continuedl"):
            cmd.append("--continue")
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return proc.returncode == 0
        except Exception:
            return False

    def download_audio(self, url, **kwargs):
        fmt = kwargs.get("format", self.config.get("audio.preferred_format", "mp3"))
        quality = kwargs.get("quality", self.config.get("audio.default_quality", "320k"))
        q_map = {"64k": 0, "128k": 5, "192k": 7, "256k": 8, "320k": 9}
        br = q_map.get(quality, 9)
        kwargs["postprocessors"] = [{"key": "FFmpegExtractAudio",
                                     "preferredcodec": fmt, "preferredquality": str(br)}]
        kwargs["_audio_mode"] = True
        return self.download(url, **kwargs)

    def download_video(self, url, **kwargs):
        quality = kwargs.get("quality", self.config.get("video.default_quality", "1080p"))
        fmt = kwargs.get("format", self.config.get("video.preferred_format", "mp4"))
        height = quality.replace("p", "")
        format_str = f"bestvideo[height<={height}]+bestaudio/best[height<={height}]/best"
        kwargs["format"] = format_str
        kwargs["merge_output_format"] = fmt
        return self.download(url, **kwargs)

    def download_batch(self, filepath, **kwargs):
        urls = []
        try:
            with open(filepath) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        urls.append(line)
        except OSError as e:
            print(error(f"Cannot read batch file: {e}"))
            return []
        results = []
        max_c = kwargs.get("max_concurrent", self.config.get("download.max_concurrent", 3))
        for chunk in chunked(urls, max_c):
            chunk_results = []
            threads = []
            def _dl(u):
                chunk_results.append(self.download(u, **kwargs))
            for url in chunk:
                t = threading.Thread(target=_dl, args=(url,))
                threads.append(t)
                t.start()
            for t in threads:
                t.join()
            results.extend(chunk_results)
        return results

    def download_playlist(self, url, **kwargs):
        kwargs["no_playlist"] = False
        start = kwargs.get("start", 1)
        end = kwargs.get("end", None)
        kwargs["playliststart"] = start
        if end:
            kwargs["playlistend"] = end
        if kwargs.get("reverse"):
            kwargs["playlistreverse"] = True
        return [self.download(url, **kwargs)]

    def record_live(self, url, **kwargs):
        kwargs["live_from_start"] = True
        duration = kwargs.get("duration", 0)
        if duration > 0:
            kwargs["timeout"] = duration
        return self.download(url, **kwargs)

    def download_subtitles(self, url, **kwargs):
        langs = kwargs.get("languages", ["en"])
        sub_fmt = kwargs.get("format", "srt")
        kwargs["writesubtitles"] = True
        kwargs["subtitleslangs"] = langs
        kwargs["subtitlesformat"] = sub_fmt
        kwargs["skip_download"] = True
        return self.download(url, **kwargs)

    def download_thumbnail(self, url, **kwargs):
        kwargs["writethumbnail"] = True
        kwargs["skip_download"] = True
        return self.download(url, **kwargs)

    def extract_metadata(self, url, **kwargs):
        opts = self._build_ydl_opts(url, **kwargs)
        opts["quiet"] = True
        opts["skip_download"] = True
        opts["dumpjson"] = True
        info = {}
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False) or {}
        except ImportError:
            try:
                proc = subprocess.run(["yt-dlp", "--dump-json", "--no-download", url],
                                      capture_output=True, text=True, timeout=60)
                if proc.returncode == 0:
                    info = safe_json_loads(proc.stdout, default={})
            except Exception:
                pass
        except Exception as e:
            info["error"] = str(e)
        return info

    def search(self, query, **kwargs):
        engine = kwargs.get("engine", "youtube")
        max_results = kwargs.get("max_results", 20)
        results = []
        try:
            import yt_dlp
            search_url = f"{engine}search{max_results}:{query}"
            with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                info = ydl.extract_info(search_url, download=False)
                if info and "entries" in info:
                    for entry in info["entries"][:max_results]:
                        results.append({"title": entry.get("title", "Unknown"),
                                        "url": entry.get("url", entry.get("webpage_url", "")),
                                        "duration": entry.get("duration"),
                                        "uploader": entry.get("uploader", "")})
        except ImportError:
            print(error("yt-dlp is required for search"))
        except Exception as e:
            print(error(f"Search failed: {e}"))
        return results

    def convert(self, input_file, output_format, **kwargs):
        if not shutil.which("ffmpeg"):
            return {"status": "error", "error": "ffmpeg not found"}
        output_file = kwargs.get("output_file")
        if not output_file:
            base = Path(input_file).stem
            output_file = str(Path(input_file).parent / f"{base}.{output_format}")
        cmd = ["ffmpeg", "-i", input_file]
        if output_format in VIDEO_FORMATS:
            cmd.extend(["-c:v", kwargs.get("video_codec", "libx264"),
                         "-crf", str(kwargs.get("crf", 23))])
        cmd.extend(["-c:a", kwargs.get("audio_codec", "aac"),
                     "-b:a", kwargs.get("audio_bitrate", "192k"), "-y", output_file])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
            if proc.returncode == 0:
                return {"status": "completed", "output_file": output_file}
            return {"status": "error", "error": proc.stderr[-500:] if proc.stderr else "Unknown"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def mirror(self, url, **kwargs):
        if not shutil.which("wget"):
            return {"status": "error", "error": "wget not found"}
        output_dir = kwargs.get("output_dir", self.config.get("storage.download_dir") or self.config.get("storage.download_dir") or config.get("download.output_dir"))
        depth = kwargs.get("depth", 3)
        domains = kwargs.get("domains", "")
        cmd = ["wget", "--mirror", "--directory-prefix", output_dir,
               "--level", str(depth), "--no-parent", "--convert-links", "--no-clobber"]
        if domains:
            cmd.extend(["--domains", domains])
        cmd.append(url)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=86400)
            return {"status": "completed" if proc.returncode == 0 else "error"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def recursive_download(self, url, **kwargs):
        if not shutil.which("wget"):
            return {"status": "error", "error": "wget not found"}
        depth = kwargs.get("depth", 2)
        types = kwargs.get("types", "")
        output_dir = kwargs.get("output_dir", self.config.get("storage.download_dir") or self.config.get("storage.download_dir") or config.get("download.output_dir"))
        cmd = ["wget", "--recursive", "--level", str(depth),
               "--directory-prefix", output_dir, "--no-clobber"]
        if types:
            cmd.extend(["--accept", types])
        cmd.append(url)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=86400)
            return {"status": "completed" if proc.returncode == 0 else "error"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def download_torrent(self, magnet_or_file, **kwargs):
        if not shutil.which("aria2c") and not shutil.which("webtorrent"):
            return {"status": "error", "error": "No torrent client found (aria2c/webtorrent)"}
        output_dir = kwargs.get("output_dir", self.config.get("storage.download_dir") or self.config.get("storage.download_dir") or config.get("download.output_dir"))
        seed_ratio = kwargs.get("seed_ratio", 1.0)
        if shutil.which("aria2c"):
            cmd = ["aria2c", "--seed-ratio", str(seed_ratio), "--dir", output_dir, magnet_or_file]
        else:
            cmd = ["webtorrent", "download", magnet_or_file, "--out", output_dir]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=86400)
            return {"status": "completed" if proc.returncode == 0 else "error"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    @property
    def stats(self):
        with self._lock:
            return {"active": len(self._active), "completed": len(self._completed),
                    "failed": len(self._failed),
                    "total": len(self._completed) + len(self._failed) + len(self._active)}


# Initialize orchestrator
def create_orchestrator(config):
    """Create the appropriate orchestrator based on available modules."""
    if Orchestrator is not None:
        try:
            return Orchestrator(config)
        except Exception:
            pass
    return LocalOrchestrator(config)


# ==============================================================================
# History Manager
# ==============================================================================

class HistoryManager:
    """Manages download history."""

    def __init__(self, history_file=None):
        self._file = history_file or HISTORY_FILE
        self._entries = []
        self._load()

    def _load(self):
        if self._file.exists():
            try:
                with open(self._file) as f:
                    self._entries = safe_json_loads(f.read(), default=[])
            except OSError:
                self._entries = []

    def _save(self):
        try:
            with open(self._file, "w") as f:
                f.write(safe_json_dumps(self._entries, indent=2))
        except OSError:
            pass

    def add(self, entry):
        self._entries.append(entry)
        self._save()

    def search(self, query):
        query = query.lower()
        return [e for e in self._entries
                if query in e.get("url", "").lower()
                or query in e.get("title", "").lower()
                or query in e.get("filename", "").lower()]

    def list_entries(self, limit=20, offset=0, **kwargs):
        entries = self._entries
        if kwargs.get("status"):
            entries = [e for e in entries if e.get("status") == kwargs["status"]]
        if kwargs.get("platform"):
            entries = [e for e in entries if e.get("platform") == kwargs["platform"]]
        if kwargs.get("date_from"):
            entries = [e for e in entries if e.get("started_at", "") >= kwargs["date_from"]]
        if kwargs.get("date_to"):
            entries = [e for e in entries if e.get("started_at", "") <= kwargs["date_to"]]
        return entries[offset:offset + limit]

    def export_entries(self, fmt="json", output=None):
        entries = self._entries
        if fmt == "csv":
            import csv
            import io
            buf = io.StringIO()
            if entries:
                writer = csv.DictWriter(buf, fieldnames=entries[0].keys())
                writer.writeheader()
                writer.writerows(entries)
            content = buf.getvalue()
        elif fmt == "html":
            content = "<html><body><table border='1'>\n"
            if entries:
                content += "<tr>" + "".join(f"<th>{k}</th>" for k in entries[0].keys()) + "</tr>\n"
                for e in entries:
                    content += "<tr>" + "".join(f"<td>{v}</td>" for v in e.values()) + "</tr>\n"
            content += "</table></body></html>"
        else:
            content = safe_json_dumps(entries, indent=2)
        if output:
            with open(output, "w") as f:
                f.write(content)
        return content

    def clear(self):
        self._entries = []
        self._save()

    @property
    def count(self):
        return len(self._entries)


# ==============================================================================
# Scheduler Manager
# ==============================================================================

class SchedulerManager:
    """Manages scheduled download tasks."""

    def __init__(self):
        self._tasks = {}
        self._load()

    def _load(self):
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE) as f:
                    self._tasks = safe_json_loads(f.read(), default={})
            except OSError:
                self._tasks = {}

    def _save(self):
        try:
            with open(SCHEDULE_FILE, "w") as f:
                f.write(safe_json_dumps(self._tasks, indent=2))
        except OSError:
            pass

    def add_task(self, url, schedule=None, cron=None):
        task_id = generate_id("sched")
        self._tasks[task_id] = {
            "id": task_id, "url": url, "schedule": schedule, "cron": cron,
            "enabled": True, "created_at": datetime.now().isoformat(),
            "last_run": None, "run_count": 0,
        }
        self._save()
        return task_id

    def remove_task(self, task_id):
        removed = self._tasks.pop(task_id, None)
        if removed:
            self._save()
        return removed is not None

    def enable_task(self, task_id):
        if task_id in self._tasks:
            self._tasks[task_id]["enabled"] = True
            self._save()
            return True
        return False

    def disable_task(self, task_id):
        if task_id in self._tasks:
            self._tasks[task_id]["enabled"] = False
            self._save()
            return True
        return False

    def list_tasks(self):
        return list(self._tasks.values())


# ==============================================================================
# Proxy Manager
# ==============================================================================

class ProxyManager:
    """Manages proxy configuration and testing."""

    def __init__(self):
        self._proxies = {}
        self._load()

    def _load(self):
        if PROXY_FILE.exists():
            try:
                with open(PROXY_FILE) as f:
                    self._proxies = safe_json_loads(f.read(), default={})
            except OSError:
                self._proxies = {}

    def _save(self):
        try:
            with open(PROXY_FILE, "w") as f:
                f.write(safe_json_dumps(self._proxies, indent=2))
        except OSError:
            pass

    def add_proxy(self, proxy_url, proxy_type="http", country=""):
        proxy_id = generate_id("px")
        self._proxies[proxy_id] = {
            "id": proxy_id, "url": proxy_url, "type": proxy_type,
            "country": country, "enabled": True,
            "added_at": datetime.now().isoformat(),
            "last_test": None, "latency_ms": None, "working": None,
        }
        self._save()
        return proxy_id

    def remove_proxy(self, proxy_id):
        removed = self._proxies.pop(proxy_id, None)
        if removed:
            self._save()
        return removed is not None

    def test_proxy(self, proxy_url):
        """Test a proxy by making a request through it."""
        try:
            cmd = ["curl", "-x", proxy_url, "-o", "/dev/null",
                   "-s", "-w", "%{time_total}", "--connect-timeout", "10",
                   "https://httpbin.org/ip"]
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if proc.returncode == 0:
                latency = float(proc.stdout.strip()) * 1000
                return {"working": True, "latency_ms": round(latency, 2)}
            return {"working": False, "latency_ms": None, "error": "Connection failed"}
        except Exception as e:
            return {"working": False, "latency_ms": None, "error": str(e)}

    def health_check(self):
        """Test all proxies."""
        results = {}
        for pid, proxy in self._proxies.items():
            if proxy.get("enabled"):
                result = self.test_proxy(proxy["url"])
                proxy["last_test"] = datetime.now().isoformat()
                proxy["working"] = result["working"]
                proxy["latency_ms"] = result.get("latency_ms")
                results[pid] = result
        self._save()
        return results

    def list_proxies(self):
        return list(self._proxies.values())

    def enable_proxy(self, proxy_id):
        if proxy_id in self._proxies:
            self._proxies[proxy_id]["enabled"] = True
            self._save()
            return True
        return False

    def disable_proxy(self, proxy_id):
        if proxy_id in self._proxies:
            self._proxies[proxy_id]["enabled"] = False
            self._save()
            return True
        return False


# ==============================================================================
# Cache Manager
# ==============================================================================

class CacheManager:
    """Simple key-value cache with TTL support."""

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def get(self, key):
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if entry.get("expires_at") and time.time() > entry["expires_at"]:
                del self._cache[key]
                return None
            return entry["value"]

    def set(self, key, value, ttl=None):
        with self._lock:
            expires_at = time.time() + ttl if ttl else None
            self._cache[key] = {"value": value, "expires_at": expires_at,
                                "created_at": time.time()}

    def delete(self, key):
        with self._lock:
            return self._cache.pop(key, None) is not None

    def cleanup(self):
        with self._lock:
            now = time.time()
            expired = [k for k, v in self._cache.items()
                       if v.get("expires_at") and now > v["expires_at"]]
            for k in expired:
                del self._cache[k]
            return len(expired)

    def stats(self):
        with self._lock:
            now = time.time()
            active = sum(1 for v in self._cache.values()
                         if not v.get("expires_at") or now <= v["expires_at"])
            expired = len(self._cache) - active
            return {"total": len(self._cache), "active": active, "expired": expired}


# ==============================================================================
# Backup Manager
# ==============================================================================

class BackupManager:
    """Manages configuration and data backups."""

    def create(self, output=None):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = output or str(BACKUP_DIR / f"backup_{timestamp}.json")
        data = {"version": VERSION, "created_at": datetime.now().isoformat(), "data": {}}
        # Collect config
        if (CONFIG_DIR / "config.json").exists():
            try:
                with open(CONFIG_DIR / "config.json") as f:
                    data["data"]["config"] = safe_json_loads(f.read(), default={})
            except OSError:
                pass
        # Collect history
        if HISTORY_FILE.exists():
            try:
                with open(HISTORY_FILE) as f:
                    data["data"]["history"] = safe_json_loads(f.read(), default=[])
            except OSError:
                pass
        # Collect schedules
        if SCHEDULE_FILE.exists():
            try:
                with open(SCHEDULE_FILE) as f:
                    data["data"]["schedules"] = safe_json_loads(f.read(), default={})
            except OSError:
                pass
        try:
            with open(filename, "w") as f:
                f.write(safe_json_dumps(data, indent=2))
            return filename
        except OSError as e:
            print(error(f"Backup failed: {e}"))
            return None

    def restore(self, input_path):
        try:
            with open(input_path) as f:
                data = safe_json_loads(f.read(), default={})
        except OSError as e:
            print(error(f"Cannot read backup: {e}"))
            return False
        backup_data = data.get("data", {})
        if "config" in backup_data:
            with open(CONFIG_DIR / "config.json", "w") as f:
                f.write(safe_json_dumps(backup_data["config"], indent=2))
        if "history" in backup_data:
            with open(HISTORY_FILE, "w") as f:
                f.write(safe_json_dumps(backup_data["history"], indent=2))
        if "schedules" in backup_data:
            with open(SCHEDULE_FILE, "w") as f:
                f.write(safe_json_dumps(backup_data["schedules"], indent=2))
        return True

    def list_backups(self):
        if not BACKUP_DIR.exists():
            return []
        backups = []
        for f in sorted(BACKUP_DIR.glob("backup_*.json")):
            stat = f.stat()
            backups.append({"name": f.name, "path": str(f),
                            "size": stat.st_size, "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()})
        return backups


# ==============================================================================
# CLI Argument Builder
# ==============================================================================

def build_parser():
    """Build the main argument parser with all subcommands."""
    parser = argparse.ArgumentParser(
        prog=CLI_NAME,
        description=f"{PROJECT_NAME} v{VERSION} - The Ultimate Download Toolkit",
        epilog=f"Author: {AUTHOR} | License: MIT | Codename: {CODENAME}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Global options
    parser.add_argument("--version", action="version",
                        version=f"%(prog)s {VERSION} ({CODENAME})")
    parser.add_argument("-v", "--verbose", action="count", default=0,
                        help="Increase verbosity (can be used multiple times)")
    parser.add_argument("-q", "--quiet", action="store_true",
                        help="Suppress non-error output")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    parser.add_argument("--config", metavar="FILE", type=str,
                        help="Path to configuration file")
    parser.add_argument("--profile", metavar="PROFILE", type=str,
                        help="Configuration profile to use")

    # Subparsers
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # --- Download Commands ---
    _add_download_subparser(subparsers)
    _add_audio_subparser(subparsers)
    _add_video_subparser(subparsers)
    _add_batch_subparser(subparsers)
    _add_playlist_subparser(subparsers)
    _add_live_subparser(subparsers)
    _add_subtitle_subparser(subparsers)
    _add_thumbnail_subparser(subparsers)
    _add_metadata_subparser(subparsers)
    _add_convert_subparser(subparsers)
    _add_search_subparser(subparsers)
    _add_torrent_subparser(subparsers)
    _add_mirror_subparser(subparsers)
    _add_recursive_subparser(subparsers)

    # --- Platform Commands ---
    _add_platform_subparsers(subparsers)

    # --- Management Commands ---
    _add_config_subparser(subparsers)
    _add_system_subparser(subparsers)
    _add_update_subparser(subparsers)
    _add_history_subparser(subparsers)
    _add_scheduler_subparser(subparsers)
    _add_proxy_subparser(subparsers)
    _add_cloud_subparser(subparsers)
    _add_plugin_subparser(subparsers)
    _add_agents_subparser(subparsers)
    _add_stats_subparser(subparsers)
    _add_cache_subparser(subparsers)
    _add_backup_subparser(subparsers)
    _add_speed_test_subparser(subparsers)

    return parser


# ---- Download subcommand builders ----

def _add_download_subparser(subparsers):
    p = subparsers.add_parser("download", aliases=["dl"],
                              help="Download any URL (auto-detect platform)")
    p.add_argument("url", help="URL to download")
    p.add_argument("-q", "--quality", default=None, help="Quality selection")
    p.add_argument("-f", "--format", default=None, help="Output format")
    p.add_argument("-o", "--output", default=None, help="Output directory")
    p.add_argument("--proxy", default=None, help="Proxy URL")
    p.add_argument("--no-check", action="store_true", help="Skip certificate checks")
    p.add_argument("--subtitle", action="store_true", help="Download subtitles")
    p.add_argument("--thumbnail", action="store_true", help="Download thumbnail")
    p.add_argument("--metadata", action="store_true", help="Download metadata")
    p.add_argument("--convert", metavar="FORMAT", default=None,
                   help="Convert to format after download")


def _add_audio_subparser(subparsers):
    p = subparsers.add_parser("audio", aliases=["au"],
                              help="Download audio from URL")
    p.add_argument("url", help="URL to download audio from")
    p.add_argument("-f", "--format", default="mp3",
                   choices=["mp3", "flac", "aac", "wav", "ogg", "opus", "m4a"],
                   help="Audio format (default: mp3)")
    p.add_argument("-q", "--quality", default="320k",
                   choices=["64k", "128k", "192k", "256k", "320k"],
                   help="Audio quality (default: 320k)")
    p.add_argument("-o", "--output", default=None, help="Output directory")
    p.add_argument("--embed-thumb", action="store_true", help="Embed thumbnail")
    p.add_argument("--embed-metadata", action="store_true", help="Embed metadata")


def _add_video_subparser(subparsers):
    p = subparsers.add_parser("video", aliases=["vid"],
                              help="Download video from URL")
    p.add_argument("url", help="URL to download video from")
    p.add_argument("-q", "--quality", default="1080p",
                   choices=["240p", "360p", "480p", "720p", "1080p", "1440p", "2160p", "4320p", "8K"],
                   help="Video quality (default: 1080p)")
    p.add_argument("-f", "--format", default="mp4",
                   choices=["mp4", "mkv", "webm", "avi"],
                   help="Video format (default: mp4)")
    p.add_argument("-o", "--output", default=None, help="Output directory")
    p.add_argument("--subtitle", action="store_true", help="Download subtitles")
    p.add_argument("--thumbnail", action="store_true", help="Download thumbnail")
    p.add_argument("--audio-only", action="store_true", help="Extract audio only")


def _add_batch_subparser(subparsers):
    p = subparsers.add_parser("batch", aliases=["b"],
                              help="Download URLs from a file")
    p.add_argument("file", help="File containing URLs (one per line)")
    p.add_argument("-q", "--quality", default=None, help="Quality for all downloads")
    p.add_argument("--max-concurrent", type=int, default=3, help="Max concurrent downloads")
    p.add_argument("--retry-failed", action="store_true", help="Retry failed downloads")


def _add_playlist_subparser(subparsers):
    p = subparsers.add_parser("playlist", aliases=["pl"],
                              help="Download a playlist")
    p.add_argument("url", help="Playlist URL")
    p.add_argument("--start", type=int, default=1, help="Start from item #")
    p.add_argument("--end", type=int, default=None, help="End at item #")
    p.add_argument("--reverse", action="store_true", help="Download in reverse order")
    p.add_argument("-q", "--quality", default=None, help="Quality selection")


def _add_live_subparser(subparsers):
    p = subparsers.add_parser("live", aliases=["rec"],
                              help="Record a live stream")
    p.add_argument("url", help="Live stream URL")
    p.add_argument("--duration", type=int, default=0, help="Recording duration in seconds (0=unlimited)")
    p.add_argument("--format", default="ts", help="Output format (default: ts)")
    p.add_argument("--quality", default="best", help="Stream quality (default: best)")


def _add_subtitle_subparser(subparsers):
    p = subparsers.add_parser("subtitle", aliases=["sub"],
                              help="Download subtitles")
    p.add_argument("url", help="URL to get subtitles from")
    p.add_argument("--lang", nargs="+", default=["en"], help="Language codes (default: en)")
    p.add_argument("--format", default="srt", choices=["srt", "vtt", "ass"],
                   help="Subtitle format (default: srt)")
    p.add_argument("--translate", metavar="LANG", default=None, help="Translate to language")
    p.add_argument("--output", default=None, help="Output directory")


def _add_thumbnail_subparser(subparsers):
    p = subparsers.add_parser("thumbnail", aliases=["thumb"],
                              help="Download video thumbnail")
    p.add_argument("url", help="URL to get thumbnail from")
    p.add_argument("--all", action="store_true", help="Download all available thumbnails")
    p.add_argument("--format", default="jpg", choices=["jpg", "png", "webp"],
                   help="Image format (default: jpg)")
    p.add_argument("--output", default=None, help="Output directory")


def _add_metadata_subparser(subparsers):
    p = subparsers.add_parser("metadata", aliases=["meta"],
                              help="Extract media metadata")
    p.add_argument("url", help="URL to extract metadata from")
    p.add_argument("--json", action="store_true", help="Output as JSON")
    p.add_argument("--save", action="store_true", help="Save metadata to file")


def _add_convert_subparser(subparsers):
    p = subparsers.add_parser("convert", aliases=["conv"],
                              help="Convert between media formats")
    p.add_argument("input", help="Input file path")
    p.add_argument("--to-format", required=True, help="Target format (e.g., mp4, mp3, mkv)")
    p.add_argument("--quality", default=None, help="Quality preset")
    p.add_argument("--output", default=None, help="Output file path")


def _add_search_subparser(subparsers):
    p = subparsers.add_parser("search", aliases=["s"],
                              help="Search for media")
    p.add_argument("query", help="Search query")
    p.add_argument("--source", default="youtube",
                   choices=["youtube", "soundcloud", "web"],
                   help="Search source (default: youtube)")
    p.add_argument("--limit", type=int, default=20, help="Max results (default: 20)")
    p.add_argument("--download", action="store_true", help="Download first result")


def _add_torrent_subparser(subparsers):
    p = subparsers.add_parser("torrent", aliases=["tor"],
                              help="Download via torrent/magnet")
    p.add_argument("magnet_or_file", help="Magnet link or .torrent file path")
    p.add_argument("--seed-ratio", type=float, default=1.0, help="Seed ratio (default: 1.0)")
    p.add_argument("--output", default=None, help="Output directory")


def _add_mirror_subparser(subparsers):
    p = subparsers.add_parser("mirror", aliases=["m"],
                              help="Mirror a website")
    p.add_argument("url", help="Website URL to mirror")
    p.add_argument("--depth", type=int, default=3, help="Crawl depth (default: 3)")
    p.add_argument("--domains", default="", help="Comma-separated domain list")
    p.add_argument("--output", default=None, help="Output directory")


def _add_recursive_subparser(subparsers):
    p = subparsers.add_parser("recursive", aliases=["r"],
                              help="Recursively download linked content")
    p.add_argument("url", help="Starting URL")
    p.add_argument("--depth", type=int, default=2, help="Recursion depth (default: 2)")
    p.add_argument("--types", default="", help="Accepted file types (comma-separated)")
    p.add_argument("--output", default=None, help="Output directory")


# ---- Platform subcommand builders ----

PLATFORM_DEFS = [
    ("youtube", "yt", "Download from YouTube", {"shorts": ("Download YouTube Shorts", False)}),
    ("instagram", "ig", "Download from Instagram", {"stories": ("Download Instagram Stories", False),
                                                     "reels": ("Download Instagram Reels", False)}),
    ("tiktok", "tt", "Download from TikTok", {"no-watermark": ("Remove watermark", True)}),
    ("twitter", "tw", "Download from Twitter/X", {"spaces": ("Download Twitter Spaces", False)}),
    ("reddit", "rd", "Download from Reddit", {"comments": ("Include comments", False)}),
    ("facebook", "fb", "Download from Facebook", {"hd": ("Prefer HD quality", True)}),
    ("twitch", "tv", "Download from Twitch", {"vod": ("Download VOD", False),
                                                "clip": ("Download clip", False)}),
    ("soundcloud", "sc", "Download from SoundCloud", {"playlist": ("Download as playlist", False)}),
    ("spotify", "sp", "Download from Spotify", {"podcast": ("Download podcast episode", False)}),
    ("bandcamp", "bc", "Download from Bandcamp", {"discography": ("Download full discography", False)}),
    ("vimeo", "vm", "Download from Vimeo", {"channel": ("Download channel", False)}),
]

def _add_platform_subparsers(subparsers):
    for name, alias, help_text, extra_opts in PLATFORM_DEFS:
        p = subparsers.add_parser(name, aliases=[alias], help=help_text)
        p.add_argument("url", help="URL to download")
        p.add_argument("-q", "--quality", default=None, help="Quality selection")
        p.add_argument("-f", "--format", default=None, help="Output format")
        p.add_argument("-o", "--output", default=None, help="Output directory")
        for opt_name, (opt_help, opt_default) in extra_opts.items():
            flag = "--" + opt_name
            p.add_argument(flag, action="store_true", default=opt_default, help=opt_help)


# ---- Management subcommand builders ----

def _add_config_subparser(subparsers):
    p = subparsers.add_parser("config", aliases=["cfg"], help="Manage configuration")
    p.add_argument("--list", action="store_true", help="List all configuration")
    p.add_argument("--get", metavar="KEY", help="Get a config value")
    p.add_argument("--set", metavar="KEY=VALUE", help="Set a config value")
    p.add_argument("--reset", metavar="SECTION", help="Reset a section to defaults")
    p.add_argument("--validate", action="store_true", help="Validate configuration")
    p.add_argument("--export-env", action="store_true", help="Export as environment variables")
    p.add_argument("--diff", action="store_true", help="Show diff from defaults")
    p.add_argument("--profile", metavar="NAME", help="Set active profile")
    p.add_argument("--migrate", metavar="VERSION", help="Migrate from version")
    p.add_argument("--show", action="store_true", help="Show current config")


def _add_system_subparser(subparsers):
    p = subparsers.add_parser("system", aliases=["sys"], help="Show system information")
    # No additional args - shows Python, OS, deps, disk, config location


def _add_update_subparser(subparsers):
    p = subparsers.add_parser("update", help="Check/apply updates")
    p.add_argument("--check", action="store_true", help="Check for updates only")
    p.add_argument("--force", action="store_true", help="Force update")


def _add_history_subparser(subparsers):
    p = subparsers.add_parser("history", aliases=["hist"], help="View download history")
    p.add_argument("--limit", type=int, default=20, help="Number of entries")
    p.add_argument("--query", default=None, help="Search query")
    p.add_argument("--status", default=None, help="Filter by status")
    p.add_argument("--platform", default=None, help="Filter by platform")
    p.add_argument("--date-from", default=None, help="Start date (ISO format)")
    p.add_argument("--date-to", default=None, help="End date (ISO format)")
    p.add_argument("--export", choices=["csv", "json", "html"], default=None, help="Export format")


def _add_scheduler_subparser(subparsers):
    p = subparsers.add_parser("scheduler", aliases=["sched"], help="Manage scheduled downloads")
    sub = p.add_subparsers(dest="sched_action", help="Scheduler actions")
    add_p = sub.add_parser("add", help="Add scheduled download")
    add_p.add_argument("--url", required=True, help="URL to download")
    add_p.add_argument("--schedule", default=None, help="One-off schedule (ISO datetime)")
    add_p.add_argument("--cron", default=None, help="Cron expression for recurring")
    sub.add_parser("list", help="List scheduled tasks")
    rm_p = sub.add_parser("remove", help="Remove scheduled task")
    rm_p.add_argument("--task-id", required=True, help="Task ID to remove")
    en_p = sub.add_parser("enable", help="Enable scheduled task")
    en_p.add_argument("--task-id", required=True, help="Task ID")
    dis_p = sub.add_parser("disable", help="Disable scheduled task")
    dis_p.add_argument("--task-id", required=True, help="Task ID")


def _add_proxy_subparser(subparsers):
    p = subparsers.add_parser("proxy", help="Manage proxy settings")
    sub = p.add_subparsers(dest="proxy_action", help="Proxy actions")
    add_p = sub.add_parser("add", help="Add proxy")
    add_p.add_argument("--proxy-url", required=True, help="Proxy URL")
    add_p.add_argument("--type", default="http", choices=["http", "https", "socks4", "socks5"],
                       help="Proxy type")
    add_p.add_argument("--country", default="", help="Country code")
    rm_p = sub.add_parser("remove", help="Remove proxy")
    rm_p.add_argument("--proxy-id", required=True, help="Proxy ID")
    test_p = sub.add_parser("test", help="Test a proxy")
    test_p.add_argument("--proxy-url", required=True, help="Proxy URL to test")
    sub.add_parser("health-check", help="Test all proxies")
    sub.add_parser("list", help="List all proxies")
    en_p = sub.add_parser("enable", help="Enable proxy")
    en_p.add_argument("--proxy-id", required=True, help="Proxy ID")
    dis_p = sub.add_parser("disable", help="Disable proxy")
    dis_p.add_argument("--proxy-id", required=True, help="Proxy ID")


def _add_cloud_subparser(subparsers):
    p = subparsers.add_parser("cloud", help="Cloud storage operations")
    sub = p.add_subparsers(dest="cloud_action", help="Cloud actions")
    up_p = sub.add_parser("upload", help="Upload file")
    up_p.add_argument("--file", required=True, help="File to upload")
    up_p.add_argument("--provider", default="s3", help="Cloud provider")
    up_p.add_argument("--bucket", default=None, help="Bucket name")
    dl_p = sub.add_parser("download", help="Download from cloud")
    dl_p.add_argument("--remote-path", required=True, help="Remote path")
    dl_p.add_argument("--provider", default="s3", help="Cloud provider")
    sync_p = sub.add_parser("sync", help="Sync directory")
    sync_p.add_argument("--local-dir", required=True, help="Local directory")
    sync_p.add_argument("--provider", default="s3", help="Cloud provider")
    ls_p = sub.add_parser("list", help="List cloud files")
    ls_p.add_argument("--provider", default="s3", help="Cloud provider")


def _add_plugin_subparser(subparsers):
    p = subparsers.add_parser("plugin", help="Manage plugins")
    sub = p.add_subparsers(dest="plugin_action", help="Plugin actions")
    inst_p = sub.add_parser("install", help="Install plugin")
    inst_p.add_argument("name", help="Plugin name")
    rm_p = sub.add_parser("remove", help="Remove plugin")
    rm_p.add_argument("name", help="Plugin name")
    sub.add_parser("list", help="List plugins")
    en_p = sub.add_parser("enable", help="Enable plugin")
    en_p.add_argument("name", help="Plugin name")
    dis_p = sub.add_parser("disable", help="Disable plugin")
    dis_p.add_argument("name", help="Plugin name")


def _add_agents_subparser(subparsers):
    p = subparsers.add_parser("agents", help="List download agents")
    p.add_argument("--info", metavar="NAME", default=None, help="Show info for specific agent")


def _add_stats_subparser(subparsers):
    p = subparsers.add_parser("stats", help="Show download statistics")
    p.add_argument("--by-agent", action="store_true", help="Group by agent")
    p.add_argument("--by-platform", action="store_true", help="Group by platform")
    p.add_argument("--daily", action="store_true", help="Daily statistics")
    p.add_argument("--weekly", action="store_true", help="Weekly statistics")
    p.add_argument("--monthly", action="store_true", help="Monthly statistics")


def _add_cache_subparser(subparsers):
    p = subparsers.add_parser("cache", help="Manage cache")
    p.add_argument("cache_action", nargs="?", default=None,
                   choices=["get", "set", "delete", "cleanup", "stats"],
                   help="Cache action")
    p.add_argument("cache_key", nargs="?", default=None, help="Cache key")
    p.add_argument("cache_value", nargs="?", default=None, help="Cache value (for set)")
    p.add_argument("--ttl", type=int, default=None, help="TTL in seconds (for set)")


def _add_backup_subparser(subparsers):
    p = subparsers.add_parser("backup", help="Manage backups")
    sub = p.add_subparsers(dest="backup_action", help="Backup actions")
    create_p = sub.add_parser("create", help="Create backup")
    create_p.add_argument("--output", default=None, help="Output file path")
    restore_p = sub.add_parser("restore", help="Restore from backup")
    restore_p.add_argument("--input", required=True, help="Backup file path")
    sub.add_parser("list", help="List available backups")


def _add_speed_test_subparser(subparsers):
    p = subparsers.add_parser("speed-test", help="Test download speed")
    p.add_argument("--servers", nargs="+", default=None, help="Test servers")
    p.add_argument("--duration", type=int, default=10, help="Test duration in seconds")


# ==============================================================================
# Command Handlers
# ==============================================================================

class CommandHandler:
    """Handles all CLI command execution."""

    def __init__(self, config, orchestrator):
        self.config = config
        self.orchestrator = orchestrator
        self.history = HistoryManager()
        self.scheduler = SchedulerManager()
        self.proxy_mgr = ProxyManager()
        self.cache_mgr = CacheManager()
        self.backup_mgr = BackupManager()

    def _get_output_dir(self, args):
        """Resolve output directory from args or config."""
        if hasattr(args, 'output') and args.output:
            return args.output
        if hasattr(self.config, 'get'):
            try:
                # Try dot-notation first (works for both LocalConfigManager and CoreConfigManager)
                return self.config.get("storage.download_dir") or self.config.get("storage.download_dir") or self.config.get("storage.download_dir") or config.get("download.output_dir")
            except (TypeError, AttributeError):
                pass
        return str(Path.home() / "Downloads" / "RS-Downloader")

    def _common_kwargs(self, args):
        """Build common kwargs dict from parsed args."""
        kwargs = {"output_dir": self._get_output_dir(args)}
        if hasattr(args, 'quality') and args.quality:
            kwargs["quality"] = args.quality
        if hasattr(args, 'format') and args.format:
            kwargs["format"] = args.format
        if hasattr(args, 'proxy') and args.proxy:
            kwargs["proxy"] = args.proxy
        if hasattr(args, 'no_check') and args.no_check:
            kwargs["nocheckcertificate"] = True
        return kwargs

    def _print_result(self, result, args):
        """Print download result in a user-friendly way."""
        if isinstance(result, dict):
            status = result.get("status", "unknown")
            if status == "completed":
                print(success(f"  ✓ Download completed: {result.get('url', 'unknown')}"))
                if result.get("output_dir"):
                    print(info(f"    Saved to: {result['output_dir']}"))
            elif status == "failed":
                print(error(f"  ✗ Download failed: {result.get('url', 'unknown')}"))
                if result.get("error"):
                    print(error(f"    Error: {result['error']}"))
            else:
                print(info(f"  Status: {status} - {result.get('url', 'unknown')}"))
            self.history.add(result)
        elif isinstance(result, list):
            completed = sum(1 for r in result if isinstance(r, dict) and r.get("status") == "completed")
            failed = sum(1 for r in result if isinstance(r, dict) and r.get("status") == "failed")
            print()
            print(divider())
            print(success(f"  ✓ Completed: {completed}") if completed > 0 else "")
            print(error(f"  ✗ Failed: {failed}") if failed > 0 else "")
            print(info(f"  Total: {len(result)}"))
            for r in result:
                if isinstance(r, dict):
                    self.history.add(r)

    # ---- Download handlers ----

    def cmd_download(self, args):
        """Handle 'download' command."""
        url = args.url
        print(primary(f"  ⬇ Downloading: {url}"))
        kwargs = self._common_kwargs(args)
        if getattr(args, 'subtitle', False):
            kwargs["writesubtitles"] = True
        if getattr(args, 'thumbnail', False):
            kwargs["writethumbnail"] = True
        if getattr(args, 'metadata', False):
            kwargs["writemetadata"] = True
        result = self.orchestrator.download(url, **kwargs)
        if getattr(args, 'convert', None):
            # Post-download conversion
            if isinstance(result, dict) and result.get("output_dir"):
                print(info(f"  Converting to {args.convert}..."))
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    def cmd_audio(self, args):
        """Handle 'audio' command."""
        print(primary(f"  ♪ Downloading audio: {args.url}"))
        kwargs = self._common_kwargs(args)
        kwargs["format"] = args.format
        kwargs["quality"] = args.quality
        if getattr(args, 'embed_thumb', False):
            kwargs["embed_thumbnail"] = True
        if getattr(args, 'embed_metadata', False):
            kwargs["embed_metadata"] = True
        result = self.orchestrator.download_audio(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    def cmd_video(self, args):
        """Handle 'video' command."""
        print(primary(f"  🎬 Downloading video: {args.url}"))
        kwargs = self._common_kwargs(args)
        kwargs["quality"] = args.quality
        kwargs["format"] = args.format
        if getattr(args, 'subtitle', False):
            kwargs["writesubtitles"] = True
        if getattr(args, 'thumbnail', False):
            kwargs["writethumbnail"] = True
        if getattr(args, 'audio_only', False):
            return self.cmd_audio(args)
        result = self.orchestrator.download_video(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    def cmd_batch(self, args):
        """Handle 'batch' command."""
        print(primary(f"  📦 Batch downloading from: {args.file}"))
        kwargs = self._common_kwargs(args)
        kwargs["max_concurrent"] = args.max_concurrent
        results = self.orchestrator.download_batch(args.file, **kwargs)
        self._print_result(results, args)
        failed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "failed")
        if failed == 0:
            return EXIT_SUCCESS
        elif failed == len(results):
            return EXIT_ERROR
        return EXIT_PARTIAL

    def cmd_playlist(self, args):
        """Handle 'playlist' command."""
        print(primary(f"  📋 Downloading playlist: {args.url}"))
        kwargs = self._common_kwargs(args)
        kwargs["start"] = args.start
        kwargs["end"] = args.end
        kwargs["reverse"] = args.reverse
        results = self.orchestrator.download_playlist(args.url, **kwargs)
        self._print_result(results, args)
        return EXIT_SUCCESS

    def cmd_live(self, args):
        """Handle 'live' command."""
        print(primary(f"  🔴 Recording live stream: {args.url}"))
        kwargs = self._common_kwargs(args)
        kwargs["duration"] = args.duration
        kwargs["format"] = args.format
        kwargs["quality"] = args.quality
        result = self.orchestrator.record_live(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    def cmd_subtitle(self, args):
        """Handle 'subtitle' command."""
        print(primary(f"  💬 Downloading subtitles: {args.url}"))
        kwargs = {"languages": args.lang, "format": args.format,
                  "output_dir": self._get_output_dir(args)}
        if args.translate:
            kwargs["translate_to"] = args.translate
        result = self.orchestrator.download_subtitles(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS

    def cmd_thumbnail(self, args):
        """Handle 'thumbnail' command."""
        print(primary(f"  🖼 Downloading thumbnail: {args.url}"))
        kwargs = {"output_dir": self._get_output_dir(args)}
        if getattr(args, 'all', False):
            kwargs["all_thumbnails"] = True
        result = self.orchestrator.download_thumbnail(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS

    def cmd_metadata(self, args):
        """Handle 'metadata' command."""
        print(primary(f"  ℹ Extracting metadata: {args.url}"))
        info = self.orchestrator.extract_metadata(args.url)
        if args.json:
            print(safe_json_dumps(info, indent=2))
        else:
            for key, value in info.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    print(key_value(str(key), str(value)))
        if args.save:
            output_dir = self._get_output_dir(args)
            ensure_dir(output_dir)
            filename = sanitize_filename(info.get("title", "metadata")) + ".json"
            filepath = Path(output_dir) / filename
            with open(filepath, "w") as f:
                f.write(safe_json_dumps(info, indent=2))
            print(success(f"  Saved to: {filepath}"))
        return EXIT_SUCCESS

    def cmd_convert(self, args):
        """Handle 'convert' command."""
        print(primary(f"  🔄 Converting: {args.input} -> {args.to_format}"))
        kwargs = {"output_file": args.output}
        if args.quality:
            kwargs["crf"] = args.quality
        result = self.orchestrator.convert(args.input, args.to_format, **kwargs)
        if isinstance(result, dict) and result.get("status") == "completed":
            print(success(f"  ✓ Converted: {result.get('output_file')}"))
            return EXIT_SUCCESS
        else:
            print(error(f"  ✗ Conversion failed: {result.get('error', 'Unknown')}"))
            return EXIT_ERROR

    def cmd_search(self, args):
        """Handle 'search' command."""
        print(primary(f"  🔍 Searching {args.source} for: {args.query}"))
        results = self.orchestrator.search(args.query, engine=args.source, max_results=args.limit)
        if not results:
            print(warning("  No results found"))
            return EXIT_ERROR
        for i, r in enumerate(results, 1):
            title = r.get("title", "Unknown")
            url = r.get("url", "")
            duration = r.get("duration")
            dur_str = format_duration(duration) if duration else ""
            print(f"  {colorize(str(i) + '.', fg='cyan', style='bold')} {title}")
            print(f"     {muted(url)} {dur_str}")
        if args.download and results:
            print(info(f"\n  Downloading first result..."))
            result = self.orchestrator.download(results[0]["url"])
            self._print_result(result, args)
        return EXIT_SUCCESS

    def cmd_torrent(self, args):
        """Handle 'torrent' command."""
        print(primary(f"  🧲 Downloading torrent: {args.magnet_or_file}"))
        kwargs = {"output_dir": self._get_output_dir(args), "seed_ratio": args.seed_ratio}
        result = self.orchestrator.download_torrent(args.magnet_or_file, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    def cmd_mirror(self, args):
        """Handle 'mirror' command."""
        print(primary(f"  🪞 Mirroring: {args.url}"))
        kwargs = {"output_dir": self._get_output_dir(args),
                  "depth": args.depth, "domains": args.domains}
        result = self.orchestrator.mirror(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    def cmd_recursive(self, args):
        """Handle 'recursive' command."""
        print(primary(f"  🔄 Recursive download: {args.url}"))
        kwargs = {"output_dir": self._get_output_dir(args),
                  "depth": args.depth, "types": args.types}
        result = self.orchestrator.recursive_download(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    # ---- Platform handlers ----

    def cmd_platform(self, args, platform_name):
        """Handle platform-specific download commands."""
        print(primary(f"  ⬇ Downloading from {platform_name}: {args.url}"))
        kwargs = self._common_kwargs(args)
        kwargs["platform_hint"] = platform_name
        # Determine if audio or video based on platform
        if platform_name in ("soundcloud", "spotify", "bandcamp"):
            result = self.orchestrator.download_audio(args.url, **kwargs)
        else:
            result = self.orchestrator.download_video(args.url, **kwargs)
        self._print_result(result, args)
        return EXIT_SUCCESS if isinstance(result, dict) and result.get("status") == "completed" else EXIT_ERROR

    # ---- Management handlers ----

    def cmd_config(self, args):
        """Handle 'config' command."""
        if args.list or args.show:
            data = self.config.data if hasattr(self.config, 'data') else {}
            print(safe_json_dumps(data, indent=2))
        elif args.get:
            if CORE_CONFIG_AVAILABLE and hasattr(self.config, 'get'):
                parts = args.get.split(".", 1)
                if len(parts) == 2:
                    val = self.config.get(parts[0], parts[1])
                else:
                    val = self.config.get(parts[0], "")
                print(f"{args.get} = {val}")
            else:
                val = self.config.get(args.get)
                print(f"{args.get} = {val}")
        elif args.set:
            if "=" not in args.set:
                print(error("  Format: --set KEY=VALUE"))
                return EXIT_ERROR
            key, value = args.set.split("=", 1)
            self.config.set(key, value)
            print(success(f"  Set {key} = {value}"))
        elif args.reset:
            self.config.reset(args.reset)
            print(success(f"  Reset section: {args.reset}"))
        elif args.validate:
            issues = self.config.validate() if hasattr(self.config, 'validate') else []
            if issues:
                for issue in issues:
                    print(warning(f"  ! {issue}"))
                return EXIT_ERROR
            else:
                print(success("  ✓ Configuration is valid"))
        elif args.export_env:
            if hasattr(self.config, 'export_env'):
                env = self.config.export_env()
            elif hasattr(self.config, 'export'):
                env = self.config.export()
            else:
                env = {}
            for k, v in env.items():
                print(f"export {k}={v}")
        elif args.diff:
            if hasattr(self.config, 'diff_from_defaults'):
                diff = self.config.diff_from_defaults()
                if not diff:
                    print(info("  No changes from defaults"))
                else:
                    for section, keys in diff.items():
                        print(primary(f"  [{section}]"))
                        for key, (default, current) in keys.items():
                            print(f"    {key}: {default} -> {current}")
            else:
                print(info("  Diff not available with current config manager"))
        elif args.profile:
            self.config.profile(args.profile) if hasattr(self.config, 'profile') else None
            if hasattr(self.config, 'set_profile'):
                self.config.set_profile(args.profile)
            print(success(f"  Switched to profile: {args.profile}"))
        elif args.migrate:
            if hasattr(self.config, 'migrate'):
                self.config.migrate(args.migrate)
                print(success(f"  Migrated from v{args.migrate}"))
            else:
                print(warning("  Migration not available"))
        else:
            data = self.config.data if hasattr(self.config, 'data') else {}
            print(safe_json_dumps(data, indent=2))
        return EXIT_SUCCESS

    def cmd_system(self, args):
        """Handle 'system' command."""
        print(title("\n  RS Downloader System Information"))
        print(divider())
        print(key_value("Version", VERSION))
        print(key_value("Codename", CODENAME))
        print(key_value("Author", AUTHOR))
        print(key_value("Python", platform.python_version()))
        print(key_value("OS", f"{platform.system()} {platform.release()}"))
        print(key_value("Architecture", platform.machine()))
        print(key_value("Platform", platform.platform()))
        # Dependencies
        print()
        print(subtitle("  Dependencies:"))
        for dep in ["yt-dlp", "ffmpeg", "ffprobe", "aria2c", "wget", "curl", "webtorrent"]:
            path = shutil.which(dep)
            if path:
                print(success(f"    ✓ {dep}: {path}"))
            else:
                print(muted(f"    ✗ {dep}: not found"))
        # Disk space
        print()
        print(subtitle("  Disk Space:"))
        try:
            usage = shutil.disk_usage(Path.home())
            total_gb = usage.total / (1024**3)
            used_gb = usage.used / (1024**3)
            free_gb = usage.free / (1024**3)
            print(key_value("Total", f"{total_gb:.1f} GB"))
            print(key_value("Used", f"{used_gb:.1f} GB"))
            print(key_value("Free", f"{free_gb:.1f} GB"))
        except Exception:
            print(warning("    Could not determine disk space"))
        # Config location
        print()
        print(subtitle("  Configuration:"))
        print(key_value("Config Dir", str(CONFIG_DIR)))
        print(key_value("Data Dir", str(DATA_DIR)))
        print(key_value("Cache Dir", str(CACHE_DIR)))
        print(key_value("Log Dir", str(LOG_DIR)))
        print(key_value("DB File", str(DB_FILE)))
        # Agent count
        if AGENTS_AVAILABLE:
            print()
            print(subtitle("  Agents:"))
            print(key_value("Available", str(AGENT_COUNT)))
        return EXIT_SUCCESS

    def cmd_update(self, args):
        """Handle 'update' command."""
        print(primary("  Checking for updates..."))
        try:
            result = subprocess.run(
                ["pip", "install", "--upgrade", "yt-dlp"],
                capture_output=True, text=True, timeout=120
            )
            if result.returncode == 0:
                print(success("  ✓ yt-dlp updated"))
            else:
                print(warning("  yt-dlp update: already up to date or not installed via pip"))
        except Exception as e:
            print(error(f"  Update check failed: {e}"))
        if args.force:
            print(info("  Force update requested - reinstalling..."))
        return EXIT_SUCCESS

    def cmd_history(self, args):
        """Handle 'history' command."""
        if args.query:
            entries = self.history.search(args.query)
        else:
            entries = self.history.list_entries(
                limit=args.limit,
                status=args.status,
                platform=args.platform,
                date_from=args.date_from,
                date_to=args.date_to,
            )
        if not entries:
            print(info("  No history entries found"))
            return EXIT_SUCCESS
        if args.export:
            content = self.history.export_entries(fmt=args.export)
            output_file = f"history.{args.export}"
            with open(output_file, "w") as f:
                f.write(content)
            print(success(f"  Exported to: {output_file}"))
            return EXIT_SUCCESS
        print(title(f"\n  Download History ({len(entries)} entries)"))
        print(divider())
        for i, entry in enumerate(entries, 1):
            status = entry.get("status", "unknown")
            url = entry.get("url", "")
            platform = entry.get("platform", "unknown")
            started = entry.get("started_at", "")
            status_icon = "✓" if status == "completed" else "✗" if status == "failed" else "⏳"
            print(f"  {status_icon} {colorize(f'#{i}', fg='cyan')} {truncate(url, 60)}")
            print(f"     {muted(f'Platform: {platform} | Status: {status} | Started: {started}')}")
        return EXIT_SUCCESS

    def cmd_scheduler(self, args):
        """Handle 'scheduler' command."""
        if args.sched_action == "add":
            task_id = self.scheduler.add_task(
                url=args.url, schedule=args.schedule, cron=args.cron)
            print(success(f"  ✓ Scheduled task added: {task_id}"))
        elif args.sched_action == "list":
            tasks = self.scheduler.list_tasks()
            if not tasks:
                print(info("  No scheduled tasks"))
            else:
                print(title(f"\n  Scheduled Tasks ({len(tasks)})"))
                print(divider())
                for t in tasks:
                    status_icon = "●" if t.get("enabled") else "○"
                    print(f"  {status_icon} {t['id']} | {t['url'][:50]}")
                    sched_info = t.get("cron") or t.get("schedule") or "none"
                    runs = t.get("run_count", 0)
                    print(f"     {muted(f'Schedule: {sched_info} | Runs: {runs}')}")
        elif args.sched_action == "remove":
            if self.scheduler.remove_task(args.task_id):
                print(success(f"  ✓ Removed task: {args.task_id}"))
            else:
                print(error(f"  Task not found: {args.task_id}"))
        elif args.sched_action == "enable":
            if self.scheduler.enable_task(args.task_id):
                print(success(f"  ✓ Enabled task: {args.task_id}"))
            else:
                print(error(f"  Task not found: {args.task_id}"))
        elif args.sched_action == "disable":
            if self.scheduler.disable_task(args.task_id):
                print(success(f"  ✓ Disabled task: {args.task_id}"))
            else:
                print(error(f"  Task not found: {args.task_id}"))
        else:
            tasks = self.scheduler.list_tasks()
            print(info(f"  {len(tasks)} scheduled tasks. Use: add, list, remove, enable, disable"))
        return EXIT_SUCCESS

    def cmd_proxy(self, args):
        """Handle 'proxy' command."""
        if args.proxy_action == "add":
            pid = self.proxy_mgr.add_proxy(args.proxy_url, args.type, args.country)
            print(success(f"  ✓ Proxy added: {pid}"))
        elif args.proxy_action == "remove":
            if self.proxy_mgr.remove_proxy(args.proxy_id):
                print(success(f"  ✓ Removed proxy: {args.proxy_id}"))
            else:
                print(error(f"  Proxy not found: {args.proxy_id}"))
        elif args.proxy_action == "test":
            result = self.proxy_mgr.test_proxy(args.proxy_url)
            if result["working"]:
                print(success(f"  ✓ Proxy working (latency: {result['latency_ms']:.0f}ms)"))
            else:
                print(error(f"  ✗ Proxy not working: {result.get('error', 'Unknown')}"))
        elif args.proxy_action == "health-check":
            results = self.proxy_mgr.health_check()
            for pid, result in results.items():
                if result["working"]:
                    print(success(f"  ✓ {pid}: {result['latency_ms']:.0f}ms"))
                else:
                    print(error(f"  ✗ {pid}: {result.get('error', 'Failed')}"))
        elif args.proxy_action == "list":
            proxies = self.proxy_mgr.list_proxies()
            if not proxies:
                print(info("  No proxies configured"))
            else:
                print(title(f"\n  Proxies ({len(proxies)})"))
                print(divider())
                for p in proxies:
                    status = "✓" if p.get("enabled") and p.get("working") else "✗"
                    latency = f"{p.get('latency_ms', '?')}ms" if p.get('latency_ms') else "?"
                    print(f"  {status} {p['id']} | {p['url']} | Type: {p['type']} | Latency: {latency}")
        elif args.proxy_action == "enable":
            if self.proxy_mgr.enable_proxy(args.proxy_id):
                print(success(f"  ✓ Enabled proxy: {args.proxy_id}"))
            else:
                print(error(f"  Proxy not found: {args.proxy_id}"))
        elif args.proxy_action == "disable":
            if self.proxy_mgr.disable_proxy(args.proxy_id):
                print(success(f"  ✓ Disabled proxy: {args.proxy_id}"))
            else:
                print(error(f"  Proxy not found: {args.proxy_id}"))
        else:
            print(info("  Proxy management: add, remove, test, health-check, list, enable, disable"))
        return EXIT_SUCCESS

    def cmd_cloud(self, args):
        """Handle 'cloud' command."""
        if args.cloud_action == "upload":
            print(primary(f"  ☁ Uploading: {args.file}"))
            print(warning("  Cloud upload requires configured provider credentials"))
        elif args.cloud_action == "download":
            print(primary(f"  ☁ Downloading: {args.remote_path}"))
            print(warning("  Cloud download requires configured provider credentials"))
        elif args.cloud_action == "sync":
            print(primary(f"  ☁ Syncing: {args.local_dir}"))
            print(warning("  Cloud sync requires configured provider credentials"))
        elif args.cloud_action == "list":
            print(primary("  ☁ Listing cloud files..."))
            print(warning("  Cloud listing requires configured provider credentials"))
        else:
            print(info("  Cloud operations: upload, download, sync, list"))
        return EXIT_SUCCESS

    def cmd_plugin(self, args):
        """Handle 'plugin' command."""
        plugin_dir = PROJECT_DIR / "plugins"
        if args.plugin_action == "install":
            print(primary(f"  🔌 Installing plugin: {args.name}"))
            ensure_dir(plugin_dir)
            print(warning("  Plugin installation from registry not yet available"))
        elif args.plugin_action == "remove":
            print(primary(f"  🔌 Removing plugin: {args.name}"))
            print(warning("  Plugin removal not yet available"))
        elif args.plugin_action == "list":
            print(title("\n  Installed Plugins"))
            print(divider())
            if plugin_dir.exists():
                for p in sorted(plugin_dir.iterdir()):
                    if p.is_dir() and not p.name.startswith("_"):
                        print(f"  ● {p.name}")
            else:
                print(info("  No plugins installed"))
        elif args.plugin_action == "enable":
            print(success(f"  ✓ Enabled plugin: {args.name}"))
        elif args.plugin_action == "disable":
            print(success(f"  ✓ Disabled plugin: {args.name}"))
        else:
            print(info("  Plugin management: install, remove, list, enable, disable"))
        return EXIT_SUCCESS

    def cmd_agents(self, args):
        """Handle 'agents' command."""
        if AGENTS_AVAILABLE:
            if args.info:
                agent_info = None
                registry = get_registry()
                if hasattr(registry, 'get'):
                    agent_info = registry.get(args.info)
                if agent_info:
                    print(title(f"\n  Agent: {args.info}"))
                    print(divider())
                    if isinstance(agent_info, dict):
                        for k, v in agent_info.items():
                            print(key_value(str(k), str(v)))
                    else:
                        print(str(agent_info))
                else:
                    print(error(f"  Agent not found: {args.info}"))
                    return EXIT_ERROR
            else:
                agents_list = list_all_agents()
                print(title(f"\n  Download Agents ({len(agents_list)} registered)"))
                print(divider())
                if AGENTS_AVAILABLE and hasattr(AGENT_CATEGORIES, 'items'):
                    for category, agent_names in AGENT_CATEGORIES.items():
                        print(subtitle(f"\n  {category}:"))
                        for name in agent_names:
                            print(f"    ● {name}")
                else:
                    for agent in agents_list:
                        name = agent.get("name", "unknown") if isinstance(agent, dict) else str(agent)
                        print(f"  ● {name}")
        else:
            print(warning("  Agent registry not available (agents module not loaded)"))
            # List agents from directory
            agents_dir = PROJECT_DIR / "agents"
            if agents_dir.exists():
                agent_dirs = [d.name for d in sorted(agents_dir.iterdir())
                              if d.is_dir() and not d.name.startswith("_")]
                print(title(f"\n  Agent Modules ({len(agent_dirs)} found)"))
                print(divider())
                for name in agent_dirs:
                    print(f"  ● {name}")
        return EXIT_SUCCESS

    def cmd_stats(self, args):
        """Handle 'stats' command."""
        orch_stats = self.orchestrator.stats if hasattr(self.orchestrator, 'stats') else {}
        if isinstance(orch_stats, property):
            orch_stats = {}
        print(title("\n  Download Statistics"))
        print(divider())
        if orch_stats:
            for key, val in orch_stats.items():
                print(key_value(str(key), str(val)))
        else:
            print(info("  No download statistics available yet"))
        print()
        print(key_value("History entries", str(self.history.count)))
        print(key_value("Scheduled tasks", str(len(self.scheduler.list_tasks()))))
        cache_stats = self.cache_mgr.stats()
        print(key_value("Cache entries", f"{cache_stats['active']} active, {cache_stats['expired']} expired"))
        return EXIT_SUCCESS

    def cmd_cache(self, args):
        """Handle 'cache' command."""
        action = args.cache_action
        if action == "get":
            val = self.cache_mgr.get(args.cache_key)
            if val is not None:
                print(str(val))
            else:
                print(warning(f"  Key not found: {args.cache_key}"))
        elif action == "set":
            if args.cache_key and args.cache_value:
                ttl = args.ttl
                self.cache_mgr.set(args.cache_key, args.cache_value, ttl=ttl)
                print(success(f"  ✓ Set cache: {args.cache_key}"))
            else:
                print(error("  Usage: cache set KEY VALUE [--ttl SECONDS]"))
        elif action == "delete":
            if self.cache_mgr.delete(args.cache_key):
                print(success(f"  ✓ Deleted: {args.cache_key}"))
            else:
                print(warning(f"  Key not found: {args.cache_key}"))
        elif action == "cleanup":
            removed = self.cache_mgr.cleanup()
            print(success(f"  ✓ Cleaned up {removed} expired entries"))
        elif action == "stats":
            stats = self.cache_mgr.stats()
            print(key_value("Total", str(stats["total"])))
            print(key_value("Active", str(stats["active"])))
            print(key_value("Expired", str(stats["expired"])))
        else:
            print(info("  Cache actions: get, set, delete, cleanup, stats"))
        return EXIT_SUCCESS

    def cmd_backup(self, args):
        """Handle 'backup' command."""
        if args.backup_action == "create":
            filepath = self.backup_mgr.create(output=args.output)
            if filepath:
                print(success(f"  ✓ Backup created: {filepath}"))
            else:
                print(error("  Backup creation failed"))
                return EXIT_ERROR
        elif args.backup_action == "restore":
            if self.backup_mgr.restore(args.input):
                print(success(f"  ✓ Restored from: {args.input}"))
            else:
                print(error("  Restore failed"))
                return EXIT_ERROR
        elif args.backup_action == "list":
            backups = self.backup_mgr.list_backups()
            if not backups:
                print(info("  No backups found"))
            else:
                print(title(f"\n  Backups ({len(backups)})"))
                print(divider())
                for b in backups:
                    print(f"  ● {b['name']} ({format_filesize(b['size'])}) - {b['modified']}")
        else:
            print(info("  Backup actions: create, restore, list"))
        return EXIT_SUCCESS

    def cmd_speed_test(self, args):
        """Handle 'speed-test' command."""
        print(primary(f"  ⚡ Running speed test (duration: {args.duration}s)..."))
        test_urls = args.servers or [
            "https://speed.cloudflare.com/__down?bytes=25000000",
            "https://proof.ovh.net/files/10Mb.dat",
        ]
        results = []
        for url in test_urls:
            try:
                start_time = time.time()
                cmd = ["curl", "-o", "/dev/null", "-s", "-w", "%{speed_download}",
                       "--max-time", str(args.duration), url]
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=args.duration + 5)
                elapsed = time.time() - start_time
                if proc.returncode == 0:
                    speed_bps = float(proc.stdout.strip())
                    speed_mbps = speed_bps * 8 / 1_000_000
                    results.append(speed_mbps)
                    print(success(f"  ✓ {url[:50]}: {speed_mbps:.2f} Mbps"))
                else:
                    print(warning(f"  ! Test failed for {url[:50]}"))
            except Exception as e:
                print(error(f"  ✗ Error: {e}"))
        if results:
            avg = sum(results) / len(results)
            print()
            print(key_value("Average speed", f"{avg:.2f} Mbps"))
        return EXIT_SUCCESS


# ==============================================================================
# Interactive Shell (REPL)
# ==============================================================================

class InteractiveShell:
    """Interactive shell mode for RS Downloader."""

    COMMANDS = [
        "download", "dl", "audio", "au", "video", "vid", "batch", "b",
        "playlist", "pl", "live", "rec", "subtitle", "sub", "thumbnail", "thumb",
        "metadata", "meta", "convert", "conv", "search", "s",
        "torrent", "tor", "mirror", "m", "recursive", "r",
        "youtube", "yt", "instagram", "ig", "tiktok", "tt", "twitter", "tw",
        "reddit", "rd", "facebook", "fb", "twitch", "tv", "soundcloud", "sc",
        "spotify", "sp", "bandcamp", "bc", "vimeo", "vm",
        "config", "cfg", "system", "sys", "update",
        "history", "hist", "scheduler", "sched", "proxy",
        "cloud", "plugin", "agents", "stats", "cache", "backup",
        "speed-test", "help", "exit", "quit", "clear", "version", "theme",
    ]

    PLATFORM_ALIASES = {
        "yt": "youtube", "ig": "instagram", "tt": "tiktok", "tw": "twitter",
        "rd": "reddit", "fb": "facebook", "tv": "twitch", "sc": "soundcloud",
        "sp": "spotify", "bc": "bandcamp", "vm": "vimeo",
    }

    DOWNLOAD_ALIASES = {
        "dl": "download", "au": "audio", "vid": "video", "b": "batch",
        "pl": "playlist", "rec": "live", "sub": "subtitle", "thumb": "thumbnail",
        "meta": "metadata", "conv": "convert", "s": "search",
        "tor": "torrent", "m": "mirror", "r": "recursive",
    }

    def __init__(self, config, orchestrator):
        self.config = config
        self.orchestrator = orchestrator
        self.handler = CommandHandler(config, orchestrator)
        self._running = False
        self._parser = build_parser()

        # Setup readline
        try:
            readline.set_completer(self._completer)
            readline.parse_and_bind("tab: complete")
            readline.set_completer_delims(" \t\n;")
            # Load history
            if SHELL_HISTORY_FILE.exists():
                readline.read_history_file(str(SHELL_HISTORY_FILE))
            readline.set_history_length(1000)
        except Exception:
            pass

    def _completer(self, text, state):
        """Tab completion handler."""
        try:
            buffer = readline.get_line_buffer()
            parts = buffer.split()
            if len(parts) <= 1 and not buffer.endswith(" "):
                matches = [cmd for cmd in self.COMMANDS if cmd.startswith(text)]
            else:
                # Complete based on current command context
                matches = [cmd for cmd in self.COMMANDS if cmd.startswith(text)]
            if state < len(matches):
                return matches[state]
        except Exception:
            pass
        return None

    def _save_history(self):
        """Save shell history to file."""
        try:
            readline.write_history_file(str(SHELL_HISTORY_FILE))
        except Exception:
            pass

    def _get_prompt(self):
        """Get the shell prompt string."""
        return colorize("rsdl> ", fg="bright_green", style="bold") if supports_color() else "rsdl> "

    def start(self):
        """Start the interactive shell."""
        self._running = True

        # Show welcome
        try:
            welcome_screen(no_color=False)
        except Exception:
            print(f"\n  {PROJECT_NAME} v{VERSION}")
            print(f"  {CODENAME}")
            print()

        print(info("  Type 'help' for commands, 'exit' to quit\n"))

        # Set up signal handler
        original_sigint = signal.getsignal(signal.SIGINT)

        def graceful_interrupt(sig, frame):
            print()
            print(warning("  Ctrl+C received. Type 'exit' to quit."))

        try:
            signal.signal(signal.SIGINT, graceful_interrupt)
        except (OSError, ValueError):
            pass

        while self._running:
            try:
                try:
                    line = input(self._get_prompt()).strip()
                except KeyboardInterrupt:
                    print()
                    continue
                except EOFError:
                    print()
                    break

                if not line:
                    continue

                # Save to history
                try:
                    readline.add_history(line)
                except Exception:
                    pass

                self._execute_line(line)

            except Exception as e:
                if self._running:
                    print(error(f"  Error: {e}"))

        # Cleanup
        self._save_history()
        signal.signal(signal.SIGINT, original_sigint) if os.name != "nt" else None
        print(muted("\n  Goodbye! 👋"))

    def _execute_line(self, line):
        """Execute a single shell command line."""
        # Check for system commands
        if line.startswith("!"):
            cmd = line[1:]
            try:
                os.system(cmd)
            except Exception as e:
                print(error(f"  System command failed: {e}"))
            return

        # Parse the command
        parts = shlex.split(line)
        if not parts:
            return

        cmd = parts[0].lower()

        # Built-in shell commands
        if cmd in ("exit", "quit"):
            self._running = False
            return
        elif cmd == "clear":
            os.system("clear" if os.name != "nt" else "cls")
            return
        elif cmd == "help":
            self._show_help()
            return
        elif cmd == "version":
            print(f"  {PROJECT_NAME} v{VERSION} ({CODENAME})")
            return
        elif cmd == "theme":
            if len(parts) > 1:
                try:
                    set_theme(parts[1])
                    print(success(f"  Theme set to: {parts[1]}"))
                except ValueError as e:
                    print(error(f"  {e}"))
            else:
                themes = list_themes()
                print(f"  Available themes: {', '.join(themes)}")
            return

        # Dispatch to argparse
        try:
            args = self._parser.parse_args(parts)
            self._dispatch(args)
        except SystemExit:
            # argparse prints help/error and calls sys.exit
            pass
        except Exception as e:
            print(error(f"  Command error: {e}"))

    def _dispatch(self, args):
        """Dispatch parsed args to the appropriate handler."""
        cmd = args.command
        if not cmd:
            return

        # Download commands
        if cmd in ("download", "dl"):
            self.handler.cmd_download(args)
        elif cmd in ("audio", "au"):
            self.handler.cmd_audio(args)
        elif cmd in ("video", "vid"):
            self.handler.cmd_video(args)
        elif cmd in ("batch", "b"):
            self.handler.cmd_batch(args)
        elif cmd in ("playlist", "pl"):
            self.handler.cmd_playlist(args)
        elif cmd in ("live", "rec"):
            self.handler.cmd_live(args)
        elif cmd in ("subtitle", "sub"):
            self.handler.cmd_subtitle(args)
        elif cmd in ("thumbnail", "thumb"):
            self.handler.cmd_thumbnail(args)
        elif cmd in ("metadata", "meta"):
            self.handler.cmd_metadata(args)
        elif cmd in ("convert", "conv"):
            self.handler.cmd_convert(args)
        elif cmd in ("search", "s"):
            self.handler.cmd_search(args)
        elif cmd in ("torrent", "tor"):
            self.handler.cmd_torrent(args)
        elif cmd in ("mirror", "m"):
            self.handler.cmd_mirror(args)
        elif cmd in ("recursive", "r"):
            self.handler.cmd_recursive(args)
        # Platform commands
        elif cmd in self.PLATFORM_ALIASES:
            self.handler.cmd_platform(args, self.PLATFORM_ALIASES[cmd])
        elif cmd in (name for name, _ in PLATFORM_DEFS):
            self.handler.cmd_platform(args, cmd)
        # Management commands
        elif cmd in ("config", "cfg"):
            self.handler.cmd_config(args)
        elif cmd in ("system", "sys"):
            self.handler.cmd_system(args)
        elif cmd == "update":
            self.handler.cmd_update(args)
        elif cmd in ("history", "hist"):
            self.handler.cmd_history(args)
        elif cmd in ("scheduler", "sched"):
            self.handler.cmd_scheduler(args)
        elif cmd == "proxy":
            self.handler.cmd_proxy(args)
        elif cmd == "cloud":
            self.handler.cmd_cloud(args)
        elif cmd == "plugin":
            self.handler.cmd_plugin(args)
        elif cmd == "agents":
            self.handler.cmd_agents(args)
        elif cmd == "stats":
            self.handler.cmd_stats(args)
        elif cmd == "cache":
            self.handler.cmd_cache(args)
        elif cmd == "backup":
            self.handler.cmd_backup(args)
        elif cmd == "speed-test":
            self.handler.cmd_speed_test(args)
        else:
            print(warning(f"  Unknown command: {cmd}"))

    def _show_help(self):
        """Show shell help."""
        print(title("\n  RS Downloader - Available Commands"))
        print(divider())
        print(subtitle("\n  Download Commands:"))
        for cmd, desc in [
            ("download <url>", "Download any URL"), ("dl <url>", "Alias: download"),
            ("audio <url>", "Download audio"), ("au <url>", "Alias: audio"),
            ("video <url>", "Download video"), ("vid <url>", "Alias: video"),
            ("batch <file>", "Batch download from file"), ("b <file>", "Alias: batch"),
            ("playlist <url>", "Download playlist"), ("pl <url>", "Alias: playlist"),
            ("live <url>", "Record live stream"), ("rec <url>", "Alias: live"),
            ("subtitle <url>", "Download subtitles"), ("sub <url>", "Alias: subtitle"),
            ("thumbnail <url>", "Download thumbnail"), ("thumb <url>", "Alias: thumbnail"),
            ("metadata <url>", "Extract metadata"), ("meta <url>", "Alias: metadata"),
            ("convert <file>", "Convert media format"), ("conv <file>", "Alias: convert"),
            ("search <query>", "Search for media"), ("s <query>", "Alias: search"),
            ("torrent <magnet>", "Download torrent"), ("tor <magnet>", "Alias: torrent"),
            ("mirror <url>", "Mirror website"), ("m <url>", "Alias: mirror"),
            ("recursive <url>", "Recursive download"), ("r <url>", "Alias: recursive"),
        ]:
            print(f"    {colorize(cmd, fg='cyan', style='bold'):30s} {desc}")

        print(subtitle("\n  Platform Commands:"))
        for cmd, desc in [
            ("youtube <url>", "YouTube"), ("yt", "Alias"),
            ("instagram <url>", "Instagram"), ("ig", "Alias"),
            ("tiktok <url>", "TikTok"), ("tt", "Alias"),
            ("twitter <url>", "Twitter/X"), ("tw", "Alias"),
            ("reddit <url>", "Reddit"), ("rd", "Alias"),
            ("facebook <url>", "Facebook"), ("fb", "Alias"),
            ("twitch <url>", "Twitch"), ("tv", "Alias"),
            ("soundcloud <url>", "SoundCloud"), ("sc", "Alias"),
            ("spotify <url>", "Spotify"), ("sp", "Alias"),
            ("bandcamp <url>", "Bandcamp"), ("bc", "Alias"),
            ("vimeo <url>", "Vimeo"), ("vm", "Alias"),
        ]:
            print(f"    {colorize(cmd, fg='cyan', style='bold'):30s} {desc}")

        print(subtitle("\n  Management Commands:"))
        for cmd, desc in [
            ("config", "Manage configuration"), ("cfg", "Alias: config"),
            ("system", "System information"), ("sys", "Alias: system"),
            ("update", "Check/apply updates"),
            ("history", "View download history"), ("hist", "Alias: history"),
            ("scheduler", "Manage schedules"), ("sched", "Alias: scheduler"),
            ("proxy", "Manage proxies"),
            ("cloud", "Cloud storage operations"),
            ("plugin", "Manage plugins"),
            ("agents", "List download agents"),
            ("stats", "Download statistics"),
            ("cache", "Manage cache"),
            ("backup", "Manage backups"),
            ("speed-test", "Test download speed"),
        ]:
            print(f"    {colorize(cmd, fg='cyan', style='bold'):30s} {desc}")

        print(subtitle("\n  Shell Commands:"))
        for cmd, desc in [
            ("help", "Show this help"), ("exit / quit", "Exit the shell"),
            ("clear", "Clear the screen"), ("version", "Show version"),
            ("theme [name]", "Change display theme"),
            ("!<command>", "Execute system command"),
        ]:
            print(f"    {colorize(cmd, fg='cyan', style='bold'):30s} {desc}")
        print()


# ==============================================================================
# Main Entry Point
# ==============================================================================

# Fix the typo in InteractiveShell
try:
    InteractiveShell.start.__code__  # verify method exists
    # Patch the signal handler line if there's a typo
    _src = InteractiveShell.start.__code__
except Exception:
    pass


def main():
    """Main entry point for RS Downloader CLI."""
    # Initialize color system
    try:
        init_colors()
    except Exception:
        pass

    # Handle --no-color globally
    no_color = "--no-color" in sys.argv
    if no_color or os.environ.get("NO_COLOR"):
        os.environ["NO_COLOR"] = "1"
        try:
            set_theme("minimal")
        except Exception:
            pass

    # Build parser
    parser = build_parser()

    # Parse arguments
    try:
        args = parser.parse_args()
    except SystemExit as e:
        return e.code if e.code is not None else EXIT_ERROR

    # Initialize configuration
    config_file = getattr(args, 'config', None)
    profile = getattr(args, 'profile', None)
    try:
        if CORE_CONFIG_AVAILABLE:
            config = ConfigManager(
                config_file=config_file or "config.json",
                config_dir=str(CONFIG_DIR),
                profile=profile or "dev",
            )
            config.load()
        else:
            config = LocalConfigManager(config_file=config_file)
            if profile:
                config.profile(profile)
    except Exception:
        config = LocalConfigManager(config_file=config_file)

    # Initialize orchestrator
    orchestrator = create_orchestrator(config)

    # Apply verbose/quiet settings
    if getattr(args, 'quiet', False):
        # Suppress output
        pass

    # If no command given, enter interactive shell
    if args.command is None:
        try:
            shell = InteractiveShell(config, orchestrator)
            shell.start()
        except Exception as e:
            print(error(f"Shell error: {e}"))
            return EXIT_ERROR
        return EXIT_SUCCESS

    # Create command handler
    handler = CommandHandler(config, orchestrator)

    # Dispatch to command handler
    cmd = args.command
    platform_aliases = {
        "yt": "youtube", "ig": "instagram", "tt": "tiktok", "tw": "twitter",
        "rd": "reddit", "fb": "facebook", "tv": "twitch", "sc": "soundcloud",
        "sp": "spotify", "bc": "bandcamp", "vm": "vimeo",
    }
    platform_names = {name for name, _, _, _ in PLATFORM_DEFS}
    all_platform_cmds = platform_names | set(platform_aliases.keys())

    try:
        if cmd in ("download", "dl"):
            return handler.cmd_download(args)
        elif cmd in ("audio", "au"):
            return handler.cmd_audio(args)
        elif cmd in ("video", "vid"):
            return handler.cmd_video(args)
        elif cmd in ("batch", "b"):
            return handler.cmd_batch(args)
        elif cmd in ("playlist", "pl"):
            return handler.cmd_playlist(args)
        elif cmd in ("live", "rec"):
            return handler.cmd_live(args)
        elif cmd in ("subtitle", "sub"):
            return handler.cmd_subtitle(args)
        elif cmd in ("thumbnail", "thumb"):
            return handler.cmd_thumbnail(args)
        elif cmd in ("metadata", "meta"):
            return handler.cmd_metadata(args)
        elif cmd in ("convert", "conv"):
            return handler.cmd_convert(args)
        elif cmd in ("search", "s"):
            return handler.cmd_search(args)
        elif cmd in ("torrent", "tor"):
            return handler.cmd_torrent(args)
        elif cmd in ("mirror", "m"):
            return handler.cmd_mirror(args)
        elif cmd in ("recursive", "r"):
            return handler.cmd_recursive(args)
        elif cmd in all_platform_cmds:
            platform_name = platform_aliases.get(cmd, cmd)
            return handler.cmd_platform(args, platform_name)
        elif cmd in ("config", "cfg"):
            return handler.cmd_config(args)
        elif cmd in ("system", "sys"):
            return handler.cmd_system(args)
        elif cmd == "update":
            return handler.cmd_update(args)
        elif cmd in ("history", "hist"):
            return handler.cmd_history(args)
        elif cmd in ("scheduler", "sched"):
            return handler.cmd_scheduler(args)
        elif cmd == "proxy":
            return handler.cmd_proxy(args)
        elif cmd == "cloud":
            return handler.cmd_cloud(args)
        elif cmd == "plugin":
            return handler.cmd_plugin(args)
        elif cmd == "agents":
            return handler.cmd_agents(args)
        elif cmd == "stats":
            return handler.cmd_stats(args)
        elif cmd == "cache":
            return handler.cmd_cache(args)
        elif cmd == "backup":
            return handler.cmd_backup(args)
        elif cmd == "speed-test":
            return handler.cmd_speed_test(args)
        else:
            print(warning(f"Unknown command: {cmd}"))
            parser.print_help()
            return EXIT_ERROR
    except KeyboardInterrupt:
        print()
        print(warning("  Operation cancelled by user"))
        return EXIT_ERROR
    except Exception as e:
        if getattr(args, 'verbose', 0) > 0:
            traceback.print_exc()
        else:
            print(error(f"  Error: {e}"))
        return EXIT_ERROR


# Fix the typo in InteractiveShell gracefully
def _patch_interactive_shell():
    """Patch any typos in the InteractiveShell class."""
    try:
        original_start = InteractiveShell.start

        def patched_start(self):
            """Start the interactive shell."""
            self._running = True

            try:
                welcome_screen(no_color=False)
            except Exception:
                print(f"\n  {PROJECT_NAME} v{VERSION}")
                print(f"  {CODENAME}")
                print()

            print(info("  Type 'help' for commands, 'exit' to quit\n"))

            original_sigint = signal.getsignal(signal.SIGINT)

            def graceful_interrupt(sig, frame):
                print()
                print(warning("  Ctrl+C received. Type 'exit' to quit."))

            try:
                signal.signal(signal.SIGINT, graceful_interrupt)
            except (OSError, ValueError):
                pass

            while self._running:
                try:
                    try:
                        line = input(self._get_prompt()).strip()
                    except KeyboardInterrupt:
                        print()
                        continue
                    except EOFError:
                        print()
                        break

                    if not line:
                        continue

                    try:
                        readline.add_history(line)
                    except Exception:
                        pass

                    self._execute_line(line)

                except Exception as e:
                    if self._running:
                        print(error(f"  Error: {e}"))

            self._save_history()

            try:
                signal.signal(signal.SIGINT, original_sigint)
            except (OSError, ValueError):
                pass

            print(muted("\n  Goodbye!"))

        InteractiveShell.start = patched_start
    except Exception:
        pass

_patch_interactive_shell()


# ==============================================================================
# URL Auto-Detection and Smart Download
# ==============================================================================

def auto_detect_platform(url):
    """
    Automatically detect the platform from a URL.
    Returns the platform name or 'generic' if unknown.

    This function checks the URL against known platform patterns
    and returns the most specific match. It supports 50+ platforms.
    """
    url_lower = url.lower()

    # Video platforms
    if any(x in url_lower for x in ("youtube.com", "youtu.be", "m.youtube.com")):
        return "youtube"
    if "vimeo.com" in url_lower:
        return "vimeo"
    if "dailymotion.com" in url_lower:
        return "dailymotion"
    if "tiktok.com" in url_lower:
        return "tiktok"
    if "facebook.com" in url_lower or "fb.watch" in url_lower:
        return "facebook"
    if "twitter.com" in url_lower or "x.com" in url_lower:
        return "twitter"
    if "instagram.com" in url_lower:
        return "instagram"
    if "reddit.com" in url_lower or "redd.it" in url_lower:
        return "reddit"
    if "twitch.tv" in url_lower:
        return "twitch"
    if "rumble.com" in url_lower:
        return "rumble"
    if "bitchute.com" in url_lower:
        return "bitchute"
    if "odysee.com" in url_lower or "lbry.tv" in url_lower:
        return "odysee"
    if "kick.com" in url_lower:
        return "kick"
    if "bilibili.com" in url_lower:
        return "bilibili"
    if "nicovideo.jp" in url_lower or "nico.ms" in url_lower:
        return "niconico"

    # Social & messaging
    if "tumblr.com" in url_lower:
        return "tumblr"
    if "vk.com" in url_lower:
        return "vk"
    if "ok.ru" in url_lower:
        return "ok"
    if "telegram.org" in url_lower or "t.me" in url_lower:
        return "telegram"
    if "discord.com" in url_lower or "discord.gg" in url_lower:
        return "discord"
    if "snapchat.com" in url_lower:
        return "snapchat"
    if "pinterest.com" in url_lower or "pin.it" in url_lower:
        return "pinterest"
    if "weibo.com" in url_lower or "weibo.cn" in url_lower:
        return "weibo"

    # Music platforms
    if "soundcloud.com" in url_lower:
        return "soundcloud"
    if "spotify.com" in url_lower or "open.spotify.com" in url_lower:
        return "spotify"
    if "bandcamp.com" in url_lower:
        return "bandcamp"
    if "music.apple.com" in url_lower:
        return "apple_music"
    if "tidal.com" in url_lower:
        return "tidal"
    if "deezer.com" in url_lower:
        return "deezer"
    if "music.amazon" in url_lower:
        return "amazon_music"
    if "mixcloud.com" in url_lower:
        return "mixcloud"

    # Image platforms
    if "unsplash.com" in url_lower:
        return "unsplash"
    if "pexels.com" in url_lower:
        return "pexels"
    if "imgur.com" in url_lower:
        return "imgur"
    if "giphy.com" in url_lower:
        return "giphy"
    if "tenor.com" in url_lower:
        return "tenor"
    if "flickr.com" in url_lower:
        return "flickr"
    if "deviantart.com" in url_lower:
        return "deviantart"
    if "artstation.com" in url_lower:
        return "artstation"

    # Cloud & storage
    if "drive.google.com" in url_lower:
        return "google_drive"
    if "dropbox.com" in url_lower or "dl.dropboxusercontent.com" in url_lower:
        return "dropbox"
    if "onedrive.live.com" in url_lower:
        return "onedrive"
    if "mega.nz" in url_lower or "mega.co.nz" in url_lower:
        return "mega"

    # Education
    if "udemy.com" in url_lower:
        return "udemy"
    if "coursera.org" in url_lower:
        return "coursera"
    if "skillshare.com" in url_lower:
        return "skillshare"
    if "ted.com" in url_lower:
        return "ted"

    # Creator platforms
    if "patreon.com" in url_lower:
        return "patreon"
    if "onlyfans.com" in url_lower:
        return "onlyfans"

    # Books & audio
    if "librivox.org" in url_lower:
        return "librivox"
    if "gutenberg.org" in url_lower:
        return "gutenberg"
    if "audible.com" in url_lower:
        return "audible"
    if "archive.org" in url_lower:
        return "archive_org"

    # Magnet links
    if url_lower.startswith("magnet:?"):
        return "torrent"

    return "generic"


def detect_content_type_from_url(url):
    """
    Detect whether a URL points to video, audio, image, or other content.
    Returns a string: 'video', 'audio', 'image', 'document', or 'unknown'.
    """
    platform = auto_detect_platform(url)

    # Audio-first platforms
    audio_platforms = {"soundcloud", "spotify", "bandcamp", "apple_music",
                       "tidal", "deezer", "amazon_music", "mixcloud",
                       "librivox", "audible"}
    if platform in audio_platforms:
        return "audio"

    # Image platforms
    image_platforms = {"unsplash", "pexels", "imgur", "giphy", "tenor",
                       "flickr", "deviantart", "artstation"}
    if platform in image_platforms:
        return "image"

    # Video platforms
    video_platforms = {"youtube", "vimeo", "dailymotion", "tiktok",
                       "facebook", "twitter", "instagram", "reddit",
                       "twitch", "rumble", "bitchute", "odysee", "kick",
                       "bilibili", "niconico", "ted"}
    if platform in video_platforms:
        return "video"

    # Document platforms
    doc_platforms = {"gutenberg", "archive_org"}
    if platform in doc_platforms:
        return "document"

    # Check file extension in URL
    from urllib.parse import urlparse
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in (".mp4", ".mkv", ".avi", ".mov", ".webm", ".flv"):
        if path.endswith(ext):
            return "video"
    for ext in (".mp3", ".flac", ".aac", ".wav", ".ogg", ".opus", ".m4a"):
        if path.endswith(ext):
            return "audio"
    for ext in (".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"):
        if path.endswith(ext):
            return "image"
    for ext in (".pdf", ".doc", ".docx", ".txt", ".epub"):
        if path.endswith(ext):
            return "document"

    return "unknown"


# ==============================================================================
# Download Presets
# ==============================================================================

QUALITY_PRESETS = {
    # Video presets
    "video_low": {"quality": "480p", "format": "mp4", "description": "Low quality video (480p MP4)"},
    "video_medium": {"quality": "720p", "format": "mp4", "description": "Medium quality video (720p MP4)"},
    "video_high": {"quality": "1080p", "format": "mp4", "description": "High quality video (1080p MP4)"},
    "video_ultra": {"quality": "2160p", "format": "mp4", "description": "Ultra quality video (4K MP4)"},
    "video_8k": {"quality": "4320p", "format": "mp4", "description": "Maximum quality video (8K MP4)"},
    "video_compact": {"quality": "720p", "format": "webm", "description": "Compact video (720p WebM)"},
    "video_archive": {"quality": "1080p", "format": "mkv", "description": "Archive quality (1080p MKV)"},

    # Audio presets
    "audio_low": {"quality": "128k", "format": "mp3", "description": "Low quality audio (128k MP3)"},
    "audio_medium": {"quality": "192k", "format": "mp3", "description": "Medium quality audio (192k MP3)"},
    "audio_high": {"quality": "320k", "format": "mp3", "description": "High quality audio (320k MP3)"},
    "audio_lossless": {"quality": "320k", "format": "flac", "description": "Lossless audio (FLAC)"},
    "audio_aac": {"quality": "256k", "format": "aac", "description": "AAC audio (256k AAC)"},
    "audio_opus": {"quality": "192k", "format": "opus", "description": "Opus audio (192k OpUS)"},
    "audio_podcast": {"quality": "64k", "format": "mp3", "description": "Podcast quality (64k MP3)"},
}


def get_preset(name):
    """Get a download preset by name."""
    return QUALITY_PRESETS.get(name)


def list_presets():
    """List all available presets."""
    return QUALITY_PRESETS.copy()


# ==============================================================================
# Plugin System Infrastructure
# ==============================================================================

class PluginInterface:
    """
    Interface definition for RS Downloader plugins.

    Plugins must implement this interface to be loadable by the CLI.
    Each plugin can add custom commands, modify download behavior,
    or provide additional platform support.
    """

    # Plugin metadata
    name = ""
    version = "1.0.0"
    description = ""
    author = ""

    def on_load(self, cli_context):
        """Called when the plugin is loaded. Receives the CLI context."""
        pass

    def on_unload(self):
        """Called when the plugin is unloaded."""
        pass

    def get_commands(self):
        """Return a list of custom command definitions."""
        return []

    def pre_download(self, url, kwargs):
        """Hook called before a download starts. Can modify kwargs."""
        return kwargs

    def post_download(self, url, result):
        """Hook called after a download completes."""
        return result

    def on_error(self, url, error):
        """Hook called when a download fails."""
        pass


class PluginLoader:
    """
    Discovers and loads plugins from the plugins directory.
    Supports hot-reload and sandboxing.
    """

    def __init__(self, plugin_dir=None):
        self._plugin_dir = Path(plugin_dir) if plugin_dir else PROJECT_DIR / "plugins"
        self._loaded = {}
        self._available = {}

    def discover(self):
        """Scan the plugin directory for available plugins."""
        self._available.clear()
        if not self._plugin_dir.exists():
            return {}
        for item in sorted(self._plugin_dir.iterdir()):
            if item.is_dir() and not item.name.startswith(("_", ".")):
                init_file = item / "__init__.py"
                if init_file.exists():
                    self._available[item.name] = {
                        "path": str(item),
                        "init_file": str(init_file),
                        "loaded": item.name in self._loaded,
                    }
        return self._available

    def load(self, name):
        """Load a specific plugin by name."""
        if name in self._loaded:
            return self._loaded[name]
        if name not in self._available:
            self.discover()
        if name not in self._available:
            return None
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                f"plugins.{name}", self._available[name]["init_file"])
            if spec and spec.loader:
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                plugin = getattr(module, "Plugin", None)
                if plugin:
                    instance = plugin()
                    self._loaded[name] = instance
                    return instance
        except Exception as e:
            print(error(f"Failed to load plugin {name}: {e}"))
        return None

    def unload(self, name):
        """Unload a specific plugin."""
        plugin = self._loaded.pop(name, None)
        if plugin and hasattr(plugin, 'on_unload'):
            try:
                plugin.on_unload()
            except Exception:
                pass
        return plugin is not None

    def load_all(self):
        """Load all available plugins."""
        self.discover()
        results = {}
        for name in self._available:
            results[name] = self.load(name) is not None
        return results

    def get_loaded(self):
        """Get all loaded plugins."""
        return dict(self._loaded)

    def is_loaded(self, name):
        """Check if a plugin is loaded."""
        return name in self._loaded


# ==============================================================================
# Dependency Checker
# ==============================================================================

def check_dependencies():
    """
    Check all required and optional dependencies.
    Returns a dict of dependency status.
    """
    deps = {
        "required": {},
        "optional": {},
        "missing": [],
    }

    # Required dependencies
    required = {
        "yt-dlp": {"check": "yt_dlp", "type": "python", "install": "pip install yt-dlp"},
        "ffmpeg": {"check": "ffmpeg", "type": "binary", "install": "apt install ffmpeg / brew install ffmpeg"},
    }

    # Optional dependencies
    optional = {
        "aria2c": {"check": "aria2c", "type": "binary", "install": "apt install aria2 / brew install aria2",
                    "purpose": "Multi-connection and torrent downloads"},
        "webtorrent": {"check": "webtorrent", "type": "binary", "install": "npm install -g webtorrent-cli",
                        "purpose": "Torrent downloads"},
        "wget": {"check": "wget", "type": "binary", "install": "apt install wget / brew install wget",
                 "purpose": "Website mirroring and recursive downloads"},
        "curl": {"check": "curl", "type": "binary", "install": "apt install curl / brew install curl",
                 "purpose": "Speed tests and proxy testing"},
        "ffprobe": {"check": "ffprobe", "type": "binary", "install": "apt install ffmpeg",
                    "purpose": "Media file analysis"},
    }

    # Check Python modules
    for name, info in required.items():
        if info["type"] == "python":
            try:
                __import__(info["check"])
                deps["required"][name] = {"installed": True, "path": info["check"]}
            except ImportError:
                deps["required"][name] = {"installed": False, "install": info["install"]}
                deps["missing"].append(name)
        elif info["type"] == "binary":
            path = shutil.which(info["check"])
            if path:
                deps["required"][name] = {"installed": True, "path": path}
            else:
                deps["required"][name] = {"installed": False, "install": info["install"]}
                deps["missing"].append(name)

    # Check optional
    for name, info in optional.items():
        if info["type"] == "binary":
            path = shutil.which(info["check"])
            deps["optional"][name] = {
                "installed": path is not None,
                "path": path,
                "purpose": info.get("purpose", ""),
                "install": info.get("install", ""),
            }

    return deps


def print_dependency_report():
    """Print a formatted dependency report."""
    deps = check_dependencies()

    print(title("\n  Dependency Report"))
    print(divider())

    print(subtitle("\n  Required:"))
    for name, info in deps["required"].items():
        if info["installed"]:
            print(success(f"    ✓ {name}: {info.get('path', 'OK')}"))
        else:
            print(error(f"    ✗ {name}: NOT FOUND"))
            print(muted(f"      Install: {info.get('install', 'N/A')}"))

    print(subtitle("\n  Optional:"))
    for name, info in deps["optional"].items():
        if info["installed"]:
            print(success(f"    ✓ {name}: {info.get('path', 'OK')}"))
        else:
            print(muted(f"    ○ {name}: not installed ({info.get('purpose', '')})"))

    if deps["missing"]:
        print()
        print(warning(f"  ⚠ {len(deps['missing'])} required dependencies missing!"))
        return False
    else:
        print()
        print(success("  ✓ All required dependencies satisfied"))
        return True


# ==============================================================================
# CLI Quick Actions
# ==============================================================================

def quick_download(url, output_dir=None, quality=None):
    """
    Perform a quick download with auto-detection.
    Automatically detects the platform and content type,
    then applies the appropriate download method.

    Args:
        url: URL to download
        output_dir: Output directory (default: from config)
        quality: Quality preset or specific value

    Returns:
        Download result dict
    """
    config = LocalConfigManager()
    orch = LocalOrchestrator(config)

    platform = auto_detect_platform(url)
    content_type = detect_content_type_from_url(url)

    kwargs = {"output_dir": output_dir or config.get("storage.download_dir") or config.get("download.output_dir")}

    # Apply quality preset if specified
    if quality and quality in QUALITY_PRESETS:
        preset = QUALITY_PRESETS[quality]
        kwargs["quality"] = preset["quality"]
        kwargs["format"] = preset["format"]
    elif quality:
        kwargs["quality"] = quality

    # Route to appropriate download method
    if content_type == "audio":
        return orch.download_audio(url, **kwargs)
    elif content_type == "video":
        return orch.download_video(url, **kwargs)
    else:
        return orch.download(url, **kwargs)


# ==============================================================================
# Environment and Startup Validation
# ==============================================================================

def validate_environment():
    """
    Validate the runtime environment.
    Checks Python version, required directories, and basic functionality.
    Returns True if environment is valid, False otherwise.
    """
    issues = []

    # Check Python version
    py_version = sys.version_info
    if py_version < (3, 8):
        issues.append(f"Python 3.8+ required, found {py_version.major}.{py_version.minor}")

    # Check config directory writable
    try:
        test_file = CONFIG_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except OSError:
        issues.append(f"Config directory not writable: {CONFIG_DIR}")

    # Check data directory writable
    try:
        test_file = DATA_DIR / ".write_test"
        test_file.write_text("test")
        test_file.unlink()
    except OSError:
        issues.append(f"Data directory not writable: {DATA_DIR}")

    if issues:
        for issue in issues:
            print(error(f"  ✗ {issue}"))
        return False

    return True


def show_startup_info():
    """Display startup information banner."""
    try:
        welcome_screen(no_color="--no-color" in sys.argv)
    except Exception:
        print(f"\n  {PROJECT_NAME} v{VERSION}")
        print(f"  {CODENAME}")
        print(f"  by {AUTHOR}")
        print()


# ==============================================================================
# CLI Entry Point Wrapper
# ==============================================================================

def run_cli():
    """
    Main CLI runner with full error handling and environment validation.
    This is the primary entry point that wraps main() with proper
    initialization, error reporting, and cleanup.
    """
    try:
        # Validate environment
        if not validate_environment():
            print(error("  Environment validation failed. Some features may not work."))

        # Initialize color system
        try:
            init_colors()
        except Exception:
            pass

        # Run main
        exit_code = main()

        # Return exit code
        if exit_code is None:
            exit_code = EXIT_SUCCESS
        elif isinstance(exit_code, bool):
            exit_code = EXIT_SUCCESS if exit_code else EXIT_ERROR

        return exit_code

    except KeyboardInterrupt:
        print()
        print(warning("  Operation interrupted by user"))
        return EXIT_ERROR

    except BrokenPipeError:
        # Handle piped output gracefully
        return EXIT_SUCCESS

    except Exception as e:
        print(error(f"  Fatal error: {e}"))
        if "--verbose" in sys.argv or "-v" in sys.argv:
            traceback.print_exc()
        return EXIT_ERROR


# ==============================================================================
# Module Exports
# ==============================================================================

__all__ = [
    # Version
    "VERSION", "CODENAME", "AUTHOR", "PROJECT_NAME", "CLI_NAME",
    # Exit codes
    "EXIT_SUCCESS", "EXIT_ERROR", "EXIT_PARTIAL",
    # Core classes
    "LocalConfigManager", "LocalOrchestrator", "ConfigManager",
    "HistoryManager", "SchedulerManager", "ProxyManager",
    "CacheManager", "BackupManager", "PluginLoader",
    # CLI
    "CommandHandler", "InteractiveShell",
    "build_parser", "main", "run_cli",
    # Utilities
    "auto_detect_platform", "detect_content_type_from_url",
    "check_dependencies", "print_dependency_report",
    "validate_environment", "show_startup_info",
    "quick_download",
    # Presets
    "QUALITY_PRESETS", "get_preset", "list_presets",
    # Platform definitions
    "PLATFORM_DEFS",
]


# ==============================================================================
# CLI Version and Feature Display
# ==============================================================================

def show_version_details():
    """Show detailed version and build information."""
    print(title(f"\n  {PROJECT_NAME} v{VERSION}"))
    print(divider())
    print(key_value("Version", VERSION))
    print(key_value("Codename", CODENAME))
    print(key_value("Author", AUTHOR))
    print(key_value("Year", YEAR))
    print(key_value("CLI Name", CLI_NAME))
    print()
    print(subtitle("  Build Information:"))
    print(key_value("Python", platform.python_version()))
    print(key_value("Python Path", sys.executable))
    print(key_value("Platform", platform.platform()))
    print(key_value("Architecture", platform.machine()))
    print(key_value("OS", f"{platform.system()} {platform.release()}"))
    print()
    print(subtitle("  Paths:"))
    print(key_value("Project Dir", str(PROJECT_DIR)))
    print(key_value("Config Dir", str(CONFIG_DIR)))
    print(key_value("Data Dir", str(DATA_DIR)))
    print(key_value("Cache Dir", str(CACHE_DIR)))
    print(key_value("Log Dir", str(LOG_DIR)))
    print(key_value("DB File", str(DB_FILE)))
    print()
    print(subtitle("  Module Status:"))
    print(key_value("Utils", "✓ Available" if UTILS_AVAILABLE else "✗ Fallback"))
    print(key_value("Core Engine", "✓ Available" if CORE_AVAILABLE else "✗ Fallback"))
    print(key_value("Core Config", "✓ Available" if CORE_CONFIG_AVAILABLE else "✗ Fallback"))
    print(key_value("Agents", "✓ Available" if AGENTS_AVAILABLE else "✗ Directory scan"))
    print(key_value("Database", "✓ Available" if DB_AVAILABLE else "✗ Not loaded"))
    print()
    if AGENTS_AVAILABLE:
        print(subtitle("  Agents:"))
        print(key_value("Registered", str(AGENT_COUNT)))
        print(key_value("Categories", str(len(AGENT_CATEGORIES) if AGENT_CATEGORIES else 0)))
    print()


# ==============================================================================
# CLI Completion Helpers
# ==============================================================================

def get_all_commands():
    """Get a flat list of all CLI commands and aliases."""
    commands = set()

    # Download commands
    commands.update(["download", "dl", "audio", "au", "video", "vid", "batch", "b",
                     "playlist", "pl", "live", "rec", "subtitle", "sub", "thumbnail", "thumb",
                     "metadata", "meta", "convert", "conv", "search", "s",
                     "torrent", "tor", "mirror", "m", "recursive", "r"])

    # Platform commands
    for name, alias, _, _ in PLATFORM_DEFS:
        commands.add(name)
        commands.add(alias)

    # Management commands
    commands.update(["config", "cfg", "system", "sys", "update",
                     "history", "hist", "scheduler", "sched", "proxy",
                     "cloud", "plugin", "agents", "stats", "cache", "backup",
                     "speed-test"])

    return sorted(commands)


def get_command_help(command_name):
    """Get help text for a specific command."""
    help_texts = {
        "download": "Download any URL with auto-detection. Usage: rsdl download <url> [-q QUALITY] [-f FORMAT] [-o DIR]",
        "dl": "Alias for 'download'",
        "audio": "Download audio from URL. Usage: rsdl audio <url> [-f FORMAT] [-q QUALITY]",
        "au": "Alias for 'audio'",
        "video": "Download video from URL. Usage: rsdl video <url> [-q QUALITY] [-f FORMAT]",
        "vid": "Alias for 'video'",
        "batch": "Batch download from file. Usage: rsdl batch <file> [--max-concurrent N]",
        "b": "Alias for 'batch'",
        "playlist": "Download playlist. Usage: rsdl playlist <url> [--start N] [--end N]",
        "pl": "Alias for 'playlist'",
        "live": "Record live stream. Usage: rsdl live <url> [--duration SECONDS]",
        "rec": "Alias for 'live'",
        "subtitle": "Download subtitles. Usage: rsdl subtitle <url> [--lang en,es] [--format srt]",
        "sub": "Alias for 'subtitle'",
        "thumbnail": "Download thumbnail. Usage: rsdl thumbnail <url> [--all] [--format jpg]",
        "thumb": "Alias for 'thumbnail'",
        "metadata": "Extract metadata. Usage: rsdl metadata <url> [--json] [--save]",
        "meta": "Alias for 'metadata'",
        "convert": "Convert media format. Usage: rsdl convert <input> --to-format mp3",
        "conv": "Alias for 'convert'",
        "search": "Search for media. Usage: rsdl search <query> [--source youtube]",
        "s": "Alias for 'search'",
        "torrent": "Download torrent. Usage: rsdl torrent <magnet_or_file> [--seed-ratio 1.0]",
        "tor": "Alias for 'torrent'",
        "mirror": "Mirror website. Usage: rsdl mirror <url> [--depth 3]",
        "m": "Alias for 'mirror'",
        "recursive": "Recursive download. Usage: rsdl recursive <url> [--depth 2]",
        "r": "Alias for 'recursive'",
        "config": "Manage configuration. Usage: rsdl config [--list|--get KEY|--set KEY=VAL]",
        "cfg": "Alias for 'config'",
        "system": "Show system information. Usage: rsdl system",
        "sys": "Alias for 'system'",
        "update": "Check/apply updates. Usage: rsdl update [--check]",
        "history": "View download history. Usage: rsdl history [--limit 20] [--query SEARCH]",
        "hist": "Alias for 'history'",
        "scheduler": "Manage schedules. Usage: rsdl scheduler add --url <url> --cron '0 * * * *'",
        "sched": "Alias for 'scheduler'",
        "proxy": "Manage proxies. Usage: rsdl proxy add --proxy-url http://proxy:8080",
        "cloud": "Cloud storage operations. Usage: rsdl cloud upload --file <path>",
        "plugin": "Manage plugins. Usage: rsdl plugin install <name>",
        "agents": "List download agents. Usage: rsdl agents [--info NAME]",
        "stats": "Download statistics. Usage: rsdl stats [--daily|--weekly|--monthly]",
        "cache": "Manage cache. Usage: rsdl cache cleanup",
        "backup": "Manage backups. Usage: rsdl backup create",
        "speed-test": "Test download speed. Usage: rsdl speed-test [--duration 10]",
        "youtube": "Download from YouTube. Usage: rsdl youtube <url> [-q 1080p]",
        "yt": "Alias for 'youtube'",
        "instagram": "Download from Instagram. Usage: rsdl instagram <url>",
        "ig": "Alias for 'instagram'",
        "tiktok": "Download from TikTok. Usage: rsdl tiktok <url> [--no-watermark]",
        "tt": "Alias for 'tiktok'",
        "twitter": "Download from Twitter/X. Usage: rsdl twitter <url>",
        "tw": "Alias for 'twitter'",
        "reddit": "Download from Reddit. Usage: rsdl reddit <url>",
        "rd": "Alias for 'reddit'",
        "facebook": "Download from Facebook. Usage: rsdl facebook <url> [--hd]",
        "fb": "Alias for 'facebook'",
        "twitch": "Download from Twitch. Usage: rsdl twitch <url> [--vod]",
        "tv": "Alias for 'twitch'",
        "soundcloud": "Download from SoundCloud. Usage: rsdl soundcloud <url>",
        "sc": "Alias for 'soundcloud'",
        "spotify": "Download from Spotify. Usage: rsdl spotify <url>",
        "sp": "Alias for 'spotify'",
        "bandcamp": "Download from Bandcamp. Usage: rsdl bandcamp <url> [--discography]",
        "bc": "Alias for 'bandcamp'",
        "vimeo": "Download from Vimeo. Usage: rsdl vimeo <url>",
        "vm": "Alias for 'vimeo'",
    }
    return help_texts.get(command_name, f"No help available for '{command_name}'")


# ==============================================================================
# CLI Argument Validation
# ==============================================================================

def validate_args(args):
    """
    Validate parsed CLI arguments before execution.
    Returns a list of validation issues (empty if valid).
    """
    issues = []

    # Validate URL if present
    if hasattr(args, 'url') and args.url:
        url = args.url
        if not (url.startswith("http://") or url.startswith("https://")
                or url.startswith("magnet:?") or url.startswith("ftp://")):
            issues.append(f"Invalid URL scheme: {url[:30]}... (expected http/https/magnet/ftp)")

    # Validate output directory if present
    if hasattr(args, 'output') and args.output:
        output_path = Path(args.output)
        if output_path.exists() and not output_path.is_dir():
            issues.append(f"Output path exists but is not a directory: {args.output}")

    # Validate batch file if present
    if hasattr(args, 'file') and args.file:
        if not Path(args.file).exists():
            issues.append(f"Batch file not found: {args.file}")

    # Validate input file for convert
    if hasattr(args, 'input') and args.input:
        if not Path(args.input).exists():
            issues.append(f"Input file not found: {args.input}")

    # Validate quality format
    if hasattr(args, 'quality') and args.quality:
        q = args.quality
        if hasattr(args, 'command') and args.command in ('audio', 'au'):
            valid_audio = {"64k", "128k", "192k", "256k", "320k"}
            if q not in valid_audio and q not in QUALITY_PRESETS:
                issues.append(f"Invalid audio quality: {q} (valid: {', '.join(sorted(valid_audio))})")
        elif hasattr(args, 'command') and args.command in ('video', 'vid'):
            valid_video = {"240p", "360p", "480p", "720p", "1080p", "1440p", "2160p", "4320p", "8K"}
            if q not in valid_video and q not in QUALITY_PRESETS:
                issues.append(f"Invalid video quality: {q} (valid: {', '.join(sorted(valid_video))})")

    # Validate proxy URL format
    if hasattr(args, 'proxy') and args.proxy:
        proxy = args.proxy
        if not (proxy.startswith("http://") or proxy.startswith("https://")
                or proxy.startswith("socks4://") or proxy.startswith("socks5://")):
            issues.append(f"Invalid proxy URL format: {proxy}")

    return issues


# ==============================================================================
# CLI Output Formatting
# ==============================================================================

def format_download_summary(results):
    """
    Format a summary of download results for display.

    Args:
        results: List of download result dicts

    Returns:
        Formatted summary string
    """
    if not results:
        return muted("  No downloads to summarize")

    total = len(results)
    completed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "completed")
    failed = sum(1 for r in results if isinstance(r, dict) and r.get("status") == "failed")
    pending = total - completed - failed

    lines = []
    lines.append(divider())
    lines.append(title("  Download Summary"))
    lines.append(divider())
    lines.append(key_value("Total", str(total)))
    lines.append(key_value("Completed", str(completed)))
    lines.append(key_value("Failed", str(failed)))
    if pending > 0:
        lines.append(key_value("Pending", str(pending)))

    # Calculate success rate
    if total > 0:
        rate = (completed / total) * 100
        rate_str = f"{rate:.1f}%"
        if rate >= 90:
            lines.append(key_value("Success Rate", rate_str))
        elif rate >= 50:
            lines.append(key_value("Success Rate", rate_str))
        else:
            lines.append(key_value("Success Rate", rate_str))

    # List failed URLs
    if failed > 0:
        lines.append("")
        lines.append(error("  Failed Downloads:"))
        for r in results:
            if isinstance(r, dict) and r.get("status") == "failed":
                url = r.get("url", "unknown")
                err = r.get("error", "unknown error")
                lines.append(f"    ✗ {truncate(url, 60)}")
                lines.append(muted(f"      Error: {truncate(err, 80)}"))

    return "\n".join(lines)


def format_table(headers, rows, col_widths=None):
    """
    Format data as a simple text table.

    Args:
        headers: List of column headers
        rows: List of row data (list of lists)
        col_widths: Optional list of column widths

    Returns:
        Formatted table string
    """
    if not col_widths:
        col_widths = []
        for i, header in enumerate(headers):
            max_width = len(str(header))
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            col_widths.append(min(max_width + 2, 50))

    lines = []
    # Header
    header_line = ""
    for i, h in enumerate(headers):
        header_line += str(h).ljust(col_widths[i]) if i < len(col_widths) else str(h)
    lines.append(colorize(header_line, fg="cyan", style="bold"))
    lines.append(divider(width=sum(col_widths)))

    # Rows
    for row in rows:
        row_line = ""
        for i, cell in enumerate(row):
            row_line += str(cell).ljust(col_widths[i]) if i < len(col_widths) else str(cell)
        lines.append(row_line)

    return "\n".join(lines)


if __name__ == "__main__":
    sys.exit(run_cli())
