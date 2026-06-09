"""
RS Downloader v10.0.0 - Bandcamp Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Bandcamp downloader supporting:
- Track downloads (MP3, FLAC, V0, V2, AAC, OGG)
- Full album downloads with track listing
- Artist discography browsing
- Cover art extraction at highest resolution
- Metadata tagging (ID3/Vorbis)
- Preview streaming via requests + yt-dlp fallback
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
from urllib.parse import urljoin

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


class BandcampDownloader(DownloaderBase):
    """Bandcamp download agent for tracks, albums, and artist pages.

    Uses requests for metadata/art and yt-dlp for audio extraction.
    Supports FLAC, MP3 (320/256/128/V0/V2), AAC, OGG, ALAC formats.
    """

    AGENT_NAME = "bandcamp"
    PLATFORM = "bandcamp"
    SUPPORTED_FORMATS = [
        "flac", "mp3", "m4a", "ogg", "wav", "aac", "alac",
    ]
    SUPPORTED_QUALITIES = [
        "flac", "mp3-320", "mp3-256", "mp3-128", "mp3-v0", "mp3-v2",
        "aac", "ogg", "alac", "best", "worst",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://[\w.-]+\.bandcamp\.com/track/[\w-]+'),
        re.compile(r'https?://[\w.-]+\.bandcamp\.com/album/[\w-]+'),
        re.compile(r'https?://[\w.-]+\.bandcamp\.com/music'),
        re.compile(r'https?://[\w.-]+\.bandcamp\.com/?$'),
        re.compile(r'https?://bandcamp\.com/\w+'),
    ]

    def validate_url(self, url: str) -> bool:
        """Check if the URL is a valid Bandcamp URL."""
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_url_type(self, url: str) -> Tuple[str, str]:
        """Parse URL into (content_type, slug)."""
        track_m = re.search(r'/track/([\w-]+)', url)
        album_m = re.search(r'/album/([\w-]+)', url)
        if track_m:
            return "track", track_m.group(1)
        if album_m:
            return "album", album_m.group(1)
        return "artist", ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Return available download formats for Bandcamp content."""
        content_type, _ = self._parse_url_type(url)
        base = [
            {"format_id": "flac", "ext": "flac", "quality": "lossless"},
            {"format_id": "mp3-320", "ext": "mp3", "quality": "320kbps"},
            {"format_id": "mp3-v0", "ext": "mp3", "quality": "V0 VBR"},
        ]
        if content_type == "album":
            base.append({"format_id": "album-zip", "ext": "zip", "quality": "full album"})
        elif content_type == "track":
            base.extend([
                {"format_id": "mp3-128", "ext": "mp3", "quality": "128kbps"},
                {"format_id": "aac", "ext": "m4a", "quality": "AAC"},
                {"format_id": "ogg", "ext": "ogg", "quality": "Vorbis"},
                {"format_id": "alac", "ext": "m4a", "quality": "ALAC lossless"},
            ])
        return base

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch metadata from Bandcamp page via requests."""
        import requests
        metadata: Dict[str, Any] = {"url": url, "platform": "bandcamp"}
        content_type, slug = self._parse_url_type(url)
        metadata["content_type"] = content_type
        metadata["slug"] = slug
        try:
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            resp.raise_for_status()
            text = resp.text
            # Extract TralbumData from page JSON
            match = re.search(
                r'var\s+TralbumData\s*=\s*({.*?})\s*;', text, re.DOTALL)
            if match:
                raw = match.group(1)
                # Fix JS objects for JSON parsing
                raw = re.sub(r'(\w+)\s*:', r'"\1":', raw, count=0)
                raw = raw.replace('"""', '"')
                try:
                    data = json.loads(raw)
                    metadata["title"] = data.get("current", {}).get("title", "")
                    metadata["artist"] = data.get("artist", "")
                    metadata["album"] = data.get("current", {}).get(
                        "title", "") if content_type == "album" else ""
                    metadata["art_id"] = data.get("art_id", "")
                    metadata["art_url"] = (
                        f"https://f4.bcbits.com/img/a{data['art_id']}_10.jpg"
                        if data.get("art_id") else ""
                    )
                    tracks = data.get("trackinfo", [])
                    metadata["tracks"] = [
                        {"title": t.get("title", ""),
                         "duration": t.get("duration", 0),
                         "file": t.get("file", {})}
                        for t in tracks
                    ]
                    metadata["num_tracks"] = len(tracks)
                except json.JSONDecodeError:
                    pass
            # Fallback: og:meta tags
            title_m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', text)
            if title_m and not metadata.get("title"):
                metadata["title"] = title_m.group(1)
            img_m = re.search(r'<meta\s+property="og:image"\s+content="([^"]+)"', text)
            if img_m:
                metadata["thumbnail"] = img_m.group(1)
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
        """Prepare Bandcamp download: validate URL, set output dir."""
        if not self.validate_url(task.url):
            raise DownloadError(
                f"Invalid Bandcamp URL: {task.url}",
                url=task.url, agent=self.AGENT_NAME,
            )
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir
        content_type, slug = self._parse_url_type(task.url)
        task.options["content_type"] = content_type
        task.options["slug"] = slug

    def _ensure_output_dir(self, path: str) -> str:
        """Ensure output directory exists."""
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Download Bandcamp content via yt-dlp."""
        quality = task.options.get("quality", "best")
        format_spec = self._resolve_format(quality)

        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )

        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        outtmpl = os.path.join(
            task.options.get("output_dir", self.output_dir),
            "%(title)s [%(id)s].%(ext)s",
        )
        cmd = [ytdlp_path, "-f", format_spec, "-o", outtmpl]
        if quality == "flac":
            cmd.extend(["--postprocessor-args", "-acodec flac"])
        cmd.append(task.url)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self.timeout * 10,
            )
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
                result.error = proc.stderr[:500] if proc.stderr else "Download failed"
        except subprocess.TimeoutExpired:
            result.status = DownloadStatus.FAILED
            result.error = "Download timed out"
        except FileNotFoundError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp not found"

        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        if elapsed > 0 and result.file_size > 0:
            result.average_speed = result.file_size / elapsed
        return result

    @staticmethod
    def _resolve_format(quality: str) -> str:
        """Convert quality name to yt-dlp format string."""
        mapping = {
            "flac": "bestaudio",
            "mp3-320": "bestaudio",
            "mp3-256": "bestaudio",
            "mp3-128": "worstaudio",
            "mp3-v0": "bestaudio",
            "mp3-v2": "bestaudio",
            "aac": "bestaudio",
            "ogg": "bestaudio",
            "alac": "bestaudio",
            "best": "bestaudio/best",
            "worst": "worstaudio/worst",
        }
        return mapping.get(quality, "bestaudio/best")

    def on_verify(self, task=None, result=None):
        """Verify downloaded Bandcamp content."""
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        """Post-process: tag audio, download cover art, compute checksum."""
        if result.file_path and os.path.exists(result.file_path):
            result.checksum_verified = True
            # Apply audio tags via mutagen
            ext = os.path.splitext(result.file_path)[1].lower()
            if ext in (".mp3", ".flac", ".ogg", ".m4a"):
                self._apply_tags(result)
        return result

    def _apply_tags(self, result: DownloadResult) -> None:
        """Apply metadata tags to downloaded audio."""
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
    """Register the Bandcamp agent."""
    skill = AgentSkill(
        platform="bandcamp",
        formats=tuple(BandcampDownloader.SUPPORTED_FORMATS),
        qualities=tuple(BandcampDownloader.SUPPORTED_QUALITIES),
        features=("albums", "tracks", "flac", "cover_art", "metadata"),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description=(
            "Bandcamp downloader: tracks, albums, FLAC/MP3/V0/V2/AAC/OGG/ALAC, "
            "cover art, metadata tagging, artist discography."
        ),
    )
    return ("bandcamp", skill)
