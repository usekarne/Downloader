"""
RS Downloader v10.0.0 - Format Conversion Utility Agent
==========================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Format conversion utility agent providing:
- Video conversion (MP4, MKV, WebM, AVI, MOV)
- Audio conversion (MP3, M4A, FLAC, OGG, WAV, AAC)
- Image conversion (JPG, PNG, WebP, BMP)
- Document conversion (PDF, TXT, HTML)
- Output size estimation
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


class ConvertAgent(DownloaderBase):
    """Format conversion utility agent powered by ffmpeg."""

    AGENT_NAME = "convert"
    PLATFORM = "convert"
    SUPPORTED_FORMATS = [
        "mp4", "mkv", "webm", "avi", "mov", "flv",
        "mp3", "m4a", "flac", "ogg", "wav", "aac", "opus",
        "jpg", "png", "webp", "bmp", "gif",
        "pdf", "txt",
    ]
    SUPPORTED_QUALITIES = ["original", "high", "medium", "low", "custom"]

    _VIDEO_FORMATS = {"mp4", "mkv", "webm", "avi", "mov", "flv"}
    _AUDIO_FORMATS = {"mp3", "m4a", "flac", "ogg", "wav", "aac", "opus"}
    _IMAGE_FORMATS = {"jpg", "png", "webp", "bmp", "gif"}

    _QUALITY_PRESETS = {
        "original": {},
        "high": {"video_bitrate": "5000k", "audio_bitrate": "256k", "crf": "18"},
        "medium": {"video_bitrate": "2500k", "audio_bitrate": "128k", "crf": "23"},
        "low": {"video_bitrate": "1000k", "audio_bitrate": "96k", "crf": "28"},
    }

    def validate_url(self, url: str) -> bool:
        return os.path.exists(url) or url.startswith("file://") or url.startswith("/")

    def _resolve_path(self, url: str) -> str:
        if url.startswith("file://"):
            return url[7:]
        return url

    def convert(self, input_path: str, output_format: str, quality: str = "original",
                custom_params: Optional[Dict] = None) -> str:
        """Convert a file to the specified format using ffmpeg."""
        import shutil
        ffmpeg = shutil.which("ffmpeg")
        if not ffmpeg:
            raise DownloadError("ffmpeg not found", url=input_path, agent=self.AGENT_NAME)
        input_path = self._resolve_path(input_path)
        if not os.path.exists(input_path):
            raise DownloadError(f"File not found: {input_path}", url=input_path, agent=self.AGENT_NAME)
        output_path = os.path.splitext(input_path)[0] + f".{output_format}"
        cmd = [ffmpeg, "-i", input_path, "-y"]
        # Apply quality presets
        preset = self._QUALITY_PRESETS.get(quality, {})
        src_ext = Path(input_path).suffix.lower().lstrip(".")
        dst_ext = output_format.lower()
        if dst_ext in self._VIDEO_FORMATS:
            if "crf" in preset:
                cmd.extend(["-crf", preset["crf"]])
            elif "video_bitrate" in preset:
                cmd.extend(["-b:v", preset["video_bitrate"]])
            if "audio_bitrate" in preset:
                cmd.extend(["-b:a", preset["audio_bitrate"]])
            # Video codec selection
            if dst_ext == "mp4":
                cmd.extend(["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart"])
            elif dst_ext == "webm":
                cmd.extend(["-c:v", "libvpx-vp9", "-c:a", "libopus"])
            elif dst_ext == "mkv":
                cmd.extend(["-c:v", "libx264", "-c:a", "aac"])
        elif dst_ext in self._AUDIO_FORMATS:
            if "audio_bitrate" in preset:
                cmd.extend(["-b:a", preset["audio_bitrate"]])
            if dst_ext == "mp3":
                cmd.extend(["-c:a", "libmp3lame"])
            elif dst_ext == "m4a":
                cmd.extend(["-c:a", "aac"])
            elif dst_ext == "flac":
                cmd.extend(["-c:a", "flac"])
            elif dst_ext == "ogg":
                cmd.extend(["-c:a", "libvorbis"])
            elif dst_ext == "opus":
                cmd.extend(["-c:a", "libopus"])
            elif dst_ext == "wav":
                cmd.extend(["-c:a", "pcm_s16le"])
            # Extract audio only if source is video
            if src_ext in self._VIDEO_FORMATS:
                cmd.extend(["-vn"])
        elif dst_ext in self._IMAGE_FORMATS:
            # Image conversion: single frame
            cmd.extend(["-frames:v", "1", "-q:v", "2"])
        # Custom parameters
        if custom_params:
            for key, value in custom_params.items():
                cmd.extend([f"-{key}", str(value)])
        cmd.append(output_path)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if proc.returncode != 0:
            if os.path.exists(output_path):
                os.remove(output_path)
            raise DownloadError(f"Conversion failed: {proc.stderr[:500]}", url=input_path, agent=self.AGENT_NAME)
        return output_path

    def get_supported_conversions(self, input_format: str) -> List[str]:
        """Get list of supported output formats for a given input format."""
        inf = input_format.lower().lstrip(".")
        if inf in self._VIDEO_FORMATS:
            return sorted(self._VIDEO_FORMATS | self._AUDIO_FORMATS | {"gif"})
        elif inf in self._AUDIO_FORMATS:
            return sorted(self._AUDIO_FORMATS)
        elif inf in self._IMAGE_FORMATS:
            return sorted(self._IMAGE_FORMATS)
        return []

    def estimate_output_size(self, input_path: str, output_format: str, quality: str = "medium") -> int:
        """Estimate output file size for a conversion."""
        input_path = self._resolve_path(input_path)
        if not os.path.exists(input_path):
            return 0
        input_size = os.path.getsize(input_path)
        src_ext = Path(input_path).suffix.lower().lstrip(".")
        dst_ext = output_format.lower()
        # Rough estimation based on format ratios
        size_ratios = {
            "mp3": 0.1, "flac": 0.6, "wav": 1.4, "ogg": 0.08,
            "m4a": 0.1, "opus": 0.07, "aac": 0.1,
            "mp4": 0.15, "webm": 0.12, "mkv": 0.15,
            "jpg": 0.05, "png": 0.15, "webp": 0.04, "gif": 0.3,
        }
        ratio = size_ratios.get(dst_ext, 0.1)
        quality_mult = {"original": 1.0, "high": 0.8, "medium": 0.5, "low": 0.3}.get(quality, 0.5)
        if src_ext in self._VIDEO_FORMATS and dst_ext in self._AUDIO_FORMATS:
            ratio *= 0.1  # Audio is much smaller than video
        return int(input_size * ratio * quality_mult)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ext = Path(url).suffix.lower().lstrip(".")
        conversions = self.get_supported_conversions(ext)
        return [{"format_id": fmt, "ext": fmt, "quality": fmt} for fmt in conversions]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        filepath = self._resolve_path(url)
        metadata: Dict[str, Any] = {"platform": "convert", "url": url}
        if os.path.exists(filepath):
            ext = Path(filepath).suffix.lower().lstrip(".")
            metadata["input_format"] = ext
            metadata["file_size"] = os.path.getsize(filepath)
            metadata["available_conversions"] = self.get_supported_conversions(ext)
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            output_format = task.options.get("output_format", "mp4")
            quality = task.options.get("quality", "medium")
            custom_params = task.options.get("custom_params")
            output_path = self.convert(task.url, output_format, quality, custom_params)
            result.file_path = os.path.abspath(output_path)
            result.filename = os.path.basename(output_path)
            result.file_size = os.path.getsize(output_path)
            result.content_type = detect_content_type(filename=output_path)
            result.metadata = {
                "input_format": Path(task.url).suffix.lower().lstrip("."),
                "output_format": output_format,
                "quality": quality,
            }
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
        name="convert", platform="convert",
        description="Format conversion: video/audio/image/document via ffmpeg. Size estimation, quality presets.",
        supported_formats=ConvertAgent.SUPPORTED_FORMATS,
        supported_qualities=ConvertAgent.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.HIGH,
    )
    return ("convert", skill)
