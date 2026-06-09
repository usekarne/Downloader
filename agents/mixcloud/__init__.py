"""
RS Downloader v10.0.0 - Mixcloud Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Mixcloud downloader supporting:
- Show/cloudcast downloads (full audio)
- Artist uploads browsing
- Metadata extraction (title, artist, duration, tags)
- Thumbnail/artwork downloads
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


class MixcloudDownloader(DownloaderBase):
    """Mixcloud download agent for shows, uploads, and cloudcasts.

    Uses yt-dlp for audio extraction and Mixcloud API for metadata.
    """

    AGENT_NAME = "mixcloud"
    PLATFORM = "mixcloud"
    SUPPORTED_FORMATS = ["mp3", "m4a", "ogg", "opus", "json"]
    SUPPORTED_QUALITIES = ["best", "worst", "bestaudio", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.mixcloud\.com/[\w-]+/[\w-]+/'),
        re.compile(r'https?://www\.mixcloud\.com/[\w-]+/$'),
        re.compile(r'https?://mixcloud\.com/[\w-]+/[\w-]+/'),
    ]

    _MIXCLOUD_API = "https://api.mixcloud.com"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_url(self, url: str) -> Tuple[str, str]:
        m = re.search(r'mixcloud\.com/([\w-]+)/([\w-]+)', url)
        if m:
            artist, slug = m.group(1), m.group(2)
            if slug:
                return "cloudcast", f"{artist}/{slug}"
            return "artist", artist
        return "unknown", ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        content_type, _ = self._parse_url(url)
        formats = [
            {"format_id": "best", "ext": "mp3", "quality": "best audio"},
            {"format_id": "worst", "ext": "mp3", "quality": "worst audio"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        content_type, key = self._parse_url(url)
        metadata: Dict[str, Any] = {"url": url, "platform": "mixcloud",
                                    "content_type": content_type}
        if content_type == "cloudcast" and key:
            try:
                resp = requests.get(
                    f"{self._MIXCLOUD_API}/{key}/",
                    timeout=self.timeout)
                resp.raise_for_status()
                data = resp.json()
                metadata.update({
                    "title": data.get("name", ""),
                    "artist": data.get("owner", {}).get("name", ""),
                    "duration": data.get("audio_length", 0),
                    "thumbnail": data.get("pictures", {}).get("extra_large", ""),
                    "description": data.get("description", ""),
                    "tags": [t.get("name", "") for t in data.get("tags", [])],
                    "play_count": data.get("play_count", 0),
                    "favorite_count": data.get("favorite_count", 0),
                    "created_time": data.get("created_time", ""),
                })
            except Exception as exc:
                metadata["error"] = str(exc)
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(
                f"Invalid Mixcloud URL: {task.url}",
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

        if quality == "metadata_only":
            return self._download_metadata(task, result)

        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        outtmpl = os.path.join(
            task.options.get("output_dir", self.output_dir),
            "%(title)s [%(id)s].%(ext)s")
        fmt = "bestaudio/best" if quality in ("best", "bestaudio") else "worstaudio/worst"
        cmd = [ytdlp_path, "-f", fmt, "-o", outtmpl, task.url]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout * 10)
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
            result.error = "Download timed out"
        except FileNotFoundError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp not found"
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_metadata(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            filename = self._safe_filename(f"{metadata.get('title', 'mixcloud')}_metadata.json")
            filepath = os.path.join(out_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = os.path.getsize(filepath)
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        return result

    @staticmethod
    def _safe_filename(name: str) -> str:
        return re.sub(r'[<>:"|?*\\]', '_', name)[:200]

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="mixcloud",
        formats=tuple(MixcloudDownloader.SUPPORTED_FORMATS),
        qualities=tuple(MixcloudDownloader.SUPPORTED_QUALITIES),
        features=("shows", "cloudcasts", "uploads", "metadata"),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Mixcloud downloader: shows, cloudcasts, uploads, metadata, yt-dlp audio.",
    )
    return ("mixcloud", skill)
