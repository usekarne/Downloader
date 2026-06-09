"""
RS Downloader v10.0.0 - Pexels Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Pexels downloader supporting:
- Photo downloads at multiple resolutions
- Video downloads (HD, SD, mobile)
- Collection and search-based discovery
- Photographer attribution
- API key support for enhanced access
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


class PexelsDownloader(DownloaderBase):
    """Pexels download agent for photos and videos."""

    AGENT_NAME = "pexels"
    PLATFORM = "pexels"
    SUPPORTED_FORMATS = ["jpg", "png", "mp4", "webm"]
    SUPPORTED_QUALITIES = ["original", "large", "medium", "small", "portrait", "landscape"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.pexels\.com/photo/[\w-]+'),
        re.compile(r'https?://www\.pexels\.com/video/[\w-]+'),
        re.compile(r'https?://www\.pexels\.com/search/[\w-]+'),
        re.compile(r'https?://www\.pexels\.com/collections/[\w-]+'),
    ]
    _API_BASE = "https://api.pexels.com/v1"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_media_id(self, url: str) -> Tuple[str, str]:
        """Extract media type and ID from URL. Returns (type, id)."""
        video_match = re.search(r'/video/[\w-]+-(\d+)/', url)
        if video_match:
            return ("video", video_match.group(1))
        photo_match = re.search(r'/photo/[\w-]+-(\d+)/', url)
        if photo_match:
            return ("photo", photo_match.group(1))
        # Try numeric ID at end
        num_match = re.search(r'-(\d+)/?$', url)
        if num_match:
            return ("photo", num_match.group(1))
        return ("unknown", "")

    def _get_api_headers(self) -> Dict[str, str]:
        headers = dict(self.headers)
        api_key = self.memory.get("api_key", "")
        if api_key:
            headers["Authorization"] = api_key
        return headers

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        media_type, _ = self._extract_media_id(url)
        if media_type == "video":
            return [
                {"format_id": "hd", "ext": "mp4", "quality": "HD 1080p"},
                {"format_id": "sd", "ext": "mp4", "quality": "SD"},
                {"format_id": "mobile", "ext": "mp4", "quality": "Mobile"},
            ]
        return [
            {"format_id": "original", "ext": "jpg", "quality": "original"},
            {"format_id": "large", "ext": "jpg", "quality": "large (1600px)"},
            {"format_id": "medium", "ext": "jpg", "quality": "medium (800px)"},
            {"format_id": "small", "ext": "jpg", "quality": "small (400px)"},
            {"format_id": "portrait", "ext": "jpg", "quality": "portrait"},
            {"format_id": "landscape", "ext": "jpg", "quality": "landscape"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "pexels", "url": url}
        media_type, media_id = self._extract_media_id(url)
        if media_id:
            endpoint = "videos" if media_type == "video" else "photos"
            try:
                resp = requests.get(
                    f"{self._API_BASE.replace('v1', 'v1')}/{endpoint}/{media_id}",
                    headers=self._get_api_headers(),
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    metadata.update({
                        "id": data.get("id", ""),
                        "photographer": data.get("user", {}).get("name", ""),
                        "width": data.get("width", 0),
                        "height": data.get("height", 0),
                        "url": data.get("url", ""),
                        "media_type": media_type,
                    })
                    if media_type == "photo" and "src" in data:
                        metadata["src"] = data["src"]
                    elif media_type == "video" and "video_files" in data:
                        metadata["video_files"] = data["video_files"]
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Pexels URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        media_type, media_id = self._extract_media_id(task.url)
        task.options["media_type"] = media_type
        task.options["media_id"] = media_id

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "large")
        media_type = task.options.get("media_type", "photo")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            download_url = ""
            if media_type == "video":
                video_files = metadata.get("video_files", [])
                for vf in video_files:
                    if vf.get("quality") == quality or (quality == "hd" and vf.get("quality") == "hd"):
                        download_url = vf.get("link", "")
                        break
                if not download_url and video_files:
                    download_url = video_files[0].get("link", "")
            else:
                src = metadata.get("src", {})
                download_url = src.get(quality, src.get("original", ""))
            if not download_url:
                result.status = DownloadStatus.FAILED
                result.error = "No download URL found"
                return result
            ext = "mp4" if media_type == "video" else "jpg"
            title = metadata.get("photographer") or metadata.get("media_id") or "pexels"
            filename = self._safe_filename(f"{title}_{quality}.{ext}")
            filepath = os.path.join(task.options.get("output_dir", self.output_dir), filename)
            resp = requests.get(download_url, headers=self.headers, stream=True,
                                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                                timeout=self.timeout)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
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
        name="pexels", platform="pexels",
        description="Pexels downloader: photos and videos, multiple resolutions, collections, API support.",
        supported_formats=PexelsDownloader.SUPPORTED_FORMATS,
        supported_qualities=PexelsDownloader.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.NORMAL,
    )
    return ("pexels", skill)
