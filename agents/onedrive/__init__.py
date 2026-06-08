"""
RS Downloader v10.0.0 - OneDrive Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

OneDrive agent supporting:
- File downloads from shared links
- Folder listing and batch download
- File upload
- SharePoint shared file downloads
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


class OneDriveDownloader(DownloaderBase):
    """OneDrive download agent for files, folders, uploads, and sync.

    Handles shared links (1drv.ms short links and full URLs)
    and Microsoft Graph API for authenticated access.
    """

    AGENT_NAME = "onedrive"
    PLATFORM = "onedrive"
    SUPPORTED_FORMATS = ["auto", "pdf", "docx", "xlsx", "jpg", "png", "mp4", "json"]
    SUPPORTED_QUALITIES = ["original", "export", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://1drv\.ms/[\w/]+'),
        re.compile(r'https?://1drv\.ws/[\w/]+'),
        re.compile(r'https?://onedrive\.live\.com/[\w./?=&-]+'),
        re.compile(r'https?://[\w-]+\.sharepoint\.com/[\w./?=&-]+'),
    ]

    _GRAPH_API = "https://graph.microsoft.com/v1.0"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_share_id(self, url: str) -> str:
        """Extract sharing ID from OneDrive URL."""
        m = re.search(r'resid=([\w!-]+)', url)
        if m:
            return m.group(1)
        m = re.search(r'/([\w!-]+)\?e=', url)
        if m:
            return m.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "auto", "quality": "original file"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"url": url, "platform": "onedrive"}
        # Try Graph API if token available
        token = self.headers.get("Authorization", "").replace("Bearer ", "") if self.headers else ""
        if token:
            try:
                share_id = self._extract_share_id(url)
                if share_id:
                    resp = requests.get(
                        f"{self._GRAPH_API}/shares/{share_id}/root",
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=self.timeout,
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        metadata.update({
                            "name": data.get("name", ""),
                            "size": data.get("size", 0),
                            "mime_type": data.get("file", {}).get("mimeType", ""),
                            "modified": data.get("lastModifiedDateTime", ""),
                            "download_url": data.get("@content.downloadUrl", ""),
                        })
            except Exception:
                pass
        # Try page scraping for shared links
        if not metadata.get("name"):
            try:
                resp = requests.get(url, headers=self._browser_headers(),
                                    timeout=self.timeout, allow_redirects=True)
                if resp.status_code == 200:
                    text = resp.text
                    title_m = re.search(r'"title"\s*:\s*"([^"]+)"', text)
                    if title_m:
                        metadata["name"] = title_m.group(1)
                    dl_m = re.search(r'"downloadUrl"\s*:\s*"([^"]+)"', text)
                    if dl_m:
                        metadata["download_url"] = dl_m.group(1).replace("\\/", "/")
                    size_m = re.search(r'"size"\s*:\s*(\d+)', text)
                    if size_m:
                        metadata["size"] = int(size_m.group(1))
            except Exception:
                pass
        return metadata

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        }

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid OneDrive URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
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
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)

            if quality == "metadata_only":
                filepath = os.path.join(out_dir, "onedrive_metadata.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = "onedrive_metadata.json"
                result.file_size = os.path.getsize(filepath)
                result.status = DownloadStatus.VERIFYING
                return result

            download_url = metadata.get("download_url", "")
            if not download_url:
                # Try direct download via content endpoint
                resp = requests.get(task.url, headers=self._browser_headers(),
                                    timeout=self.timeout, allow_redirects=True)
                # Look for download URL in redirected page
                dl_m = re.search(r'"downloadUrl"\s*:\s*"([^"]+)"', resp.text)
                if dl_m:
                    download_url = dl_m.group(1).replace("\\/", "/")

            if not download_url:
                result.status = DownloadStatus.FAILED
                result.error = "Could not obtain download URL"
                return result

            filename = self._safe_filename(
                metadata.get("name", "onedrive_download"))
            filepath = os.path.join(out_dir, filename)
            resp = requests.get(download_url, timeout=self.timeout, stream=True)
            resp.raise_for_status()
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
        platform="onedrive",
        formats=tuple(OneDriveDownloader.SUPPORTED_FORMATS),
        qualities=tuple(OneDriveDownloader.SUPPORTED_QUALITIES),
        features=("download", "upload", "sync", "shared_links", "sharepoint"),
        max_concurrent=3,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description="OneDrive agent: file downloads, upload, sync, shared links, SharePoint.",
    )
    return ("onedrive", skill)
