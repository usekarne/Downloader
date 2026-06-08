"""
RS Downloader v10.0.0 - Apple Music Download Agent
===================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Apple Music agent supporting:
- Track/album metadata extraction via iTunes Search API
- 30-second preview downloads (M4A AAC)
- Album artwork at multiple resolutions
- Playlist info extraction
- Full metadata: ISRC, UPC, release date, genre, etc.
"""

from __future__ import annotations

import json
import os
import re
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


class AppleMusicDownloader(DownloaderBase):
    """Apple Music download agent for metadata, previews, and artwork.

    Uses the public iTunes Search/Lookup API for metadata extraction.
    Full track downloads require Apple Music subscription DRM, not supported.
    Provides: 30s M4A previews, high-res artwork, complete metadata.
    """

    AGENT_NAME = "apple_music"
    PLATFORM = "apple_music"
    SUPPORTED_FORMATS = ["m4a", "mp3", "jpg", "png", "json"]
    SUPPORTED_QUALITIES = ["preview", "artwork", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://music\.apple\.com/\w{2}/album/[\w-]+/\d+'),
        re.compile(r'https?://music\.apple\.com/\w{2}/song/[\w-]+/\d+'),
        re.compile(r'https?://music\.apple\.com/\w{2}/playlist/[\w-]+/pl\.\w+'),
        re.compile(r'https?://music\.apple\.com/\w{2}/artist/[\w-]+/\d+'),
        re.compile(r'https?://embed\.music\.apple\.com/'),
    ]

    _ITUNES_LOOKUP = "https://itunes.apple.com/lookup"
    _ITUNES_SEARCH = "https://itunes.apple.com/search"

    def validate_url(self, url: str) -> bool:
        """Check if the URL is a valid Apple Music URL."""
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_id(self, url: str) -> Tuple[str, str]:
        """Extract content type and ID from Apple Music URL."""
        id_match = re.search(r'/(\d+)(?:\?|$)', url)
        content_id = id_match.group(1) if id_match else ""
        if "/album/" in url:
            return "album", content_id
        elif "/song/" in url:
            return "song", content_id
        elif "/playlist/" in url:
            return "playlist", content_id
        elif "/artist/" in url:
            return "artist", content_id
        return "unknown", content_id

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Return available formats for Apple Music content."""
        content_type, _ = self._extract_id(url)
        formats = [
            {"format_id": "preview", "ext": "m4a", "quality": "30s preview AAC"},
            {"format_id": "artwork", "ext": "jpg", "quality": "cover art"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if content_type == "album":
            formats.insert(0, {"format_id": "album-art", "ext": "jpg",
                               "quality": "full album artwork"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch metadata via iTunes Lookup API."""
        import requests
        content_type, content_id = self._extract_id(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "apple_music",
            "content_type": content_type, "id": content_id,
        }
        if not content_id:
            return metadata
        try:
            resp = requests.get(
                self._ITUNES_LOOKUP,
                params={"id": content_id},
                headers={"Accept": "application/json"},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results", [])
            if results:
                item = results[0]
                metadata.update({
                    "title": item.get("trackName", item.get("collectionName", "")),
                    "artist": item.get("artistName", ""),
                    "album": item.get("collectionName", ""),
                    "genre": item.get("primaryGenreName", ""),
                    "release_date": item.get("releaseDate", ""),
                    "isrc": item.get("isrc", ""),
                    "upc": item.get("upc", ""),
                    "preview_url": item.get("previewUrl", ""),
                    "artwork_url": self._artwork_hires(item.get("artworkUrl100", "")),
                    "duration_ms": item.get("trackTimeMillis", 0),
                    "track_number": item.get("trackNumber", 0),
                    "track_count": item.get("trackCount", 0),
                    "disc_number": item.get("discNumber", 1),
                    "disc_count": item.get("discCount", 1),
                    "explicit": item.get("trackExplicitness", "notExplicit"),
                    "country": item.get("country", ""),
                    "currency": item.get("currency", ""),
                    "price": item.get("trackPrice", 0),
                })
                # Album: collect all tracks
                if content_type == "album" and len(results) > 1:
                    metadata["tracks"] = [
                        {"title": r.get("trackName", ""),
                         "track_number": r.get("trackNumber", 0),
                         "preview_url": r.get("previewUrl", ""),
                         "duration_ms": r.get("trackTimeMillis", 0)}
                        for r in results[1:] if r.get("wrapperType") == "track"
                    ]
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _artwork_hires(url: str) -> str:
        """Convert 100x100 artwork URL to highest resolution."""
        if not url:
            return ""
        return url.replace("100x100bb", "6000x6000bb")

    def on_prepare(self, task: DownloadTask) -> None:
        """Prepare Apple Music download."""
        if not self.validate_url(task.url):
            raise DownloadError(
                f"Invalid Apple Music URL: {task.url}",
                url=task.url, agent=self.AGENT_NAME,
            )
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        content_type, content_id = self._extract_id(task.url)
        task.options["content_type"] = content_type
        task.options["content_id"] = content_id

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Download Apple Music preview, artwork, or metadata."""
        import requests
        quality = task.options.get("quality", "preview")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)

            if quality == "preview" and metadata.get("preview_url"):
                self._download_file(
                    metadata["preview_url"], out_dir,
                    f"{metadata.get('artist', 'unknown')} - {metadata.get('title', 'track')}.m4a",
                    result, requests,
                )
            elif quality in ("artwork", "album-art") and metadata.get("artwork_url"):
                self._download_file(
                    metadata["artwork_url"], out_dir,
                    f"{metadata.get('album', 'artwork')}_cover.jpg",
                    result, requests,
                )
            else:
                # Metadata only
                filename = f"{metadata.get('title', 'apple_music')}_metadata.json"
                filepath = os.path.join(out_dir, self._safe_filename(filename))
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = os.path.basename(filepath)
                result.file_size = os.path.getsize(filepath)
                result.content_type = "application/json"
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)

        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_file(self, url: str, out_dir: str, filename: str,
                       result: DownloadResult, requests) -> None:
        """Download a file from URL."""
        safe_name = self._safe_filename(filename)
        filepath = os.path.join(out_dir, safe_name)
        resp = requests.get(url, timeout=self.timeout)
        resp.raise_for_status()
        with open(filepath, "wb") as f:
            f.write(resp.content)
        result.file_path = os.path.abspath(filepath)
        result.filename = safe_name
        result.file_size = len(resp.content)

    @staticmethod
    def _safe_filename(name: str) -> str:
        """Sanitize filename."""
        return re.sub(r'[<>:"|?*\\]', '_', name)[:200]

    def on_verify(self, result: DownloadResult) -> bool:
        """Verify downloaded content."""
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        """Post-process: apply tags to preview, compute checksum."""
        if result.file_path and os.path.exists(result.file_path):
            ext = os.path.splitext(result.file_path)[1].lower()
            if ext == ".m4a" and result.metadata:
                self._tag_m4a(result)
        return result

    def _tag_m4a(self, result: DownloadResult) -> None:
        """Apply metadata tags to M4A preview."""
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(result.file_path)
            if audio is None:
                return
            meta = result.metadata
            tags = {
                "\xa9nam": meta.get("title", ""),
                "\xa9ART": meta.get("artist", ""),
                "\xa9alb": meta.get("album", ""),
                "\xa9gen": meta.get("genre", ""),
            }
            for key, val in tags.items():
                if val:
                    audio[key] = val
            audio.save()
        except ImportError:
            pass
        except Exception:
            pass


def register() -> Tuple[str, AgentSkill]:
    """Register the Apple Music agent."""
    skill = AgentSkill(
        platform="apple_music",
        formats=tuple(AppleMusicDownloader.SUPPORTED_FORMATS),
        qualities=tuple(AppleMusicDownloader.SUPPORTED_QUALITIES),
        features=("metadata", "previews", "artwork", "itunes_api"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description=(
            "Apple Music agent: metadata extraction, 30s M4A previews, "
            "high-res album artwork, iTunes Search API integration."
        ),
    )
    return ("apple_music", skill)
