"""
RS Downloader v10.0.0 - DeviantArt Download Agent
====================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

DeviantArt downloader supporting:
- Art/deviation downloads
- Collection batch download
- Full resolution image extraction
- OAuth2 API support
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


class DeviantArtDownloader(DownloaderBase):
    """DeviantArt download agent for art and collections."""

    AGENT_NAME = "deviantart"
    PLATFORM = "deviantart"
    SUPPORTED_FORMATS = ["jpg", "png", "gif", "webp", "mp4"]
    SUPPORTED_QUALITIES = ["original", "preview", "thumbnail"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.deviantart\.com/[\w-]+/art/[\w-]+'),
        re.compile(r'https?://www\.deviantart\.com/[\w-]+/favourites/[\w-]*'),
        re.compile(r'https?://fav\.me/([\w]+)'),
        re.compile(r'https?://sta\.sh/([\w]+)'),
    ]
    _API_BASE = "https://www.deviantart.com/api/v1/oauth2"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_deviation_id(self, url: str) -> str:
        match = re.search(r'/art/[\w-]+-(\d+)', url)
        if match:
            return match.group(1)
        return ""

    def _get_api_headers(self) -> Dict[str, str]:
        headers = dict(self.headers)
        access_token = self.memory.get("access_token", "")
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        return headers

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "png", "quality": "full resolution"},
            {"format_id": "preview", "ext": "jpg", "quality": "preview"},
            {"format_id": "thumbnail", "ext": "jpg", "quality": "thumbnail"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "deviantart", "url": url}
        dev_id = self._extract_deviation_id(url)
        if dev_id:
            try:
                resp = requests.get(
                    f"{self._API_BASE}/deviation/{dev_id}",
                    headers=self._get_api_headers(),
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    metadata.update({
                        "id": data.get("deviationid", ""),
                        "title": data.get("title", ""),
                        "author": data.get("author", {}).get("username", ""),
                        "category": data.get("category", ""),
                        "is_mature": data.get("is_mature", False),
                        "content": data.get("content", {}),
                        "thumbs": data.get("thumbs", []),
                    })
            except Exception:
                pass
        # Fallback: page scraping
        if not metadata.get("title"):
            try:
                resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    og_img = re.search(r'og:image["\s]+content=["\']([^"\']+)', resp.text)
                    if og_img:
                        metadata["thumbnail"] = og_img.group(1)
                    title = re.search(r'<title>([^<]+)</title>', resp.text)
                    if title:
                        metadata["title"] = title.group(1).strip()
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid DeviantArt URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["deviation_id"] = self._extract_deviation_id(task.url)

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
            download_url = ""
            content = metadata.get("content", {})
            thumbs = metadata.get("thumbs", [])
            if quality == "original" and content:
                download_url = content.get("src", "")
            elif quality == "thumbnail" and thumbs:
                download_url = thumbs[0].get("src", "") if thumbs else ""
            elif content:
                download_url = content.get("src", "")
            if not download_url and thumbs:
                download_url = thumbs[-1].get("src", "")
            if not download_url:
                result.status = DownloadStatus.FAILED
                result.error = "No download URL found"
                return result
            ext = download_url.rsplit(".", 1)[-1].split("?")[0] if "." in download_url else "png"
            title = metadata.get("title") or task.options.get("deviation_id") or "deviantart"
            filename = self._safe_filename(f"{title}.{ext}")
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

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        if result.file_path and os.path.exists(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="deviantart", platform="deviantart",
        description="DeviantArt downloader: art, collections, full resolution, OAuth2 API.",
        supported_formats=DeviantArtDownloader.SUPPORTED_FORMATS,
        supported_qualities=DeviantArtDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("deviantart", skill)
