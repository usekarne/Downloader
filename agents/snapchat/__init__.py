"""
RS Downloader v10.0.0 - Snapchat Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Snapchat downloader supporting:
- Story downloads (images, videos)
- Spotlight video downloads
- Snap metadata extraction
- Public profile content
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


class SnapchatDownloader(DownloaderBase):
    """Snapchat download agent for stories, spots, and public content."""

    AGENT_NAME = "snapchat"
    PLATFORM = "snapchat"
    SUPPORTED_FORMATS = ["mp4", "jpg", "png", "webp", "json"]
    SUPPORTED_QUALITIES = ["best", "worst", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://story\.snapchat\.com/s/[\w-]+'),
        re.compile(r'https?://www\.snapchat\.com/add/[\w.]+'),
        re.compile(r'https?://www\.snapchat\.com/spotlight/[\w-]+'),
        re.compile(r'https?://snapchat\.com/spotlight/[\w-]+'),
        re.compile(r'https?://t\.snapchat\.com/[\w-]+'),
    ]

    _SPOTLIGHT_API = "https://www.snapchat.com/spotlight/"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_content_type(self, url: str) -> str:
        if "/spotlight/" in url:
            return "spotlight"
        elif "/s/" in url or "story.snapchat.com" in url:
            return "story"
        elif "/add/" in url:
            return "profile"
        return "unknown"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype = self._detect_content_type(url)
        formats = [
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if ctype == "spotlight":
            formats.insert(0, {"format_id": "best", "ext": "mp4", "quality": "best video"})
        elif ctype == "story":
            formats.insert(0, {"format_id": "best", "ext": "mp4", "quality": "story media"})
            formats.insert(1, {"format_id": "image", "ext": "jpg", "quality": "story image"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype = self._detect_content_type(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "snapchat", "content_type": ctype}
        try:
            resp = requests.get(
                url, headers=self._browser_headers(),
                timeout=self.timeout, allow_redirects=True)
            if resp.status_code == 200:
                text = resp.text
                for tag, key in [("og:title", "title"), ("og:image", "thumbnail"),
                                 ("og:description", "description"),
                                 ("og:video", "video_url")]:
                    m = re.search(rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key] = m.group(1)
                # Extract story data from embedded JSON
                story_m = re.search(
                    r'"story"\s*:\s*({[^}]+})', text)
                if story_m:
                    try:
                        story_data = json.loads(story_m.group(1))
                        metadata["story_title"] = story_data.get("title", "")
                        metadata["story_duration"] = story_data.get("duration", 0)
                    except json.JSONDecodeError:
                        pass
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {
            "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                           "AppleWebKit/605.1.15 (KHTML, like Gecko) "
                           "Version/16.0 Mobile/15E148 Safari/604.1"),
        }

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(
                f"Invalid Snapchat URL: {task.url}",
                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["content_type"] = self._detect_content_type(task.url)

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

            video_url = metadata.get("video_url", "")
            thumbnail = metadata.get("thumbnail", "")

            if video_url and quality != "metadata_only":
                filename = self._safe_filename(
                    f"{metadata.get('title', 'snapchat')}.mp4")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(video_url, timeout=self.timeout)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = len(resp.content)
                result.content_type = "video/mp4"
            elif thumbnail and quality != "metadata_only":
                filename = self._safe_filename(
                    f"{metadata.get('title', 'snapchat')}.jpg")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(thumbnail, timeout=self.timeout)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = len(resp.content)
                result.content_type = "image/jpeg"
            else:
                filename = self._safe_filename(
                    f"{metadata.get('title', 'snapchat')}_metadata.json")
                filepath = os.path.join(out_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
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
        platform="snapchat",
        formats=tuple(SnapchatDownloader.SUPPORTED_FORMATS),
        qualities=tuple(SnapchatDownloader.SUPPORTED_QUALITIES),
        features=("stories", "spotlight", "metadata", "images", "videos"),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Snapchat downloader: stories, spotlight videos, metadata.",
    )
    return ("snapchat", skill)
