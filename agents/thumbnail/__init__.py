"""
RS Downloader v10.0.0 - Thumbnail Utility Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Thumbnail utility agent providing:
- Thumbnail download at multiple resolutions
- WebP/JPG/PNG format support
- Video thumbnail extraction via ffmpeg
- Batch thumbnail extraction from playlists
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class ThumbnailAgent(DownloaderBase):
    """Thumbnail utility agent for download and extraction."""

    AGENT_NAME = "thumbnail"
    PLATFORM = "thumbnail"
    SUPPORTED_FORMATS = ["jpg", "png", "webp"]
    SUPPORTED_QUALITIES = ["maxresdefault", "hqdefault", "mqdefault", "sddefault", "default"]

    def validate_url(self, url: str) -> bool:
        return url.startswith("http") or os.path.exists(url)

    def download_thumbnail(self, video_url: str, quality: str = "maxresdefault",
                           output_format: str = "jpg") -> str:
        """Download thumbnail for a video URL using yt-dlp."""
        import shutil
        ytdlp = shutil.which("yt-dlp") or "yt-dlp"
        out_path = f"thumbnail_{quality}.%(ext)s"
        cmd = [ytdlp, "--write-thumbnail", "--skip-download",
               "-o", out_path, "--thumbnail-format", output_format]
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        cmd.append(video_url)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        # Find downloaded thumbnail
        for f in Path(".").glob(f"thumbnail_{quality}*"):
            if f.suffix.lower() in (".jpg", ".png", ".webp"):
                return str(f.resolve())
        return ""

    def extract_thumbnails(self, video_path: str, interval: int = 60,
                           output_format: str = "jpg") -> List[str]:
        """Extract thumbnails from a video file at regular intervals using ffmpeg."""
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise DownloadError("ffmpeg not found", url=video_path, agent=self.AGENT_NAME)
        video_path = video_path.replace("file://", "")
        if not os.path.exists(video_path):
            raise DownloadError(f"File not found: {video_path}", url=video_path, agent=self.AGENT_NAME)
        out_dir = os.path.dirname(video_path)
        base_name = Path(video_path).stem
        pattern = os.path.join(out_dir, f"{base_name}_thumb_%04d.{output_format}")
        cmd = [ffmpeg, "-i", video_path, "-vf", f"fps=1/{interval}",
               "-q:v", "2", "-y", pattern]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        thumbnails = sorted(Path(out_dir).glob(f"{base_name}_thumb_*.{output_format}"))
        return [str(t.resolve()) for t in thumbnails]

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "maxresdefault", "ext": "jpg", "quality": "max resolution (1280x720)"},
            {"format_id": "hqdefault", "ext": "jpg", "quality": "high quality (480x360)"},
            {"format_id": "mqdefault", "ext": "jpg", "quality": "medium quality (320x180)"},
            {"format_id": "sddefault", "ext": "jpg", "quality": "standard (640x480)"},
            {"format_id": "default", "ext": "jpg", "quality": "default (120x90)"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "thumbnail", "url": url}
        try:
            import yt_dlp
            opts = {"quiet": True, "no_warnings": True, "skip_download": True}
            if self.proxy:
                opts["proxy"] = self.proxy
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if info:
                    metadata["title"] = info.get("title", "")
                    metadata["thumbnail"] = info.get("thumbnail", "")
                    metadata["thumbnails"] = info.get("thumbnails", [])
        except Exception:
            pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        action = task.options.get("action", "download")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            out_dir = task.options.get("output_dir", self.output_dir)
            quality = task.options.get("quality", "maxresdefault")
            output_format = task.options.get("output_format", "jpg")
            if action == "extract":
                interval = task.options.get("interval", 60)
                thumbnails = self.extract_thumbnails(task.url, interval, output_format)
                result.metadata = {"thumbnails": thumbnails, "count": len(thumbnails)}
                if thumbnails:
                    result.file_path = thumbnails[0]
                    result.filename = os.path.basename(thumbnails[0])
                    result.file_size = os.path.getsize(thumbnails[0]) if os.path.exists(thumbnails[0]) else 0
            else:
                thumb_path = self.download_thumbnail(task.url, quality, output_format)
                if thumb_path and os.path.exists(thumb_path):
                    # Move to output dir
                    dest = os.path.join(out_dir, os.path.basename(thumb_path))
                    os.makedirs(out_dir, exist_ok=True)
                    if thumb_path != dest:
                        import shutil
                        shutil.move(thumb_path, dest)
                    result.file_path = os.path.abspath(dest)
                    result.filename = os.path.basename(dest)
                    result.file_size = os.path.getsize(dest)
                    result.content_type = detect_content_type(filename=dest)
                else:
                    result.status = DownloadStatus.FAILED
                    result.error = "Failed to download thumbnail"
                    return result
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        if result.file_path and os.path.isfile(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="thumbnail", platform="thumbnail",
        description="Thumbnail utility: download at multiple resolutions, extract from video, WebP/JPG/PNG.",
        supported_formats=ThumbnailAgent.SUPPORTED_FORMATS,
        supported_qualities=ThumbnailAgent.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.NORMAL,
    )
    return ("thumbnail", skill)
