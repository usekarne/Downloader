"""
RS Downloader v10.0.0 - IPFS Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

IPFS download agent supporting:
- Content downloads via IPFS gateways
- CID-based content resolution
- Multiple gateway fallback
- IPFS Companion integration
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


class IPFSDownloader(DownloaderBase):
    """IPFS download agent for content addressed via CIDs and gateways."""

    AGENT_NAME = "ipfs"
    PLATFORM = "ipfs"
    SUPPORTED_FORMATS = ["*"]
    SUPPORTED_QUALITIES = ["original"]

    _URL_PATTERNS = [
        re.compile(r'https?://ipfs\.io/ipfs/([\w]+)'),
        re.compile(r'ipfs://([\w]+)'),
        re.compile(r'https?://[\w.]+/ipfs/([\w]+)'),
        re.compile(r'https?://dweb\.link/ipfs/([\w]+)'),
    ]
    _GATEWAYS = [
        "https://ipfs.io/ipfs/",
        "https://dweb.link/ipfs/",
        "https://cloudflare-ipfs.com/ipfs/",
        "https://gateway.pinata.cloud/ipfs/",
        "https://ipfs.eth.aragon.network/ipfs/",
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS) or url.startswith("ipfs://")

    def _extract_cid(self, url: str) -> str:
        match = re.search(r'/ipfs/([\w]+)', url)
        if match:
            return match.group(1)
        if url.startswith("ipfs://"):
            return url[7:].split("/")[0]
        return ""

    def _resolve_gateway_url(self, cid: str, path: str = "") -> List[str]:
        """Generate URLs for all known gateways."""
        return [f"{gateway}{cid}{path}" for gateway in self._GATEWAYS]

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [{"format_id": "original", "ext": "*", "quality": "original content"}]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "ipfs", "url": url}
        cid = self._extract_cid(url)
        if cid:
            metadata["cid"] = cid
            # Try to get metadata from first available gateway
            gateway_urls = self._resolve_gateway_url(cid)
            for gw_url in gateway_urls[:2]:
                try:
                    resp = requests.head(gw_url, headers=self.headers, timeout=self.timeout)
                    if resp.status_code == 200:
                        metadata["content_type"] = resp.headers.get("Content-Type", "")
                        metadata["file_size"] = int(resp.headers.get("Content-Length", "0"))
                        metadata["gateway_used"] = gw_url
                        break
                except Exception:
                    continue
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid IPFS URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        task.options["cid"] = self._extract_cid(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        cid = task.options.get("cid", "")
        if not cid:
            result.status = DownloadStatus.FAILED
            result.error = "Could not extract CID from URL"
            return result
        out_dir = task.options.get("output_dir", self.output_dir)
        gateway_urls = self._resolve_gateway_url(cid)
        downloaded = False
        for gw_url in gateway_urls:
            try:
                resp = requests.get(gw_url, headers=self.headers, stream=True, timeout=self.timeout * 3)
                if resp.status_code == 200:
                    filename = suggest_filename(url=gw_url, content_type=resp.headers.get("Content-Type", ""))
                    filename = self._safe_filename(filename)
                    filepath = os.path.join(out_dir, filename)
                    total = int(resp.headers.get("Content-Length", "0"))
                    bytes_written = 0
                    with open(filepath, "wb") as f:
                        for chunk in resp.iter_content(8192):
                            f.write(chunk)
                            bytes_written += len(chunk)
                            if total > 0:
                                self._speed_tracker.update(bytes_written)
                    result.file_path = os.path.abspath(filepath)
                    result.filename = filename
                    result.file_size = os.path.getsize(filepath)
                    result.content_type = detect_content_type(filename=filename)
                    result.metadata["gateway_used"] = gw_url
                    downloaded = True
                    break
            except Exception:
                continue
        if downloaded:
            result.status = DownloadStatus.VERIFYING
        else:
            result.status = DownloadStatus.FAILED
            result.error = "Failed to download from all IPFS gateways"
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
        name="ipfs", platform="ipfs",
        description="IPFS downloader: CID resolution, multi-gateway fallback, decentralized content.",
        supported_formats=IPFSDownloader.SUPPORTED_FORMATS,
        supported_qualities=IPFSDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.BACKGROUND,
    )
    return ("ipfs", skill)
