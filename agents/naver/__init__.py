"""
RS Downloader v10.0.0 - Naver Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Naver download agent supporting:
- Naver TV video downloads
- Naver Blog media extraction
- Naver Post content
- yt-dlp integration
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


class NaverDownloader(DownloaderBase):
    """Naver download agent for videos and posts."""

    AGENT_NAME = "naver"
    PLATFORM = "naver"
    SUPPORTED_FORMATS = ["mp4", "ts", "mp3", "m4a"]
    SUPPORTED_QUALITIES = ["1080p", "720p", "480p", "360p", "best", "bestaudio"]

    _URL_PATTERNS = [
        re.compile(r'https?://tv\.naver\.com/v/(\d+)'),
        re.compile(r'https?://tv\.naver\.com/[\w-]+/clips'),
        re.compile(r'https?://blog\.naver\.com/[\w-]+/(\d+)'),
        re.compile(r'https?://post\.naver\.com/viewer/[\w-]+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "1080p", "ext": "mp4", "quality": "1080p"},
            {"format_id": "720p", "ext": "mp4", "quality": "720p"},
            {"format_id": "480p", "ext": "mp4", "quality": "480p"},
            {"format_id": "360p", "ext": "mp4", "quality": "360p"},
            {"format_id": "best", "ext": "mp4", "quality": "best"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "naver", "url": url}
        try:
            import yt_dlp
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            if self.proxy:
                opts["proxy"] = self.proxy
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    metadata.update({
                        "id": info.get("id", ""),
                        "title": info.get("title", ""),
                        "duration": info.get("duration", 0),
                        "uploader": info.get("uploader", ""),
                        "thumbnail": info.get("thumbnail", ""),
                        "view_count": info.get("view_count", 0),
                    })
        except Exception:
            pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Naver URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
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
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "best": "bestvideo+bestaudio/best",
            "bestaudio": "bestaudio/best",
        }
        cmd = [ytdlp, "-f", fmt_map.get(quality, "best"),
               "-o", os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s"),
               "--merge-output-format", "mp4"]
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
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
                result.error = proc.stderr[:500] if proc.stderr else "Download failed"
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
        name="naver", platform="naver",
        description="Naver downloader: Naver TV videos, blog media, post content via yt-dlp.",
        supported_formats=NaverDownloader.SUPPORTED_FORMATS,
        supported_qualities=NaverDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("naver", skill)
