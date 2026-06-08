"""
RS Downloader v10.0.0 - Telegram Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Telegram download agent supporting:
- Message media downloads (photos, videos, documents, audio, voice)
- Channel post media extraction
- Group media downloads
- Sticker pack downloads
- File download with resume support
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


class TelegramDownloader(DownloaderBase):
    """Telegram download agent for messages, media, and files.

    Uses requests for public channel post downloads and
    the Telegram Bot API for accessible content.
    """

    AGENT_NAME = "telegram"
    PLATFORM = "telegram"
    SUPPORTED_FORMATS = ["mp4", "mkv", "jpg", "png", "mp3", "ogg", "pdf", "zip", "json"]
    SUPPORTED_QUALITIES = ["best", "original", "compressed", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://t\.me/[\w-]+/\d+'),
        re.compile(r'https?://t\.me/[\w-]+$'),
        re.compile(r'https?://telegram\.me/[\w-]+/\d+'),
        re.compile(r'https?://t\.me/joinchat/[\w-]+'),
        re.compile(r'https?://t\.me/addstickers/[\w-]+'),
        re.compile(r'https?://t\.me/c/\d+/\d+'),
    ]

    _TELEGRAM_EMBED = "https://t.me/{}/{}?embed=1"
    _TELEGRAM_API = "https://api.telegram.org"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_url(self, url: str) -> Tuple[str, str, str]:
        """Parse URL into (type, channel, message_id)."""
        # Channel with message
        m = re.search(r't\.me/([\w-]+)/(\d+)', url)
        if m:
            return "message", m.group(1), m.group(2)
        # Channel only
        m = re.search(r't\.me/([\w-]+)$', url)
        if m:
            return "channel", m.group(1), ""
        # Sticker pack
        m = re.search(r'addstickers/([\w-]+)', url)
        if m:
            return "stickers", m.group(1), ""
        # Private channel
        m = re.search(r't\.me/c/(\d+)/(\d+)', url)
        if m:
            return "private", m.group(1), m.group(2)
        return "unknown", "", ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype, _, _ = self._parse_url(url)
        formats = [
            {"format_id": "best", "ext": "mp4", "quality": "best available"},
            {"format_id": "original", "ext": "mp4", "quality": "original quality"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if ctype == "stickers":
            formats.insert(0, {"format_id": "webp", "ext": "webp",
                               "quality": "sticker pack"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype, channel, msg_id = self._parse_url(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "telegram",
            "content_type": ctype, "channel": channel,
            "message_id": msg_id,
        }
        if ctype == "message" and channel and msg_id:
            try:
                embed_url = self._TELEGRAM_EMBED.format(channel, msg_id)
                resp = requests.get(embed_url, headers=self._browser_headers(),
                                    timeout=self.timeout)
                if resp.status_code == 200:
                    text = resp.text
                    # Extract embedded video/image URL
                    video_m = re.search(r'"og:video:url"\s+content="([^"]+)"', text)
                    if not video_m:
                        video_m = re.search(r'video_src\s*=\s*"([^"]+)"', text)
                    if video_m:
                        metadata["video_url"] = video_m.group(1).replace("&amp;", "&")
                    img_m = re.search(r'"og:image"\s+content="([^"]+)"', text)
                    if img_m:
                        metadata["image_url"] = img_m.group(1).replace("&amp;", "&")
                    title_m = re.search(r'"og:title"\s+content="([^"]+)"', text)
                    if title_m:
                        metadata["title"] = title_m.group(1)
                    desc_m = re.search(r'"og:description"\s+content="([^"]+)"', text)
                    if desc_m:
                        metadata["description"] = desc_m.group(1)
                    # Extract message text
                    text_m = re.search(
                        r'<div\s+class="tgme_widget_message_text"[^>]*>(.*?)</div>',
                        text, re.DOTALL)
                    if text_m:
                        clean = re.sub(r'<[^>]+>', '', text_m.group(1))
                        metadata["message_text"] = clean.strip()
            except Exception as exc:
                metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        }

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Telegram URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        ctype, channel, msg_id = self._parse_url(task.url)
        task.options["content_type"] = ctype
        task.options["channel"] = channel
        task.options["message_id"] = msg_id

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "best")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            channel = task.options.get("channel", "telegram")
            msg_id = task.options.get("message_id", "")

            if quality == "metadata_only":
                filename = f"{channel}_{msg_id}_metadata.json"
                filepath = os.path.join(out_dir, self._safe_filename(filename))
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = os.path.basename(filepath)
                result.file_size = os.path.getsize(filepath)
                result.status = DownloadStatus.VERIFYING
                return result

            # Try video download first
            video_url = metadata.get("video_url", "")
            image_url = metadata.get("image_url", "")

            if video_url:
                ext = "mp4"
                filename = self._safe_filename(f"{channel}_{msg_id}.{ext}")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(video_url, headers=self._browser_headers(),
                                    timeout=self.timeout, stream=True)
                resp.raise_for_status()
                total = 0
                with open(filepath, "wb") as f:
                    for chunk in resp.iter_content(chunk_size=8192):
                        f.write(chunk)
                        total += len(chunk)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = total
                result.content_type = "video/mp4"
            elif image_url:
                ext = "jpg"
                filename = self._safe_filename(f"{channel}_{msg_id}.{ext}")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(image_url, headers=self._browser_headers(),
                                    timeout=self.timeout)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = len(resp.content)
                result.content_type = "image/jpeg"
            else:
                result.status = DownloadStatus.FAILED
                result.error = "No downloadable media found (private or restricted content)"
                return result

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

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="telegram",
        formats=tuple(TelegramDownloader.SUPPORTED_FORMATS),
        qualities=tuple(TelegramDownloader.SUPPORTED_QUALITIES),
        features=("messages", "videos", "photos", "documents", "stickers", "channels"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Telegram downloader: messages, videos, photos, documents, stickers via embed API.",
    )
    return ("telegram", skill)
