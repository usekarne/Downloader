"""
RS Downloader v10.0.0 - ArtStation Download Agent
====================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

ArtStation downloader supporting:
- Artwork/project downloads
- Multiple image projects
- High-resolution image extraction
- Artist portfolio browsing
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


class ArtStationDownloader(DownloaderBase):
    """ArtStation download agent for artwork and projects."""

    AGENT_NAME = "artstation"
    PLATFORM = "artstation"
    SUPPORTED_FORMATS = ["jpg", "png", "gif", "mp4"]
    SUPPORTED_QUALITIES = ["original", "large", "small", "thumbnail"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.artstation\.com/artwork/([\w-]+)'),
        re.compile(r'https?://www\.artstation\.com/[\w-]+'),
        re.compile(r'https?://[\w-]+\.artstation\.com/p/'),
    ]
    _API_BASE = "https://www.artstation.com/projects"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_project_hash(self, url: str) -> str:
        match = re.search(r'/artwork/([\w-]+)', url)
        if match:
            return match.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "png", "quality": "original"},
            {"format_id": "large", "ext": "jpg", "quality": "large cover"},
            {"format_id": "small", "ext": "jpg", "quality": "small cover"},
            {"format_id": "thumbnail", "ext": "jpg", "quality": "thumbnail"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "artstation", "url": url}
        project_hash = self._extract_project_hash(url)
        if project_hash:
            try:
                resp = requests.get(
                    f"{self._API_BASE}/{project_hash}.json",
                    headers={**self.headers, "Accept": "application/json"},
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    metadata.update({
                        "id": data.get("id", ""),
                        "hash_id": data.get("hash_id", project_hash),
                        "title": data.get("title", ""),
                        "user": data.get("user", {}).get("username", ""),
                        "user_name": data.get("user", {}).get("full_name", ""),
                        "description": data.get("description", ""),
                        "tags": data.get("tags", []),
                        "assets": data.get("assets", []),
                        "likes_count": data.get("likes_count", 0),
                        "views_count": data.get("views_count", 0),
                    })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid ArtStation URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        task.options["project_hash"] = self._extract_project_hash(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            assets = metadata.get("assets", [])
            out_dir = task.options.get("output_dir", self.output_dir)
            title = metadata.get("title") or task.options.get("project_hash") or "artstation"
            if len(assets) > 1:
                # Multi-image project: download all
                for i, asset in enumerate(assets):
                    img_url = asset.get("image_url", "") or asset.get("player_embedded", "")
                    if img_url:
                        ext = img_url.rsplit(".", 1)[-1].split("?")[0] if "." in img_url else "png"
                        fname = self._safe_filename(f"{title}_{i+1:03d}.{ext}")
                        fpath = os.path.join(out_dir, fname)
                        resp = requests.get(img_url, headers=self.headers, stream=True, timeout=self.timeout)
                        with open(fpath, "wb") as f:
                            for chunk in resp.iter_content(8192):
                                f.write(chunk)
                result.file_path = os.path.abspath(out_dir)
                result.filename = f"project_{title}"
                total_size = sum(f.stat().st_size for f in Path(out_dir).iterdir() if f.is_file())
                result.file_size = total_size
            elif assets:
                # Single image
                img_url = assets[0].get("image_url", "")
                ext = img_url.rsplit(".", 1)[-1].split("?")[0] if "." in img_url else "png"
                filename = self._safe_filename(f"{title}.{ext}")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(img_url, headers=self.headers, stream=True, timeout=self.timeout)
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

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        if os.path.isdir(result.file_path):
            return any(Path(result.file_path).iterdir())
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.file_path and os.path.isfile(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="artstation", platform="artstation",
        description="ArtStation downloader: artwork, projects, multi-image, high-res, portfolio.",
        supported_formats=ArtStationDownloader.SUPPORTED_FORMATS,
        supported_qualities=ArtStationDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("artstation", skill)
