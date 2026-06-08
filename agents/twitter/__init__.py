"""
RS Downloader v10.0.0 - Twitter/X Download Agent
==================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Twitter/X downloader supporting:
- Videos (all qualities)
- Images and image galleries
- Twitter Spaces audio
- Tweet threads
- Cookie authentication
"""

from __future__ import annotations

import hashlib
import json
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


class TwitterDownloader(DownloaderBase):
    """
    Twitter/X download agent using yt-dlp.

    Supports video downloads, image extraction, Twitter Spaces,
    and gallery content. Cookie auth for protected content.
    """

    AGENT_NAME = "twitter"
    PLATFORM = "twitter"
    SUPPORTED_FORMATS = ["mp4", "m4a", "mp3", "jpg", "png", "webp", "gif"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low", "audio"]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?(twitter|x)\.com/\w+/status/\d+'),
        re.compile(r'https?://(www\.)?(twitter|x)\.com/i/spaces/\w+'),
        re.compile(r'https?://(www\.)?(twitter|x)\.com/\w+/photo/\d+'),
        re.compile(r'https?://t\.co/\w+'),
        re.compile(r'https?://(mobile\.)?(twitter|x)\.com/\w+/status/\d+'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 120)

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
        }
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if self._proxy:
            opts["proxy"] = self._proxy
        if extra:
            opts.update(extra)
        return opts

    def _detect_content_type(self, url: str) -> str:
        if "/spaces/" in url:
            return "space"
        if "/photo/" in url:
            return "image"
        return "video"

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
                        "width": fmt.get("width", 0),
                        "height": fmt.get("height", 0),
                        "filesize": fmt.get("filesize") or 0,
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
                    "uploader_id": info.get("uploader_id", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "repost_count": info.get("repost_count", 0),
                    "comment_count": info.get("comment_count", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "timestamp": info.get("timestamp", 0),
                    "content_type": self._detect_content_type(url),
                }
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    # -------------------------------------------------------------------
    # Lifecycle: Prepare
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Twitter/X URL: {task.url}")
        out_dir = self._ensure_output_dir(
            task.output_path or self._output_dir
        )
        task.output_path = out_dir

    # -------------------------------------------------------------------
    # Lifecycle: Download
    # -------------------------------------------------------------------

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.tags[0] if task.tags else "best"
        content_type = self._detect_content_type(task.url)
        format_spec = self._resolve_format(quality, content_type)

        outtmpl = os.path.join(
            task.output_path or self._output_dir,
            "%(uploader)s - %(title)s [%(id)s].%(ext)s",
        )

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": outtmpl,
        })

        # Spaces need special handling
        if content_type == "space":
            ytdlp_opts["extractor"] = "TwitterSpaces"

        if quality == "audio" or content_type == "space":
            ytdlp_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "best"},
                {"key": "FFmpegMetadata"},
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
                        "uploader": info.get("uploader", ""),
                        "duration": info.get("duration", 0),
                        "content_type": content_type,
                    }
                    filename = ydl.prepare_filename(info)
                    if quality == "audio" or content_type == "space":
                        for ext in ("m4a", "mp3", "opus"):
                            alt = os.path.splitext(filename)[0] + f".{ext}"
                            if os.path.exists(alt):
                                filename = alt
                                break
                    if os.path.exists(filename):
                        result.output_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                    # Gallery images
                    entries = info.get("entries", [])
                    if entries:
                        result.metadata["extra_files"] = [
                            os.path.abspath(ydl.prepare_filename(e))
                            for e in entries
                            if os.path.exists(ydl.prepare_filename(e))
                        ]
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
    def _resolve_format(quality: str, content_type: str) -> str:
        if content_type == "space":
            return "bestaudio/best"
        quality_map = {
            "best": "bestvideo+bestaudio/best",
            "high": "best[height<=1080]",
            "medium": "best[height<=720]",
            "low": "best[height<=480]",
            "audio": "bestaudio/best",
        }
        return quality_map.get(quality, "bestvideo+bestaudio/best")

    # -------------------------------------------------------------------
    # Lifecycle: Verify & Post-Process
    # -------------------------------------------------------------------

    def on_verify(self, task=None, result=None):
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    def on_post_process(self, task=None, result=None):
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
    """Register the Twitter/X agent."""
    skill = AgentSkill(
        platform="twitter",
        formats=frozenset(TwitterDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(TwitterDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "video", "images", "spaces", "galleries",
            "cookie_auth", "threads",
        ]),
        max_concurrent=2,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description="Twitter/X downloader: videos, images, Spaces audio, galleries, cookie auth.",
    )
    return ("twitter", skill)
