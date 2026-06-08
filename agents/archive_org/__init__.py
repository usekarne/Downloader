"""
RS Downloader v10.0.0 - Internet Archive Download Agent
==========================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Internet Archive download agent supporting:
- Book, audio, and video downloads
- Multi-file item downloads
- Metadata extraction via Archive.org API
- Multiple format selection
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


class ArchiveOrgDownloader(DownloaderBase):
    """Internet Archive download agent for books, audio, video."""

    AGENT_NAME = "archive_org"
    PLATFORM = "archive_org"
    SUPPORTED_FORMATS = ["pdf", "epub", "mp3", "ogg", "mp4", "zip", "txt", "mobi"]
    SUPPORTED_QUALITIES = ["original", "best"]

    _URL_PATTERNS = [
        re.compile(r'https?://archive\.org/details/([\w-]+)'),
        re.compile(r'https?://archive\.org/download/([\w-]+)'),
    ]
    _API_BASE = "https://archive.org/metadata"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_identifier(self, url: str) -> str:
        match = re.search(r'archive\.org/(?:details|download)/([\w-]+)', url)
        if match:
            return match.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        import requests
        identifier = self._extract_identifier(url)
        if identifier:
            try:
                resp = requests.get(
                    f"{self._API_BASE}/{identifier}",
                    params={"output": "json"},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    files = data.get("files", [])
                    return [
                        {"format_id": f.get("name", ""), "ext": f.get("name", "").rsplit(".", 1)[-1] if "." in f.get("name", "") else "",
                         "quality": f.get("format", "") or f.get("name", "")}
                        for f in files[:20]
                    ]
            except Exception:
                pass
        return [{"format_id": "original", "ext": "*", "quality": "original file"}]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "archive_org", "url": url}
        identifier = self._extract_identifier(url)
        if identifier:
            try:
                resp = requests.get(
                    f"{self._API_BASE}/{identifier}",
                    params={"output": "json"},
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    meta = data.get("metadata", {})
                    metadata.update({
                        "identifier": identifier,
                        "title": meta.get("title", [""])[0] if isinstance(meta.get("title"), list) else meta.get("title", ""),
                        "creator": meta.get("creator", [""])[0] if isinstance(meta.get("creator"), list) else meta.get("creator", ""),
                        "description": meta.get("description", [""])[0] if isinstance(meta.get("description"), list) else meta.get("description", ""),
                        "date": meta.get("date", [""])[0] if isinstance(meta.get("date"), list) else meta.get("date", ""),
                        "files": data.get("files", []),
                        "server": data.get("server", ""),
                        "dir": data.get("dir", ""),
                    })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Archive.org URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["identifier"] = self._extract_identifier(task.url)

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
            identifier = task.options.get("identifier", "")
            out_dir = task.options.get("output_dir", self.output_dir)
            server = metadata.get("server", "https://archive.org")
            directory = metadata.get("dir", f"/download/{identifier}")
            target_file = task.options.get("target_file", "")
            if target_file:
                download_url = f"{server}{directory}/{target_file}"
                filename = self._safe_filename(target_file)
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(download_url, headers=self.headers, stream=True, timeout=self.timeout * 5)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
            else:
                # Download main file (first suitable)
                files = metadata.get("files", [])
                priority_exts = ["pdf", "epub", "mp4", "mp3", "ogg", "zip"]
                chosen = None
                for ext in priority_exts:
                    for f in files:
                        name = f.get("name", "")
                        if name.lower().endswith(f".{ext}") and "_meta.xml" not in name:
                            chosen = f
                            break
                    if chosen:
                        break
                if not chosen and files:
                    chosen = files[0]
                if chosen:
                    fname = chosen.get("name", "")
                    download_url = f"{server}{directory}/{fname}"
                    filename = self._safe_filename(fname)
                    filepath = os.path.join(out_dir, filename)
                    resp = requests.get(download_url, headers=self.headers, stream=True, timeout=self.timeout * 5)
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
        name="archive_org", platform="archive_org",
        description="Internet Archive downloader: books, audio, video, multi-format, metadata API.",
        supported_formats=ArchiveOrgDownloader.SUPPORTED_FORMATS,
        supported_qualities=ArchiveOrgDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("archive_org", skill)
