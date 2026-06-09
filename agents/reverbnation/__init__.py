"""
RS Downloader v10.0.0 - ReverbNation Download Agent
====================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

ReverbNation downloader supporting:
- Audio track downloads
- Artist profile metadata
- Track metadata extraction
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
)


class ReverbNationDownloader(DownloaderBase):
    """ReverbNation download agent for audio tracks and metadata."""

    AGENT_NAME = "reverbnation"
    PLATFORM = "reverbnation"
    SUPPORTED_FORMATS = ["mp3", "m4a", "ogg", "json"]
    SUPPORTED_QUALITIES = ["best", "worst", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.reverbnation\.com/[\w-]+/song/\d+'),
        re.compile(r'https?://www\.reverbnation\.com/[\w-]+$'),
        re.compile(r'https?://reverbnation\.com/[\w-]+/song/\d+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "best", "ext": "mp3", "quality": "best audio"},
            {"format_id": "worst", "ext": "mp3", "quality": "worst audio"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"url": url, "platform": "reverbnation"}
        try:
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            if resp.status_code == 200:
                text = resp.text
                for tag, key in [("og:title", "title"), ("og:image", "thumbnail"),
                                 ("og:description", "description")]:
                    m = re.search(rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key] = m.group(1)
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid ReverbNation URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.options.get("quality", "best")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)
        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        outtmpl = os.path.join(
            task.options.get("output_dir", self.output_dir),
            "%(title)s.%(ext)s")
        fmt = "bestaudio/best" if quality != "worst" else "worstaudio/worst"
        cmd = [ytdlp_path, "-f", fmt, "-o", outtmpl, task.url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.timeout * 10)
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                out_dir = task.options.get("output_dir", self.output_dir)
                for f in Path(out_dir).iterdir():
                    if f.is_file() and f.stat().st_mtime > time.time() - 600:
                        result.file_path = str(f.resolve())
                        result.filename = f.name
                        result.file_size = f.stat().st_size
                        break
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "Failed"
        except subprocess.TimeoutExpired:
            result.status = DownloadStatus.FAILED
            result.error = "Timed out"
        except FileNotFoundError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp not found"
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="reverbnation",
        formats=tuple(ReverbNationDownloader.SUPPORTED_FORMATS),
        qualities=tuple(ReverbNationDownloader.SUPPORTED_QUALITIES),
        features=("audio", "metadata"),
        max_concurrent=2,
        priority=DownloadPriority.LOW,
        version="10.0.0",
        description="ReverbNation downloader: audio tracks and metadata via yt-dlp.",
    )
    return ("reverbnation", skill)
