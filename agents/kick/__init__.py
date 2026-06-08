"""
RS Downloader v10.0.0 - Kick Download Agent
=============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Kick downloader supporting:
- VOD (Video on Demand) downloads
- Clip downloads
- Livestream recording
- Channel metadata extraction
- Chat replay extraction
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


class KickDownloader(DownloaderBase):
    """Kick download agent for VODs, clips, and livestreams."""

    AGENT_NAME = "kick"
    PLATFORM = "kick"
    SUPPORTED_FORMATS = ["mp4", "mkv", "webm", "ts", "m4a", "json"]
    SUPPORTED_QUALITIES = [
        "1080p", "720p", "480p", "360p", "160p",
        "best", "worst", "bestaudio", "metadata_only",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://kick\.com/[\w-]+\?clip=clip_[\w]+'),
        re.compile(r'https?://kick\.com/[\w-]+/videos/[\w-]+'),
        re.compile(r'https?://kick\.com/[\w-]+$'),
        re.compile(r'https?://kick\.com/video/[\w-]+'),
        re.compile(r'https?://kick\.com/clips/clip_[\w-]+'),
    ]

    _KICK_API = "https://kick.com/api/v1"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_type(self, url: str) -> str:
        if "clip=" in url or "/clips/" in url:
            return "clip"
        elif "/videos/" in url or "/video/" in url:
            return "vod"
        elif re.search(r'kick\.com/[\w-]+$', url):
            return "channel"
        return "unknown"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype = self._detect_type(url)
        formats = []
        if ctype in ("vod", "clip"):
            for q in ["1080p", "720p", "480p", "360p", "160p"]:
                formats.append({"format_id": q, "ext": "mp4", "quality": q})
        elif ctype == "channel":
            formats.append({"format_id": "live", "ext": "ts", "quality": "livestream"})
        formats.append({"format_id": "metadata", "ext": "json", "quality": "metadata only"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype = self._detect_type(url)
        metadata: Dict[str, Any] = {"url": url, "platform": "kick",
                                    "content_type": ctype}
        try:
            # Extract channel name
            channel_m = re.search(r'kick\.com/([\w-]+)', url)
            channel = channel_m.group(1) if channel_m else ""
            metadata["channel"] = channel
            if channel:
                try:
                    resp = requests.get(
                        f"{self._KICK_API}/channels/{channel}",
                        timeout=self.timeout)
                    if resp.status_code == 200:
                        data = resp.json()
                        metadata["channel_title"] = data.get("title", "")
                        metadata["channel_bio"] = data.get("bio", "")
                        metadata["followers"] = data.get("followers_count", 0)
                        metadata["is_live"] = data.get("is_live", False)
                        metadata["thumbnail"] = data.get("thumbnail", "")
                except Exception:
                    pass
            # Try page scraping for video info
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            if resp.status_code == 200:
                text = resp.text
                for tag, key in [("og:title", "title"), ("og:image", "thumbnail"),
                                 ("og:description", "description")]:
                    m = re.search(rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key] = m.group(1)
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
            raise DownloadError(f"Invalid Kick URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
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
            return self._download_metadata(task, result)

        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        fmt_map = {
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
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
        # Livestream options
        ctype = task.options.get("content_type", "")
        if ctype == "channel":
            cmd.extend(["--hls-prefer-native"])
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
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_metadata(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            filename = self._safe_filename(f"{metadata.get('channel', 'kick')}_metadata.json")
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

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="kick",
        formats=tuple(KickDownloader.SUPPORTED_FORMATS),
        qualities=tuple(KickDownloader.SUPPORTED_QUALITIES),
        features=("vods", "clips", "livestreams", "chat_replay", "channels"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Kick downloader: VODs, clips, livestreams, channel metadata via yt-dlp.",
    )
    return ("kick", skill)
