"""
RS Downloader v10.0.0 - Twitch Download Agent
================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Twitch downloader supporting:
- VODs (Video on Demand)
- Clips
- Livestreams
- Chat dump/replay
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
from pathlib import Path
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


class TwitchDownloader(DownloaderBase):
    """
    Twitch download agent using yt-dlp.

    Supports VODs, clips, livestreams, and chat downloads.
    """

    AGENT_NAME = "twitch"
    PLATFORM = "twitch"
    SUPPORTED_FORMATS = ["mp4", "webm", "mkv", "mp3", "m4a", "flv"]
    SUPPORTED_QUALITIES = ["best", "1080p", "720p", "480p", "360p", "160p", "audio", "worst"]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?twitch\.tv/videos/\d+'),
        re.compile(r'https?://(www\.)?twitch\.tv/\w+/clip/'),
        re.compile(r'https?://(www\.)?twitch\.tv/clip/'),
        re.compile(r'https?://clips\.twitch\.tv/'),
        re.compile(r'https?://(www\.)?twitch\.tv/\w+$'),
        re.compile(r'https?://m\.twitch\.tv/videos/\d+'),
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

    def _detect_content_type(self, url: str) -> str:
        if "/videos/" in url:
            return "vod"
        if "/clip/" in url or "clips.twitch.tv" in url:
            return "clip"
        return "livestream"

    # -------------------------------------------------------------------
    # URL Validation
    # -------------------------------------------------------------------

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    # -------------------------------------------------------------------
    # Format Discovery
    # -------------------------------------------------------------------

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
                        "fps": fmt.get("fps"),
                        "tbr": fmt.get("tbr", 0),
                        "filesize": fmt.get("filesize") or fmt.get("filesize_approx", 0),
                        "vcodec": fmt.get("vcodec", "none"),
                        "acodec": fmt.get("acodec", "none"),
                    })
                return formats
        except Exception as exc:
            raise DownloadError(f"Failed to query formats: {exc}")

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------

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
                    "channel": info.get("channel", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "is_live": info.get("is_live", False),
                    "was_live": info.get("was_live", False),
                    "live_status": info.get("live_status", ""),
                    "thumbnail": info.get("thumbnail", ""),
                    "timestamp": info.get("timestamp", 0),
                    "release_timestamp": info.get("release_timestamp"),
                    "content_type": self._detect_content_type(url),
                }
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    # -------------------------------------------------------------------
    # Lifecycle Hooks
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Twitch URL: {task.url}")
        out_dir = self._ensure_output_dir(
            task.output_path or self._output_dir
        )
        task.output_path = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.tags[0] if task.tags else "best"
        content_type = self._detect_content_type(task.url)
        format_spec = self._resolve_format(quality)

        outtmpl = os.path.join(
            task.output_path or self._output_dir,
            "%(channel)s - %(title)s [%(id)s].%(ext)s",
        )

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": outtmpl,
        })

        # Livestream options
        if content_type == "livestream":
            ytdlp_opts["hls_prefer_native"] = True
            if task.headers and task.headers.get("live_from_start"):
                ytdlp_opts["live_from_start"] = True

        # Chat download
        if task.headers and task.headers.get("download_chat"):
            ytdlp_opts["writecomments"] = True

        # Audio only
        if quality == "audio":
            ytdlp_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "best"},
            ]

        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url,
            agent_name=self.AGENT_NAME,
            platform=self.PLATFORM,
            status=DownloadStatus.DOWNLOADING,
        )

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                if info:
                    result.metadata = {
                        "id": info.get("id", ""),
                        "title": info.get("title", ""),
                        "channel": info.get("channel", ""),
                        "duration": info.get("duration", 0),
                        "content_type": content_type,
                    }
                    filename = ydl.prepare_filename(info)
                    if os.path.exists(filename):
                        result.output_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                    result.status = DownloadStatus.VERIFYING
        except ImportError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp required. Install: pip install yt-dlp"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)

        elapsed = time.monotonic() - start_time
        result.elapsed = elapsed
        if elapsed > 0 and result.file_size > 0:
            result.average_speed = result.file_size / elapsed
        return result

    @staticmethod
    def _resolve_format(quality: str) -> str:
        quality_map = {
            "best": "bestvideo+bestaudio/best",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "160p": "worstvideo+worstaudio/worst",
            "audio": "bestaudio/best",
            "worst": "worstvideo+worstaudio/worst",
        }
        return quality_map.get(quality, "bestvideo+bestaudio/best")

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        if result.output_path and os.path.exists(result.output_path):
            result.metadata["checksum"] = self._compute_checksum(result.output_path)
            result.metadata["checksum_algorithm"] = "sha256"
        return result

    def _compute_checksum(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def register() -> Tuple[str, AgentSkill]:
    """Register the Twitch agent."""
    skill = AgentSkill(
        platform="twitch",
        formats=frozenset(TwitchDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(TwitchDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "vods", "clips", "livestreams", "chat_download",
            "cookie_auth", "live_from_start",
        ]),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Twitch downloader: VODs, clips, livestreams, chat with quality selection.",
    )
    return ("twitch", skill)
