"""
RS Downloader v10.0.0 - Flickr Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Flickr downloader supporting:
- Photo downloads at multiple sizes
- Album/collection batch download
- Photo metadata and EXIF data
- Flickr API support
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


class FlickrDownloader(DownloaderBase):
    """Flickr download agent for photos and albums."""

    AGENT_NAME = "flickr"
    PLATFORM = "flickr"
    SUPPORTED_FORMATS = ["jpg", "png", "gif"]
    SUPPORTED_QUALITIES = ["original", "large", "medium_800", "medium_640", "small", "thumbnail", "square"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.flickr\.com/photos/[\w@]+/([\d]+)'),
        re.compile(r'https?://www\.flickr\.com/photos/[\w@]+/albums/([\d]+)'),
        re.compile(r'https?://www\.flickr\.com/galleries/([\d]+)'),
        re.compile(r'https?://flic\.kr/p/([\w]+)'),
    ]
    _API_BASE = "https://api.flickr.com/services/rest"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_photo_id(self, url: str) -> Tuple[str, str]:
        album_match = re.search(r'/albums/([\d]+)', url)
        if album_match:
            return ("album", album_match.group(1))
        photo_match = re.search(r'/photos/[\w@]+/([\d]+)', url)
        if photo_match:
            return ("photo", photo_match.group(1))
        short_match = re.search(r'flic\.kr/p/([\w]+)', url)
        if short_match:
            return ("photo_short", short_match.group(1))
        return ("unknown", "")

    def _api_params(self, method: str, **kwargs) -> Dict[str, str]:
        api_key = self.memory.get("api_key", "")
        params = {"method": method, "format": "json", "nojsoncallback": "1"}
        if api_key:
            params["api_key"] = api_key
        params.update(kwargs)
        return params

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "jpg", "quality": "original"},
            {"format_id": "large", "ext": "jpg", "quality": "large 2048px"},
            {"format_id": "medium_800", "ext": "jpg", "quality": "medium 800px"},
            {"format_id": "medium_640", "ext": "jpg", "quality": "medium 640px"},
            {"format_id": "small", "ext": "jpg", "quality": "small 320px"},
            {"format_id": "thumbnail", "ext": "jpg", "quality": "thumbnail"},
            {"format_id": "square", "ext": "jpg", "quality": "square 150px"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "flickr", "url": url}
        content_type, content_id = self._extract_photo_id(url)
        if content_type == "photo" and content_id:
            try:
                resp = requests.get(
                    self._API_BASE,
                    params=self._api_params("flickr.photos.getInfo", photo_id=content_id),
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json().get("photo", {})
                    metadata.update({
                        "id": data.get("id", ""),
                        "title": data.get("title", {}).get("_content", ""),
                        "description": data.get("description", {}).get("_content", ""),
                        "owner": data.get("owner", {}).get("username", ""),
                        "dates": data.get("dates", {}),
                        "views": data.get("views", "0"),
                    })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Flickr URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        content_type, content_id = self._extract_photo_id(task.url)
        task.options["content_type"] = content_type
        task.options["content_id"] = content_id

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "large")
        content_type = task.options.get("content_type", "photo")
        content_id = task.options.get("content_id", "")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            if content_type == "album":
                result.status = DownloadStatus.FAILED
                result.error = "Album download requires API key - use batch mode"
                return result
            # Build photo URL from sizes API
            sizes_resp = requests.get(
                self._API_BASE,
                params=self._api_params("flickr.photos.getSizes", photo_id=content_id),
                timeout=self.timeout,
            )
            download_url = ""
            if sizes_resp.status_code == 200:
                sizes = sizes_resp.json().get("sizes", {}).get("size", [])
                for s in sizes:
                    if s.get("label", "").lower().replace(" ", "_") == quality:
                        download_url = s.get("source", "")
                        break
                if not download_url and sizes:
                    download_url = sizes[-1].get("source", "")
            if not download_url:
                result.status = DownloadStatus.FAILED
                result.error = "Could not resolve download URL"
                return result
            title = metadata.get("title") or content_id or "flickr"
            ext = download_url.rsplit(".", 1)[-1] if "." in download_url else "jpg"
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
        name="flickr", platform="flickr",
        description="Flickr downloader: photos at multiple sizes, albums, EXIF data, API support.",
        supported_formats=FlickrDownloader.SUPPORTED_FORMATS,
        supported_qualities=FlickrDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("flickr", skill)
