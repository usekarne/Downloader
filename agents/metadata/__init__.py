"""
RS Downloader v10.0.0 - Metadata Utility Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Metadata utility agent providing:
- Audio/video metadata extraction (mutagen, ffmpeg)
- Metadata embedding for audio/video files
- Metadata stripping for privacy
- Support for MP3, M4A, FLAC, OGG, MP4, MKV, etc.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class MetadataAgent(DownloaderBase):
    """Metadata utility agent for extracting, embedding, and stripping media metadata."""

    AGENT_NAME = "metadata"
    PLATFORM = "metadata"
    SUPPORTED_FORMATS = ["mp3", "m4a", "flac", "ogg", "opus", "mp4", "mkv", "webm", "json"]
    SUPPORTED_QUALITIES = ["full", "basic", "minimal"]

    _AUDIO_EXTS = {".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wma", ".wav", ".aac"}
    _VIDEO_EXTS = {".mp4", ".mkv", ".webm", ".avi", ".mov", ".wmv", ".flv"}

    def validate_url(self, url: str) -> bool:
        # Accept file paths as "URLs" for utility agents
        return os.path.exists(url) or url.startswith("file://") or url.startswith("/")

    def _resolve_path(self, url: str) -> str:
        if url.startswith("file://"):
            return url[7:]
        return url

    def extract_metadata(self, filepath: str) -> Dict[str, Any]:
        """Extract metadata from an audio/video file using mutagen and ffmpeg."""
        filepath = self._resolve_path(filepath)
        if not os.path.exists(filepath):
            raise DownloadError(f"File not found: {filepath}", url=filepath, agent=self.AGENT_NAME)
        ext = Path(filepath).suffix.lower()
        metadata: Dict[str, Any] = {"filepath": filepath, "extension": ext}
        # Try mutagen for audio files
        if ext in self._AUDIO_EXTS:
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(filepath)
                if audio:
                    metadata["mutagen"] = {}
                    metadata["mutagen"]["length"] = getattr(audio.info, "length", 0)
                    metadata["mutagen"]["bitrate"] = getattr(audio.info, "bitrate", 0)
                    metadata["mutagen"]["channels"] = getattr(audio.info, "channels", 0)
                    metadata["mutagen"]["sample_rate"] = getattr(audio.info, "sample_rate", 0)
                    metadata["mutagen"]["tags"] = dict(audio.tags) if audio.tags else {}
            except ImportError:
                pass
            except Exception:
                pass
        # Try ffprobe for all media types
        try:
            probe_data = self._ffprobe(filepath)
            if probe_data:
                metadata["ffprobe"] = probe_data
        except Exception:
            pass
        # Basic file info
        stat = os.stat(filepath)
        metadata["file_size"] = stat.st_size
        metadata["modified"] = stat.st_mtime
        return metadata

    def _ffprobe(self, filepath: str) -> Dict[str, Any]:
        """Extract metadata using ffprobe."""
        import shutil
        ffprobe = shutil.which("ffprobe")
        if not ffprobe:
            return {}
        cmd = [ffprobe, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", filepath]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if proc.returncode == 0:
                data = json.loads(proc.stdout)
                result: Dict[str, Any] = {}
                fmt = data.get("format", {})
                result["duration"] = float(fmt.get("duration", 0))
                result["bit_rate"] = int(fmt.get("bit_rate", 0))
                result["format_name"] = fmt.get("format_name", "")
                result["format_long_name"] = fmt.get("format_long_name", "")
                result["tags"] = fmt.get("tags", {})
                streams = data.get("streams", [])
                result["streams"] = []
                for s in streams:
                    stream_info: Dict[str, Any] = {
                        "codec_type": s.get("codec_type", ""),
                        "codec_name": s.get("codec_name", ""),
                    }
                    if s.get("codec_type") == "video":
                        stream_info["width"] = s.get("width", 0)
                        stream_info["height"] = s.get("height", 0)
                        stream_info["fps"] = s.get("r_frame_rate", "")
                    elif s.get("codec_type") == "audio":
                        stream_info["sample_rate"] = s.get("sample_rate", "")
                        stream_info["channels"] = s.get("channels", 0)
                    result["streams"].append(stream_info)
                return result
        except Exception:
            pass
        return {}

    def embed_metadata(self, filepath: str, tags: Dict[str, str]) -> bool:
        """Embed metadata tags into an audio file using mutagen."""
        filepath = self._resolve_path(filepath)
        if not os.path.exists(filepath):
            return False
        ext = Path(filepath).suffix.lower()
        if ext not in self._AUDIO_EXTS:
            # Use ffmpeg for video files
            return self._embed_via_ffmpeg(filepath, tags)
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(filepath)
            if audio is None:
                return False
            for key, value in tags.items():
                try:
                    audio[key] = value
                except (KeyError, TypeError):
                    pass
            audio.save()
            return True
        except ImportError:
            return self._embed_via_ffmpeg(filepath, tags)
        except Exception:
            return False

    def _embed_via_ffmpeg(self, filepath: str, tags: Dict[str, str]) -> bool:
        """Embed metadata via ffmpeg."""
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return False
        output = filepath + ".tagged"
        cmd = [ffmpeg, "-i", filepath, "-y"]
        for key, value in tags.items():
            cmd.extend(["-metadata", f"{key}={value}"])
        cmd.extend(["-c", "copy", output])
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0 and os.path.exists(output):
                os.replace(output, filepath)
                return True
        except Exception:
            pass
        if os.path.exists(output):
            os.remove(output)
        return False

    def strip_metadata(self, filepath: str) -> bool:
        """Strip all metadata from a media file for privacy."""
        filepath = self._resolve_path(filepath)
        if not os.path.exists(filepath):
            return False
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            return False
        output = filepath + ".stripped"
        cmd = [ffmpeg, "-i", filepath, "-map_metadata", "-1", "-y", "-c", "copy", output]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0 and os.path.exists(output):
                os.replace(output, filepath)
                return True
        except Exception:
            pass
        if os.path.exists(output):
            os.remove(output)
        return False

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "json", "ext": "json", "quality": "full metadata"},
            {"format_id": "embed", "ext": "*", "quality": "embed tags"},
            {"format_id": "strip", "ext": "*", "quality": "strip metadata"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        return self.extract_metadata(url)

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        action = task.options.get("action", "extract")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            filepath = self._resolve_path(task.url)
            out_dir = task.options.get("output_dir", self.output_dir)
            if action == "extract":
                metadata = self.extract_metadata(filepath)
                result.metadata = metadata
                basename = Path(filepath).stem
                filename = self._safe_filename(f"{basename}_metadata.json")
                filepath_out = os.path.join(out_dir, filename)
                with open(filepath_out, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath_out)
                result.filename = filename
                result.file_size = os.path.getsize(filepath_out)
                result.content_type = "application/json"
            elif action == "embed":
                tags = task.options.get("tags", {})
                success = self.embed_metadata(filepath, tags)
                result.metadata = {"success": success, "tags": tags}
                result.file_path = os.path.abspath(filepath)
                result.filename = os.path.basename(filepath)
                result.file_size = os.path.getsize(filepath)
            elif action == "strip":
                success = self.strip_metadata(filepath)
                result.metadata = {"success": success, "action": "strip"}
                result.file_path = os.path.abspath(filepath)
                result.filename = os.path.basename(filepath)
                result.file_size = os.path.getsize(filepath)
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        if result.file_path and os.path.isfile(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="metadata", platform="metadata",
        description="Metadata utility: extract, embed, strip audio/video metadata. mutagen + ffmpeg.",
        supported_formats=MetadataAgent.SUPPORTED_FORMATS,
        supported_qualities=MetadataAgent.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.HIGH,
    )
    return ("metadata", skill)
