"""
RS Downloader v10.0.0 - YouTube Music Download Agent
======================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

YouTube Music downloader supporting:
- Audio playlists, albums, artist pages
- High-quality audio extraction (opus, m4a, mp3)
- Album art and metadata embedding
- Cookie authentication for premium content
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentSkill,
    DownloadError,
    DownloadPriority,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
)


class YouTubeMusicDownloader(DownloaderBase):
    """
    YouTube Music download agent using yt-dlp.

    Focused on audio extraction from YouTube Music with support for
    playlists, albums, and artist discographies.
    """

    AGENT_NAME = "youtube_music"
    PLATFORM = "youtube_music"
    SUPPORTED_FORMATS = ["mp3", "m4a", "opus", "ogg", "wav", "flac", "aac"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low", "bestaudio", "worstaudio"]

    _URL_PATTERNS = [
        re.compile(r'https?://music\.youtube\.com/watch\?'),
        re.compile(r'https?://music\.youtube\.com/playlist\?'),
        re.compile(r'https?://music\.youtube\.com/album/'),
        re.compile(r'https?://music\.youtube\.com/channel/'),
        re.compile(r'https?://music\.youtube\.com/artist/'),
        re.compile(r'https?://music\.youtube\.com/browse/'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 600)

    def _ensure_output_dir(self, path: str) -> str:
        """Ensure output directory exists."""
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        """Build yt-dlp options for YouTube Music."""
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "extract_flat": False,
        }
        if self._proxy:
            opts["proxy"] = self._proxy
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if extra:
            opts.update(extra)
        return opts

    # -------------------------------------------------------------------
    # URL Validation
    # -------------------------------------------------------------------

    def validate_url(self, url: str) -> bool:
        """Check if the URL is a valid YouTube Music URL."""
        return any(pattern.match(url) for pattern in self._URL_PATTERNS)

    # -------------------------------------------------------------------
    # Format Discovery
    # -------------------------------------------------------------------

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Query available audio formats for YouTube Music URL."""
        opts = self._build_ytdlp_opts({"skip_download": True})
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return []
                formats = []
                for fmt in info.get("formats", []):
                    acodec = fmt.get("acodec", "none")
                    if acodec != "none" or fmt.get("vcodec", "none") == "none":
                        formats.append({
                            "format_id": fmt.get("format_id", ""),
                            "ext": fmt.get("ext", ""),
                            "acodec": acodec,
                            "abr": fmt.get("abr", 0),
                            "filesize": fmt.get("filesize") or fmt.get("filesize_approx", 0),
                            "quality": f"{fmt.get('abr', 0):.0f}kbps" if fmt.get("abr") else "audio",
                        })
                return formats
        except Exception as exc:
            raise DownloadError(f"Failed to query formats: {exc}")

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch metadata for YouTube Music content."""
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
                    "album": info.get("album", ""),
                    "artist": info.get("artist") or info.get("uploader", ""),
                    "duration": info.get("duration", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "track_number": info.get("track_number"),
                    "genre": info.get("genre", ""),
                    "release_date": info.get("release_date", ""),
                    "playlist": info.get("playlist", ""),
                    "playlist_count": info.get("playlist_count"),
                    "entries": len(info.get("entries", [])) if info.get("entries") else None,
                }
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    # -------------------------------------------------------------------
    # Lifecycle: Prepare
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        """Prepare YouTube Music download."""
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid YouTube Music URL: {task.url}")
        out_dir = self._ensure_output_dir(
            task.output_path or self._output_dir
        )
        task.output_path = out_dir

    # -------------------------------------------------------------------
    # Lifecycle: Download
    # -------------------------------------------------------------------

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Download YouTube Music audio via yt-dlp."""
        quality = task.tags[0] if task.tags else "best"
        format_spec = self._resolve_format(quality)

        outtmpl = os.path.join(
            task.output_path or self._output_dir,
            "%(artist)s - %(title)s [%(id)s].%(ext)s",
        )

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": outtmpl,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "best"},
                {"key": "FFmpegMetadata"},
            ],
        })

        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url,
            agent_name=self.AGENT_NAME,
            platform=self.PLATFORM,
            status=DownloadStatus.DOWNLOADING,
        )

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                if info:
                    result.metadata = {
                        "title": info.get("title", ""),
                        "artist": info.get("artist") or info.get("uploader", ""),
                        "album": info.get("album", ""),
                        "duration": info.get("duration", 0),
                    }
                    filename = ydl.prepare_filename(info)
                    # After audio extraction, the extension may change
                    for ext in ("m4a", "opus", "mp3", "ogg", "wav"):
                        alt = os.path.splitext(filename)[0] + f".{ext}"
                        if os.path.exists(alt):
                            filename = alt
                            break
                    if os.path.exists(filename):
                        result.output_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                    result.status = DownloadStatus.VERIFYING
        except ImportError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp required. Install: pip install yt-dlp"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)

        elapsed = time.monotonic() - start_time
        result.elapsed = elapsed
        if elapsed > 0 and result.file_size > 0:
            result.average_speed = result.file_size / elapsed
        return result

    @staticmethod
    def _resolve_format(quality: str) -> str:
        """Convert quality name to yt-dlp format spec."""
        quality_map = {
            "best": "bestaudio/best",
            "high": "bestaudio[abr<=320]/bestaudio/best",
            "medium": "bestaudio[abr<=128]/bestaudio/best",
            "low": "worstaudio/worst",
            "bestaudio": "bestaudio/best",
            "worstaudio": "worstaudio/worst",
        }
        return quality_map.get(quality, "bestaudio/best")

    # -------------------------------------------------------------------
    # Lifecycle: Verify
    # -------------------------------------------------------------------

    def on_verify(self, task=None, result=None):
        """Verify downloaded audio file."""
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    # -------------------------------------------------------------------
    # Lifecycle: Post-Process
    # -------------------------------------------------------------------

    def on_post_process(self, task=None, result=None):
        """Post-process: checksum, collect extra files."""
        if result.output_path and os.path.exists(result.output_path):
            result.metadata["checksum"] = self._compute_checksum(result.output_path)
            result.metadata["checksum_algorithm"] = "sha256"
        return result

    def _compute_checksum(self, filepath: str) -> str:
        """Compute SHA-256 checksum."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def register() -> Tuple[str, AgentSkill]:
    """Register the YouTube Music agent."""
    skill = AgentSkill(
        platform="youtube_music",
        formats=frozenset(YouTubeMusicDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(YouTubeMusicDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "audio", "playlists", "albums", "artists",
            "metadata_embedding", "cookie_auth", "album_art",
        ]),
        max_concurrent=3,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description="YouTube Music downloader: audio playlists, albums, artists with metadata.",
    )
    return ("youtube_music", skill)
