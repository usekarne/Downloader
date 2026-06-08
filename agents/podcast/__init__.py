"""
RS Downloader v10.0.0 - Podcast Download Agent
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Podcast downloader supporting:
- RSS feed parsing and episode listing
- Individual episode downloads (MP3, M4A, OGG)
- Full podcast batch download
- Episode metadata extraction
- OPML import support
"""

from __future__ import annotations

import json
import os
import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class PodcastDownloader(DownloaderBase):
    """Podcast download agent for RSS feeds and episodes."""

    AGENT_NAME = "podcast"
    PLATFORM = "podcast"
    SUPPORTED_FORMATS = ["mp3", "m4a", "ogg", "wav", "aac"]
    SUPPORTED_QUALITIES = ["best", "standard"]

    _URL_PATTERNS = [
        re.compile(r'https?://feeds\.[\w.]+/[\w/-]+'),
        re.compile(r'https?://[\w.]+/feed/?$'),
        re.compile(r'https?://[\w.]+/podcast/[\w/-]+'),
        re.compile(r'https?://[\w.]+/rss'),
        re.compile(r'https?://podcasts\.apple\.com/[\w/]+/id(\d+)'),
    ]
    _RSS_NAMESPACES = {
        "itunes": "http://www.itunes.com/dtds/podcast-1.0.dtd",
        "podcast": "https://podcastindex.org/namespace/1.0",
    }

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_rss_feed(self, feed_url: str) -> Dict[str, Any]:
        """Parse RSS feed and extract podcast/episode info."""
        import requests
        result: Dict[str, Any] = {"episodes": []}
        try:
            resp = requests.get(feed_url, headers=self.headers,
                                proxies={"http": self.proxy, "https": self.proxy} if self.proxy else None,
                                timeout=self.timeout)
            if resp.status_code != 200:
                return result
            root = ET.fromstring(resp.text)
            channel = root.find(".//channel")
            if channel is None:
                return result
            result["title"] = channel.findtext("title", "")
            result["description"] = channel.findtext("description", "")
            result["link"] = channel.findtext("link", "")
            result["language"] = channel.findtext("language", "")
            # Parse episodes
            for item in channel.findall("item")[:100]:
                episode = {
                    "title": item.findtext("title", ""),
                    "description": item.findtext("description", ""),
                    "pub_date": item.findtext("pubDate", ""),
                    "duration": item.findtext("itunes:duration", "", self._RSS_NAMESPACES),
                }
                enclosure = item.find("enclosure")
                if enclosure is not None:
                    episode["audio_url"] = enclosure.get("url", "")
                    episode["audio_type"] = enclosure.get("type", "audio/mpeg")
                    episode["audio_size"] = int(enclosure.get("length", "0"))
                result["episodes"].append(episode)
        except Exception:
            pass
        return result

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "mp3", "ext": "mp3", "quality": "MP3 audio"},
            {"format_id": "m4a", "ext": "m4a", "quality": "M4A audio"},
            {"format_id": "ogg", "ext": "ogg", "quality": "OGG audio"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        metadata: Dict[str, Any] = {"platform": "podcast", "url": url}
        feed_data = self._parse_rss_feed(url)
        metadata.update(feed_data)
        metadata["episode_count"] = len(feed_data.get("episodes", []))
        return metadata

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid podcast URL: {task.url}", url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            episodes = metadata.get("episodes", [])
            episode_index = task.options.get("episode_index", 0)
            # Download single episode or latest
            if isinstance(episode_index, int) and episodes:
                ep = episodes[min(episode_index, len(episodes) - 1)]
                audio_url = ep.get("audio_url", "")
                if not audio_url:
                    result.status = DownloadStatus.FAILED
                    result.error = "No audio URL found for episode"
                    return result
                title = ep.get("title") or f"episode_{episode_index}"
                ext = "mp3"
                if ".m4a" in audio_url:
                    ext = "m4a"
                elif ".ogg" in audio_url:
                    ext = "ogg"
                filename = self._safe_filename(f"{title}.{ext}")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(audio_url, headers=self.headers, stream=True, timeout=self.timeout * 5)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    downloaded = 0
                    for chunk in resp.iter_content(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        self._speed_tracker.update(downloaded)
                result.file_path = os.path.abspath(filepath)
                result.filename = filename
                result.file_size = os.path.getsize(filepath)
                result.content_type = detect_content_type(filename=filename)
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
        if result.file_path and os.path.exists(result.file_path):
            result.checksum = self._compute_checksum(result.file_path)
            result.checksum_algorithm = "sha256"
            # Apply audio tags if mutagen available
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(result.file_path)
                if audio and result.metadata:
                    ep_meta = result.metadata.get("episodes", [{}])[0] if result.metadata.get("episodes") else {}
                    if ep_meta.get("title"):
                        audio["title"] = ep_meta["title"]
                    if result.metadata.get("title"):
                        audio["album"] = result.metadata["title"]
                    audio.save()
            except Exception:
                pass
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="podcast", platform="podcast",
        description="Podcast downloader: RSS feeds, episode download, batch, metadata, OPML.",
        supported_formats=PodcastDownloader.SUPPORTED_FORMATS,
        supported_qualities=PodcastDownloader.SUPPORTED_QUALITIES,
        max_concurrent=3, priority=DownloadPriority.NORMAL,
    )
    return ("podcast", skill)
