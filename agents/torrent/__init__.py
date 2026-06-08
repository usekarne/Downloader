"""
RS Downloader v10.0.0 - Torrent Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Torrent download agent supporting:
- Magnet link handling
- .torrent file downloads
- DHT/PEX peer discovery
- Sequential downloading for media
- libtorrent-style approach via subprocess
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class TorrentDownloader(DownloaderBase):
    """Torrent download agent using aria2c/libtorrent-style approach."""

    AGENT_NAME = "torrent"
    PLATFORM = "torrent"
    SUPPORTED_FORMATS = ["torrent", "magnet", "*"]
    SUPPORTED_QUALITIES = ["best", "sequential", "fastest"]

    _URL_PATTERNS = [
        re.compile(r'magnet:\?xt=urn:btih:[\w]+'),
        re.compile(r'https?://[\w./-]+\.torrent$'),
        re.compile(r'file:///[\w./-]+\.torrent'),
    ]

    def validate_url(self, url: str) -> bool:
        if url.startswith("magnet:"):
            return url.startswith("magnet:?xt=urn:btih:")
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _find_downloader(self) -> str:
        """Find available torrent download tool."""
        for tool in ("aria2c", "transmission-cli", "ctorrent", "webtorrent"):
            import shutil
            path = shutil.which(tool)
            if path:
                return tool
        return "aria2c"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "all", "ext": "*", "quality": "all files"},
            {"format_id": "select", "ext": "*", "quality": "selected files"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "torrent", "url": url}
        if url.startswith("magnet:"):
            # Extract info hash
            hash_match = re.search(r'xt=urn:btih:([\w]+)', url)
            if hash_match:
                metadata["info_hash"] = hash_match.group(1)
            name_match = re.search(r'dn=([^&]+)', url)
            if name_match:
                metadata["name"] = name_match.group(1).replace("+", " ")
            tracker_matches = re.findall(r'tr=([^&]+)', url)
            metadata["trackers"] = tracker_matches
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid torrent/magnet URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        # Download .torrent file if it's a URL
        if task.url.startswith("http") and task.url.endswith(".torrent"):
            torrent_path = os.path.join(out_dir, "download.torrent")
            try:
                import requests
                resp = requests.get(task.url, headers=self.headers, timeout=self.timeout)
                with open(torrent_path, "wb") as f:
                    f.write(resp.content)
                task.options["torrent_file"] = torrent_path
            except Exception as exc:
                raise DownloadError(f"Failed to download .torrent file: {exc}", url=task.url, agent=self.AGENT_NAME)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        out_dir = task.options.get("output_dir", self.output_dir)
        quality = task.options.get("quality", "best")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        tool = self._find_downloader()
        try:
            if tool == "aria2c":
                result = self._download_aria2c(task, out_dir, result, quality)
            elif tool == "transmission-cli":
                result = self._download_transmission(task, out_dir, result)
            elif tool == "webtorrent":
                result = self._download_webtorrent(task, out_dir, result)
            else:
                result.status = DownloadStatus.FAILED
                result.error = f"No torrent client found. Install aria2c or transmission-cli."
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def _download_aria2c(self, task: DownloadTask, out_dir: str, result: DownloadResult, quality: str) -> DownloadResult:
        """Download via aria2c."""
        source = task.options.get("torrent_file", task.url)
        cmd = [
            "aria2c",
            "--dir", out_dir,
            "--seed-time=0",
            "--max-overall-download-limit=0",
            "--continue=true",
            "--max-tries=5",
            "--retry-wait=10",
        ]
        if quality == "sequential":
            cmd.append("--enable-dht=true")
        if self.proxy:
            cmd.extend(["--all-proxy", self.proxy])
        cmd.append(source)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=task.max_retries * 3600)
        if proc.returncode == 0:
            result.status = DownloadStatus.VERIFYING
            # Find downloaded files
            files = list(Path(out_dir).iterdir())
            media_files = [f for f in files if f.is_file() and not f.name.endswith(".torrent")]
            if media_files:
                largest = max(media_files, key=lambda f: f.stat().st_size)
                result.file_path = str(largest.resolve())
                result.filename = largest.name
                result.file_size = largest.stat().st_size
                total_size = sum(f.stat().st_size for f in media_files)
                result.metadata["total_size"] = total_size
                result.metadata["file_count"] = len(media_files)
        else:
            result.status = DownloadStatus.FAILED
            result.error = proc.stderr[:500] if proc.stderr else "aria2c download failed"
        return result

    def _download_transmission(self, task: DownloadTask, out_dir: str, result: DownloadResult) -> DownloadResult:
        """Download via transmission-cli."""
        source = task.options.get("torrent_file", task.url)
        cmd = ["transmission-cli", "--download-dir", out_dir, "--no-port-forward", source]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=task.max_retries * 3600)
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                files = [f for f in Path(out_dir).iterdir() if f.is_file()]
                if files:
                    largest = max(files, key=lambda f: f.stat().st_size)
                    result.file_path = str(largest.resolve())
                    result.filename = largest.name
                    result.file_size = largest.stat().st_size
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "transmission-cli failed"
        except subprocess.TimeoutExpired:
            result.status = DownloadStatus.FAILED
            result.error = "Torrent download timed out"
        return result

    def _download_webtorrent(self, task: DownloadTask, out_dir: str, result: DownloadResult) -> DownloadResult:
        """Download via webtorrent-cli."""
        source = task.options.get("torrent_file", task.url)
        cmd = ["webtorrent", "download", source, "--out", out_dir]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=task.max_retries * 3600)
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                files = [f for f in Path(out_dir).iterdir() if f.is_file()]
                if files:
                    largest = max(files, key=lambda f: f.stat().st_size)
                    result.file_path = str(largest.resolve())
                    result.filename = largest.name
                    result.file_size = largest.stat().st_size
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "webtorrent failed"
        except subprocess.TimeoutExpired:
            result.status = DownloadStatus.FAILED
            result.error = "Torrent download timed out"
        return result

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.file_path and os.path.isfile(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="torrent", platform="torrent",
        description="Torrent downloader: magnet links, .torrent files, aria2c/transmission/webtorrent.",
        supported_formats=TorrentDownloader.SUPPORTED_FORMATS,
        supported_qualities=TorrentDownloader.SUPPORTED_QUALITIES,
        max_concurrent=2, priority=DownloadPriority.LOW,
    )
    return ("torrent", skill)
