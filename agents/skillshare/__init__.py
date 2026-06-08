"""
RS Downloader v10.0.0 - Skillshare Download Agent
===================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Skillshare download agent supporting:
- Video class downloads
- Course metadata extraction
- Subtitle downloads
- Multi-quality video selection
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
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
)


class SkillshareDownloader(DownloaderBase):
    """Skillshare download agent for video classes and course content.

    Uses yt-dlp for video downloads with cookie authentication.
    Requires Skillshare account cookies for enrolled class access.
    """

    AGENT_NAME = "skillshare"
    PLATFORM = "skillshare"
    SUPPORTED_FORMATS = ["mp4", "mkv", "webm", "m4a", "srt", "vtt", "json"]
    SUPPORTED_QUALITIES = [
        "1080p", "720p", "480p", "360p",
        "best", "worst", "bestaudio", "metadata_only",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://www\.skillshare\.com/classes/[\w-]+/\d+'),
        re.compile(r'https?://www\.skillshare\.com/student/preview/[\w-]+/\d+'),
        re.compile(r'https?://skl\.sh/[\w-]+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _extract_class_id(self, url: str) -> str:
        m = re.search(r'/(\d+)', url)
        return m.group(1) if m else ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        formats = []
        for q in ["1080p", "720p", "480p", "360p"]:
            formats.append({"format_id": q, "ext": "mp4", "quality": q})
        formats.extend([
            {"format_id": "bestaudio", "ext": "m4a", "quality": "audio only"},
            {"format_id": "subtitles", "ext": "srt", "quality": "subtitles"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ])
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        class_id = self._extract_class_id(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "skillshare", "class_id": class_id}
        try:
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            if resp.status_code == 200:
                text = resp.text
                for tag, key in [("og:title", "title"), ("og:image", "thumbnail"),
                                 ("og:description", "description")]:
                    m = re.search(rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key] = m.group(1)
                # Extract class data from page
                teacher_m = re.search(r'"teacherName"\s*:\s*"([^"]+)"', text)
                if teacher_m:
                    metadata["teacher"] = teacher_m.group(1)
                students_m = re.search(r'"studentCount"\s*:\s*(\d+)', text)
                if students_m:
                    metadata["students"] = int(students_m.group(1))
                lessons_m = re.search(r'"lessonCount"\s*:\s*(\d+)', text)
                if lessons_m:
                    metadata["lessons"] = int(lessons_m.group(1))
                duration_m = re.search(r'"totalDuration"\s*:\s*(\d+)', text)
                if duration_m:
                    metadata["total_duration"] = int(duration_m.group(1))
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        }

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Skillshare URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["class_id"] = self._extract_class_id(task.url)

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.options.get("quality", "best")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)

        if quality == "metadata_only":
            return self._download_metadata(task, result)

        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        fmt_map = {
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "480p": "bestvideo[height<=480]+bestaudio/best[height<=480]",
            "360p": "bestvideo[height<=360]+bestaudio/best[height<=360]",
            "best": "bestvideo+bestaudio/best",
            "bestaudio": "bestaudio/best",
            "worst": "worstvideo+worstaudio/worst",
        }
        format_spec = fmt_map.get(quality, "bestvideo+bestaudio/best")
        out_dir = task.options.get("output_dir", self.output_dir)
        outtmpl = os.path.join(out_dir, "%(title)s.%(ext)s")
        cmd = [ytdlp_path, "-f", format_spec, "-o", outtmpl]
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
        cmd.extend(["--write-auto-sub", "--sub-format", "srt/vtt"])
        cmd.append(task.url)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.timeout * 10)
            if proc.returncode == 0:
                result.status = DownloadStatus.VERIFYING
                for f in Path(out_dir).iterdir():
                    if f.is_file() and f.stat().st_mtime > time.time() - 600:
                        if f.suffix in (".mp4", ".mkv", ".webm", ".m4a"):
                            result.file_path = str(f.resolve())
                            result.filename = f.name
                            result.file_size = f.stat().st_size
                            break
            else:
                result.status = DownloadStatus.FAILED
                result.error = proc.stderr[:500] if proc.stderr else "Failed"
        except subprocess.TimeoutExpired:
            result.status = DownloadStatus.FAILED
            result.error = "Timed out"
        except FileNotFoundError:
            result.status = DownloadStatus.FAILED
            result.error = "yt-dlp not found"
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_metadata(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            filepath = os.path.join(out_dir, "skillshare_metadata.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
            result.file_path = os.path.abspath(filepath)
            result.filename = "skillshare_metadata.json"
            result.file_size = os.path.getsize(filepath)
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        return result

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="skillshare",
        formats=tuple(SkillshareDownloader.SUPPORTED_FORMATS),
        qualities=tuple(SkillshareDownloader.SUPPORTED_QUALITIES),
        features=("videos", "classes", "subtitles", "cookies"),
        max_concurrent=2,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Skillshare downloader: video classes and subtitles via yt-dlp + cookies.",
    )
    return ("skillshare", skill)
