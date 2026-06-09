"""
RS Downloader v10.0.0 - Audible Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Audible audiobook metadata agent supporting:
- Audiobook metadata extraction
- Chapter info and timestamps
- Book details (author, narrator, duration)
- Cover art download
- Note: Full audio download requires DRM bypass (not supported)
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


class AudibleDownloader(DownloaderBase):
    """Audible audiobook metadata and cover art agent."""

    AGENT_NAME = "audible"
    PLATFORM = "audible"
    SUPPORTED_FORMATS = ["json", "jpg", "png"]
    SUPPORTED_QUALITIES = ["metadata_only", "cover_art"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.audible\.(com|co\.uk|de|fr|it|es|co\.jp|com\.au)/pd/[\w-]+/([\dA-Z]+)'),
        re.compile(r'https?://www\.audible\.\w+/pd/[\w-]+/([\dA-Z]+)'),
    ]
    _API_BASE = "https://api.audible.com/1.0/catalog/products"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_asin(self, url: str) -> str:
        match = re.search(r'/([\dA-Z]{10})(?:\?|$|/)', url)
        if match:
            return match.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "metadata", "ext": "json", "quality": "book metadata"},
            {"format_id": "cover", "ext": "jpg", "quality": "cover art"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "audible", "url": url}
        asin = self._extract_asin(url)
        if asin:
            try:
                resp = requests.get(
                    f"{self._API_BASE}/{asin}",
                    params={
                        "response_groups": "contributors,media,product_attrs,product_desc",
                    },
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json().get("product", {})
                    metadata.update({
                        "asin": data.get("asin", asin),
                        "title": data.get("title", ""),
                        "subtitle": data.get("subtitle", ""),
                        "authors": [a.get("name", "") for a in data.get("authors", [])],
                        "narrators": [n.get("name", "") for n in data.get("narrators", [])],
                        "publisher": data.get("publisher_name", ""),
                        "language": data.get("language", ""),
                        "runtime_min": data.get("runtime_length_min", 0),
                        "release_date": data.get("release_date", ""),
                        "summary": data.get("merchandising_summary", ""),
                        "cover_url": data.get("product_images", {}).get("500", ""),
                    })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Audible URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        task.options["asin"] = self._extract_asin(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "metadata_only")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            title = metadata.get("title") or task.options.get("asin") or "audible"
            if quality == "cover_art":
                cover_url = metadata.get("cover_url", "")
                if not cover_url:
                    asin = task.options.get("asin", "")
                    cover_url = f"https://images-na.ssl-images-amazon.com/images/I/{asin}._SL500_.jpg"
                filename = self._safe_filename(f"{title}_cover.jpg")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(cover_url, headers=self.headers, timeout=self.timeout)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
                result.content_type = "image/jpeg"
            else:
                filename = self._safe_filename(f"{title}_metadata.json")
                filepath = os.path.join(out_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
                result.content_type = "application/json"
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
        name="audible", platform="audible",
        description="Audible metadata agent: book info, chapter data, cover art, narrator details.",
        supported_formats=AudibleDownloader.SUPPORTED_FORMATS,
        supported_qualities=AudibleDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("audible", skill)
