"""
RS Downloader v10.0.0 - LibriVox Download Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

LibriVox audiobook downloader supporting:
- Full audiobook downloads (MP3, OGG)
- Chapter-by-chapter download
- Metadata extraction
- LibriVox API support
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


class LibriVoxDownloader(DownloaderBase):
    """LibriVox download agent for free public domain audiobooks."""

    AGENT_NAME = "librivox"
    PLATFORM = "librivox"
    SUPPORTED_FORMATS = ["mp3", "ogg", "zip"]
    SUPPORTED_QUALITIES = ["standard", "64kbps", "128kbps"]

    _URL_PATTERNS = [
        re.compile(r'https?://librivox\.org/[\w-]+-by-[\w-]+/'),
        re.compile(r'https?://librivox\.org/[\w-]+/'),
    ]
    _API_BASE = "https://librivox.org/api/info/audiobooks"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_book_id(self, url: str) -> str:
        # LibriVox URLs use slug format; we search API by URL
        return url.rstrip("/").rsplit("/", 1)[-1]

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "mp3", "ext": "mp3", "quality": "MP3 chapters"},
            {"format_id": "ogg", "ext": "ogg", "quality": "OGG chapters"},
            {"format_id": "zip", "ext": "zip", "quality": "ZIP archive"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "librivox", "url": url}
        try:
            resp = requests.get(
                self._API_BASE,
                params={"format": "json", "url": url},
                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                data = resp.json()
                books = data.get("books", [])
                if books:
                    book = books[0]
                    metadata.update({
                        "id": book.get("id", ""),
                        "title": book.get("title", ""),
                        "description": book.get("description", ""),
                        "authors": [a.get("name", "") for a in book.get("authors", [])],
                        "language": book.get("language", ""),
                        "totaltime": book.get("totaltime", ""),
                        "url_zip_file": book.get("url_zip_file", ""),
                        "url_other_format": book.get("url_other_format", ""),
                        "sections": book.get("sections", []),
                    })
        except Exception:
            pass
        # Fallback: page scraping
        if not metadata.get("title"):
            try:
                from bs4 import BeautifulSoup
                resp = requests.get(url, headers=self.headers, timeout=self.timeout)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    title_tag = soup.find("h1", class_="book-title")
                    if title_tag:
                        metadata["title"] = title_tag.get_text(strip=True)
                    dl_btn = soup.find("a", href=re.compile(r'\.zip'))
                    if dl_btn:
                        metadata["url_zip_file"] = dl_btn.get("href", "")
            except ImportError:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid LibriVox URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "mp3")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            title = metadata.get("title") or "librivox_book"
            if quality == "zip" and metadata.get("url_zip_file"):
                zip_url = metadata["url_zip_file"]
                filename = self._safe_filename(f"{title}.zip")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(zip_url, headers=self.headers, stream=True, timeout=self.timeout * 5)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
            else:
                # Download chapters individually
                sections = metadata.get("sections", [])
                total_size = 0
                for i, section in enumerate(sections):
                    listen_url = section.get("listen_url", "")
                    if not listen_url:
                        continue
                    ext = "mp3" if quality == "mp3" else "ogg"
                    if ".ogg" in listen_url:
                        ext = "ogg"
                    fname = self._safe_filename(f"{title}_ch{i+1:03d}.{ext}")
                    fpath = os.path.join(out_dir, fname)
                    try:
                        resp = requests.get(listen_url, headers=self.headers, stream=True, timeout=self.timeout)
                        with open(fpath, "wb") as f:
                            for chunk in resp.iter_content(8192):
                                f.write(chunk)
                        total_size += os.path.getsize(fpath)
                    except Exception:
                        continue
                result.file_path = os.path.abspath(out_dir)
                result.filename = f"{title}_audiobook"
                result.file_size = total_size
            result.content_type = "audio/mpeg" if quality != "zip" else "application/zip"
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
        name="librivox", platform="librivox",
        description="LibriVox audiobook downloader: MP3/OGG chapters, ZIP archives, metadata.",
        supported_formats=LibriVoxDownloader.SUPPORTED_FORMATS,
        supported_qualities=LibriVoxDownloader.SUPPORTED_QUALITIES,
        max_concurrent=2, priority=DownloadPriority.LOW,
    )
    return ("librivox", skill)
