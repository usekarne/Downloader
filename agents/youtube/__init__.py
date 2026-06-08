"""
RS Downloader v10.0.0 - YouTube Download Agent
================================================

Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Full-featured YouTube downloader supporting:
- Video (240p through 8K), audio (all formats)
- Playlists, livestreams, shorts
- Subtitles, thumbnails, metadata extraction
- Chapter splitting, SponsorBlock integration
- Age-gate bypass, cookie authentication
- Proxy support, custom headers
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
    AgentMemory,
    AgentSkill,
    DownloadError,
    DownloadPriority,
    DownloadResult,
    DownloadStatus,
    DownloadTask,
    DownloaderBase,
)


class YouTubeDownloader(DownloaderBase):
    """
    YouTube download agent powered by yt-dlp.

    Supports video downloads from 240p to 8K, audio extraction in all
    available formats, playlist batch downloads, livestream recording,
    subtitle extraction, thumbnail downloads, chapter splitting,
    SponsorBlock segment removal, age-gate bypass via cookies,
    and full proxy/header customization.
    """

    AGENT_NAME = "youtube"
    PLATFORM = "youtube"
    SUPPORTED_FORMATS = [
        "mp4", "webm", "mkv", "flv", "3gp",
        "mp3", "m4a", "opus", "ogg", "wav", "flac", "aac",
    ]
    SUPPORTED_QUALITIES = [
        "8K", "4K", "1440p", "1080p", "720p", "480p",
        "360p", "240p", "144p",
        "best", "bestaudio", "worst", "worstaudio",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://(www\.)?youtube\.com/watch\?'),
        re.compile(r'https?://(www\.)?youtube\.com/shorts/'),
        re.compile(r'https?://(www\.)?youtube\.com/embed/'),
        re.compile(r'https?://(www\.)?youtube\.com/playlist\?'),
        re.compile(r'https?://(www\.)?youtube\.com/live/'),
        re.compile(r'https?://(www\.)?youtube\.com/@[\w.-]+'),
        re.compile(r'https?://youtu\.be/'),
        re.compile(r'https?://music\.youtube\.com/watch\?'),
        re.compile(r'https?://m\.youtube\.com/watch\?'),
    ]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._ytdlp_path = self._find_ytdlp()
        self._cookies = kwargs.get("cookies")
        self._proxy = kwargs.get("proxy")
        self._output_dir = kwargs.get("output_dir", "downloads")
        self._timeout = kwargs.get("timeout", 600)

    @staticmethod
    def _find_ytdlp() -> str:
        """Locate yt-dlp binary on the system."""
        for candidate in ("yt-dlp", "yt_dlp"):
            path = shutil.which(candidate)
            if path:
                return path
        return "yt-dlp"

    def _ensure_output_dir(self, path: str) -> str:
        """Ensure output directory exists."""
        os.makedirs(path, exist_ok=True)
        return path

    def _build_ytdlp_opts(self, extra: Optional[Dict] = None) -> Dict:
        """Build yt-dlp options dict with common defaults."""
        opts: Dict[str, Any] = {
            "quiet": True,
            "no_warnings": True,
            "nocheckcertificate": True,
            "noplaylist": False,
        }
        if self._proxy:
            opts["proxy"] = self._proxy
        if self._cookies:
            opts["cookiefile"] = self._cookies
        if extra:
            opts.update(extra)
        return opts

    def _compute_checksum(self, filepath: str) -> str:
        """Compute SHA-256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    # -------------------------------------------------------------------
    # URL Validation
    # -------------------------------------------------------------------

    def validate_url(self, url: str) -> bool:
        """Check if the URL is a valid YouTube URL."""
        return any(pattern.match(url) for pattern in self._URL_PATTERNS)

    # -------------------------------------------------------------------
    # Format Discovery
    # -------------------------------------------------------------------

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        """Query all available formats for the given YouTube URL."""
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
                        "quality": self._quality_label(fmt),
                        "fps": fmt.get("fps"),
                        "vcodec": fmt.get("vcodec", "none"),
                        "acodec": fmt.get("acodec", "none"),
                        "filesize": fmt.get("filesize") or fmt.get("filesize_approx", 0),
                        "tbr": fmt.get("tbr", 0),
                        "vbr": fmt.get("vbr", 0),
                        "abr": fmt.get("abr", 0),
                        "width": fmt.get("width", 0),
                        "height": fmt.get("height", 0),
                    })
                return formats
        except ImportError:
            return self._formats_via_cli(url)
        except Exception as exc:
            raise DownloadError(
                f"Failed to query formats: {exc}",
            )

    def _formats_via_cli(self, url: str) -> List[Dict[str, Any]]:
        """Fallback: query formats using yt-dlp CLI."""
        try:
            cmd = [self._ytdlp_path, "-J", "--no-download", url]
            if self._proxy:
                cmd.extend(["--proxy", self._proxy])
            if self._cookies:
                cmd.extend(["--cookiefile", self._cookies])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout,
            )
            if result.returncode != 0:
                return []
            data = json.loads(result.stdout)
            formats = []
            for fmt in data.get("formats", []):
                formats.append({
                    "format_id": fmt.get("format_id", ""),
                    "ext": fmt.get("ext", ""),
                    "quality": self._quality_label(fmt),
                    "vcodec": fmt.get("vcodec", "none"),
                    "acodec": fmt.get("acodec", "none"),
                    "filesize": fmt.get("filesize") or fmt.get("filesize_approx", 0),
                    "height": fmt.get("height", 0),
                })
            return formats
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return []

    @staticmethod
    def _quality_label(fmt: Dict) -> str:
        """Generate a human-readable quality label from format info."""
        height = fmt.get("height", 0) or 0
        fps = fmt.get("fps") or 0
        vcodec = fmt.get("vcodec", "none")
        acodec = fmt.get("acodec", "none")

        if vcodec == "none" and acodec != "none":
            abr = fmt.get("abr", 0) or 0
            return f"audio {abr:.0f}kbps" if abr else "audio only"

        labels = {
            4320: "8K", 2160: "4K", 1440: "1440p",
            1080: "1080p", 720: "720p", 480: "480p",
            360: "360p", 240: "240p", 144: "144p",
        }
        label = "unknown"
        for h, name in sorted(labels.items(), reverse=True):
            if height >= h:
                label = name
                break
        if fps and fps > 30:
            label += f"{fps:.0f}"
        return label

    # -------------------------------------------------------------------
    # Metadata
    # -------------------------------------------------------------------

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Fetch comprehensive metadata for a YouTube URL."""
        opts = self._build_ytdlp_opts({"skip_download": True})
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {}
                return self._extract_metadata(info)
        except ImportError:
            return self._metadata_via_cli(url)
        except Exception as exc:
            raise DownloadError(f"Failed to fetch metadata: {exc}")

    def _metadata_via_cli(self, url: str) -> Dict[str, Any]:
        """Fallback: fetch metadata using yt-dlp CLI."""
        try:
            cmd = [self._ytdlp_path, "-J", "--no-download", url]
            if self._proxy:
                cmd.extend(["--proxy", self._proxy])
            if self._cookies:
                cmd.extend(["--cookiefile", self._cookies])
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout,
            )
            if result.returncode != 0:
                return {}
            data = json.loads(result.stdout)
            return self._extract_metadata(data)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
            return {}

    @staticmethod
    def _extract_metadata(info: Dict) -> Dict[str, Any]:
        """Extract structured metadata from yt-dlp info dict."""
        return {
            "id": info.get("id", ""),
            "title": info.get("title", ""),
            "description": info.get("description", ""),
            "duration": info.get("duration", 0),
            "uploader": info.get("uploader", ""),
            "uploader_id": info.get("uploader_id", ""),
            "uploader_url": info.get("uploader_url", ""),
            "channel": info.get("channel", ""),
            "channel_id": info.get("channel_id", ""),
            "upload_date": info.get("upload_date", ""),
            "view_count": info.get("view_count", 0),
            "like_count": info.get("like_count", 0),
            "categories": info.get("categories", []),
            "tags": info.get("tags", []),
            "thumbnails": info.get("thumbnails", []),
            "thumbnail": info.get("thumbnail", ""),
            "chapters": info.get("chapters", []),
            "subtitles": list((info.get("subtitles") or {}).keys()),
            "automatic_captions": list((info.get("automatic_captions") or {}).keys()),
            "is_live": info.get("is_live", False),
            "was_live": info.get("was_live", False),
            "live_status": info.get("live_status", ""),
            "playlist": info.get("playlist", ""),
            "playlist_index": info.get("playlist_index"),
            "playlist_count": info.get("playlist_count"),
            "age_limit": info.get("age_limit", 0),
            "availability": info.get("availability", ""),
        }

    # -------------------------------------------------------------------
    # Lifecycle: Prepare
    # -------------------------------------------------------------------

    def on_prepare(self, task: DownloadTask) -> None:
        """Prepare download: validate URL, ensure output dir, resolve info."""
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid YouTube URL: {task.url}")
        out_dir = self._ensure_output_dir(
            task.output_path or self._output_dir
        )
        task.output_path = out_dir

        # Pre-fetch info for filename resolution
        opts = self._build_ytdlp_opts({"skip_download": True})
        try:
            import yt_dlp
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(task.url, download=False)
                if info:
                    task.filename = task.filename or info.get("title", "video")
        except Exception:
            pass  # Non-fatal; download may still succeed

    # -------------------------------------------------------------------
    # Lifecycle: Download
    # -------------------------------------------------------------------

    def on_download(self, task: DownloadTask) -> DownloadResult:
        """Execute the YouTube download via yt-dlp."""
        quality = getattr(task, 'tags', []) and task.tags[0] if task.tags else "best"
        format_spec = self._resolve_format_spec(quality)

        outtmpl = os.path.join(
            task.output_path or self._output_dir,
            "%(title)s [%(id)s].%(ext)s",
        )

        ytdlp_opts = self._build_ytdlp_opts({
            "format": format_spec,
            "outtmpl": outtmpl,
        })

        # Subtitle options
        if task.headers and task.headers.get("subtitles_lang"):
            subs_lang = task.headers["subtitles_lang"]
            ytdlp_opts["writeautomaticsub"] = True
            ytdlp_opts["subtitleslangs"] = (
                subs_lang if isinstance(subs_lang, list) else [subs_lang]
            )
            ytdlp_opts["writesubtitles"] = True
            ytdlp_opts["subtitlesformat"] = task.headers.get("subtitles_format", "srt")

        # Thumbnail
        if task.headers and task.headers.get("write_thumbnail"):
            ytdlp_opts["writethumbnail"] = True

        # SponsorBlock
        if task.headers and task.headers.get("sponsorblock"):
            ytdlp_opts["sponsorblock_remove"] = "sponsor,intro,outro"

        # Chapter splitting
        if task.headers and task.headers.get("split_chapters"):
            ytdlp_opts["split_chapters"] = True

        # Embed metadata
        if task.headers and task.headers.get("embed_metadata"):
            ytdlp_opts["postprocessors"] = ytdlp_opts.get("postprocessors", [])
            ytdlp_opts["postprocessors"].append({"key": "FFmpegMetadata"})

        # Live stream options
        if task.headers and task.headers.get("is_live"):
            ytdlp_opts["hls_prefer_native"] = True
            if task.headers.get("live_from_start"):
                ytdlp_opts["live_from_start"] = True

        # Merge output format
        if quality not in ("bestaudio", "worstaudio"):
            ytdlp_opts["merge_output_format"] = task.headers.get("merge_output_format", "mkv") if task.headers else "mkv"

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
                    result.metadata = self._extract_metadata(info)
                    filename = ydl.prepare_filename(info)
                    merge_ext = ytdlp_opts.get("merge_output_format", "mkv")
                    if not os.path.exists(filename):
                        for ext in (merge_ext, "mp4", "mkv", "webm"):
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
            result = self._download_via_cli(task, ytdlp_opts, result)
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
            return result

        elapsed = time.monotonic() - start_time
        result.elapsed = elapsed
        if elapsed > 0 and result.file_size > 0:
            result.average_speed = result.file_size / elapsed
        return result

    def _download_via_cli(
        self, task: DownloadTask, opts: Dict, result: DownloadResult,
    ) -> DownloadResult:
        """Fallback: download using yt-dlp CLI."""
        cmd = [self._ytdlp_path]
        cmd.extend(["-f", opts.get("format", "best")])
        cmd.extend(["-o", opts.get("outtmpl", "%(title)s.%(ext)s")])
        if self._proxy:
            cmd.extend(["--proxy", self._proxy])
        if self._cookies:
            cmd.extend(["--cookiefile", self._cookies])
        if opts.get("writesubtitles"):
            cmd.append("--write-subs")
        if opts.get("writeautomaticsub"):
            cmd.append("--write-auto-subs")
        if opts.get("writethumbnail"):
            cmd.append("--write-thumbnail")
        if opts.get("split_chapters"):
            cmd.append("--split-chapters")
        cmd.append(task.url)

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=self._timeout * 10,
            )
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                out_dir = task.output_path or self._output_dir
                for f in Path(out_dir).iterdir():
                    if f.is_file() and f.stat().st_mtime > time.time() - 300:
                        result.output_path = str(f.resolve())
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
            result.error = "yt-dlp not found. Install: pip install yt-dlp"
        return result

    def _resolve_format_spec(self, quality: str) -> str:
        """Convert quality name to yt-dlp format string."""
        quality_map = {
            "8K": "bestvideo[height<=4320]+bestaudio/best[height<=4320]",
            "4K": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
            "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "240p": "bestvideo[height<=240]+bestaudio/best[height<=240]",
            "144p": "worstvideo+worstaudio/worst",
            "best": "bestvideo+bestaudio/best",
            "bestaudio": "bestaudio/best",
            "worst": "worstvideo+worstaudio/worst",
            "worstaudio": "worstaudio/worst",
        }
        return quality_map.get(quality, "bestvideo+bestaudio/best")

    # -------------------------------------------------------------------
    # Lifecycle: Verify
    # -------------------------------------------------------------------

    def on_verify(self, task=None, result=None):
        """Verify the downloaded file exists and has non-zero size."""
        if not result.output_path:
            return False
        if not os.path.exists(result.output_path):
            return False
        return os.path.getsize(result.output_path) > 0

    # -------------------------------------------------------------------
    # Lifecycle: Post-Process
    # -------------------------------------------------------------------

    def on_post_process(self, task=None, result=None):
        """Post-process: collect extra files, compute checksum."""
        if not result.output_path or not os.path.exists(result.output_path):
            return result

        # Collect extra files (thumbnails, subtitles, etc.)
        out_dir = os.path.dirname(result.output_path)
        base_name = os.path.splitext(os.path.basename(result.output_path))[0]
        for f in Path(out_dir).iterdir():
            if f.is_file() and f.name.startswith(base_name) and str(f) != result.output_path:
                if "extra_files" not in result.metadata:
                    result.metadata["extra_files"] = []
                result.metadata["extra_files"].append(str(f.resolve()))

        # Compute final checksum
        result.metadata["checksum"] = self._compute_checksum(result.output_path)
        result.metadata["checksum_algorithm"] = "sha256"

        return result


def register() -> Tuple[str, AgentSkill]:
    """Register the YouTube agent with the agent registry."""
    skill = AgentSkill(
        platform="youtube",
        formats=frozenset(YouTubeDownloader.SUPPORTED_FORMATS),
        qualities=frozenset(YouTubeDownloader.SUPPORTED_QUALITIES),
        features=frozenset([
            "video", "audio", "playlists", "livestreams", "shorts",
            "subtitles", "thumbnails", "chapters", "sponsorblock",
            "age_gate_bypass", "cookie_auth", "proxy",
        ]),
        max_concurrent=3,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description=(
            "YouTube downloader: videos 240p-8K, audio, playlists, "
            "livestreams, subtitles, thumbnails, SponsorBlock, age-gate bypass."
        ),
    )
    return ("youtube", skill)
