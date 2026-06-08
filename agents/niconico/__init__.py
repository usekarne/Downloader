"""
RS Downloader v10.0.0 - Niconico Download Agent
==================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Niconico (NicoNico Douga) downloader supporting:
- Videos (all qualities including premium)
- Livestreams
- Cookie authentication for premium content
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentSkill,
    DownloadError,
    DownloadPriority,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
)


class NiconicoDownloader(DownloaderBase):
    """Niconico download agent using yt-dlp with premium cookie support."""

    AGENT_NAME = "niconico"
    PLATFORM = "niconico"
    SUPPORTED_FORMATS = ["mp4", "webm", "mkv", "mp3", "m4a", "flv"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low", "audio"]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?nicovideo\.jp/watch/(?:sm|nm|so)\d+'),
        re.compile(r'https?://(www\.)?nicovideo\.jp/watch/\d+'),
        re.compile(r'https?://nico\.ms/(?:sm|nm|so)\d+'),
        re.compile(r'https?://(www\.)?nicovideo\.jp/live/[\w-]+'),
        re.compile(r'https?://(www\.)?nicovideo\.jp/mylist/\d+'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 600)

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
        }
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if self._proxy:
            opts["proxy"] = self._proxy
        if extra:
            opts.update(extra)
        return opts

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        opts = self._build_ytdlp_opts({"skip_download": True})
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return []
                formats = []
                for fmt in info.get("formats", []):
                    formats.append({
                        "format_id": fmt.get("format_id", ""),
                        "ext": fmt.get("ext", ""),
                        "quality": fmt.get("format_note", ""),
                        "height": fmt.get("height", 0),
                        "filesize": fmt.get("filesize") or 0,
                        "vcodec": fmt.get("vcodec", "none"),
                        "acodec": fmt.get("acodec", "none"),
                    })
                return formats
        except Exception as exc:
            raise DownloadError(f"Failed to query formats: {exc}")

    def get_metadata(self, url: str) -> Dict[str, Any]:
        opts = self._build_ytdlp_opts({"skip_download": True})
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {}
                return {
                    "id": info.get("id", ""),
                    "title": info.get("title", ""),
                    "description": info.get("description", ""),
                    "uploader": info.get("uploader", ""),
                    "uploader_id": info.get("uploader_id", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "comment_count": info.get("comment_count", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "timestamp": info.get("timestamp", 0),
                    "is_live": info.get("is_live", False),
                    "tags": info.get("tags", []),
                }
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Niconico URL: {task.url}")
        out_dir = self._ensure_output_dir(task.output_path or self._output_dir)
        task.output_path = out_dir
        # Niconico heavily requires cookies for most content
        if not self._cookies:
            task.headers = task.headers or {}
            task.headers["auth_warning"] = (
                "Niconico typically requires login cookies for downloads."
            )

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.tags[0] if task.tags else "best"
        format_spec = self._resolve_format(quality)

        outtmpl = os.path.join(
            task.output_path or self._output_dir,
            "%(uploader)s - %(title)s [%(id)s].%(ext)s",
        )

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": outtmpl,
        })

        if quality == "audio":
            ytdlp_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "best"},
            ]

        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                if info:
                    result.metadata = {
                        "id": info.get("id", ""),
                        "title": info.get("title", ""),
                        "uploader": info.get("uploader", ""),
                    }
                    filename = ydl.prepare_filename(info)
                    if os.path.exists(filename):
                        result.output_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                    result.status = DownloadStatus.VERIFYING
        except ImportError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp required"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)

        result.elapsed = time.monotonic() - start_time
        return result

    @staticmethod
    def _resolve_format(quality: str) -> str:
        quality_map = {
            "best": "bestvideo+bestaudio/best",
            "high": "best[height<=1080]",
            "medium": "best[height<=720]",
            "low": "best[height<=480]",
            "audio": "bestaudio/best",
        }
        return quality_map.get(quality, "bestvideo+bestaudio/best")

    def on_verify(self, task=None, result=None):
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.output_path and os.path.exists(result.output_path):
            result.metadata["checksum"] = self._compute_checksum(result.output_path)
        return result

    def _compute_checksum(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="niconico",
        formats=frozenset(NiconicoDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(NiconicoDownloader.SUPPORTED_QUALITIES),
        features=frozenset(["video", "livestreams", "cookie_auth", "premium", "mylists"]),
        max_concurrent=1,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Niconico downloader: videos, livestreams with cookie auth for premium.",
    )
    return ("niconico", skill)
