"""
RS Downloader v10.0.0 - Search Utility Agent
================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Search utility agent providing:
- YouTube search with metadata
- SoundCloud search
- Web search via DuckDuckGo
- Result filtering and ranking
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


class SearchAgent(DownloaderBase):
    """Search utility agent for finding downloadable content."""

    AGENT_NAME = "search"
    PLATFORM = "search"
    SUPPORTED_FORMATS = ["json", "txt"]
    SUPPORTED_QUALITIES = ["relevance", "date", "views", "rating"]

    def validate_url(self, url: str) -> bool:
        # Search agent accepts query strings as "URLs"
        return bool(url.strip())

    def search_youtube(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search YouTube and return results with metadata."""
        results = []
        try:
            import yt_dlp
            opts = {"quiet": True, "no_warnings": True, "skip_download": True,
                    "extract_flat": True, "playlistend": max_results}
            if self.proxy:
                opts["proxy"] = self.proxy
            search_url = f"ytsearch{max_results}:{query}"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                if info and "entries" in info:
                    for entry in info["entries"]:
                        if entry:
                            results.append({
                                "title": entry.get("title", ""),
                                "url": entry.get("url", entry.get("webpage_url", "")),
                                "duration": entry.get("duration"),
                                "uploader": entry.get("uploader", ""),
                                "view_count": entry.get("view_count"),
                                "thumbnail": entry.get("thumbnail", ""),
                                "platform": "youtube",
                            })
        except Exception:
            pass
        return results

    def search_soundcloud(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search SoundCloud and return results."""
        results = []
        try:
            import yt_dlp
            opts = {"quiet": True, "no_warnings": True, "skip_download": True,
                    "extract_flat": True, "playlistend": max_results}
            if self.proxy:
                opts["proxy"] = self.proxy
            search_url = f"scsearch{max_results}:{query}"
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(search_url, download=False)
                if info and "entries" in info:
                    for entry in info["entries"]:
                        if entry:
                            results.append({
                                "title": entry.get("title", ""),
                                "url": entry.get("url", entry.get("webpage_url", "")),
                                "duration": entry.get("duration"),
                                "uploader": entry.get("uploader", ""),
                                "platform": "soundcloud",
                            })
        except Exception:
            pass
        return results

    def search_web(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search the web via DuckDuckGo HTML."""
        import requests
        results = []
        try:
            resp = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={**self.headers, "User-Agent": "Mozilla/5.0"},
                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                # Parse HTML results
                links = re.findall(
                    r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>',
                    resp.text, re.DOTALL
                )
                for url, title in links[:max_results]:
                    title = re.sub(r"<[^>]+>", "", title).strip()
                    results.append({
                        "title": title,
                        "url": url,
                        "platform": "web",
                    })
        except Exception:
            pass
        return results

    def search(self, query: str, platforms: Optional[List[str]] = None,
               max_results: int = 10) -> Dict[str, List[Dict[str, Any]]]:
        """Search across multiple platforms."""
        platforms = platforms or ["youtube", "soundcloud", "web"]
        all_results: Dict[str, List[Dict[str, Any]]] = {}
        if "youtube" in platforms:
            all_results["youtube"] = self.search_youtube(query, max_results)
        if "soundcloud" in platforms:
            all_results["soundcloud"] = self.search_soundcloud(query, max_results)
        if "web" in platforms:
            all_results["web"] = self.search_web(query, max_results)
        return all_results

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "json", "ext": "json", "quality": "structured results"},
            {"format_id": "txt", "ext": "txt", "quality": "text list"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        return {"platform": "search", "query": url}

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            query = task.url
            platforms = task.options.get("platforms", ["youtube", "soundcloud", "web"])
            max_results = task.options.get("max_results", 10)
            search_results = self.search(query, platforms, max_results)
            result.metadata = search_results
            out_dir = task.options.get("output_dir", self.output_dir)
            # Save results as JSON
            filename = self._safe_filename(f"search_{query[:50]}.json")
            filepath = os.path.join(out_dir, filename)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(search_results, f, indent=2, ensure_ascii=False, default=str)
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

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="search", platform="search",
        description="Search utility: YouTube, SoundCloud, web search with metadata results.",
        supported_formats=SearchAgent.SUPPORTED_FORMATS,
        supported_qualities=SearchAgent.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.HIGH,
    )
    return ("search", skill)
