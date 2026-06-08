"""
RS Downloader v10.0.0 - SoundCloud Download Agent
====================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

SoundCloud downloader supporting:
- Audio tracks (all qualities)
- Playlists/sets
- Artist tracks
- Cookie authentication for Go+ content
"""

from __future__ import annotations

import hashlib
import os
import re
import shutil
import time
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


class SoundCloudDownloader(DownloaderBase):
    """SoundCloud download agent using yt-dlp."""

    AGENT_NAME = "soundcloud"
    PLATFORM = "soundcloud"
    SUPPORTED_FORMATS = ["mp3", "m4a", "opus", "ogg", "wav", "flac"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low", "bestaudio"]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?soundcloud\.com/[\w-]+/[\w-]+'),
        re.compile(r'https?://(www\.)?soundcloud\.com/[\w-]+/sets/[\w-]+'),
        re.compile(r'https?://(www\.)?soundcloud\.com/[\w-]+/tracks'),
        re.compile(r'https?://(www\.)?soundcloud\.com/[\w-]+$'),
        re.compile(r'https?://on\.soundcloud\.com/[\w]+'),
        re.compile(r'https?://api\.soundcloud\.com/tracks/\d+'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 300)
        self._client_id = kwargs.get("soundcloud_client_id")

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
        }
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if self._proxy:
            opts["proxy"] = self._proxy
        if self._client_id:
            opts["extractor_args"] = {"soundcloud": {"client_id": self._client_id}}
        if extra:
            opts.update(extra)
        return opts

    def _detect_content_type(self, url: str) -> str:
        if "/sets/" in url:
            return "playlist"
        if "/tracks" in url:
            return "artist_tracks"
        return "track"

    # -------------------------------------------------------------------
    # URL Validation
    # -------------------------------------------------------------------

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    # -------------------------------------------------------------------
    # Format Discovery
    # -------------------------------------------------------------------

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        opts = self._build_ytdlp_opts({"skip_download": True})
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
                        "quality": fmt.get("format_note", ""),
                        "abr": fmt.get("abr", 0),
                        "filesize": fmt.get("filesize") or 0,
                        "acodec": fmt.get("acodec", "none"),
                        "vcodec": fmt.get("vcodec", "none"),
                    })
                return formats
        except Exception as exc:
            raise DownloadError(f"Failed to query formats: {exc}")

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------

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
                    "uploader": info.get("uploader", ""),
                    "uploader_id": info.get("uploader_id", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "repost_count": info.get("repost_count", 0),
                    "comment_count": info.get("comment_count", 0),
                    "thumbnail": info.get("thumbnail", ""),
                    "timestamp": info.get("timestamp", 0),
                    "genre": info.get("genre", ""),
                    "track_number": info.get("track_number"),
                    "playlist": info.get("playlist", ""),
                    "playlist_count": info.get("playlist_count"),
                    "content_type": self._detect_content_type(url),
                }
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    # -------------------------------------------------------------------
    # Lifecycle Hooks
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid SoundCloud URL: {task.url}")
        out_dir = self._ensure_output_dir(task.output_path or self._output_dir)
        task.output_path = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.tags[0] if task.tags else "best"
        format_spec = self._resolve_format(quality)

        outtmpl = os.path.join(
            task.output_path or self._output_dir,
            "%(uploader)s - %(title)s [%(id)s].%(ext)s",
        )

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": outtmpl,
        })

        # Embed metadata for audio files
        ytdlp_opts["postprocessors"] = [
            {"key": "FFmpegMetadata"},
        ]

        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
                info = ydl.extract_info(task.url, download=True)
                if info:
                    result.metadata = {
                        "id": info.get("id", ""),
                        "title": info.get("title", ""),
                        "uploader": info.get("uploader", ""),
                        "duration": info.get("duration", 0),
                        "content_type": self._detect_content_type(task.url),
                    }
                    filename = ydl.prepare_filename(info)
                    if os.path.exists(filename):
                        result.output_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                    # Playlist entries
                    entries = info.get("entries", [])
                    if entries:
                        result.metadata["playlist_count"] = len(entries)
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
        quality_map = {
            "best": "bestaudio/best",
            "high": "bestaudio[abr<=320]/bestaudio/best",
            "medium": "bestaudio[abr<=128]/bestaudio/best",
            "low": "worstaudio/worst",
            "bestaudio": "bestaudio/best",
        }
        return quality_map.get(quality, "bestaudio/best")

    def on_verify(self, task=None, result=None):
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.output_path and os.path.exists(result.output_path):
            result.metadata["checksum"] = self._compute_checksum(result.output_path)
            result.metadata["checksum_algorithm"] = "sha256"
        return result

    def _compute_checksum(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="soundcloud",
        formats=frozenset(SoundCloudDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(SoundCloudDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "audio", "playlists", "sets", "artist_tracks",
            "cookie_auth", "goplus", "metadata_embedding",
        ]),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="SoundCloud downloader: audio, playlists, sets with metadata and cookie auth.",
    )
    return ("soundcloud", skill)
