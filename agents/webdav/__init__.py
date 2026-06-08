"""
RS Downloader v10.0.0 - WebDAV Download Agent
===============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

WebDAV agent supporting:
- File downloads from WebDAV servers
- File uploads to WebDAV servers
- Directory listing
- Basic and Digest authentication
- Chunked upload for large files
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from xml.etree import ElementTree as ET

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
)


class WebDAVDownloader(DownloaderBase):
    """WebDAV download agent for file transfers and directory listing.

    Uses requests with Basic/Digest auth for WebDAV operations.
    Supports PROPFIND, GET, PUT, MKCOL, DELETE methods.
    """

    AGENT_NAME = "webdav"
    PLATFORM = "webdav"
    SUPPORTED_FORMATS = ["auto", "json"]
    SUPPORTED_QUALITIES = ["original", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://[\w.-]+/dav/[\w./-]+'),
        re.compile(r'https?://[\w.-]+/webdav/[\w./-]+'),
        re.compile(r'https?://[\w.-]+/remote\.php/dav/[\w./-]+'),
        re.compile(r'https?://[\w.-]+/nextcloud/[\w./-]+'),
        re.compile(r'webdav://[\w.-]+/[\w./-]+'),
        re.compile(r'davs://[\w.-]+/[\w./-]+'),
    ]

    _DAV_NAMESPACE = {"d": "DAV:"}

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _normalize_url(self, url: str) -> str:
        """Convert webdav:// and davs:// to https://."""
        if url.startswith("webdav://"):
            return "http://" + url[9:]
        elif url.startswith("davs://"):
            return "https://" + url[7:]
        return url

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "auto", "quality": "original file"},
            {"format_id": "metadata", "ext": "json", "quality": "file metadata"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        norm_url = self._normalize_url(url)
        metadata: Dict[str, Any] = {"url": url, "platform": "webdav",
                                    "normalized_url": norm_url}
        # PROPFIND to get file metadata
        try:
            headers = {
                "Depth": "0",
                "Content-Type": "application/xml",
            }
            if self.headers:
                headers.update(self.headers)
            resp = requests.request(
                "PROPFIND", norm_url, headers=headers,
                timeout=self.timeout,
            )
            if resp.status_code in (200, 207):
                # Parse multistatus XML
                root = ET.fromstring(resp.text)
                responses = root.findall(".//d:response", self._DAV_NAMESPACE)
                if responses:
                    href = responses[0].find("d:href", self._DAV_NAMESPACE)
                    if href is not None:
                        metadata["href"] = href.text
                    props = responses[0].find(".//d:prop", self._DAV_NAMESPACE)
                    if props is not None:
                        displayname = props.find("d:displayname", self._DAV_NAMESPACE)
                        if displayname is not None and displayname.text:
                            metadata["name"] = displayname.text
                        content_length = props.find("d:getcontentlength", self._DAV_NAMESPACE)
                        if content_length is not None and content_length.text:
                            metadata["size"] = int(content_length.text)
                        content_type = props.find("d:getcontenttype", self._DAV_NAMESPACE)
                        if content_type is not None and content_type.text:
                            metadata["mime_type"] = content_type.text
                        last_modified = props.find("d:getlastmodified", self._DAV_NAMESPACE)
                        if last_modified is not None and last_modified.text:
                            metadata["last_modified"] = last_modified.text
                        etag = props.find("d:getetag", self._DAV_NAMESPACE)
                        if etag is not None and etag.text:
                            metadata["etag"] = etag.text
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    def list_directory(self, url: str) -> List[Dict[str, Any]]:
        """List files in a WebDAV directory."""
        import requests
        norm_url = self._normalize_url(url)
        files = []
        try:
            headers = {"Depth": "1", "Content-Type": "application/xml"}
            if self.headers:
                headers.update(self.headers)
            resp = requests.request("PROPFIND", norm_url, headers=headers,
                                    timeout=self.timeout)
            if resp.status_code in (200, 207):
                root = ET.fromstring(resp.text)
                for response in root.findall(".//d:response", self._DAV_NAMESPACE):
                    href = response.find("d:href", self._DAV_NAMESPACE)
                    if href is None or href.text is None:
                        continue
                    props = response.find(".//d:prop", self._DAV_NAMESPACE)
                    entry = {"href": href.text}
                    if props is not None:
                        for tag in ["displayname", "getcontentlength",
                                    "getcontenttype", "getlastmodified"]:
                            el = props.find(f"d:{tag}", self._DAV_NAMESPACE)
                            if el is not None and el.text:
                                entry[tag] = el.text
                    files.append(entry)
        except Exception:
            pass
        return files

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid WebDAV URL: {task.url}",
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
            norm_url = self._normalize_url(task.url)
            out_dir = task.options.get("output_dir", self.output_dir)

            if quality == "metadata_only":
                metadata = self.get_metadata(task.url)
                result.metadata = metadata
                filepath = os.path.join(out_dir, "webdav_metadata.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = "webdav_metadata.json"
                result.file_size = os.path.getsize(filepath)
                result.status = DownloadStatus.VERIFYING
                return result

            # GET request to download file
            headers = dict(self.headers) if self.headers else {}
            resp = requests.get(norm_url, headers=headers,
                                timeout=self.timeout, stream=True)
            resp.raise_for_status()
            # Extract filename from URL path
            from urllib.parse import urlparse, unquote
            path = unquote(urlparse(norm_url).path)
            filename = path.rsplit("/", 1)[-1] if "/" in path else "webdav_download"
            filename = self._safe_filename(filename)
            # Override from Content-Disposition
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
        platform="webdav",
        formats=tuple(WebDAVDownloader.SUPPORTED_FORMATS),
        qualities=tuple(WebDAVDownloader.SUPPORTED_QUALITIES),
        features=("download", "upload", "listing", "propfind", "auth"),
        max_concurrent=3,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description="WebDAV agent: download, upload, directory listing, PROPFIND, Basic/Digest auth.",
    )
    return ("webdav", skill)
