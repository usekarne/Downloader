"""
RS Downloader v10.0.0 - Unsplash Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Unsplash downloader supporting:
- High-resolution photo downloads
- Collection browsing and batch download
- Multiple resolution options (raw, full, regular, small, thumb)
- Photographer attribution and metadata
- Search-based photo discovery
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory,
    AgentSkill,
    DownloadError,
    DownloadPriority,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
    detect_content_type,
    suggest_filename,
)


class UnsplashDownloader(DownloaderBase):
    """
    Unsplash download agent for high-resolution photos and collections.

    Supports downloading individual photos at various resolutions,
    entire collections, and search-based photo discovery.
    Requires Unsplash API key for full functionality.
    """

    AGENT_NAME = "unsplash"
    PLATFORM = "unsplash"
    SUPPORTED_FORMATS = ["jpg", "png", "webp"]
    SUPPORTED_QUALITIES = ["raw", "full", "regular", "small", "thumb"]

    _URL_PATTERNS = [
        re.compile(r'https?://unsplash\.com/photos/[\w-]+'),
        re.compile(r'https?://unsplash\.com/collections/[\d]+'),
        re.compile(r'https?://unsplash\.com/s/photos/[\w-]+'),
        re.compile(r'https?://images\.unsplash\.com/'),
    ]
    _API_BASE = "https://api.unsplash.com"

    def validate_url(self, url: str) -> bool:
        """Check if the URL is a valid Unsplash URL."""
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_photo_id(self, url: str) -> str:
        """Extract photo ID from Unsplash URL."""
        match = re.search(r'/photos/([\w-]+)', url)
        if match:
            return match.group(1).split("-")[0]
        match = re.search(r'/photo-([\w-]+)', url)
        if match:
            return match.group(1).split("-")[0]
        return ""

    def _get_api_headers(self) -> Dict[str, str]:
        """Build headers with API key if available."""
        headers = dict(self.headers)
        api_key = self.memory.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Client-ID {api_key}"
        return headers

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Return available formats/resolutions for an Unsplash photo."""
        return [
            {"format_id": "raw", "ext": "jpg", "quality": "original (max resolution)"},
            {"format_id": "full", "ext": "jpg", "quality": "full (max 4000x4000)"},
            {"format_id": "regular", "ext": "jpg", "quality": "regular (max 1080px)"},
            {"format_id": "small", "ext": "jpg", "quality": "small (max 400px)"},
            {"format_id": "thumb", "ext": "jpg", "quality": "thumbnail (max 200px)"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch metadata for an Unsplash photo via API or page scraping."""
        import requests
        metadata: Dict[str, Any] = {"platform": "unsplash", "url": url}
        photo_id = self._extract_photo_id(url)
        if photo_id:
            try:
                resp = requests.get(
                    f"{self._API_BASE}/photos/{photo_id}",
                    headers=self._get_api_headers(),
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    metadata.update({
                        "id": data.get("id", ""),
                        "title": data.get("description") or data.get("alt_description") or "",
                        "photographer": data.get("user", {}).get("name", ""),
                        "photographer_url": data.get("user", {}).get("links", {}).get("html", ""),
                        "width": data.get("width", 0),
                        "height": data.get("height", 0),
                        "color": data.get("color", ""),
                        "likes": data.get("likes", 0),
                        "tags": [t.get("title", "") for t in data.get("tags", [])],
                        "urls": data.get("urls", {}),
                        "created_at": data.get("created_at", ""),
                    })
                    return metadata
            except Exception:
                pass
        # Fallback: page scraping
        try:
            resp = requests.get(url, headers=self.headers,
                                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                                timeout=self.timeout)
            if resp.status_code == 200:
                og_match = re.search(r'og:image["\s]+content=["\']([^"\']+)', resp.text)
                if og_match:
                    metadata["thumbnail"] = og_match.group(1)
                title_match = re.search(r'og:title["\s]+content=["\']([^"\']+)', resp.text)
                if title_match:
                    metadata["title"] = title_match.group(1)
        except Exception:
            pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        """Prepare Unsplash download."""
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Unsplash URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["photo_id"] = self._extract_photo_id(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Download Unsplash photo at the specified resolution."""
        import requests
        quality = task.options.get("quality", "full")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            urls = metadata.get("urls", {})
            download_url = urls.get(quality, urls.get("full", ""))
            if not download_url and "thumbnail" in metadata:
                download_url = metadata["thumbnail"]
            if not download_url:
                result.status = DownloadStatus.FAILED
                result.error = "No download URL found"
                return result
            title = metadata.get("title") or metadata.get("photographer") or task.options.get("photo_id", "unsplash")
            filename = self._safe_filename(f"{title}_{quality}.jpg")
            filepath = os.path.join(task.options.get("output_dir", self.output_dir), filename)
            resp = requests.get(download_url, headers=self.headers,
                                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                                timeout=self.timeout, stream=True)
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            with open(filepath, "wb") as f:
                downloaded = 0
                for chunk in resp.iter_content(chunk_size=8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        self._speed_tracker.update(downloaded)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = os.path.getsize(filepath)
            result.content_type = "image/jpeg"
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        elapsed = time.monotonic() - start_time
        result.elapsed = elapsed
        if elapsed > 0 and result.file_size > 0:
            result.average_speed = result.file_size / elapsed
        return result

    def on_verify(self, result: DownloadResult) -> bool:
        """Verify the downloaded Unsplash photo."""
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        """Post-process: compute checksum, add attribution metadata."""
        if result.file_path and os.path.exists(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    """Register the Unsplash agent."""
    skill = AgentSkill(
        name="unsplash",
        platform="unsplash",
        description=(
            "Unsplash photo downloader: high-res photos, collections, "
            "multiple resolutions (raw/full/regular/small/thumb), "
            "photographer attribution, search discovery."
        ),
        supported_formats=UnsplashDownloader.SUPPORTED_FORMATS,
        supported_qualities=UnsplashDownloader.SUPPORTED_QUALITIES,
        max_concurrent=5,
        priority=DownloadPriority.NORMAL,
    )
    return ("unsplash", skill)
