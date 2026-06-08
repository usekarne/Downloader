"""
RS Downloader v10.0.0 - Tor (.onion) Download Agent
======================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Tor download agent supporting:
- .onion site downloads via SOCKS proxy
- Tor integration for anonymous downloads
- Automatic Tor proxy detection
- File downloads from hidden services
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


class TorDownloader(DownloaderBase):
    """Tor download agent for .onion sites via SOCKS proxy."""

    AGENT_NAME = "tor"
    PLATFORM = "tor"
    SUPPORTED_FORMATS = ["*"]
    SUPPORTED_QUALITIES = ["original"]

    _URL_PATTERNS = [
        re.compile(r'https?://[\w-]+\.onion/[\w./-]*'),
        re.compile(r'https?://[\w-]+\.onion'),
    ]
    _DEFAULT_SOCKS_PROXY = "socks5h://127.0.0.1:9050"
    _TOR_CHECK_URL = "https://check.torproject.org/api/ip"

    def validate_url(self, url: str) -> bool:
        return ".onion" in url

    def _get_tor_session(self) -> Any:
        """Create a requests session configured for Tor SOCKS proxy."""
        import requests
        session = requests.Session()
        tor_proxy = self.proxy or self.memory.get("socks_proxy", self._DEFAULT_SOCKS_PROXY)
        session.proxies = {
            "http": tor_proxy,
            "https": tor_proxy,
        }
        session.headers.update(self.headers)
        return session

    def _check_tor_connection(self) -> bool:
        """Check if Tor connection is working."""
        try:
            session = self._get_tor_session()
            resp = session.get(self._TOR_CHECK_URL, timeout=15)
            if resp.status_code == 200:
                return resp.json().get("IsTor", False)
        except Exception:
            pass
        return False

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [{"format_id": "original", "ext": "*", "quality": "original file"}]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "tor", "url": url}
        try:
            session = self._get_tor_session()
            resp = session.head(url, timeout=self.timeout)
            if resp.status_code == 200:
                metadata["content_type"] = resp.headers.get("Content-Type", "")
                metadata["file_size"] = int(resp.headers.get("Content-Length", "0"))
                cd = resp.headers.get("Content-Disposition", "")
                if cd:
                    fn = re.search(r'filename="?([^";\s]+)"?', cd)
                    if fn:
                        metadata["filename"] = fn.group(1)
                metadata["tor_connected"] = True
            else:
                metadata["status_code"] = resp.status_code
                metadata["tor_connected"] = True
        except Exception as exc:
            metadata["error"] = str(exc)
            metadata["tor_connected"] = self._check_tor_connection()
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid .onion URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["socks_proxy"] = self.proxy or self.memory.get("socks_proxy", self._DEFAULT_SOCKS_PROXY)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            session = self._get_tor_session()
            out_dir = task.options.get("output_dir", self.output_dir)
            filename = suggest_filename(url=task.url)
            filename = self._safe_filename(filename)
            filepath = os.path.join(out_dir, filename)
            resp = session.get(task.url, stream=True, timeout=self.timeout * 3)
            resp.raise_for_status()
            # Re-derive filename from Content-Disposition if available
            cd = resp.headers.get("Content-Disposition", "")
            if cd:
                fn = re.search(r'filename="?([^";\s]+)"?', cd)
                if fn:
                    filename = self._safe_filename(fn.group(1))
                    filepath = os.path.join(out_dir, filename)
            total = int(resp.headers.get("Content-Length", "0"))
            downloaded = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
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
        name="tor", platform="tor",
        description="Tor downloader: .onion sites, SOCKS proxy, anonymous downloads, Tor integration.",
        supported_formats=TorDownloader.SUPPORTED_FORMATS,
        supported_qualities=TorDownloader.SUPPORTED_QUALITIES,
        max_concurrent=2, priority=DownloadPriority.BACKGROUND,
    )
    return ("tor", skill)
