"""
RS Downloader v10.0.0 - Patreon Download Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Patreon download agent supporting:
- Post media downloads (images, videos, audio)
- Attachment downloads
- Cookie-based authentication
- yt-dlp integration for video content
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


class PatreonDownloader(DownloaderBase):
    """Patreon download agent for posts and media."""

    AGENT_NAME = "patreon"
    PLATFORM = "patreon"
    SUPPORTED_FORMATS = ["mp4", "mp3", "m4a", "jpg", "png", "gif", "zip", "pdf"]
    SUPPORTED_QUALITIES = ["original", "best", "bestaudio"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.patreon\.com/posts/[\w-]+'),
        re.compile(r'https?://www\.patreon\.com/[\w-]+'),
    ]
    _API_BASE = "https://www.patreon.com/api"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_post_id(self, url: str) -> str:
        match = re.search(r'/posts/([\w-]+)', url)
        if match:
            return match.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "*", "quality": "original media"},
            {"format_id": "best", "ext": "mp4", "quality": "best video"},
            {"format_id": "bestaudio", "ext": "m4a", "quality": "best audio"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "patreon", "url": url}
        # Try yt-dlp for metadata
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
                        "description": info.get("description", ""),
                        "duration": info.get("duration", 0),
                        "uploader": info.get("uploader", ""),
                        "thumbnail": info.get("thumbnail", ""),
                    })
        except Exception:
            pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Patreon URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
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
        # Use yt-dlp for Patreon downloads
        ytdlp = shutil.which("yt-dlp") or "yt-dlp"
        fmt_map = {
            "best": "bestvideo+bestaudio/best",
            "bestaudio": "bestaudio/best",
            "original": "best",
        }
        cmd = [ytdlp, "-f", fmt_map.get(quality, "best"),
               "-o", os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s")]
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
        elif task.cookies:
            cmd.extend(["--cookiefile", task.cookies])
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
                        result.content_type = detect_content_type(filename=f.name)
                        break
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "Patreon download failed"
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
        name="patreon", platform="patreon",
        description="Patreon downloader: posts, media, attachments, cookie auth, yt-dlp integration.",
        supported_formats=PatreonDownloader.SUPPORTED_FORMATS,
        supported_qualities=PatreonDownloader.SUPPORTED_QUALITIES,
        max_concurrent=2, priority=DownloadPriority.NORMAL,
    )
    return ("patreon", skill)
