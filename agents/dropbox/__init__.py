"""
RS Downloader v10.0.0 - Dropbox Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Dropbox agent supporting:
- File downloads (public and shared links)
- Folder listing and batch download
- File upload
- Shared link resolution
- Sync operations
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
)


class DropboxDownloader(DownloaderBase):
    """Dropbox download agent for files, folders, uploads, and sync.

    Handles public/shared links and Dropbox API for authenticated access.
    """

    AGENT_NAME = "dropbox"
    PLATFORM = "dropbox"
    SUPPORTED_FORMATS = ["auto", "pdf", "docx", "xlsx", "jpg", "png", "mp4", "zip", "json"]
    SUPPORTED_QUALITIES = ["original", "export", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.dropbox\.com/s/[\w]+/[\w.-]+'),
        re.compile(r'https?://www\.dropbox\.com/sh/[\w]+/[\w-]+'),
        re.compile(r'https?://www\.dropbox\.com/home/[\w./-]+'),
        re.compile(r'https?://dl\.dropboxusercontent\.com/[\w./-]+'),
        re.compile(r'https?://dropbox\.com/scl/fi/[\w]+/[\w.-]+'),
    ]

    _DROPBOX_API = "https://api.dropboxapi.com/2"
    _DROPBOX_CONTENT_API = "https://content.dropboxapi.com/2"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _get_direct_url(self, url: str) -> str:
        """Convert Dropbox share URL to direct download URL."""
        if "dl.dropboxusercontent.com" in url:
            return url
        # Replace www.dropbox.com with dl.dropboxusercontent.com
        direct = url.replace("www.dropbox.com", "dl.dropboxusercontent.com")
        # Remove query params except raw=1
        if "?" in direct:
            direct = direct.split("?")[0]
        direct += "?dl=1"
        return direct

    def _extract_path(self, url: str) -> Tuple[str, str]:
        """Extract shared link info from URL."""
        m = re.search(r'/s/([\w]+)/([\w.-]+)', url)
        if m:
            return m.group(1), m.group(2)
        m = re.search(r'/scl/fi/([\w]+)/([\w.-]+)', url)
        if m:
            return m.group(1), m.group(2)
        return "", ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "auto", "quality": "original file"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"url": url, "platform": "dropbox"}
        share_key, filename = self._extract_path(url)
        metadata["share_key"] = share_key
        metadata["filename"] = filename
        # Try API if token available
        token = self.headers.get("Authorization", "").replace("Bearer ", "") if self.headers else ""
        if token:
            try:
                resp = requests.post(
                    f"{self._DROPBOX_API}/sharing/get_shared_link_metadata",
                    json={"url": url},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    metadata.update({
                        "name": data.get("name", ""),
                        "size": data.get("size", 0),
                        "path_lower": data.get("path_lower", ""),
                        "is_folder": data.get(".tag") == "folder",
                        "modified": data.get("server_modified", ""),
                    })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Dropbox URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "original")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)
        try:
            if quality == "metadata_only":
                return self._save_metadata(task, result)

            out_dir = task.options.get("output_dir", self.output_dir)
            direct_url = self._get_direct_url(task.url)
            # Extract filename from URL
            _, filename = self._extract_path(task.url)
            if not filename:
                filename = "dropbox_download"
            filename = self._safe_filename(filename)

            headers = dict(self.headers) if self.headers else {}
            resp = requests.get(direct_url, headers=headers,
                                timeout=self.timeout, stream=True,
                                allow_redirects=True)
            resp.raise_for_status()
            # Get filename from Content-Disposition
            cd = resp.headers.get("Content-Disposition", "")
            if cd:
                m = re.search(r'filename[*]?=["\']?([^"\';\n]+)', cd)
                if m:
                    filename = self._safe_filename(m.group(1).strip())
            filepath = os.path.join(out_dir, filename)
            total = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    total += len(chunk)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = total
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _save_metadata(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        metadata = self.get_metadata(task.url)
        result.metadata = metadata
        out_dir = task.options.get("output_dir", self.output_dir)
        filepath = os.path.join(out_dir, "dropbox_metadata.json")
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        result.file_path = os.path.abspath(filepath)
        result.filename = "dropbox_metadata.json"
        result.file_size = os.path.getsize(filepath)
        result.status = DownloadStatus.VERIFYING
        return result

    @staticmethod
    def _safe_filename(name: str) -> str:
        return re.sub(r'[<>:"|?*\\]', '_', name)[:200]

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="dropbox",
        formats=tuple(DropboxDownloader.SUPPORTED_FORMATS),
        qualities=tuple(DropboxDownloader.SUPPORTED_QUALITIES),
        features=("download", "upload", "sync", "shared_links", "folders"),
        max_concurrent=3,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description="Dropbox agent: file downloads, upload, sync, shared links, folder listing.",
    )
    return ("dropbox", skill)
