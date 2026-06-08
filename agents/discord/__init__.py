"""
RS Downloader v10.0.0 - Discord Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Discord download agent supporting:
- Attachment downloads (images, videos, documents)
- CDN media downloads
- Message media extraction
- Emoji/sticker downloads
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


class DiscordDownloader(DownloaderBase):
    """Discord download agent for attachments, CDN media, and message content."""

    AGENT_NAME = "discord"
    PLATFORM = "discord"
    SUPPORTED_FORMATS = ["mp4", "webm", "jpg", "png", "gif", "webp", "pdf", "zip", "mp3", "ogg", "json"]
    SUPPORTED_QUALITIES = ["original", "preview", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://cdn\.discordapp\.com/attachments/\d+/\d+/[\w.-]+'),
        re.compile(r'https?://media\.discordapp\.net/attachments/\d+/\d+/[\w.-]+'),
        re.compile(r'https?://cdn\.discordapp\.com/emojis/\d+'),
        re.compile(r'https?://discord\.com/channels/\d+/\d+/\d+'),
        re.compile(r'https?://discordapp\.com/channels/\d+/\d+/\d+'),
        re.compile(r'https?://cdn\.discordapp\.com/stickers/[\w.-]+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_type(self, url: str) -> str:
        if "/attachments/" in url:
            return "attachment"
        elif "/emojis/" in url:
            return "emoji"
        elif "/stickers/" in url:
            return "sticker"
        elif "/channels/" in url:
            return "message"
        return "unknown"

    def _extract_filename(self, url: str) -> str:
        """Extract filename from Discord CDN URL."""
        m = re.search(r'/attachments/\d+/\d+/([\w.-]+)', url)
        if m:
            return m.group(1)
        m = re.search(r'/emojis/(\d+)', url)
        if m:
            return f"emoji_{m.group(1)}.png"
        m = re.search(r'/stickers/([\w.-]+)', url)
        if m:
            return f"sticker_{m.group(1)}.png"
        return "discord_download"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype = self._detect_type(url)
        formats = [
            {"format_id": "original", "ext": "auto", "quality": "original file"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if ctype == "emoji":
            formats.insert(0, {"format_id": "png", "ext": "png", "quality": "emoji PNG"})
            formats.insert(1, {"format_id": "gif", "ext": "gif", "quality": "emoji GIF"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype = self._detect_type(url)
        filename = self._extract_filename(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "discord",
            "content_type": ctype, "filename": filename,
        }
        try:
            # Head request for file info
            resp = requests.head(url, timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                metadata["content_type_header"] = resp.headers.get("Content-Type", "")
                content_length = resp.headers.get("Content-Length", "0")
                metadata["file_size"] = int(content_length) if content_length.isdigit() else 0
                metadata["final_url"] = str(resp.url)
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Discord URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["content_type"] = self._detect_type(task.url)

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
            filename = self._safe_filename(
                metadata.get("filename", "discord_file"))

            if quality == "metadata_only":
                filepath = os.path.join(out_dir, f"{filename}_metadata.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = os.path.basename(filepath)
                result.file_size = os.path.getsize(filepath)
                result.status = DownloadStatus.VERIFYING
                return result

            # Handle emoji format selection
            download_url = task.url
            ctype = task.options.get("content_type", "")
            if ctype == "emoji":
                if quality == "gif":
                    download_url = task.url.split("?")[0] + ".gif?size=4096"
                else:
                    download_url = task.url.split("?")[0] + ".png?size=4096"
                filename = filename.rsplit(".", 1)[0] + (
                    ".gif" if quality == "gif" else ".png")

            filepath = os.path.join(out_dir, filename)
            resp = requests.get(download_url, timeout=self.timeout, stream=True)
            resp.raise_for_status()
            total = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=8192):
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
        platform="discord",
        formats=tuple(DiscordDownloader.SUPPORTED_FORMATS),
        qualities=tuple(DiscordDownloader.SUPPORTED_QUALITIES),
        features=("attachments", "cdn", "emojis", "stickers", "messages"),
        max_concurrent=5,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description="Discord downloader: attachments, CDN media, emojis, stickers via requests.",
    )
    return ("discord", skill)
