"""
RS Downloader v10.0.0 - AI Utility Agent
============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

AI utility agent providing:
- Content classification and analysis
- URL analysis and platform detection
- Smart filename suggestions
- Auto-tagging based on content
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

# Platform detection patterns
_PLATFORM_PATTERNS = {
    "youtube": [r"youtube\.com", r"youtu\.be"],
    "twitter": [r"twitter\.com", r"x\.com"],
    "instagram": [r"instagram\.com"],
    "tiktok": [r"tiktok\.com"],
    "reddit": [r"reddit\.com"],
    "facebook": [r"facebook\.com", r"fb\.watch"],
    "twitch": [r"twitch\.tv"],
    "vimeo": [r"vimeo\.com"],
    "soundcloud": [r"soundcloud\.com"],
    "spotify": [r"spotify\.com"],
    "bilibili": [r"bilibili\.com"],
    "pinterest": [r"pinterest\.com"],
    "tumblr": [r"tumblr\.com"],
    "unsplash": [r"unsplash\.com"],
    "pexels": [r"pexels\.com"],
    "giphy": [r"giphy\.com"],
    "imgur": [r"imgur\.com"],
    "archive_org": [r"archive\.org"],
}

_CONTENT_CATEGORIES = {
    "video": [".mp4", ".mkv", ".webm", ".avi", ".mov", ".flv", ".ts"],
    "audio": [".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav", ".aac"],
    "image": [".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".svg"],
    "document": [".pdf", ".doc", ".docx", ".txt", ".epub", ".mobi"],
    "archive": [".zip", ".rar", ".7z", ".tar", ".gz"],
}


class AIAgent(DownloaderBase):
    """AI utility agent for content analysis, classification, and smart naming."""

    AGENT_NAME = "ai"
    PLATFORM = "ai"
    SUPPORTED_FORMATS = ["json"]
    SUPPORTED_QUALITIES = ["detailed", "basic"]

    def validate_url(self, url: str) -> bool:
        return bool(url.strip())

    def classify_content(self, url_or_path: str) -> Dict[str, Any]:
        """Classify content type based on URL or file path."""
        result: Dict[str, Any] = {"input": url_or_path}
        ext = Path(url_or_path).suffix.lower()
        # Determine content category
        for category, extensions in _CONTENT_CATEGORIES.items():
            if ext in extensions:
                result["category"] = category
                break
        else:
            result["category"] = "unknown"
        # Detect platform
        result["platform"] = self.analyze_url(url_or_path).get("platform", "unknown")
        # Determine if downloadable
        result["downloadable"] = url_or_path.startswith("http") or os.path.exists(url_or_path)
        return result

    def analyze_url(self, url: str) -> Dict[str, Any]:
        """Analyze a URL to detect platform, content type, and download options."""
        result: Dict[str, Any] = {"url": url}
        # Platform detection
        for platform, patterns in _PLATFORM_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, url):
                    result["platform"] = platform
                    break
            if "platform" in result:
                break
        else:
            result["platform"] = "unknown"
        # Content type hints
        ext = Path(url).suffix.lower()
        for category, extensions in _CONTENT_CATEGORIES.items():
            if ext in extensions:
                result["content_type_hint"] = category
                break
        # Live/stream detection
        result["is_live"] = bool(re.search(r"live|stream|watch", url, re.IGNORECASE))
        # Playlist detection
        result["is_playlist"] = bool(re.search(r"playlist|list=|album|channel", url, re.IGNORECASE))
        return result

    def suggest_filename(self, url: str, metadata: Optional[Dict] = None) -> str:
        """Suggest a smart filename based on URL and metadata."""
        if metadata:
            parts = []
            if metadata.get("title"):
                title = metadata["title"]
                # Clean title
                title = re.sub(r'[<>:"/\\|?*]', '_', title)
                title = title[:200].strip()
                parts.append(title)
            if metadata.get("uploader") or metadata.get("artist"):
                parts.insert(0, metadata.get("uploader") or metadata.get("artist", ""))
            if metadata.get("id"):
                parts.append(f"[{metadata['id']}]")
            if parts:
                name = " - ".join(p for p in parts if p)
            else:
                name = suggest_filename(url=url)
        else:
            name = suggest_filename(url=url)
        # Ensure valid filename
        name = re.sub(r'[<>:"/\\|?*]', '_', name)
        name = name.strip(". ")
        return name[:255] or "download"

    def generate_tags(self, url: str, metadata: Optional[Dict] = None) -> List[str]:
        """Generate auto-tags based on URL and metadata."""
        tags = set()
        # Platform tag
        analysis = self.analyze_url(url)
        if analysis.get("platform") and analysis["platform"] != "unknown":
            tags.add(analysis["platform"])
        # Content type tags
        if analysis.get("is_live"):
            tags.add("live")
        if analysis.get("is_playlist"):
            tags.add("playlist")
        # Extension-based tags
        ext = Path(url).suffix.lower().lstrip(".")
        if ext:
            tags.add(ext)
        # Metadata-based tags
        if metadata:
            if metadata.get("duration", 0) > 3600:
                tags.add("long")
            elif metadata.get("duration", 0) > 600:
                tags.add("medium")
            else:
                tags.add("short")
            if metadata.get("categories"):
                for cat in metadata["categories"][:5]:
                    tags.add(str(cat).lower().replace(" ", "-"))
            if metadata.get("tags"):
                for tag in metadata["tags"][:5]:
                    tags.add(str(tag).lower())
        return sorted(tags)

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [{"format_id": "json", "ext": "json", "quality": "analysis results"}]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        return {
            "classify": self.classify_content(url),
            "analyze": self.analyze_url(url),
            "suggested_filename": self.suggest_filename(url),
            "tags": self.generate_tags(url),
        }

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        action = task.options.get("action", "analyze")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            out_dir = task.options.get("output_dir", self.output_dir)
            if action == "classify":
                data = self.classify_content(task.url)
            elif action == "analyze":
                data = self.analyze_url(task.url)
            elif action == "suggest_filename":
                metadata = task.options.get("metadata")
                data = {"suggested_filename": self.suggest_filename(task.url, metadata)}
            elif action == "generate_tags":
                metadata = task.options.get("metadata")
                data = {"tags": self.generate_tags(task.url, metadata)}
            else:
                data = self.get_metadata(task.url)
            result.metadata = data
            filename = self._safe_filename(f"ai_{action}_{task.url[:30]}.json")
            filepath = os.path.join(out_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = os.path.getsize(filepath)
            result.content_type = "application/json"
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
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="ai", platform="ai",
        description="AI utility: content classification, URL analysis, smart naming, auto-tagging.",
        supported_formats=AIAgent.SUPPORTED_FORMATS,
        supported_qualities=AIAgent.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.HIGH,
    )
    return ("ai", skill)
