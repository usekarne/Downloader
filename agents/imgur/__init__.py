"""
RS Downloader v10.0.0 - Imgur Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Imgur downloader supporting:
- Single image downloads
- Album/gallery batch downloads
- GIF and GIFV downloads
- Direct image URL resolution
- Imgur API v3 support
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


class ImgurDownloader(DownloaderBase):
    """Imgur download agent for images, albums, and GIFs."""

    AGENT_NAME = "imgur"
    PLATFORM = "imgur"
    SUPPORTED_FORMATS = ["jpg", "png", "gif", "gifv", "mp4", "webm"]
    SUPPORTED_QUALITIES = ["original", "medium", "thumbnail", "big_square"]

    _URL_PATTERNS = [
        re.compile(r'https?://imgur\.com/([\w]+)'),
        re.compile(r'https?://imgur\.com/a/([\w]+)'),
        re.compile(r'https?://imgur\.com/gallery/([\w]+)'),
        re.compile(r'https?://i\.imgur\.com/([\w]+)\.\w+'),
    ]
    _API_BASE = "https://api.imgur.com/3"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_id(self, url: str) -> Tuple[str, str]:
        """Extract (content_type, id) from URL."""
        album_match = re.search(r'/a/([\w]+)', url)
        if album_match:
            return ("album", album_match.group(1))
        gallery_match = re.search(r'/gallery/([\w]+)', url)
        if gallery_match:
            return ("gallery", gallery_match.group(1))
        direct_match = re.search(r'i\.imgur\.com/([\w]+)', url)
        if direct_match:
            return ("image", direct_match.group(1))
        image_match = re.search(r'imgur\.com/([\w]+)', url)
        if image_match:
            return ("image", image_match.group(1))
        return ("unknown", "")

    def _get_api_headers(self) -> Dict[str, str]:
        headers = dict(self.headers)
        client_id = self.memory.get("client_id", "")
        if client_id:
            headers["Authorization"] = f"Client-ID {client_id}"
        return headers

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "jpg", "quality": "original"},
            {"format_id": "medium", "ext": "jpg", "quality": "medium (640px)"},
            {"format_id": "thumbnail", "ext": "jpg", "quality": "thumbnail (160px)"},
            {"format_id": "big_square", "ext": "jpg", "quality": "big square (160px)"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "imgur", "url": url}
        content_type, content_id = self._extract_id(url)
        if content_id:
            endpoint = f"{self._API_BASE}/{content_type}/{content_id}"
            try:
                resp = requests.get(endpoint, headers=self._get_api_headers(),
                                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                                    timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    if content_type == "album":
                        metadata.update({
                            "id": data.get("id", ""), "title": data.get("title", ""),
                            "description": data.get("description", ""),
                            "image_count": data.get("images_count", 0),
                            "images": data.get("images", []),
                        })
                    else:
                        metadata.update({
                            "id": data.get("id", ""), "title": data.get("title", ""),
                            "description": data.get("description", ""),
                            "type": data.get("type", ""), "width": data.get("width", 0),
                            "height": data.get("height", 0), "size": data.get("size", 0),
                            "link": data.get("link", ""),
                            "animated": data.get("animated", False),
                        })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Imgur URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        content_type, content_id = self._extract_id(task.url)
        task.options["content_type"] = content_type
        task.options["content_id"] = content_id

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        content_type = task.options.get("content_type", "image")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            if content_type == "album":
                images = metadata.get("images", [])
                for i, img in enumerate(images):
                    link = img.get("link", "")
                    if link:
                        fname = self._safe_filename(f"imgur_{content_id}_{i}.{link.rsplit('.', 1)[-1]}")
                        fpath = os.path.join(out_dir, fname)
                        resp = requests.get(link, headers=self.headers, timeout=self.timeout)
                        with open(fpath, "wb") as f:
                            f.write(resp.content)
                result.file_path = os.path.abspath(out_dir)
                result.filename = f"album_{content_id}"
                result.file_size = sum(f.stat().st_size for f in Path(out_dir).iterdir() if f.is_file())
            else:
                link = metadata.get("link", "")
                if not link:
                    img_id = task.options.get("content_id", "")
                    link = f"https://i.imgur.com/{img_id}.jpg"
                ext = link.rsplit(".", 1)[-1] if "." in link else "jpg"
                filename = self._safe_filename(f"imgur_{task.options.get('content_id', 'image')}.{ext}")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(link, headers=self.headers, stream=True, timeout=self.timeout)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
            result.content_type = detect_content_type(filename=result.filename)
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        if os.path.isdir(result.file_path):
            return any(Path(result.file_path).iterdir())
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        if result.file_path and os.path.isfile(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="imgur", platform="imgur",
        description="Imgur downloader: images, albums, GIFs, direct URL resolution, API v3 support.",
        supported_formats=ImgurDownloader.SUPPORTED_FORMATS,
        supported_qualities=ImgurDownloader.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.NORMAL,
    )
    return ("imgur", skill)
