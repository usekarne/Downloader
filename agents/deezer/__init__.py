"""
RS Downloader v10.0.0 - Deezer Download Agent
===============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Deezer downloader supporting:
- Track/album metadata via Deezer API
- 30-second preview downloads (MP3)
- Playlist info extraction
- Album artwork at multiple resolutions
- Artist discography metadata
- Podcast episode metadata
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
    AgentMemory,
    AgentSkill,
    DownloadError,
    DownloadPriority,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
)


class DeezerDownloader(DownloaderBase):
    """Deezer download agent for audio, playlists, and metadata.

    Uses Deezer's public API (api.deezer.com) for metadata and previews.
    Full track downloads require premium + yt-dlp fallback.
    Provides: metadata, 30s previews, artwork, playlist info.
    """

    AGENT_NAME = "deezer"
    PLATFORM = "deezer"
    SUPPORTED_FORMATS = ["mp3", "flac", "m4a", "mp4", "jpg", "json"]
    SUPPORTED_QUALITIES = [
        "preview", "flac", "mp3-320", "mp3-128",
        "metadata_only", "best", "worst",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.deezer\.com/\w{2}/track/\d+'),
        re.compile(r'https?://www\.deezer\.com/\w{2}/album/\d+'),
        re.compile(r'https?://www\.deezer\.com/\w{2}/playlist/\d+'),
        re.compile(r'https?://www\.deezer\.com/\w{2}/artist/\d+'),
        re.compile(r'https?://www\.deezer\.com/\w{2}/podcast/\d+'),
        re.compile(r'https?://www\.deezer\.com/\w{2}/episode/\d+'),
        re.compile(r'https?://deezer\.page\.link/'),
    ]

    _DEEZER_API = "https://api.deezer.com"

    def validate_url(self, url: str) -> bool:
        """Check if the URL is a valid Deezer URL."""
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_url(self, url: str) -> Tuple[str, str]:
        """Extract content type and ID from Deezer URL."""
        for ctype, pattern in [
            ("track", r'/track/(\d+)'),
            ("album", r'/album/(\d+)'),
            ("playlist", r'/playlist/(\d+)'),
            ("artist", r'/artist/(\d+)'),
            ("podcast", r'/podcast/(\d+)'),
            ("episode", r'/episode/(\d+)'),
        ]:
            m = re.search(pattern, url)
            if m:
                return ctype, m.group(1)
        return "unknown", ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Return available formats for Deezer content."""
        content_type, _ = self._parse_url(url)
        formats = [
            {"format_id": "preview", "ext": "mp3", "quality": "30s preview"},
            {"format_id": "artwork", "ext": "jpg", "quality": "cover art"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if content_type == "track":
            formats.insert(0, {"format_id": "flac", "ext": "flac",
                               "quality": "FLAC HiFi"})
            formats.insert(1, {"format_id": "mp3-320", "ext": "mp3",
                               "quality": "MP3 320kbps"})
        elif content_type == "album":
            formats.insert(0, {"format_id": "album-info", "ext": "json",
                               "quality": "album metadata + tracks"})
        elif content_type == "playlist":
            formats.insert(0, {"format_id": "playlist-info", "ext": "json",
                               "quality": "playlist metadata + tracks"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch metadata via Deezer public API."""
        import requests
        content_type, content_id = self._parse_url(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "deezer",
            "content_type": content_type, "id": content_id,
        }
        if not content_id or content_type == "unknown":
            return metadata
        try:
            endpoint = f"{self._DEEZER_API}/{content_type}/{content_id}"
            resp = requests.get(endpoint, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
            if "error" in data:
                metadata["error"] = data["error"].get("message", "API error")
                return metadata
            metadata.update({
                "title": data.get("title", ""),
                "artist": data.get("artist", {}).get("name", ""),
                "album": data.get("album", {}).get("title", ""),
                "duration": data.get("duration", 0),
                "preview_url": data.get("preview", ""),
                "artwork_url": self._artwork_hires(data.get("album", {}).get("cover_big", "")),
                "release_date": data.get("release_date", ""),
                "isrc": data.get("isrc", ""),
                "bpm": data.get("bpm", 0),
                "genre_id": data.get("genre_id", 0),
                "rank": data.get("rank", 0),
                "explicit": data.get("explicit_lyrics", False),
            })
            # For albums/playlists, fetch tracklist
            if content_type in ("album", "playlist"):
                tracks_resp = requests.get(
                    f"{endpoint}/tracks", timeout=self.timeout)
                if tracks_resp.status_code == 200:
                    tracks_data = tracks_resp.json().get("data", [])
                    metadata["tracks"] = [
                        {"title": t.get("title", ""),
                         "artist": t.get("artist", {}).get("name", ""),
                         "duration": t.get("duration", 0),
                         "preview_url": t.get("preview", "")}
                        for t in tracks_data
                    ]
                    metadata["num_tracks"] = len(tracks_data)
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _artwork_hires(url: str) -> str:
        """Get highest resolution artwork URL."""
        if not url:
            return ""
        return url.replace("/120x120", "/1400x1400").replace(
            "/250x250", "/1400x1400").replace("/500x500", "/1400x1400")

    def on_prepare(self, task: DownloadTask) -> None:
        """Prepare Deezer download."""
        if not self.validate_url(task.url):
            raise DownloadError(
                f"Invalid Deezer URL: {task.url}",
                url=task.url, agent=self.AGENT_NAME,
            )
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        content_type, content_id = self._parse_url(task.url)
        task.options["content_type"] = content_type
        task.options["content_id"] = content_id

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Download Deezer content."""
        quality = task.options.get("quality", "preview")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        if quality == "metadata_only":
            result = self._download_metadata(task, result)
        elif quality == "preview":
            result = self._download_preview(task, result)
        else:
            result = self._download_via_ytdlp(task, result, quality)
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_preview(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        """Download 30-second preview."""
        import requests
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            preview_url = metadata.get("preview_url", "")
            if not preview_url:
                result.status = DownloadStatus.FAILED
                result.error = "No preview available"
                return result
            out_dir = task.options.get("output_dir", self.output_dir)
            filename = self._safe_filename(
                f"{metadata.get('artist', 'unknown')} - {metadata.get('title', 'track')}.mp3")
            filepath = os.path.join(out_dir, filename)
            resp = requests.get(preview_url, timeout=self.timeout)
            resp.raise_for_status()
            with open(filepath, "wb") as f:
                f.write(resp.content)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = len(resp.content)
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        return result

    def _download_via_ytdlp(self, task: DownloadTask, result: DownloadResult,
                            quality: str) -> DownloadResult:
        """Download via yt-dlp for full tracks."""
        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        fmt_map = {"flac": "bestaudio", "mp3-320": "bestaudio",
                   "mp3-128": "worstaudio", "best": "bestaudio/best",
                   "worst": "worstaudio/worst"}
        format_spec = fmt_map.get(quality, "bestaudio/best")
        outtmpl = os.path.join(
            task.options.get("output_dir", self.output_dir),
            "%(title)s [%(id)s].%(ext)s",
        )
        cmd = [ytdlp_path, "-f", format_spec, "-o", outtmpl]
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
        cmd.append(task.url)
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout * 10)
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
        return result

    def _download_metadata(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            filename = self._safe_filename(
                f"{metadata.get('title', 'deezer')}_metadata.json")
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

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.file_path and os.path.exists(result.file_path):
            ext = os.path.splitext(result.file_path)[1].lower()
            if ext in (".mp3", ".flac", ".m4a") and result.metadata:
                self._tag_audio(result)
        return result

    def _tag_audio(self, result: DownloadResult) -> None:
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(result.file_path)
            if audio is None:
                return
            meta = result.metadata
            for key in ("title", "artist", "album"):
                if meta.get(key):
                    try:
                        audio[key] = meta[key]
                    except (KeyError, TypeError):
                        pass
            audio.save()
        except ImportError:
            pass
        except Exception:
            pass


def register() -> Tuple[str, AgentSkill]:
    """Register the Deezer agent."""
    skill = AgentSkill(
        platform="deezer",
        formats=tuple(DeezerDownloader.SUPPORTED_FORMATS),
        qualities=tuple(DeezerDownloader.SUPPORTED_QUALITIES),
        features=("previews", "playlists", "artwork", "deezer_api", "podcasts"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description=(
            "Deezer downloader: metadata API, 30s previews, playlists, "
            "artwork, full tracks via yt-dlp with cookies."
        ),
    )
    return ("deezer", skill)
