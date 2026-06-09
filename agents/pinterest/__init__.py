"""
RS Downloader v10.0.0 - Pinterest Download Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Pinterest downloader supporting:
- Pin image/video downloads
- Board scraping and batch download
- Story pin downloads
- Highest resolution image extraction
- Video pin downloads via yt-dlp
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
)

class PinterestDownloader(DownloaderBase):
    """Pinterest download agent for pins, boards, and videos."""

    AGENT_NAME = "pinterest"
    PLATFORM = "pinterest"
    SUPPORTED_FORMATS = ["jpg", "png", "gif", "mp4", "webp", "json"]
    SUPPORTED_QUALITIES = ["original", "large", "medium", "thumbnail", "best", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.pinterest\.com/pin/\d+'),
        re.compile(r'https?://www\.pinterest\.com/[\w-]+/[\w-]+/'),
        re.compile(r'https?://pin\.it/[\w]+'),
        re.compile(r'https?://www\.pinterest\.com/[\w.]+/boards/[\w-]+'),
        re.compile(r'https?://www\.pinterest\.com/ideas/[\w-]+/\d+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_type(self, url: str) -> str:
        if "/pin/" in url or re.search(r'/pin/\d+', url):
            return "pin"
        elif "/boards/" in url:
            return "board"
        elif "/ideas/" in url:
            return "idea"
        elif "pin.it" in url:
            return "short_pin"
        return "profile"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype = self._detect_type(url)
        formats = [
            {"format_id": "original", "ext": "jpg", "quality": "original resolution"},
            {"format_id": "large", "ext": "jpg", "quality": "large"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if ctype == "pin":
            formats.insert(0, {"format_id": "video", "ext": "mp4", "quality": "video pin"})
        elif ctype == "board":
            formats.insert(0, {"format_id": "board-all", "ext": "zip", "quality": "all pins"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype = self._detect_type(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "pinterest", "content_type": ctype}
        try:
            # Resolve short URLs
            if ctype == "short_pin":
                resp = requests.head(url, allow_redirects=True, timeout=self.timeout)
                url = str(resp.url)
                metadata["resolved_url"] = url
                ctype = self._detect_type(url)
                metadata["content_type"] = ctype
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            if resp.status_code == 200:
                text = resp.text
                for tag, key in [
                    ("og:title", "title"), ("og:image", "thumbnail"),
                    ("og:description", "description"),
                    ("og:video", "video_url"),
                    ("pinterestapp:pinit", "pin_id"),
                ]:
                    m = re.search(rf'<meta\s+(?:property|name)="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key] = m.group(1)
                # Extract high-res image URL from page data
                img_m = re.search(r'"images"\s*:\s*\{[^}]*"orig"\s*:\s*\{[^}]*"url"\s*:\s*"([^"]+)"', text)
                if img_m:
                    metadata["original_image"] = img_m.group(1).replace("\\/", "/")
                # Extract board pins count
                count_m = re.search(r'"pin_count"\s*:\s*(\d+)', text)
                if count_m:
                    metadata["pin_count"] = int(count_m.group(1))
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
            raise DownloadError(f"Invalid Pinterest URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        task.options["content_type"] = self._detect_type(task.url)

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.options.get("quality", "original")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)

        content_type = task.options.get("content_type", "pin")
        if content_type == "pin" and quality == "video":
            result = self._download_video(task, result)
        elif quality == "metadata_only":
            result = self._download_metadata(task, result)
        else:
            result = self._download_image(task, result, quality)

        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_image(self, task: DownloadTask, result: DownloadResult,
                        quality: str) -> DownloadResult:
        import requests
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            # Choose image URL based on quality
            img_url = metadata.get("original_image", metadata.get("thumbnail", ""))
            if quality == "thumbnail" and metadata.get("thumbnail"):
                img_url = metadata["thumbnail"]
            if not img_url:
                result.status = DownloadStatus.FAILED
                result.error = "No image URL found"
                return result
            ext = "mp4" if "/video/" in img_url else "jpg"
            filename = self._safe_filename(
                f"{metadata.get('title', 'pinterest')}.{ext}")
            filepath = os.path.join(out_dir, filename)
            resp = requests.get(img_url, timeout=self.timeout)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = len(resp.content)
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        return result

    def _download_video(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        outtmpl = os.path.join(
            task.options.get("output_dir", self.output_dir),
            "%(title)s.%(ext)s")
        cmd = [ytdlp_path, "-f", "best", "-o", outtmpl, task.url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.timeout * 10)
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                out_dir = task.options.get("output_dir", self.output_dir)
                for f in Path(out_dir).iterdir():
                    if f.is_file() and f.stat().st_mtime > time.time() - 600:
                        result.file_path = str(f.resolve())
                        result.filename = f.name
                        result.file_size = f.stat().st_size
                        break
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "Failed"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        return result

    def _download_metadata(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        import requests
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            filename = self._safe_filename(f"{metadata.get('title', 'pinterest')}_metadata.json")
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
        return result

    @staticmethod
    def _safe_filename(name: str) -> str:
        return re.sub(r'[<>:"|?*\\]', '_', name)[:200]

    def on_verify(self, task: DownloadTask = None, result: DownloadResult = None) -> DownloadResult:
        if result is None:
            return DownloadResult(status=DownloadStatus.FAILED, error="No result to verify")
        if not result.file_path or not os.path.exists(result.file_path):
            result.status = DownloadStatus.FAILED
            result.error = "Downloaded file not found"
            return result
        if os.path.getsize(result.file_path) > 0:
            result.status = DownloadStatus.COMPLETED
        else:
            result.status = DownloadStatus.FAILED
            result.error = "Downloaded file is empty"
        return result

    def on_post_process(self, task: DownloadTask = None, result: DownloadResult = None) -> DownloadResult:
        if result is not None:
            return result
        return DownloadResult()


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="pinterest",
        formats=tuple(PinterestDownloader.SUPPORTED_FORMATS),
        qualities=tuple(PinterestDownloader.SUPPORTED_QUALITIES),
        features=("pins", "boards", "videos", "images", "story_pins"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Pinterest downloader: pins, boards, videos, images at original resolution.",
    )
    return ("pinterest", skill)
