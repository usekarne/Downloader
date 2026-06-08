"""
RS Downloader v10.0.0 - Spotify Download Agent
==================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Spotify downloader supporting:
- Track metadata extraction (via Spotify Web API)
- Playlist info and track listing
- Album metadata
- yt-dlp fallback for actual audio download
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
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


class SpotifyDownloader(DownloaderBase):
    """
    Spotify download agent using requests for metadata and yt-dlp fallback.

    Spotify does not provide direct audio downloads. This agent:
    1. Extracts track/playlist/album metadata via Spotify Web API
    2. Falls back to yt-dlp to search and download from YouTube
    """

    AGENT_NAME = "spotify"
    PLATFORM = "spotify"
    SUPPORTED_FORMATS = ["mp3", "m4a", "opus", "ogg", "wav", "flac"]
    SUPPORTED_QUALITIES = ["best", "high", "medium", "low"]

    _URL_PATTERNS = [
        re.compile(r'https?://open\.spotify\.com/track/[\w]+'),
        re.compile(r'https?://open\.spotify\.com/playlist/[\w]+'),
        re.compile(r'https?://open\.spotify\.com/album/[\w]+'),
        re.compile(r'https?://open\.spotify\.com/artist/[\w]+'),
        re.compile(r'https?://open\.spotify\.com/episode/[\w]+'),
        re.compile(r'https?://open\.spotify\.com/show/[\w]+'),
    ]

    _SPOTIFY_API_BASE = "https://api.spotify.com/v1"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._client_id = kwargs.get("spotify_client_id")
        self._client_secret = kwargs.get("spotify_client_secret")
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 120)
        self._session = requests.Session()
        if self._proxy:
            self._session.proxies = {"http": self._proxy, "https": self._proxy}
        self._access_token: Optional[str] = None

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def _authenticate(self) -> None:
        """Authenticate with Spotify Web API using client credentials."""
        if not self._client_id or not self._client_secret:
            return
        try:
            resp = self._session.post(
                "https://accounts.spotify.com/api/token",
                data={"grant_type": "client_credentials"},
                auth=(self._client_id, self._client_secret),
                timeout=self._timeout,
            )
            resp.raise_for_status()
            self._access_token = resp.json().get("access_token")
        except requests.RequestException as exc:
            raise DownloadError(f"Spotify auth failed: {exc}")

    def _api_headers(self) -> Dict[str, str]:
        """Get authorization headers for Spotify API."""
        if not self._access_token:
            self._authenticate()
        return {"Authorization": f"Bearer {self._access_token}"}

    def _detect_content_type(self, url: str) -> str:
        if "/track/" in url:
            return "track"
        if "/playlist/" in url:
            return "playlist"
        if "/album/" in url:
            return "album"
        if "/artist/" in url:
            return "artist"
        if "/episode/" in url:
            return "episode"
        if "/show/" in url:
            return "show"
        return "unknown"

    def _extract_id(self, url: str) -> str:
        """Extract Spotify ID from URL."""
        match = re.search(r'/([\w]+)(?:\?|$)', url)
        return match.group(1) if match else ""

    # -------------------------------------------------------------------
    # URL Validation
    # -------------------------------------------------------------------

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    # -------------------------------------------------------------------
    # Format Discovery
    # -------------------------------------------------------------------

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Spotify doesn't offer direct format selection; returns metadata-based formats."""
        content_type = self._detect_content_type(url)
        return [{
            "format_id": "yt-dlp-search",
            "ext": ext,
            "quality": quality,
            "note": f"Downloaded via YouTube search (Spotify {content_type})",
        } for ext in self.SUPPORTED_FORMATS
          for quality in self.SUPPORTED_QUALITIES[:2]]

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch metadata from Spotify Web API."""
        content_type = self._detect_content_type(url)
        spotify_id = self._extract_id(url)

        if not self._client_id or not self._client_secret:
            return self._metadata_fallback(url, content_type)

        try:
            headers = self._api_headers()
            endpoint = f"{self._SPOTIFY_API_BASE}/{content_type}s/{spotify_id}"
            resp = self._session.get(endpoint, headers=headers, timeout=self._timeout)
            resp.raise_for_status()
            data = resp.json()

            if content_type == "track":
                return self._parse_track_metadata(data)
            elif content_type == "playlist":
                return self._parse_playlist_metadata(data)
            elif content_type == "album":
                return self._parse_album_metadata(data)
            return {"id": spotify_id, "type": content_type}
        except requests.RequestException as exc:
            raise DownloadError(f"Spotify API error: {exc}")

    def _metadata_fallback(self, url: str, content_type: str) -> Dict[str, Any]:
        """Fallback metadata when API credentials aren't available."""
        return {
            "id": self._extract_id(url),
            "type": content_type,
            "note": "API credentials not configured; limited metadata",
        }

    @staticmethod
    def _parse_track_metadata(data: Dict) -> Dict[str, Any]:
        artists = data.get("artists", [])
        album = data.get("album", {})
        return {
            "id": data.get("id", ""),
            "title": data.get("name", ""),
            "artist": ", ".join(a.get("name", "") for a in artists),
            "album": album.get("name", ""),
            "album_artist": ", ".join(a.get("name", "") for a in album.get("artists", [])),
            "release_date": album.get("release_date", ""),
            "duration_ms": data.get("duration_ms", 0),
            "track_number": data.get("track_number"),
            "disc_number": data.get("disc_number"),
            "popularity": data.get("popularity", 0),
            "isrc": data.get("external_ids", {}).get("isrc", ""),
            "thumbnail": max(
                (i for i in album.get("images", [])),
                key=lambda i: i.get("width", 0),
            ).get("url", "") if album.get("images") else "",
            "preview_url": data.get("preview_url", ""),
            "type": "track",
        }

    @staticmethod
    def _parse_playlist_metadata(data: Dict) -> Dict[str, Any]:
        return {
            "id": data.get("id", ""),
            "title": data.get("name", ""),
            "description": data.get("description", ""),
            "owner": data.get("owner", {}).get("display_name", ""),
            "track_count": data.get("tracks", {}).get("total", 0),
            "public": data.get("public", False),
            "followers": data.get("followers", {}).get("total", 0),
            "type": "playlist",
        }

    @staticmethod
    def _parse_album_metadata(data: Dict) -> Dict[str, Any]:
        artists = data.get("artists", [])
        return {
            "id": data.get("id", ""),
            "title": data.get("name", ""),
            "artist": ", ".join(a.get("name", "") for a in artists),
            "release_date": data.get("release_date", ""),
            "total_tracks": data.get("total_tracks", 0),
            "label": data.get("label", ""),
            "type": "album",
        }

    # -------------------------------------------------------------------
    # Lifecycle Hooks
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Spotify URL: {task.url}")
        out_dir = self._ensure_output_dir(task.output_path or self._output_dir)
        task.output_path = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Download via yt-dlp by searching YouTube with track metadata."""
        content_type = self._detect_content_type(task.url)
        metadata = self.get_metadata(task.url)

        # Build search query from metadata
        if content_type == "track" and metadata.get("title"):
            search_query = f"{metadata.get('artist', '')} - {metadata['title']}"
        elif content_type == "episode" and metadata.get("title"):
            search_query = metadata["title"]
        else:
            search_query = metadata.get("title", task.url)

        yt_url = f"ytsearch1:{search_query}"

        outtmpl = os.path.join(
            task.output_path or self._output_dir,
            f"{search_query} [%(id)s].%(ext)s",
        )

        ytdlp_opts = {
            "quiet": True,
            "no_warnings": True,
            "format": "bestaudio/best",
            "outtmpl": outtmpl,
            "postprocessors": [
                {"key": "FFmpegExtractAudio", "preferredcodec": "best"},
                {"key": "FFmpegMetadata"},
            ],
        }
        if self._proxy:
            ytdlp_opts["proxy"] = self._proxy

        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )

        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(ytdlp_opts) as ydl:
                info = ydl.extract_info(yt_url, download=True)
                if info:
                    entries = info.get("entries", [])
                    entry = entries[0] if entries else info
                    result.metadata = metadata
                    result.metadata["youtube_id"] = entry.get("id", "")
                    result.metadata["download_method"] = "yt-dlp-search"
                    filename = ydl.prepare_filename(entry)
                    for ext in ("m4a", "mp3", "opus", "ogg"):
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
            result.error = "yt-dlp required for Spotify downloads"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)

        result.elapsed = time.monotonic() - start_time
        return result

    def on_verify(self, task=None, result=None):
        if not result.output_path or not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.output_path and os.path.exists(result.output_path):
            result.metadata["checksum"] = self._compute_checksum(result.output_path)
        return result

    def _compute_checksum(self, filepath: str) -> str:
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="spotify",
        formats=frozenset(SpotifyDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(SpotifyDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "metadata", "playlists", "albums", "artists",
            "yt-dlp_fallback", "spotify_api", "episodes",
        ]),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Spotify downloader: metadata via API, audio via yt-dlp YouTube search fallback.",
    )
    return ("spotify", skill)
