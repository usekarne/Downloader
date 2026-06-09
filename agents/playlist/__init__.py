"""
RS Downloader v10.0.0 - Playlist Utility Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Playlist utility agent providing:
- Playlist download management
- Playlist info extraction
- Playlist export (M3U, PLS, JSON)
- Multi-platform playlist support
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class PlaylistAgent(DownloaderBase):
    """Playlist utility agent for download, management, and export."""

    AGENT_NAME = "playlist"
    PLATFORM = "playlist"
    SUPPORTED_FORMATS = ["m3u", "pls", "json", "csv"]
    SUPPORTED_QUALITIES = ["all", "range", "selective"]

    def validate_url(self, url: str) -> bool:
        return url.startswith("http") or os.path.exists(url)

    def download_playlist(self, url: str, output_dir: str = "",
                          quality: str = "best", start: int = 1,
                          end: int = 0) -> Dict[str, Any]:
        """Download all items in a playlist."""
        import shutil, subprocess
        ytdlp = shutil.which("yt-dlp") or "yt-dlp"
        out_dir = output_dir or self.output_dir
        os.makedirs(out_dir, exist_ok=True)
        cmd = [ytdlp, "-f", quality, "-o", os.path.join(out_dir, "%(playlist_index)s - %(title)s.%(ext)s")]
        if start > 1:
            cmd.extend(["--playlist-start", str(start)])
        if end > 0:
            cmd.extend(["--playlist-end", str(end)])
        if self.proxy:
            cmd.extend(["--proxy", self.proxy])
        if self.cookies:
            cmd.extend(["--cookiefile", self.cookies])
        cmd.append(url)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=self.timeout * 20)
        files = list(Path(out_dir).iterdir()) if os.path.exists(out_dir) else []
        return {
            "url": url,
            "success": proc.returncode == 0,
            "output_dir": out_dir,
            "files_downloaded": len([f for f in files if f.is_file()]),
            "error": proc.stderr[:500] if proc.returncode != 0 and proc.stderr else "",
        }

    def get_playlist_info(self, url: str) -> Dict[str, Any]:
        """Get playlist information without downloading."""
        try:
            import yt_dlp
            opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": True}
            if self.proxy:
                opts["proxy"] = self.proxy
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    return {}
                entries = info.get("entries", []) or []
                return {
                    "title": info.get("title", info.get("playlist_title", "")),
                    "id": info.get("id", ""),
                    "count": info.get("playlist_count", len(entries)),
                    "entries": [
                        {
                            "title": e.get("title", "") if e else "",
                            "url": e.get("url", e.get("webpage_url", "")) if e else "",
                            "duration": e.get("duration") if e else None,
                            "index": e.get("playlist_index", i + 1) if e else i + 1,
                        }
                        for i, e in enumerate(entries)
                    ],
                }
        except Exception:
            pass
        return {}

    def export_playlist(self, entries: List[Dict[str, Any]], output_path: str,
                        format: str = "m3u") -> str:
        """Export playlist entries to M3U, PLS, or JSON format."""
        if format == "m3u":
            lines = ["#EXTM3U\n"]
            for entry in entries:
                duration = int(entry.get("duration") or -1)
                title = entry.get("title", "")
                url = entry.get("url", "")
                lines.append(f"#EXTINF:{duration},{title}\n{url}\n")
            content = "".join(lines)
        elif format == "pls":
            lines = ["[playlist]\n"]
            for i, entry in enumerate(entries, 1):
                lines.append(f"File{i}={entry.get('url', '')}\n")
                lines.append(f"Title{i}={entry.get('title', '')}\n")
                lines.append(f"Length{i}={int(entry.get('duration') or -1)}\n")
            lines.append(f"NumberOfEntries={len(entries)}\nVersion=2\n")
            content = "".join(lines)
        else:
            content = json.dumps(entries, indent=2, ensure_ascii=False, default=str)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        return output_path

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "m3u", "ext": "m3u", "quality": "M3U playlist"},
            {"format_id": "pls", "ext": "pls", "quality": "PLS playlist"},
            {"format_id": "json", "ext": "json", "quality": "JSON playlist"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        return self.get_playlist_info(url)

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_path)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        action = task.options.get("action", "info")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            out_dir = task.options.get("output_dir", self.output_dir)
            if action == "download":
                quality = task.options.get("quality", "best")
                start_idx = task.options.get("start", 1)
                end_idx = task.options.get("end", 0)
                data = self.download_playlist(task.url, out_dir, quality, start_idx, end_idx)
                result.metadata = data
                result.file_path = os.path.abspath(out_dir)
                result.filename = "playlist"
                total_size = sum(f.stat().st_size for f in Path(out_dir).iterdir() if f.is_file())
                result.file_size = total_size
            elif action == "export":
                info = self.get_playlist_info(task.url)
                entries = info.get("entries", [])
                export_format = task.options.get("export_format", "m3u")
                filename = self._safe_filename(f"playlist.{export_format}")
                filepath = os.path.join(out_dir, filename)
                self.export_playlist(entries, filepath, export_format)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
            else:
                info = self.get_playlist_info(task.url)
                result.metadata = info
                filename = self._safe_filename("playlist_info.json")
                filepath = os.path.join(out_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(info, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
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
        if os.path.isdir(result.file_path):
            return any(Path(result.file_path).iterdir())
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="playlist", platform="playlist",
        description="Playlist utility: download, info extraction, export (M3U/PLS/JSON), multi-platform.",
        supported_formats=PlaylistAgent.SUPPORTED_FORMATS,
        supported_qualities=PlaylistAgent.SUPPORTED_QUALITIES,
        max_concurrent=1, priority=DownloadPriority.NORMAL,
    )
    return ("playlist", skill)
