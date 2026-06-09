"""
RS Downloader v10.0.0 - Giphy Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Giphy downloader supporting:
- GIF downloads at multiple sizes
- Sticker downloads
- Search-based discovery
- Giphy API support
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


class GiphyDownloader(DownloaderBase):
    """Giphy download agent for GIFs and stickers."""

    AGENT_NAME = "giphy"
    PLATFORM = "giphy"
    SUPPORTED_FORMATS = ["gif", "mp4", "webp"]
    SUPPORTED_QUALITIES = ["original", "downsized", "medium", "small", "preview"]

    _URL_PATTERNS = [
        re.compile(r'https?://giphy\.com/gifs/[\w-]+'),
        re.compile(r'https?://giphy\.com/stickers/[\w-]+'),
        re.compile(r'https?://media\.giphy\.com/media/([\w]+)'),
    ]
    _API_BASE = "https://api.giphy.com/v1"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_gif_id(self, url: str) -> str:
        match = re.search(r'/media/([\w]+)', url)
        if match:
            return match.group(1)
        match = re.search(r'(?:gifs|stickers)/[\w-]*-([\w]+)', url)
        if match:
            return match.group(1)
        return ""

    def _get_api_params(self) -> Dict[str, str]:
        api_key = self.memory.get("api_key", "dc6zaTOxFJmzC")
        return {"api_key": api_key}

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "gif", "quality": "original GIF"},
            {"format_id": "downsized", "ext": "gif", "quality": "downsized"},
            {"format_id": "medium", "ext": "gif", "quality": "medium"},
            {"format_id": "small", "ext": "gif", "quality": "small"},
            {"format_id": "preview", "ext": "mp4", "quality": "MP4 preview"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "giphy", "url": url}
        gif_id = self._extract_gif_id(url)
        if gif_id:
            try:
                resp = requests.get(
                    f"{self._API_BASE}/gifs/{gif_id}",
                    params=self._get_api_params(),
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    images = data.get("images", {})
                    metadata.update({
                        "id": data.get("id", ""),
                        "title": data.get("title", ""),
                        "slug": data.get("slug", ""),
                        "username": data.get("username", ""),
                        "source": data.get("source", ""),
                        "rating": data.get("rating", ""),
                        "images": images,
                    })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Giphy URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
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
            images = metadata.get("images", {})
            quality_map = {
                "original": images.get("original", {}),
                "downsized": images.get("downsized", {}),
                "medium": images.get("downsized_medium", images.get("fixed_height", {})),
                "small": images.get("downsized_small", {}),
                "preview": images.get("original_mp4", {}),
            }
            img_data = quality_map.get(quality, images.get("original", {}))
            download_url = img_data.get("url", "") or img_data.get("mp4", "")
            if not download_url:
                result.status = DownloadStatus.FAILED
                result.error = "No download URL found"
                return result
            ext = "mp4" if download_url.endswith(".mp4") else "gif"
            title = metadata.get("title") or metadata.get("gif_id") or "giphy"
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
        name="giphy", platform="giphy",
        description="Giphy downloader: GIFs and stickers at multiple sizes, search, API support.",
        supported_formats=GiphyDownloader.SUPPORTED_FORMATS,
        supported_qualities=GiphyDownloader.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.NORMAL,
    )
    return ("giphy", skill)
