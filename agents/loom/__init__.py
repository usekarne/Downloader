"""
RS Downloader v10.0.0 - Loom Download Agent
==============================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Loom downloader supporting:
- Video downloads via embed URL extraction
- Direct MP4 extraction
"""

from __future__ import annotations

import hashlib
import json
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


class LoomDownloader(DownloaderBase):
    """Loom download agent using yt-dlp and embed extraction."""

    AGENT_NAME = "loom"
    PLATFORM = "loom"
    SUPPORTED_FORMATS = ["mp4", "webm", "mp3", "m4a"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low"]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?loom\.com/share/[\w-]+'),
        re.compile(r'https?://(www\.)?loom\.com/embed/[\w-]+'),
        re.compile(r'https?://(www\.)?loom\.com/[\w-]+/[\w-]+'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 180)

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
            raise DownloadError(f"Invalid Loom URL: {task.url}")
        out_dir = self._ensure_output_dir(task.output_path or self._output_dir)
        task.output_path = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        ytdlp_opts = self._build_ytdlp_opts({
            "format": "best",
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
        platform="loom",
        formats=frozenset(LoomDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(LoomDownloader.SUPPORTED_QUALITIES),
        features=frozenset(["video", "embed_extraction"]),
        max_concurrent=1,
        priority=DownloadPriority.LOW,
        version="10.0.0",
        description="Loom downloader: video downloads via embed extraction.",
    )
    return ("loom", skill)
