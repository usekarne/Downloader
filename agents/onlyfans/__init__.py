"""
RS Downloader v10.0.0 - OnlyFans Download Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

OnlyFans download agent supporting:
- Post media downloads (images, videos)
- Cookie-based authentication (required)
- yt-dlp integration for video content
- Metadata extraction
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class OnlyFansDownloader(DownloaderBase):
    """OnlyFans download agent requiring cookie authentication."""

    AGENT_NAME = "onlyfans"
    PLATFORM = "onlyfans"
    SUPPORTED_FORMATS = ["mp4", "jpg", "png", "gif", "m4a"]
    SUPPORTED_QUALITIES = ["best", "original", "bestaudio"]

    _URL_PATTERNS = [
        re.compile(r'https?://onlyfans\.com/[\w-]+'),
        re.compile(r'https?://www\.onlyfans\.com/[\w-]+/post/[\d]+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "best", "ext": "mp4", "quality": "best quality"},
            {"format_id": "original", "ext": "*", "quality": "original media"},
            {"format_id": "bestaudio", "ext": "m4a", "quality": "best audio"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "onlyfans", "url": url}
        try:
            import yt_dlp
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            if self.cookies:
                opts["cookiefile"] = self.cookies
            if self.proxy:
                opts["proxy"] = self.proxy
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    metadata.update({
                        "title": info.get("title", ""),
                        "uploader": info.get("uploader", ""),
                        "duration": info.get("duration", 0),
                        "thumbnail": info.get("thumbnail", ""),
                    })
        except Exception:
            pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid OnlyFans URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        if not self.cookies and not task.cookies:
            raise DownloadError("OnlyFans requires cookie authentication", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import shutil, subprocess
        quality = task.options.get("quality", "best")
        out_dir = task.options.get("output_dir", self.output_dir)
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        ytdlp = shutil.which("yt-dlp") or "yt-dlp"
        fmt_map = {
            "best": "bestvideo+bestaudio/best",
            "original": "best",
            "bestaudio": "bestaudio/best",
        }
        cmd = [ytdlp, "-f", fmt_map.get(quality, "best"),
               "-o", os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s")]
        cookie_file = self.cookies or task.cookies
        if cookie_file:
            cmd.extend(["--cookiefile", cookie_file])
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        cmd.append(task.url)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 5)
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                for f in Path(out_dir).iterdir():
                    if f.is_file() and f.stat().st_mtime > time.time() - 300:
                        result.file_path = str(f.resolve())
                        result.filename = f.name
                        result.file_size = f.stat().st_size
                        break
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "OnlyFans download failed"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.file_path and os.path.exists(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="onlyfans", platform="onlyfans",
        description="OnlyFans downloader: posts, media, cookie auth required, yt-dlp integration.",
        supported_formats=OnlyFansDownloader.SUPPORTED_FORMATS,
        supported_qualities=OnlyFansDownloader.SUPPORTED_QUALITIES,
        max_concurrent=2, priority=DownloadPriority.NORMAL,
    )
    return ("onlyfans", skill)
