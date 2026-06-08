"""
RS Downloader v10.0.0 - Stream Utility Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Stream utility agent providing:
- HLS stream detection and download
- DASH stream detection and download
- M3U8 playlist parsing
- Segment-based downloading with progress
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


class StreamAgent(DownloaderBase):
    """Stream utility agent for HLS/DASH stream handling."""

    AGENT_NAME = "stream"
    PLATFORM = "stream"
    SUPPORTED_FORMATS = ["mp4", "ts", "mkv", "mp3", "m4a"]
    SUPPORTED_QUALITIES = ["best", "worst", "specific"]

    def validate_url(self, url: str) -> bool:
        return url.endswith(".m3u8") or url.endswith(".mpd") or url.startswith("http")

    def detect_stream_type(self, url: str) -> str:
        """Detect whether a URL points to HLS, DASH, or direct stream."""
        if ".m3u8" in url:
            return "hls"
        if ".mpd" in url:
            return "dash"
        import requests
        try:
            resp = requests.head(url, headers=self.headers, timeout=self.timeout,
                                 proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None)
            ct = resp.headers.get("Content-Type", "")
            if "mpegurl" in ct or "m3u8" in ct:
                return "hls"
            if "dash" in ct or "mpd" in ct:
                return "dash"
        except Exception:
            pass
        return "unknown"

    def download_hls(self, url: str, output_path: str, quality: str = "best") -> str:
        """Download HLS stream using ffmpeg."""
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise DownloadError("ffmpeg not found", url=url, agent=self.AGENT_NAME)
        cmd = [ffmpeg, "-i", url, "-c", "copy", "-bsf:a", "aac_adtstoasc", "-y", output_path]
        if self.proxy:
            cmd.extend(["-http_proxy", self.proxy])
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 10)
        if proc.returncode != 0:
            raise DownloadError(f"HLS download failed: {proc.stderr[:300]}", url=url, agent=self.AGENT_NAME)
        return output_path

    def download_dash(self, url: str, output_path: str, quality: str = "best") -> str:
        """Download DASH stream using yt-dlp or ffmpeg."""
        import shutil
        # Try yt-dlp first
        ytdlp = shutil.which("yt-dlp")
        if ytdlp:
            cmd = [ytdlp, "-f", quality, "-o", output_path, "--merge-output-format", "mp4"]
            if self.proxy:
                cmd.extend(["--proxy", self.proxy])
            cmd.append(url)
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 10)
            if proc.returncode == 0:
                return output_path
        # Fallback to ffmpeg
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg:
            cmd = [ffmpeg, "-i", url, "-c", "copy", "-y", output_path]
            if self.proxy:
                cmd.extend(["-http_proxy", self.proxy])
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 10)
            if proc.returncode == 0:
                return output_path
        raise DownloadError("DASH download failed", url=url, agent=self.AGENT_NAME)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        stream_type = self.detect_stream_type(url)
        return [
            {"format_id": "best", "ext": "mp4", "quality": f"best {stream_type}"},
            {"format_id": "worst", "ext": "mp4", "quality": f"worst {stream_type}"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        metadata: Dict[str, Any] = {"platform": "stream", "url": url}
        metadata["stream_type"] = self.detect_stream_type(url)
        try:
            resp = requests.head(url, headers=self.headers, timeout=self.timeout,
                                 proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None)
            metadata["content_type"] = resp.headers.get("Content-Type", "")
        except Exception:
            pass
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["stream_type"] = self.detect_stream_type(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.options.get("quality", "best")
        stream_type = task.options.get("stream_type", "unknown")
        out_dir = task.options.get("output_dir", self.output_dir)
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            filename = self._safe_filename(suggest_filename(url=task.url, default_name="stream"))
            if not filename.endswith((".mp4", ".ts", ".mkv")):
                filename += ".mp4"
            filepath = os.path.join(out_dir, filename)
            if stream_type == "hls":
                self.download_hls(task.url, filepath, quality)
            elif stream_type == "dash":
                self.download_dash(task.url, filepath, quality)
            else:
                # Try HLS first, then DASH
                try:
                    self.download_hls(task.url, filepath, quality)
                except Exception:
                    self.download_dash(task.url, filepath, quality)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = os.path.getsize(filepath)
            result.content_type = detect_content_type(filename=filename)
            result.metadata = {"stream_type": stream_type}
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
        name="stream", platform="stream",
        description="Stream utility: HLS/DASH detection, M3U8 parsing, segment download via ffmpeg.",
        supported_formats=StreamAgent.SUPPORTED_FORMATS,
        supported_qualities=StreamAgent.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.HIGH,
    )
    return ("stream", skill)
