"""
RS Downloader v10.0.0 - Instagram Download Agent
==================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Instagram downloader supporting:
- Posts (images, videos, carousels)
- Stories (user stories, highlights)
- Reels (short videos)
- IGTV (long-form video)
- Private content via login cookies
- Multi-item carousel extraction
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.downloader_base import (
    AgentSkill,
    DownloadError,
    DownloadPriority,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
)


class InstagramDownloader(DownloaderBase):
    """
    Instagram download agent using yt-dlp and requests-based extraction.

    Supports posts, stories, reels, IGTV, and highlights.
    Login cookies are required for private content and stories.
    """

    AGENT_NAME = "instagram"
    PLATFORM = "instagram"
    SUPPORTED_FORMATS = ["mp4", "jpg", "png", "webp", "m4a"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low"]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?instagram\.com/p/[\w-]+'),
        re.compile(r'https?://(www\.)?instagram\.com/reel/[\w-]+'),
        re.compile(r'https?://(www\.)?instagram\.com/reels/'),
        re.compile(r'https?://(www\.)?instagram\.com/tv/[\w-]+'),
        re.compile(r'https?://(www\.)?instagram\.com/stories/[\w.]+/\d+'),
        re.compile(r'https?://(www\.)?instagram\.com/highlights/\d+'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 120)
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        })
        if self._proxy:
            self._session.proxies = {"http": self._proxy, "https": self._proxy}

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        opts: Dict[str, Any] = {"quiet": True, "no_warnings": True}
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if self._proxy:
            opts["proxy"] = self._proxy
        if extra:
            opts.update(extra)
        return opts

    def _detect_content_type_from_url(self, url: str) -> str:
        """Detect what type of Instagram content the URL points to."""
        if "/reel/" in url or "/reels/" in url:
            return "reel"
        if "/stories/" in url:
            return "story"
        if "/highlights/" in url:
            return "highlight"
        if "/tv/" in url:
            return "igtv"
        if "/p/" in url:
            return "post"
        return "profile"

    # -------------------------------------------------------------------
    # URL Validation
    # -------------------------------------------------------------------

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    # -------------------------------------------------------------------
    # Format Discovery
    # -------------------------------------------------------------------

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Query available formats for Instagram content."""
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
        """Fetch metadata for Instagram content."""
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
                    "like_count": info.get("like_count", 0),
                    "comment_count": info.get("comment_count", 0),
                    "timestamp": info.get("timestamp", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "thumbnails": info.get("thumbnails", []),
                    "content_type": self._detect_content_type_from_url(url),
                }
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    # -------------------------------------------------------------------
    # Lifecycle: Prepare
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        """Prepare Instagram download. Validate URL and set up output."""
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Instagram URL: {task.url}")
        out_dir = self._ensure_output_dir(
            task.output_path or self._output_dir
        )
        task.output_path = out_dir
        ct = self._detect_content_type_from_url(task.url)
        if ct in ("story", "highlight") and not self._cookies:
            task.headers = task.headers or {}
            task.headers["auth_warning"] = (
                "Stories/highlights typically require login cookies."
            )

    # -------------------------------------------------------------------
    # Lifecycle: Download
    # -------------------------------------------------------------------

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Download Instagram content via yt-dlp."""
        quality = task.tags[0] if task.tags else "best"
        format_spec = self._resolve_format(quality)

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": os.path.join(
                task.output_path or self._output_dir,
                "%(uploader)s - %(title)s [%(id)s].%(ext)s",
            ),
        })

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
                        "content_type": self._detect_content_type_from_url(task.url),
                    }
                    filename = ydl.prepare_filename(info)
                    if os.path.exists(filename):
                        result.output_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                    # Handle carousel (multiple items)
                    entries = info.get("entries", [])
                    if entries:
                        extra = []
                        for entry in entries:
                            fname = ydl.prepare_filename(entry)
                            if os.path.exists(fname):
                                extra.append(os.path.abspath(fname))
                        result.metadata["extra_files"] = extra
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
            "best": "best",
            "high": "best[height<=1080]",
            "medium": "best[height<=720]",
            "low": "best[height<=480]",
        }
        return quality_map.get(quality, "best")

    # -------------------------------------------------------------------
    # Lifecycle: Verify
    # -------------------------------------------------------------------

    def on_verify(self, task=None, result=None):
        """Verify downloaded Instagram content."""
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    # -------------------------------------------------------------------
    # Lifecycle: Post-Process
    # -------------------------------------------------------------------

    def on_post_process(self, task=None, result=None):
        """Post-process Instagram download: checksum, collect extra files."""
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
    """Register the Instagram agent."""
    skill = AgentSkill(
        platform="instagram",
        formats=frozenset(InstagramDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(InstagramDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "posts", "stories", "reels", "igtv", "highlights",
            "carousels", "cookie_auth", "multi_item",
        ]),
        max_concurrent=2,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description="Instagram downloader: posts, stories, reels, IGTV, highlights with carousel support.",
    )
    return ("instagram", skill)
