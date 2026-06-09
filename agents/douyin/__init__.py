"""
RS Downloader v10.0.0 - Douyin Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Douyin (TikTok China) downloader supporting:
- Video downloads without watermark
- Multiple quality options
- yt-dlp integration
- Direct API watermark removal
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


class DouyinDownloader(DownloaderBase):
    """Douyin download agent for watermark-free video downloads."""

    AGENT_NAME = "douyin"
    PLATFORM = "douyin"
    SUPPORTED_FORMATS = ["mp4", "webm", "mp3", "m4a"]
    SUPPORTED_QUALITIES = ["no_watermark", "watermark", "best", "bestaudio"]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.douyin\.com/video/(\d+)'),
        re.compile(r'https?://www\.douyin\.com/user/[\w-]+\?modal_id=(\d+)'),
        re.compile(r'https?://v\.douyin\.com/[\w-]+'),
        re.compile(r'https?://www\.iesdouyin\.com/share/video/(\d+)'),
    ]
    _API_BASE = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_video_id(self, url: str) -> str:
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        match = re.search(r'modal_id=(\d+)', url)
        if match:
            return match.group(1)
        return ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "no_watermark", "ext": "mp4", "quality": "no watermark"},
            {"format_id": "watermark", "ext": "mp4", "quality": "with watermark"},
            {"format_id": "best", "ext": "mp4", "quality": "best available"},
            {"format_id": "bestaudio", "ext": "m4a", "quality": "audio only"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "douyin", "url": url}
        video_id = self._extract_video_id(url)
        if video_id:
            try:
                resp = requests.get(
                    self._API_BASE,
                    params={"item_ids": video_id},
                    headers={**self.headers, "User-Agent": "Mozilla/5.0"},
                    proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                    timeout=self.timeout,
                )
                if resp.status_code == 200:
                    items = resp.json().get("item_list", [])
                    if items:
                        item = items[0]
                        video = item.get("video", {})
                        metadata.update({
                            "id": item.get("aweme_id", video_id),
                            "desc": item.get("desc", ""),
                            "author": item.get("author", {}).get("nickname", ""),
                            "author_id": item.get("author", {}).get("unique_id", ""),
                            "duration": video.get("duration", 0) / 1000,
                            "cover": video.get("cover", {}).get("url_list", [""])[0],
                            "stats": item.get("statistics", {}),
                            "video_urls": video.get("play_addr", {}).get("url_list", []),
                            "no_watermark_url": video.get("play_addr_265", {}).get("url_list", [""])[0] if video.get("play_addr_265") else "",
                        })
            except Exception:
                pass
        # Try yt-dlp fallback
        if not metadata.get("id"):
            try:
                import yt_dlp
                opts = {"quiet": True, "no_warnings": True, "skip_download": True}
                if self.proxy:
                    opts["proxy"] = self.proxy
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        metadata.update({
                            "id": info.get("id", ""),
                            "title": info.get("title", ""),
                            "duration": info.get("duration", 0),
                            "uploader": info.get("uploader", ""),
                        })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Douyin URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        task.options["video_id"] = self._extract_video_id(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "no_watermark")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            # Try no-watermark URL first
            download_url = ""
            if quality in ("no_watermark", "best"):
                download_url = metadata.get("no_watermark_url", "")
                if not download_url and metadata.get("video_urls"):
                    # Try to convert watermark URL to no-watermark
                    for u in metadata["video_urls"]:
                        if "watermark" not in u:
                            download_url = u
                            break
                    if not download_url:
                        download_url = metadata["video_urls"][0]
            elif quality == "watermark" and metadata.get("video_urls"):
                download_url = metadata["video_urls"][0]
            # Fallback to yt-dlp if no direct URL
            if not download_url:
                return self._download_via_ytdlp(task, result)
            title = metadata.get("desc") or metadata.get("id") or "douyin_video"
            title = title[:80].strip()
            filename = self._safe_filename(f"{title}.mp4")
            filepath = os.path.join(out_dir, filename)
            resp = requests.get(download_url, headers={**self.headers, "User-Agent": "Mozilla/5.0"},
                                stream=True, timeout=self.timeout)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = os.path.getsize(filepath)
            result.content_type = "video/mp4"
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def _download_via_ytdlp(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        """Fallback download via yt-dlp."""
        import shutil, subprocess
        ytdlp = shutil.which("yt-dlp") or "yt-dlp"
        out_dir = task.options.get("output_dir", self.output_dir)
        cmd = [ytdlp, "-f", "best", "-o", os.path.join(out_dir, "%(title)s.%(ext)s")]
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
        cmd.append(task.url)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 5)
            if proc.returncode == 0:
                for f in Path(out_dir).iterdir():
                    if f.is_file() and f.stat().st_mtime > time.time() - 300:
                        result.file_path = str(f.resolve())
                        result.filename = f.name
                        result.file_size = f.stat().st_size
                        break
                result.status = DownloadStatus.VERIFYING
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:300] if proc.stderr else "yt-dlp failed"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
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
        name="douyin", platform="douyin",
        description="Douyin downloader: watermark-free videos, multi-quality, yt-dlp integration.",
        supported_formats=DouyinDownloader.SUPPORTED_FORMATS,
        supported_qualities=DouyinDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.HIGH,
    )
    return ("douyin", skill)
