"""
RS Downloader v10.0.0 - Odnoklassniki (OK) Download Agent
==========================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

OK.ru downloader supporting:
- Video downloads (all qualities)
- Music track downloads
- Photo/album downloads
- Group/community content
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


class OKDownloader(DownloaderBase):
    """Odnoklassniki (OK.ru) download agent for videos, music, and photos."""

    AGENT_NAME = "ok"
    PLATFORM = "ok"
    SUPPORTED_FORMATS = ["mp4", "mkv", "webm", "mp3", "m4a", "jpg", "json"]
    SUPPORTED_QUALITIES = [
        "1080p", "720p", "480p", "360p", "240p",
        "best", "worst", "bestaudio", "metadata_only",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://ok\.ru/video/\d+'),
        re.compile(r'https?://ok\.ru/videoembed/\d+'),
        re.compile(r'https?://ok\.ru/profile/\d+'),
        re.compile(r'https?://ok\.ru/group/\d+'),
        re.compile(r'https?://m\.ok\.ru/video/\d+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_type(self, url: str) -> str:
        if "video" in url or "videoembed" in url:
            return "video"
        elif "profile" in url:
            return "profile"
        elif "group" in url:
            return "group"
        return "unknown"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype = self._detect_type(url)
        formats = []
        if ctype == "video":
            for q in ["1080p", "720p", "480p", "360p", "240p"]:
                formats.append({"format_id": q, "ext": "mp4", "quality": q})
        formats.append({"format_id": "metadata", "ext": "json", "quality": "metadata only"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {
            "url": url, "platform": "ok",
            "content_type": self._detect_type(url)}
        try:
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            if resp.status_code == 200:
                text = resp.text
                for tag, key in [("og:title", "title"), ("og:image", "thumbnail"),
                                 ("og:description", "description"),
                                 ("og:video", "video_url")]:
                    m = re.search(rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key] = m.group(1)
                # Extract video metadata from data-attributes
                vid_m = re.search(r'data-vid="(\d+)"', text)
                if vid_m:
                    metadata["video_id"] = vid_m.group(1)
                dur_m = re.search(r'data-duration="(\d+)"', text)
                if dur_m:
                    metadata["duration"] = int(dur_m.group(1))
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
            raise DownloadError(f"Invalid OK.ru URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

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
            try:
                metadata = self.get_metadata(task.url)
                result.metadata = metadata
                out_dir = task.options.get("output_dir", self.output_dir)
                filename = self._safe_filename(f"{metadata.get('title', 'ok')}_metadata.json")
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
        else:
            ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
            fmt_map = {
                "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
                "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
                "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
                "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
                "best": "bestvideo+bestaudio/best",
                "bestaudio": "bestaudio/best",
            }
            format_spec = fmt_map.get(quality, "bestvideo+bestaudio/best")
            outtmpl = os.path.join(
                task.options.get("output_dir", self.output_dir),
                "%(title)s [%(id)s].%(ext)s")
            cmd = [ytdlp_path, "-f", format_spec, "-o", outtmpl, task.url]
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
        platform="ok",
        formats=tuple(OKDownloader.SUPPORTED_FORMATS),
        qualities=tuple(OKDownloader.SUPPORTED_QUALITIES),
        features=("videos", "music", "photos", "groups"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="OK.ru downloader: videos, music, photos via yt-dlp.",
    )
    return ("ok", skill)
