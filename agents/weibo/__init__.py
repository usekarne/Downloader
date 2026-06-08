"""
RS Downloader v10.0.0 - Weibo Download Agent
==============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Weibo downloader supporting:
- Video downloads (all qualities)
- Image/posts downloads (multi-image posts)
- User profile media extraction
- Article content extraction
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


class WeiboDownloader(DownloaderBase):
    """Weibo download agent for videos, images, and posts."""

    AGENT_NAME = "weibo"
    PLATFORM = "weibo"
    SUPPORTED_FORMATS = ["mp4", "mkv", "jpg", "png", "gif", "webp", "json"]
    SUPPORTED_QUALITIES = [
        "1080p", "720p", "480p", "360p",
        "original", "large", "thumbnail",
        "best", "metadata_only",
    ]

    _URL_PATTERNS = [
        re.compile(r'https?://weibo\.com/\d+/[\w]+'),
        re.compile(r'https?://m\.weibo\.cn/status/\d+'),
        re.compile(r'https?://m\.weibo\.cn/detail/\d+'),
        re.compile(r'https?://video\.weibo\.com/show\?fid=\d+'),
        re.compile(r'https?://weibo\.com/tv/show/[\w]+'),
        re.compile(r'https?://www\.weibo\.com/\d+/[\w]+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _detect_type(self, url: str) -> str:
        if "video" in url or "tv/show" in url:
            return "video"
        elif "status" in url or "detail" in url:
            return "post"
        return "profile"

    def _extract_status_id(self, url: str) -> str:
        m = re.search(r'(?:status|detail)/(\d+)', url)
        if m:
            return m.group(1)
        m = re.search(r'/(\d+)/([\w]+)', url)
        return m.group(2) if m else ""

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        ctype = self._detect_type(url)
        formats = []
        if ctype == "video":
            for q in ["1080p", "720p", "480p", "360p"]:
                formats.append({"format_id": q, "ext": "mp4", "quality": q})
        elif ctype == "post":
            formats.append({"format_id": "original", "ext": "jpg", "quality": "original images"})
        formats.append({"format_id": "metadata", "ext": "json", "quality": "metadata only"})
        return formats

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        ctype = self._detect_type(url)
        status_id = self._extract_status_id(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "weibo", "content_type": ctype,
            "status_id": status_id}
        # Try mobile API for post data
        if status_id:
            try:
                api_url = f"https://m.weibo.cn/statuses/show?id={status_id}"
                resp = requests.get(api_url, headers=self._mobile_headers(),
                                    timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json().get("data", {})
                    metadata["title"] = data.get("status_title", "")
                    metadata["text"] = data.get("text", "")
                    metadata["user"] = data.get("user", {}).get("screen_name", "")
                    metadata["reposts"] = data.get("reposts_count", 0)
                    metadata["comments"] = data.get("comments_count", 0)
                    metadata["attitudes"] = data.get("attitudes_count", 0)
                    # Extract images
                    pics = data.get("pics", [])
                    metadata["images"] = [
                        p.get("large", {}).get("url", p.get("url", ""))
                        for p in pics
                    ]
                    # Extract video
                    page_info = data.get("page_info", {})
                    if page_info.get("type") == "video":
                        media_info = page_info.get("media_info", {})
                        metadata["video_url"] = (
                            media_info.get("stream_url_hd") or
                            media_info.get("stream_url") or
                            media_info.get("mp4_hd_url") or
                            media_info.get("mp4_sd_url", "")
                        )
                        metadata["video_cover"] = page_info.get("page_pic", {}).get("url", "")
            except Exception as exc:
                metadata["error"] = str(exc)
        return metadata

    @staticmethod
    def _mobile_headers() -> Dict[str, str]:
        return {
            "User-Agent": ("Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) "
                           "AppleWebKit/605.1.15"),
            "Accept": "application/json",
        }

    @staticmethod
    def _browser_headers() -> Dict[str, str]:
        return {
            "User-Agent": ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                           "KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"),
        }

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid Weibo URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        task.options["content_type"] = self._detect_type(task.url)

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests as req_lib
        quality = task.options.get("quality", "best")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)
        try:
            metadata = self.get_metadata(task.url)
            result.metadata = metadata
            out_dir = task.options.get("output_dir", self.output_dir)
            ctype = task.options.get("content_type", "post")

            if quality == "metadata_only":
                return self._save_metadata(metadata, out_dir, result)

            if ctype == "video":
                video_url = metadata.get("video_url", "")
                if video_url:
                    filename = self._safe_filename(f"{metadata.get('user', 'weibo')}_video.mp4")
                    filepath = os.path.join(out_dir, filename)
                    resp = req_lib.get(video_url, headers=self._browser_headers(),
                                       timeout=self.timeout)
                    resp.raise_for_status()
                    with open(filepath, "wb") as f:
                        f.write(resp.content)
                    result.file_path = os.path.abspath(filepath)
                    result.filename = filename
                    result.file_size = len(resp.content)
                else:
                    # Fallback to yt-dlp
                    return self._download_via_ytdlp(task, result, quality)
            elif ctype == "post":
                images = metadata.get("images", [])
                if images:
                    for i, img_url in enumerate(images[:20]):
                        filename = self._safe_filename(f"weibo_{i}.jpg")
                        filepath = os.path.join(out_dir, filename)
                        resp = req_lib.get(img_url, headers=self._browser_headers(),
                                           timeout=self.timeout)
                        if resp.status_code == 200:
                            with open(filepath, "wb") as f:
                                f.write(resp.content)
                            if i == 0:
                                result.file_path = os.path.abspath(filepath)
                                result.filename = filename
                                result.file_size = len(resp.content)
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
        return result

    def _download_via_ytdlp(self, task: DownloadTask, result: DownloadResult,
                            quality: str) -> DownloadResult:
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
        except Exception:
            result.status = DownloadStatus.FAILED
        return result

    def _save_metadata(self, metadata: dict, out_dir: str,
                       result: DownloadResult) -> DownloadResult:
        filename = self._safe_filename(f"weibo_metadata.json")
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

    def on_verify(self, result: DownloadResult) -> bool:
        if not result.file_path or not os.path.exists(result.file_path):
            return False
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, result: DownloadResult) -> DownloadResult:
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        platform="weibo",
        formats=tuple(WeiboDownloader.SUPPORTED_FORMATS),
        qualities=tuple(WeiboDownloader.SUPPORTED_QUALITIES),
        features=("videos", "images", "posts", "articles", "mobile_api"),
        max_concurrent=3,
        priority=DownloadPriority.NORMAL,
        version="10.0.0",
        description="Weibo downloader: videos, images, posts via mobile API + yt-dlp.",
    )
    return ("weibo", skill)
