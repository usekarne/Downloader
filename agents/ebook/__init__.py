"""
RS Downloader v10.0.0 - Ebook Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NIXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Generic ebook download agent supporting:
- EPUB, PDF, MOBI format downloads
- Direct link resolution
- Metadata extraction from ebook files
- Format detection
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


class EbookDownloader(DownloaderBase):
    """Generic ebook download agent for EPUB, PDF, and MOBI files."""

    AGENT_NAME = "ebook"
    PLATFORM = "ebook"
    SUPPORTED_FORMATS = ["epub", "pdf", "mobi", "azw3", "djvu"]
    SUPPORTED_QUALITIES = ["original", "compressed"]

    _URL_PATTERNS = [
        re.compile(r'https?://[\w./-]+\.epub$'),
        re.compile(r'https?://[\w./-]+\.pdf$'),
        re.compile(r'https?://[\w./-]+\.mobi$'),
        re.compile(r'https?://[\w.-]+/ebook/[\w-]+'),
        re.compile(r'https?://[\w.-]+/download/[\w.-]+\.(epub|pdf|mobi)'),
    ]
    _EBOOK_EXTS = {".epub", ".pdf", ".mobi", ".azw3", ".djvu"}

    def validate_url(self, url: str) -> bool:
        if any(p.match(url) for p in self._URL_PATTERNS):
            return True
        # Check if URL ends with ebook extension
        from urllib.parse import urlparse
        path = urlparse(url).path.lower()
        return any(path.endswith(ext) for ext in self._EBOOK_EXTS)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        from urllib.parse import urlparse
        path = urlparse(url).path.lower()
        ext = Path(path).suffix.lower()
        if ext in self._EBOOK_EXTS:
            return [{"format_id": "original", "ext": ext.lstrip("."), "quality": "original file"}]
        return [
            {"format_id": "epub", "ext": "epub", "quality": "EPUB"},
            {"format_id": "pdf", "ext": "pdf", "quality": "PDF"},
            {"format_id": "mobi", "ext": "mobi", "quality": "MOBI/Kindle"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "ebook", "url": url}
        try:
            resp = requests.head(url, headers=self.headers,
                                 proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                                 timeout=self.timeout)
            if resp.status_code == 200:
                metadata["content_type"] = resp.headers.get("Content-Type", "")
                metadata["file_size"] = int(resp.headers.get("Content-Length", "0"))
                cd = resp.headers.get("Content-Disposition", "")
                if cd:
                    fn_match = re.search(r'filename="?([^";\s]+)"?', cd)
                    if fn_match:
                        metadata["filename"] = fn_match.group(1)
        except Exception:
            pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid ebook URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

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
            out_dir = task.options.get("output_dir", self.output_dir)
            # Determine filename
            filename = metadata.get("filename") or suggest_filename(url=task.url)
            if not any(filename.lower().endswith(ext) for ext in self._EBOOK_EXTS):
                from urllib.parse import urlparse
                path = urlparse(task.url).path.lower()
                ext = Path(path).suffix.lower()
                if ext in self._EBOOK_EXTS:
                    filename = f"{Path(filename).stem}{ext}"
            filename = self._safe_filename(filename)
            filepath = os.path.join(out_dir, filename)
            resp = requests.get(task.url, headers=self.headers, stream=True,
                                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                                timeout=self.timeout * 5)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                downloaded = 0
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    self._speed_tracker.update(downloaded)
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
        name="ebook", platform="ebook",
        description="Ebook downloader: EPUB, PDF, MOBI, direct links, metadata extraction.",
        supported_formats=EbookDownloader.SUPPORTED_FORMATS,
        supported_qualities=EbookDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("ebook", skill)
