"""
RS Downloader v10.0.0 - Amazon Music Download Agent
====================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Amazon Music agent supporting:
- Track/album metadata extraction
- 30-second preview downloads (MP3)
- Album artwork at highest resolution
- Playlist info extraction
- Artist discography metadata
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


class AmazonMusicDownloader(DownloaderBase):
    """Amazon Music download agent for metadata, previews, and artwork.

    Uses public Amazon Music pages for metadata extraction.
    Full track downloads require Amazon Music subscription DRM, not supported.
    Provides: 30s MP3 previews, high-res artwork, complete metadata.
    """

    AGENT_NAME = "amazon_music"
    PLATFORM = "amazon_music"
    SUPPORTED_FORMATS = ["mp3", "m4a", "jpg", "png", "json"]
    SUPPORTED_QUALITIES = ["preview", "artwork", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://music\.amazon\.\w+/albums/[\w-]+'),
        re.compile(r'https?://music\.amazon\.\w+/tracks/[\w-]+'),
        re.compile(r'https?://music\.amazon\.\w+/playlists/[\w-]+'),
        re.compile(r'https?://music\.amazon\.\w+/artists/[\w-]+'),
        re.compile(r'https?://music\.amazon\.\w+/albums/[\w]+'),
        re.compile(r'https?://www\.amazon\.\w+/dp/[\w]+'),
    ]

    def validate_url(self, url: str) -> bool:
        """Check if the URL is a valid Amazon Music URL."""
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_url(self, url: str) -> Tuple[str, str]:
        """Extract content type and ID from URL."""
        for ctype, pattern in [
            ("album", r'/albums/([\w-]+)'),
            ("track", r'/tracks/([\w-]+)'),
            ("playlist", r'/playlists/([\w-]+)'),
            ("artist", r'/artists/([\w-]+)'),
            ("dp", r'/dp/([\w]+)'),
        ]:
            m = re.search(pattern, url)
            if m:
                return ctype, m.group(1)
        return "unknown", ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Return available formats for Amazon Music content."""
        content_type, _ = self._parse_url(url)
        formats = [
            {"format_id": "preview", "ext": "mp3", "quality": "30s preview"},
            {"format_id": "artwork", "ext": "jpg", "quality": "cover art"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if content_type == "album":
            formats.insert(0, {"format_id": "album-info", "ext": "json",
                               "quality": "album metadata"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch metadata from Amazon Music page."""
        import requests
        content_type, content_id = self._parse_url(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "amazon_music",
            "content_type": content_type, "id": content_id,
        }
        try:
            resp = requests.get(
                url,
                headers=self._browser_headers(),
                timeout=self.timeout,
            )
            if resp.status_code != 200:
                metadata["error"] = f"HTTP {resp.status_code}"
                return metadata
            text = resp.text
            # Extract structured data from JSON-LD
            ld_match = re.search(
                r'<script\s+type="application/ld\+json">\s*({.*?})\s*</script>',
                text, re.DOTALL,
            )
            if ld_match:
                try:
                    ld_data = json.loads(ld_match.group(1))
                    metadata["title"] = ld_data.get("name", "")
                    metadata["artist"] = ld_data.get("byArtist", {}).get("name", "")
                    metadata["genre"] = ld_data.get("genre", "")
                    metadata["release_date"] = ld_data.get("datePublished", "")
                    img = ld_data.get("image", "")
                    if isinstance(img, list):
                        img = img[0] if img else ""
                    metadata["artwork_url"] = img
                except json.JSONDecodeError:
                    pass
            # Extract from og:meta tags
            for tag, key in [
                (r'og:title', "title"),
                (r'og:image', "thumbnail"),
                (r'og:description', "description"),
            ]:
                m = re.search(
                    rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                if m and not metadata.get(key):
                    metadata[key] = m.group(1)
            # Try to extract preview URL
            preview_m = re.search(r'"previewUrl"\s*:\s*"([^"]+)"', text)
            if preview_m:
                metadata["preview_url"] = preview_m.group(1).replace("\\/", "/")
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
            "Accept": "text/html,application/xhtml+xml",
        }

    def on_prepare(self, task: DownloadTask) -> None:
        """Prepare Amazon Music download."""
        if not self.validate_url(task.url):
            raise DownloadError(
                f"Invalid Amazon Music URL: {task.url}",
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
        """Download Amazon Music content (preview, artwork, or metadata)."""
        import requests
        quality = task.options.get("quality", "metadata_only")
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
                    f"{metadata.get('artist', 'unknown')} - {metadata.get('title', 'track')}.mp3",
                    result, requests,
                )
            elif quality == "artwork" and metadata.get("artwork_url"):
                self._download_file(
                    metadata["artwork_url"], out_dir,
                    f"{metadata.get('title', 'artwork')}_cover.jpg",
                    result, requests,
                )
            else:
                filename = self._safe_filename(
                    f"{metadata.get('title', 'amazon_music')}_metadata.json")
                filepath = os.path.join(out_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
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
        return re.sub(r'[<>:"|?*\\]', '_', name)[:200]

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.file_path and os.path.exists(result.file_path):
            pass  # Checksum, tagging handled by base
        return result


def register() -> Tuple[str, AgentSkill]:
    """Register the Amazon Music agent."""
    skill = AgentSkill(
        platform="amazon_music",
        formats=tuple(AmazonMusicDownloader.SUPPORTED_FORMATS),
        qualities=tuple(AmazonMusicDownloader.SUPPORTED_QUALITIES),
        features=("metadata", "previews", "artwork"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description=(
            "Amazon Music agent: metadata, 30s MP3 previews, artwork, "
            "playlist info, artist discography."
        ),
    )
    return ("amazon_music", skill)
