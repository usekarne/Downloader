"""
RS Downloader v10.0.0 - Bilibili Download Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Bilibili downloader supporting:
- Video downloads (360p through 4K)
- Bangumi/episode downloads
- Livestream recording
- Multi-part video handling
- Danmaku subtitle extraction
- Cookie authentication for premium content
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
    detect_content_type, suggest_filename,
)


class BilibiliDownloader(DownloaderBase):
    """Bilibili download agent powered by yt-dlp with Bilibili-specific features."""

    AGENT_NAME = "bilibili"
    PLATFORM = "bilibili"
    SUPPORTED_FORMATS = ["mp4", "flv", "mkv", "mp3", "m4a", "webm"]
    SUPPORTED_QUALITIES = [
        "4K", "1080P", "1080P60", "720P", "720P60",
        "480P", "360P", "best", "bestaudio",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.bilibili\.com/video/(BV[\w]+|av[\d]+)'),
        re.compile(r'https?://www\.bilibili\.com/bangumi/play/(ep[\d]+|ss[\d]+)'),
        re.compile(r'https?://www\.bilibili\.com/live/[\d]+'),
        re.compile(r'https?://b23\.tv/[\w]+'),
        re.compile(r'https?://www\.bilibili\.com/medialist/[\w/]+'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = self._find_ytdlp()

    @staticmethod
    def _find_ytdlp() -> str:
        for candidate in ("yt-dlp", "yt_dlp"):
            path = shutil.which(candidate)
            if path:
                return path
        return "yt-dlp"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_content_type(self, url: str) -> str:
        if "/bangumi/" in url:
            return "bangumi"
        if "/live/" in url:
            return "livestream"
        if "/medialist/" in url:
            return "playlist"
        return "video"

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict[str, Any]:
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
        }
        if self.proxy:
            opts["proxy"] = self.proxy
        if self.cookies:
            opts["cookiefile"] = self.cookies
        if extra:
            opts.update(extra)
        return opts

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        opts = self._build_ytdlp_opts({"listformats": True, "skip_download": True})
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return []
                formats = []
                for fmt in info.get("formats", []):
                    formats.append({
                        "format_id": fmt.get("format_id", ""),
                        "ext": fmt.get("ext", ""),
                        "quality": fmt.get("format_note", fmt.get("height", "")),
                        "vcodec": fmt.get("vcodec", "none"),
                        "acodec": fmt.get("acodec", "none"),
                        "filesize": fmt.get("filesize") or fmt.get("filesize_approx", 0),
                        "height": fmt.get("height", 0),
                    })
                return formats
        except Exception:
            return self._formats_fallback()

    def _formats_fallback(self) -> List[Dict[str, Any]]:
        return [
            {"format_id": "4K", "ext": "mp4", "quality": "4K 2160p"},
            {"format_id": "1080P", "ext": "mp4", "quality": "1080p"},
            {"format_id": "720P", "ext": "mp4", "quality": "720p"},
            {"format_id": "480P", "ext": "mp4", "quality": "480p"},
            {"format_id": "360P", "ext": "mp4", "quality": "360p"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        opts = self._build_ytdlp_opts({"skip_download": True})
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {}
                return {
                    "id": info.get("id", ""),
                    "title": info.get("title", ""),
                    "description": info.get("description", ""),
                    "duration": info.get("duration", 0),
                    "uploader": info.get("uploader", ""),
                    "upload_date": info.get("upload_date", ""),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "categories": info.get("categories", []),
                    "tags": info.get("tags", []),
                    "is_live": info.get("is_live", False),
                    "content_type": self._detect_content_type(url),
                }
        except Exception:
            return {"content_type": self._detect_content_type(url)}

    def _resolve_format(self, quality: str) -> str:
        mapping = {
            "4K": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1080P": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "1080P60": "bestvideo[height<=1080][fps>=60]+bestaudio/best[height<=1080]",
            "720P": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "720P60": "bestvideo[height<=720][fps>=60]+bestaudio/best[height<=720]",
            "480P": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360P": "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "best": "bestvideo+bestaudio/best",
            "bestaudio": "bestaudio/best",
        }
        return mapping.get(quality, "bestvideo+bestaudio/best")

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Bilibili URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        task.options["content_type"] = self._detect_content_type(task.url)

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.options.get("quality", "1080P")
        format_spec = self._resolve_format(quality)
        out_dir = task.options.get("output_dir", self.output_dir)
        content_type = task.options.get("content_type", "video")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": os.path.join(out_dir, "%(title)s [%(id)s].%(ext)s"),
            "merge_output_format": "mp4",
        })
        # Bilibili-specific options
        if content_type == "livestream":
            ytdlp_opts["hls_prefer_native"] = True
        # Danmaku download option
        if task.options.get("download_danmaku"):
            ytdlp_opts["writesubtitles"] = True
            ytdlp_opts["subtitlesformat"] = "xml"
        # Embed metadata
        if task.options.get("embed_metadata"):
            ytdlp_opts["postprocessors"] = [{"key": "FFmpegMetadata"}]
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                if info:
                    result.metadata = {
                        "title": info.get("title", ""),
                        "duration": info.get("duration", 0),
                        "id": info.get("id", ""),
                    }
                    filename = ydl.prepare_filename(info)
                    for ext in ("mp4", "mkv", "flv", "webm"):
                        candidate = os.path.splitext(filename)[0] + f".{ext}"
                        if os.path.exists(candidate):
                            filename = candidate
                            break
                    if os.path.exists(filename):
                        result.file_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                        result.content_type = detect_content_type(filename=filename)
                result.status = DownloadStatus.VERIFYING
        except ImportError:
            result = self._download_via_cli(task, ytdlp_opts, result)
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        if result.elapsed > 0 and result.file_size > 0:
            result.average_speed = result.file_size / result.elapsed
        return result

    def _download_via_cli(self, task: DownloadTask, opts: Dict, result: DownloadResult) -> DownloadResult:
        cmd = [self._ytdlp_path, "-f", opts.get("format", "best"),
               "-o", opts.get("outtmpl", "%(title)s.%(ext)s"),
               "--merge-output-format", "mp4"]
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
        cmd.append(task.url)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 10)
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                out_dir = task.options.get("output_dir", self.output_dir)
                for f in Path(out_dir).iterdir():
                    if f.is_file() and f.stat().st_mtime > time.time() - 300:
                        result.file_path = str(f.resolve())
                        result.filename = f.name
                        result.file_size = f.stat().st_size
                        break
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "Download failed"
        except subprocess.TimeoutExpired:
            result.status = DownloadStatus.FAILED
            result.error = "Download timed out"
        except FileNotFoundError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp not found"
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
        name="bilibili", platform="bilibili",
        description="Bilibili downloader: videos (360p-4K), bangumi, livestreams, danmaku, cookie auth.",
        supported_formats=BilibiliDownloader.SUPPORTED_FORMATS,
        supported_qualities=BilibiliDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.HIGH,
    )
    return ("bilibili", skill)
