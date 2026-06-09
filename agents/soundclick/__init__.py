"""
RS Downloader v10.0.0 - SoundClick Download Agent
===================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

SoundClick downloader supporting:
- Audio track downloads via requests
- Artist profile metadata
- Track/stream metadata extraction
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
)


class SoundClickDownloader(DownloaderBase):
    """SoundClick download agent for audio tracks and metadata."""

    AGENT_NAME = "soundclick"
    PLATFORM = "soundclick"
    SUPPORTED_FORMATS = ["mp3", "m4a", "json"]
    SUPPORTED_QUALITIES = ["best", "preview", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.soundclick\.com/music/songInfo\.cfm\?songID=\d+'),
        re.compile(r'https?://www\.soundclick\.com/artist/default\.cfm\?bandid=\d+'),
        re.compile(r'https?://soundclick\.com/share\.cfm\?id=\d+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_song_id(self, url: str) -> str:
        m = re.search(r'songID=(\d+)', url)
        if m:
            return m.group(1)
        m = re.search(r'id=(\d+)', url)
        return m.group(1) if m else ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "best", "ext": "mp3", "quality": "best available"},
            {"format_id": "preview", "ext": "mp3", "quality": "stream preview"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        song_id = self._extract_song_id(url)
        metadata: Dict[str, Any] = {"url": url, "platform": "soundclick",
                                    "song_id": song_id}
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
                # Try to find stream URL
                stream_m = re.search(r'"(?:streamUrl|fileUrl)"\s*:\s*"([^"]+)"', text)
                if stream_m:
                    metadata["stream_url"] = stream_m.group(1).replace("\\/", "/")
                # Extract from page title
                title_m = re.search(r'<title>([^<]+)</title>', text)
                if title_m and not metadata.get("title"):
                    metadata["title"] = title_m.group(1).strip()
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"}

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid SoundClick URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "best")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            stream_url = metadata.get("stream_url", "")
            out_dir = task.options.get("output_dir", self.output_dir)
            if stream_url and quality != "metadata_only":
                filename = self._safe_filename(
                    f"{metadata.get('title', 'soundclick')}.mp3")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(stream_url, timeout=self.timeout)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = len(resp.content)
            else:
                # Save metadata only
                filename = self._safe_filename(
                    f"{metadata.get('title', 'soundclick')}_metadata.json")
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
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
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
        platform="soundclick",
        formats=tuple(SoundClickDownloader.SUPPORTED_FORMATS),
        qualities=tuple(SoundClickDownloader.SUPPORTED_QUALITIES),
        features=("audio", "metadata", "streaming"),
        max_concurrent=2,
        priority=DownloadPriority.LOW,
        version="10.0.0",
        description="SoundClick downloader: audio tracks and metadata via requests.",
    )
    return ("soundclick", skill)
