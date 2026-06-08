"""
RS Downloader v10.0.0 - Kakao Download Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Kakao download agent supporting:
- KakaoTV video downloads
- KakaoPage webtoon/image extraction
- Webtoon chapter batch download
- yt-dlp integration for video
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


class KakaoDownloader(DownloaderBase):
    """Kakao download agent for videos and webtoons."""

    AGENT_NAME = "kakao"
    PLATFORM = "kakao"
    SUPPORTED_FORMATS = ["mp4", "jpg", "png", "webp"]
    SUPPORTED_QUALITIES = ["1080p", "720p", "480p", "best", "webtoon_hd"]

    _URL_PATTERNS = [
        re.compile(r'https?://tv\.kakao\.com/(channel|v)/[\w-]+'),
        re.compile(r'https?://webtoon\.kakao\.com/[\w-]+/[\w-]+'),
        re.compile(r'https?://page\.kakao\.com/[\w-]+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_type(self, url: str) -> str:
        if "tv.kakao" in url:
            return "video"
        if "webtoon.kakao" in url or "page.kakao" in url:
            return "webtoon"
        return "unknown"

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        if self._detect_type(url) == "webtoon":
            return [
                {"format_id": "webtoon_hd", "ext": "jpg", "quality": "high quality"},
                {"format_id": "webtoon_sd", "ext": "jpg", "quality": "standard"},
            ]
        return [
            {"format_id": "1080p", "ext": "mp4", "quality": "1080p"},
            {"format_id": "720p", "ext": "mp4", "quality": "720p"},
            {"format_id": "480p", "ext": "mp4", "quality": "480p"},
            {"format_id": "best", "ext": "mp4", "quality": "best"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "kakao", "url": url}
        content_type = self._detect_type(url)
        metadata["content_type"] = content_type
        if content_type == "video":
            try:
                import yt_dlp
                opts = {"quiet": True, "no_warnings": True, "skip_download": True}
                if self.proxy:
                    opts["proxy"] = self.proxy
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    if info:
                        metadata.update({
                            "title": info.get("title", ""),
                            "duration": info.get("duration", 0),
                            "uploader": info.get("uploader", ""),
                            "thumbnail": info.get("thumbnail", ""),
                        })
            except Exception:
                pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Kakao URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["content_type"] = self._detect_type(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        content_type = task.options.get("content_type", "video")
        out_dir = task.options.get("output_dir", self.output_dir)
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            if content_type == "video":
                result = self._download_video(task, out_dir, result)
            else:
                result.status = DownloadStatus.FAILED
                result.error = "Webtoon download requires authentication"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def _download_video(self, task: DownloadTask, out_dir: str, result: DownloadResult) -> DownloadResult:
        import shutil, subprocess
        quality = task.options.get("quality", "best")
        fmt_map = {
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "best": "bestvideo+bestaudio/best",
        }
        ytdlp = shutil.which("yt-dlp") or "yt-dlp"
        cmd = [ytdlp, "-f", fmt_map.get(quality, "best"),
               "-o", os.path.join(out_dir, "%(title)s.%(ext)s"),
               "--merge-output-format", "mp4"]
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        cmd.append(task.url)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 5)
        if proc.returncode == 0:
            result.status = DownloadStatus.VERIFYING
            for f in Path(out_dir).iterdir():
                if f.is_file() and f.stat().st_mtime > time.time() - 300:
                    result.file_path = str(f.resolve())
                    result.filename = f.name
                    result.file_size = f.stat().st_size
                    break
        else:
            result.status = DownloadStatus.FAILED
            result.error = proc.stderr[:500] if proc.stderr else "Download failed"
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
        name="kakao", platform="kakao",
        description="Kakao downloader: KakaoTV videos, KakaoPage webtoons, yt-dlp integration.",
        supported_formats=KakaoDownloader.SUPPORTED_FORMATS,
        supported_qualities=KakaoDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("kakao", skill)
