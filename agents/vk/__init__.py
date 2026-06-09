"""
RS Downloader v10.0.0 - VK Download Agent
===========================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

VK (VKontakte) downloader supporting:
- Video downloads (all qualities)
- Audio track downloads
- Photo/album downloads
- Wall post media extraction
- Community/group content
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


class VKDownloader(DownloaderBase):
    """VK download agent for videos, audio, photos, and wall content."""

    AGENT_NAME = "vk"
    PLATFORM = "vk"
    SUPPORTED_FORMATS = ["mp4", "mkv", "webm", "mp3", "m4a", "jpg", "png", "json"]
    SUPPORTED_QUALITIES = [
        "2160p", "1440p", "1080p", "720p", "480p", "360p", "240p",
        "best", "worst", "bestaudio", "metadata_only",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://vk\.com/video[\w-]*\d+_\d+'),
        re.compile(r'https?://vk\.com/audios\d+'),
        re.compile(r'https?://vk\.com/album\d+_\d+'),
        re.compile(r'https?://vk\.com/wall\d+_\d+'),
        re.compile(r'https?://vk\.com/[\w.-]+\?z=video'),
        re.compile(r'https?://vk\.com/photo\d+_\d+'),
        re.compile(r'https?://m\.vk\.com/'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_type(self, url: str) -> str:
        if "video" in url or "z=video" in url:
            return "video"
        elif "audio" in url:
            return "audio"
        elif "album" in url or "photo" in url:
            return "photo"
        elif "wall" in url:
            return "wall"
        return "unknown"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype = self._detect_type(url)
        formats = []
        if ctype == "video":
            for q in ["2160p", "1440p", "1080p", "720p", "480p", "360p", "240p"]:
                formats.append({"format_id": q, "ext": "mp4", "quality": q})
        elif ctype == "audio":
            formats.append({"format_id": "bestaudio", "ext": "mp3", "quality": "best audio"})
        elif ctype == "photo":
            formats.append({"format_id": "original", "ext": "jpg", "quality": "original"})
        formats.append({"format_id": "metadata", "ext": "json", "quality": "metadata only"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype = self._detect_type(url)
        metadata: Dict[str, Any] = {"url": url, "platform": "vk", "content_type": ctype}
        try:
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            if resp.status_code == 200:
                text = resp.text
                for tag, key in [("og:title", "title"), ("og:image", "thumbnail"),
                                 ("og:description", "description"),
                                 ("og:video", "video_url"),
                                 ("og:video:type", "video_type")]:
                    m = re.search(rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key] = m.group(1)
                # Extract video qualities from page
                quality_matches = re.findall(
                    r'"url(\d+)"\s*:\s*"([^"]+)"', text)
                if quality_matches:
                    metadata["video_qualities"] = {
                        f"{q}p": u.replace("\\/", "/")
                        for q, u in quality_matches
                    }
                # Extract player params
                oid_m = re.search(r'"oid"\s*:\s*"([^"]+)"', text)
                vid_m = re.search(r'"vid"\s*:\s*"([^"]+)"', text)
                if oid_m and vid_m:
                    metadata["owner_id"] = oid_m.group(1)
                    metadata["video_id"] = vid_m.group(1)
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
            raise DownloadError(f"Invalid VK URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        task.options["content_type"] = self._detect_type(task.url)

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.options.get("quality", "best")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)

        if quality == "metadata_only":
            result = self._download_metadata(task, result)
        else:
            result = self._download_via_ytdlp(task, result, quality)

        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_via_ytdlp(self, task: DownloadTask, result: DownloadResult,
                            quality: str) -> DownloadResult:
        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        fmt_map = {
            "2160p": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "240p": "worstvideo+worstaudio/worst",
            "best": "bestvideo+bestaudio/best",
            "bestaudio": "bestaudio/best",
            "worst": "worstvideo+worstaudio/worst",
        }
        format_spec = fmt_map.get(quality, "bestvideo+bestaudio/best")
        outtmpl = os.path.join(
            task.options.get("output_dir", self.output_dir),
            "%(title)s [%(id)s].%(ext)s")
        cmd = [ytdlp_path, "-f", format_spec, "-o", outtmpl]
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
        cmd.append(task.url)
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
        except subprocess.TimeoutExpired:
            result.status = DownloadStatus.FAILED
            result.error = "Timed out"
        except FileNotFoundError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp not found"
        return result

    def _download_metadata(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            filename = self._safe_filename(f"{metadata.get('title', 'vk')}_metadata.json")
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

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="vk",
        formats=tuple(VKDownloader.SUPPORTED_FORMATS),
        qualities=tuple(VKDownloader.SUPPORTED_QUALITIES),
        features=("videos", "audio", "photos", "wall_posts", "albums"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="VK downloader: videos, audio, photos, wall posts via yt-dlp.",
    )
    return ("vk", skill)
