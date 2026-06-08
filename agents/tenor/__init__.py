"""
RS Downloader v10.0.0 - Tenor Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Tenor GIF downloader supporting:
- GIF downloads at multiple sizes
- MP4 and WebM formats
- Search-based discovery
- Tenor API v2 support
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


class TenorDownloader(DownloaderBase):
    """Tenor download agent for GIFs."""

    AGENT_NAME = "tenor"
    PLATFORM = "tenor"
    SUPPORTED_FORMATS = ["gif", "mp4", "webm"]
    SUPPORTED_QUALITIES = ["original", "medium", "small", "tiny"]

    _URL_PATTERNS = [
        re.compile(r'https?://tenor\.com/view/[\w-]+'),
        re.compile(r'https?://tenor\.com/[\w]+\.gif'),
        re.compile(r'https?://media\.tenor\.com/'),
    ]
    _API_BASE = "https://g.tenor.com/v1"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_gif_id(self, url: str) -> str:
        match = re.search(r'/view/[\w-]+-([\d]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'/([\w]+)\.gif', url)
        if match:
            return match.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "gif", "quality": "original GIF"},
            {"format_id": "medium", "ext": "gif", "quality": "medium (220px)"},
            {"format_id": "small", "ext": "mp4", "quality": "small MP4"},
            {"format_id": "tiny", "ext": "webm", "quality": "tiny WebM"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "tenor", "url": url}
        gif_id = self._extract_gif_id(url)
        if gif_id:
            api_key = self.memory.get("api_key", "LIVDSRZULELA")
            try:
                resp = requests.get(
                    f"{self._API_BASE}/gifs",
                    params={"ids": gif_id, "key": api_key, "media_filter": "basic"},
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    results = resp.json().get("results", [])
                    if results:
                        data = results[0]
                        metadata.update({
                            "id": data.get("id", ""),
                            "title": data.get("title", ""),
                            "url": data.get("url", ""),
                            "media": data.get("media", []),
                        })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Tenor URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["gif_id"] = self._extract_gif_id(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "original")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            media_list = metadata.get("media", [])
            download_url = ""
            ext = "gif"
            if media_list:
                media = media_list[0]
                quality_map = {"original": "gif", "medium": "mediumgif", "small": "mp4", "tiny": "webm"}
                key = quality_map.get(quality, "gif")
                if key in media:
                    download_url = media[key].get("url", "")
                    ext = media[key].get("dims", ["gif"])[-1] if "dims" in media[key] else key
            if not download_url:
                result.status = DownloadStatus.FAILED
                result.error = "No download URL found"
                return result
            title = metadata.get("title") or task.options.get("gif_id") or "tenor"
            filename = self._safe_filename(f"{title}_{quality}.{ext}")
            filepath = os.path.join(task.options.get("output_dir", self.output_dir), filename)
            resp = requests.get(download_url, headers=self.headers, stream=True, timeout=self.timeout)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = os.path.getsize(filepath)
            result.content_type = detect_content_type(filename=filename)
            result.status = DownloadStatus.VERIFYING
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
        name="tenor", platform="tenor",
        description="Tenor GIF downloader: multiple sizes, MP4/WebM, search, API v2 support.",
        supported_formats=TenorDownloader.SUPPORTED_FORMATS,
        supported_qualities=TenorDownloader.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.NORMAL,
    )
    return ("tenor", skill)
