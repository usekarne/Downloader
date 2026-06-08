"""
RS Downloader v10.0.0 - Tumblr Download Agent
===============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Tumblr downloader supporting:
- Post downloads (images, videos, text, audio)
- Blog scraping and batch download
- High-resolution image extraction
- Video downloads via yt-dlp
- GIF downloads
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


class TumblrDownloader(DownloaderBase):
    """Tumblr download agent for posts, images, videos, and blog content."""

    AGENT_NAME = "tumblr"
    PLATFORM = "tumblr"
    SUPPORTED_FORMATS = ["jpg", "png", "gif", "mp4", "webm", "mp3", "json"]
    SUPPORTED_QUALITIES = ["original", "large", "medium", "best", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://[\w-]+\.tumblr\.com/post/\d+'),
        re.compile(r'https?://[\w-]+\.tumblr\.com/$'),
        re.compile(r'https?://www\.tumblr\.com/[\w-]+/\d+'),
        re.compile(r'https?://tmblr\.co/[\w]+'),
        re.compile(r'https?://[\w-]+\.tumblr\.com/image/\d+'),
    ]

    _TUMBLR_API = "https://api.tumblr.com/v2/blog"

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_url(self, url: str) -> Tuple[str, str]:
        m = re.search(r'([\w-]+)\.tumblr\.com/post/(\d+)', url)
        if m:
            return "post", f"{m.group(1)}/{m.group(2)}"
        m = re.search(r'([\w-]+)\.tumblr\.com/?$', url)
        if m:
            return "blog", m.group(1)
        m = re.search(r'tumblr\.com/[\w-]+/(\d+)', url)
        if m:
            return "post", m.group(1)
        return "unknown", ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype, _ = self._parse_url(url)
        formats = [
            {"format_id": "original", "ext": "jpg", "quality": "original image"},
            {"format_id": "best", "ext": "mp4", "quality": "best video"},
            {"format_id": "metadata", "ext": "json", "quality": "metadata only"},
        ]
        if ctype == "blog":
            formats.insert(0, {"format_id": "blog-all", "ext": "zip",
                               "quality": "all blog posts"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype, key = self._parse_url(url)
        metadata: Dict[str, Any] = {"url": url, "platform": "tumblr",
                                    "content_type": ctype}
        try:
            resp = requests.get(url, headers=self._browser_headers(),
                                timeout=self.timeout)
            if resp.status_code == 200:
                text = resp.text
                for tag, key_name in [("og:title", "title"), ("og:image", "thumbnail"),
                                      ("og:description", "description"),
                                      ("og:video", "video_url")]:
                    m = re.search(rf'<meta\s+property="{tag}"\s+content="([^"]+)"', text)
                    if m:
                        metadata[key_name] = m.group(1)
                # Extract high-res images
                images = re.findall(r'"(?:orig|raw|high_res)"\s*:\s*"([^"]+)"', text)
                if images:
                    metadata["original_images"] = [img.replace("\\/", "/") for img in images]
                # Extract post ID and blog name
                post_m = re.search(r'data-post-id="(\d+)"', text)
                if post_m:
                    metadata["post_id"] = post_m.group(1)
                blog_m = re.search(r'data-tumblelog-name="([^"]+)"', text)
                if blog_m:
                    metadata["blog_name"] = blog_m.group(1)
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
            raise DownloadError(f"Invalid Tumblr URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        quality = task.options.get("quality", "original")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)

            if quality == "metadata_only":
                return self._save_metadata(metadata, out_dir, result)

            # Try video first, then images
            video_url = metadata.get("video_url", "")
            images = metadata.get("original_images", [])
            if video_url and quality == "best":
                return self._download_via_ytdlp(task, result)
            elif images:
                return self._download_images(images, out_dir, metadata, result)
            else:
                return self._save_metadata(metadata, out_dir, result)
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_images(self, images: list, out_dir: str, metadata: dict,
                         result: DownloadResult) -> DownloadResult:
        import requests
        try:
            downloaded = []
            for i, img_url in enumerate(images[:50]):  # Limit to 50
                ext = "gif" if ".gif" in img_url else "jpg"
                filename = self._safe_filename(
                    f"{metadata.get('blog_name', 'tumblr')}_{i}.{ext}")
                filepath = os.path.join(out_dir, filename)
                resp = requests.get(img_url, timeout=self.timeout)
                resp.raise_for_status()
                with open(filepath, "wb") as f:
                    f.write(resp.content)
                downloaded.append(filepath)
            if downloaded:
                result.file_path = os.path.abspath(downloaded[0])
                result.filename = os.path.basename(downloaded[0])
                result.file_size = os.path.getsize(downloaded[0])
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        return result

    def _download_via_ytdlp(self, task: DownloadTask, result: DownloadResult) -> DownloadResult:
        ytdlp_path = shutil.which("yt-dlp") or "yt-dlp"
        outtmpl = os.path.join(
            task.options.get("output_dir", self.output_dir),
            "%(title)s.%(ext)s")
        cmd = [ytdlp_path, "-f", "best", "-o", outtmpl, task.url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True,
                                  timeout=self.timeout * 10)
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
                result.error = proc.stderr[:500] if proc.stderr else "Failed"
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        return result

    def _save_metadata(self, metadata: dict, out_dir: str,
                       result: DownloadResult) -> DownloadResult:
        filename = self._safe_filename(f"{metadata.get('title', 'tumblr')}_metadata.json")
        filepath = os.path.join(out_dir, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
        result.file_path = os.path.abspath(filepath)
        result.filename = filename
        result.file_size = os.path.getsize(filepath)
        result.status = DownloadStatus.VERIFYING
        return result

    @staticmethod
    def _safe_filename(name: str) -> str:
        return re.sub(r'[<>:"|?*\\]', '_', name)[:200]

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="tumblr",
        formats=tuple(TumblrDownloader.SUPPORTED_FORMATS),
        qualities=tuple(TumblrDownloader.SUPPORTED_QUALITIES),
        features=("posts", "images", "videos", "gifs", "blogs", "batch"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Tumblr downloader: posts, images, videos, GIFs, blog scraping.",
    )
    return ("tumblr", skill)
