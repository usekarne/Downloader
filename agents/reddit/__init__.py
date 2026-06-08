"""
RS Downloader v10.0.0 - Reddit Download Agent
================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Reddit downloader supporting:
- Videos with audio merge (Reddit splits video/audio)
- Images and image galleries
- Audio-only extraction
- Comment thread metadata
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from core.downloader_base import (
    AgentSkill,
    DownloadError,
    DownloadPriority,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
)


class RedditDownloader(DownloaderBase):
    """
    Reddit download agent using yt-dlp and requests.

    Handles Reddit's separate video/audio streams by merging them,
    and supports image galleries and direct image downloads.
    """

    AGENT_NAME = "reddit"
    PLATFORM = "reddit"
    SUPPORTED_FORMATS = ["mp4", "webm", "mp3", "m4a", "jpg", "png", "gif", "webp"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low", "audio"]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?reddit\.com/r/\w+/comments/\w+/\w*'),
        re.compile(r'https?://(www\.)?reddit\.com/r/\w+/s/\w+'),
        re.compile(r'https?://v\.redd\.it/\w+'),
        re.compile(r'https?://old\.reddit\.com/r/\w+/comments/\w+/\w*'),
        re.compile(r'https?://(www\.)?reddit\.com/gallery/\w+'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 120)
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "RS-Downloader/10.0.0 (by /u/t3rmuxk1ng)",
        })
        if self._proxy:
            self._session.proxies = {"http": self._proxy, "https": self._proxy}

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        opts: Dict[str, Any] = {"quiet": True, "no_warnings": True}
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if self._proxy:
            opts["proxy"] = self._proxy
        if extra:
            opts.update(extra)
        return opts

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
                        "height": fmt.get("height", 0),
                        "filesize": fmt.get("filesize") or 0,
                        "vcodec": fmt.get("vcodec", "none"),
                        "acodec": fmt.get("acodec", "none"),
                    })
                return formats
        except Exception as exc:
            raise DownloadError(f"Failed to query formats: {exc}")

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch Reddit post metadata via JSON API."""
        json_url = url.rstrip("/") + ".json"
        try:
            resp = self._session.get(json_url, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()
            if not data or not isinstance(data, list):
                return {}
            post_data = data[0]["data"]["children"][0]["data"]
            return {
                "id": post_data.get("name", ""),
                "title": post_data.get("title", ""),
                "author": post_data.get("author", ""),
                "subreddit": post_data.get("subreddit", ""),
                "score": post_data.get("score", 0),
                "upvote_ratio": post_data.get("upvote_ratio", 0.0),
                "num_comments": post_data.get("num_comments", 0),
                "created_utc": post_data.get("created_utc", 0),
                "is_video": post_data.get("is_video", False),
                "is_gallery": post_data.get("is_gallery", False),
                "over_18": post_data.get("over_18", False),
                "url_overridden_by_dest": post_data.get("url_overridden_by_dest", ""),
                "thumbnail": post_data.get("thumbnail", ""),
            }
        except (requests.RequestException, KeyError, IndexError, json.JSONDecodeError) as exc:
            # Fallback to yt-dlp metadata
            opts = self._build_ytdlp_opts({"skip_download": True})
            try:
                import yt_dlp
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    return {
                        "id": info.get("id", ""),
                        "title": info.get("title", ""),
                        "author": info.get("uploader", ""),
                    } if info else {}
            except Exception:
                raise DownloadError(f"Failed to fetch metadata: {exc}")

    # -------------------------------------------------------------------
    # Lifecycle Hooks
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Reddit URL: {task.url}")
        out_dir = self._ensure_output_dir(
            task.output_path or self._output_dir
        )
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
            "merge_output_format": "mp4",
        })

        if quality == "audio":
            ytdlp_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "best"},
            ]

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
                        "id": info.get("id", ""),
                        "title": info.get("title", ""),
                        "uploader": info.get("uploader", ""),
                    }
                    filename = ydl.prepare_filename(info)
                    if quality == "audio":
                        for ext in ("m4a", "mp3", "opus"):
                            alt = os.path.splitext(filename)[0] + f".{ext}"
                            if os.path.exists(alt):
                                filename = alt
                                break
                    if os.path.exists(filename):
                        result.output_path = os.path.abspath(filename)
                        result.filename = os.path.basename(filename)
                        result.file_size = os.path.getsize(filename)
                    # Gallery entries
                    entries = info.get("entries", [])
                    if entries:
                        result.metadata["gallery_count"] = len(entries)
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
            "best": "bestvideo+bestaudio/best",
            "high": "best[height<=1080]",
            "medium": "best[height<=720]",
            "low": "best[height<=480]",
            "audio": "bestaudio/best",
        }
        return quality_map.get(quality, "bestvideo+bestaudio/best")

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
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
    """Register the Reddit agent."""
    skill = AgentSkill(
        platform="reddit",
        formats=frozenset(RedditDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(RedditDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "video", "audio_merge", "images", "galleries",
            "reddit_api", "cookie_auth",
        ]),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Reddit downloader: videos with audio merge, images, galleries via yt-dlp + API.",
    )
    return ("reddit", skill)
