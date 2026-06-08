"""
RS Downloader v10.0.0 - Vimeo Enterprise Download Agent
=========================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Vimeo Enterprise downloader supporting:
- Enterprise/private domain videos
- Password-protected content
- API token authentication
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


class VimeoEnterpriseDownloader(DownloaderBase):
    """Vimeo Enterprise download agent for private/business videos."""

    AGENT_NAME = "vimeo_enterprise"
    PLATFORM = "vimeo_enterprise"
    SUPPORTED_FORMATS = ["mp4", "webm", "mkv", "mp3", "m4a"]
    SUPPORTED_QUALITIES = ["best", "1080p", "720p", "480p", "audio"]

    _URL_PATTERNS = [
        re.compile(r'https?://[\w.-]+\.vimeo\.com/\d+'),
        re.compile(r'https?://(www\.)?vimeo\.com/\d+/[\w-]+'),
        re.compile(r'https?://(www\.)?vimeo\.com/ondemand/[\w-]+'),
        re.compile(r'https?://player\.vimeo\.com/video/\d+\?.*enterprise'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 300)
        self._api_token = kwargs.get("vimeo_api_token")

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        opts: Dict[str, Any] = {"quiet": True, "no_warnings": True}
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if self._proxy:
            opts["proxy"] = self._proxy
        if self._api_token:
            opts["api_token"] = self._api_token
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
                return [{
                    "format_id": fmt.get("format_id", ""),
                    "ext": fmt.get("ext", ""),
                    "height": fmt.get("height", 0),
                    "vcodec": fmt.get("vcodec", "none"),
                } for fmt in info.get("formats", [])]
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
                    "uploader": info.get("uploader", ""),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                }
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Vimeo Enterprise URL: {task.url}")
        out_dir = self._ensure_output_dir(task.output_path or self._output_dir)
        task.output_path = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.tags[0] if task.tags else "best"
        format_spec = self._resolve_format(quality)

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": os.path.join(
                task.output_path or self._output_dir,
                "%(title)s [%(id)s].%(ext)s",
            ),
        })

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
            "1080p": "bestvideo[height<=1080]+bestaudio/best",
            "720p": "bestvideo[height<=720]+bestaudio/best",
            "480p": "bestvideo[height<=480]+bestaudio/best",
            "audio": "bestaudio/best",
        }
        return quality_map.get(quality, "bestvideo+bestaudio/best")

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
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
        platform="vimeo_enterprise",
        formats=frozenset(VimeoEnterpriseDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(VimeoEnterpriseDownloader.SUPPORTED_QUALITIES),
        features=frozenset(["enterprise", "private_videos", "api_token", "password_protected"]),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Vimeo Enterprise downloader: private/business videos with API token auth.",
    )
    return ("vimeo_enterprise", skill)
