"""
RS Downloader v10.0.0 - Analytics Utility Agent
==================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Analytics utility agent providing:
- Usage statistics and patterns
- Download trend analysis
- Quality recommendations based on history
- Platform usage breakdown
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class AnalyticsAgent(DownloaderBase):
    """Analytics utility agent for usage statistics and recommendations."""

    AGENT_NAME = "analytics"
    PLATFORM = "analytics"
    SUPPORTED_FORMATS = ["json", "txt", "csv"]
    SUPPORTED_QUALITIES = ["detailed", "summary"]

    def validate_url(self, url: str) -> bool:
        return url == "analytics" or url.startswith("analytics:") or bool(url.strip())

    def get_stats(self, time_range: str = "all") -> Dict[str, Any]:
        """Get download statistics from agent memory."""
        total_downloads = self.memory.get("total_downloads", 0)
        total_bytes = self.memory.get("total_bytes", 0)
        platform_counts = self.memory.get("platform_counts", {})
        format_counts = self.memory.get("format_counts", {})
        quality_counts = self.memory.get("quality_counts", {})
        errors = self.memory.get("error_count", 0)
        avg_speed = self.memory.get("avg_speed", 0.0)
        return {
            "total_downloads": total_downloads,
            "total_bytes": total_bytes,
            "total_gb": round(total_bytes / (1024 ** 3), 2),
            "platform_breakdown": platform_counts,
            "format_breakdown": format_counts,
            "quality_breakdown": quality_counts,
            "error_count": errors,
            "avg_speed_kbps": round(avg_speed / 1024, 2),
            "time_range": time_range,
        }

    def get_trends(self) -> Dict[str, Any]:
        """Analyze download trends from history."""
        recent_platforms = self.memory.get("recent_platforms", [])
        daily_counts = self.memory.get("daily_counts", {})
        peak_hours = self.memory.get("peak_hours", {})
        return {
            "most_used_platform": max(recent_platforms, key=recent_platforms.count) if recent_platforms else "none",
            "daily_activity": daily_counts,
            "peak_hours": peak_hours,
            "trend": "increasing" if len(daily_counts) > 3 else "stable",
        }

    def recommend_quality(self, platform: str = "") -> Dict[str, Any]:
        """Recommend quality settings based on download history."""
        quality_history = self.memory.get("quality_counts", {})
        platform_prefs = self.memory.get(f"platform_{platform}_qualities", {})
        if platform_prefs:
            best = max(platform_prefs, key=platform_prefs.get)
            return {"recommended_quality": best, "reason": "based on your history", "platform": platform}
        if quality_history:
            best = max(quality_history, key=quality_history.get)
            return {"recommended_quality": best, "reason": "based on overall history"}
        return {"recommended_quality": "best", "reason": "default recommendation"}

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "json", "ext": "json", "quality": "detailed JSON report"},
            {"format_id": "txt", "ext": "txt", "quality": "text summary"},
            {"format_id": "csv", "ext": "csv", "quality": "CSV data"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        return self.get_stats()

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
            out_dir = task.options.get("output_dir", self.output_dir)
            action = task.options.get("action", "stats")
            if action == "stats":
                data = self.get_stats()
            elif action == "trends":
                data = self.get_trends()
            elif action == "recommend_quality":
                data = self.recommend_quality(task.options.get("platform", ""))
            else:
                data = {"stats": self.get_stats(), "trends": self.get_trends()}
            result.metadata = data
            filename = self._safe_filename(f"analytics_{action}.json")
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
        name="analytics", platform="analytics",
        description="Analytics utility: usage stats, trends, quality recommendations, platform breakdown.",
        supported_formats=AnalyticsAgent.SUPPORTED_FORMATS,
        supported_qualities=AnalyticsAgent.SUPPORTED_QUALITIES,
        max_concurrent=5, priority=DownloadPriority.LOW,
    )
    return ("analytics", skill)
