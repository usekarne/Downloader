"""
RS Downloader v10.0.0 - Project Gutenberg Download Agent
==========================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Project Gutenberg ebook downloader supporting:
- Multiple ebook formats (EPUB, Kindle, HTML, TXT, PDF)
- Metadata extraction
- Direct download from Gutenberg mirrors
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


class GutenbergDownloader(DownloaderBase):
    """Project Gutenberg download agent for free public domain ebooks."""

    AGENT_NAME = "gutenberg"
    PLATFORM = "gutenberg"
    SUPPORTED_FORMATS = ["epub", "kindle", "html", "txt", "pdf", "plucker"]
    SUPPORTED_QUALITIES = ["with_images", "no_images", "plain_text"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.gutenberg\.org/ebooks/(\d+)'),
        re.compile(r'https?://www\.gutenberg\.org/cache/epub/(\d+)/'),
        re.compile(r'https?://www\.gutenberg\.org/files/(\d+)/'),
    ]
    _MIRROR_BASE = "https://www.gutenberg.org"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_book_id(self, url: str) -> str:
        match = re.search(r'(?:ebooks|epub|files)/(\d+)', url)
        if match:
            return match.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "epub", "ext": "epub", "quality": "EPUB with images"},
            {"format_id": "epub_no_images", "ext": "epub", "quality": "EPUB no images"},
            {"format_id": "kindle", "ext": "mobi", "quality": "Kindle format"},
            {"format_id": "html", "ext": "html", "quality": "HTML"},
            {"format_id": "txt", "ext": "txt", "quality": "Plain text"},
            {"format_id": "pdf", "ext": "pdf", "quality": "PDF"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "gutenberg", "url": url}
        book_id = self._extract_book_id(url)
        if book_id:
            try:
                # Use the Gutenberg page to extract metadata
                resp = requests.get(
                    f"{self._MIRROR_BASE}/ebooks/{book_id}",
                    headers=self.headers,
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    title_match = re.search(r'<td.*?>(?:Title|Title:)</td>\s*<td>(.*?)</td>', resp.text, re.DOTALL)
                    if title_match:
                        metadata["title"] = title_match.group(1).strip()
                    author_match = re.search(r'<td.*?>(?:Author|Author:)</td>\s*<td>(.*?)</td>', resp.text, re.DOTALL)
                    if author_match:
                        metadata["author"] = author_match.group(1).strip()
                    # Extract download links
                    links = re.findall(r'href="(/(?:cache/)?epub/\d+/[\w.-]+)"', resp.text)
                    metadata["download_links"] = links
                    metadata["id"] = book_id
            except Exception:
                pass
        return metadata

    def _build_download_url(self, book_id: str, fmt: str) -> str:
        """Build download URL for a specific format."""
        base = f"{self._MIRROR_BASE}/cache/epub/{book_id}"
        url_map = {
            "epub": f"{base}/pg{book_id}-images.epub",
            "epub_no_images": f"{base}/pg{book_id}.epub",
            "kindle": f"{self._MIRROR_BASE}/files/{book_id}/{book_id}-h/{book_id}-h.htm",
            "html": f"{self._MIRROR_BASE}/files/{book_id}/{book_id}-h/{book_id}-h.htm",
            "txt": f"{self._MIRROR_BASE}/files/{book_id}/{book_id}-0.txt",
            "pdf": f"{base}/pg{book_id}.pdf",
        }
        return url_map.get(fmt, url_map.get("txt", ""))

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Gutenberg URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["book_id"] = self._extract_book_id(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        fmt = task.options.get("quality", "epub")
        book_id = task.options.get("book_id", "")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            download_url = self._build_download_url(book_id, fmt)
            if not download_url:
                download_url = f"{self._MIRROR_BASE}/files/{book_id}/{book_id}-0.txt"
                fmt = "txt"
            title = metadata.get("title") or f"gutenberg_{book_id}"
            ext_map = {"epub": "epub", "epub_no_images": "epub", "kindle": "mobi",
                       "html": "html", "txt": "txt", "pdf": "pdf"}
            ext = ext_map.get(fmt, "txt")
            filename = self._safe_filename(f"{title}.{ext}")
            filepath = os.path.join(task.options.get("output_dir", self.output_dir), filename)
            resp = requests.get(download_url, headers=self.headers, stream=True, timeout=self.timeout * 3)
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
        name="gutenberg", platform="gutenberg",
        description="Project Gutenberg ebook downloader: EPUB, Kindle, HTML, TXT, PDF formats.",
        supported_formats=GutenbergDownloader.SUPPORTED_FORMATS,
        supported_qualities=GutenbergDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.LOW,
    )
    return ("gutenberg", skill)
