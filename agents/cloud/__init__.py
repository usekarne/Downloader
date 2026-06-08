"""
RS Downloader v10.0.0 - Cloud Utility Agent
==============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Cloud utility agent providing:
- Cloud upload orchestration
- Cloud download from various providers
- Sync operations
- Remote file listing
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
    detect_content_type, suggest_filename,
)


class CloudAgent(DownloaderBase):
    """Cloud utility agent for upload, download, and sync operations."""

    AGENT_NAME = "cloud"
    PLATFORM = "cloud"
    SUPPORTED_FORMATS = ["*"]
    SUPPORTED_QUALITIES = ["original", "compressed"]

    _CLOUD_PROVIDERS = {
        "s3": "aws s3",
        "gcs": "gsutil",
        "azure": "az storage blob",
        "r2": "rclone",
        "generic": "rclone",
    }

    def validate_url(self, url: str) -> bool:
        cloud_prefixes = ("s3://", "gs://", "azure://", "r2://", "cloud://")
        return any(url.startswith(p) for p in cloud_prefixes) or url.startswith("http")

    def _detect_provider(self, url: str) -> str:
        if url.startswith("s3://"):
            return "s3"
        if url.startswith("gs://"):
            return "gcs"
        if url.startswith("azure://"):
            return "azure"
        if url.startswith("r2://"):
            return "r2"
        return "generic"

    def upload(self, local_path: str, remote_url: str) -> Dict[str, Any]:
        """Upload a local file to cloud storage."""
        provider = self._detect_provider(remote_url)
        if provider == "s3":
            return self._upload_s3(local_path, remote_url)
        # Fallback to rclone
        return self._upload_rclone(local_path, remote_url)

    def _upload_s3(self, local_path: str, remote_url: str) -> Dict[str, Any]:
        """Upload to S3 using AWS CLI."""
        cmd = ["aws", "s3", "cp", local_path, remote_url]
        if self.proxy:
            cmd = ["HTTPS_PROXY=" + self.proxy] + cmd
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {"success": proc.returncode == 0, "error": proc.stderr[:300] if proc.returncode != 0 else ""}
        except FileNotFoundError:
            return {"success": False, "error": "AWS CLI not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _upload_rclone(self, local_path: str, remote_url: str) -> Dict[str, Any]:
        """Upload using rclone."""
        cmd = ["rclone", "copy", local_path, remote_url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {"success": proc.returncode == 0, "error": proc.stderr[:300] if proc.returncode != 0 else ""}
        except FileNotFoundError:
            return {"success": False, "error": "rclone not installed"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def download(self, remote_url: str, local_path: str = "") -> Dict[str, Any]:
        """Download from cloud storage."""
        provider = self._detect_provider(remote_url)
        out_path = local_path or self.output_dir
        os.makedirs(out_path, exist_ok=True)
        if provider == "s3":
            cmd = ["aws", "s3", "cp", remote_url, out_path]
        else:
            cmd = ["rclone", "copy", remote_url, out_path]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            return {"success": proc.returncode == 0, "error": proc.stderr[:300] if proc.returncode != 0 else "", "local_path": out_path}
        except FileNotFoundError:
            return {"success": False, "error": f"Cloud CLI not installed for {provider}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def sync(self, source: str, destination: str) -> Dict[str, Any]:
        """Sync between local and cloud storage."""
        provider = self._detect_provider(source) or self._detect_provider(destination)
        if provider == "s3":
            cmd = ["aws", "s3", "sync", source, destination]
        else:
            cmd = ["rclone", "sync", source, destination]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            return {"success": proc.returncode == 0, "error": proc.stderr[:300] if proc.returncode != 0 else ""}
        except FileNotFoundError:
            return {"success": False, "error": f"Cloud CLI not installed for {provider}"}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def list_remote(self, remote_url: str) -> Dict[str, Any]:
        """List files in cloud storage."""
        provider = self._detect_provider(remote_url)
        if provider == "s3":
            cmd = ["aws", "s3", "ls", remote_url]
        else:
            cmd = ["rclone", "ls", remote_url]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            if proc.returncode == 0:
                return {"success": True, "listing": proc.stdout}
            return {"success": False, "error": proc.stderr[:300]}
        except FileNotFoundError:
            return {"success": False, "error": f"Cloud CLI not installed for {provider}"}

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [{"format_id": "original", "ext": "*", "quality": "original file"}]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        return {"platform": "cloud", "url": url, "provider": self._detect_provider(url)}

    def on_prepare(self, task: DownloadTask) -> None:
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir

    def on_download(self, task: DownloadTask) -> DownloadResult:
        action = task.options.get("action", "download")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING,
        )
        try:
            out_dir = task.options.get("output_dir", self.output_dir)
            if action == "upload":
                local_path = task.options.get("local_path", "")
                data = self.upload(local_path, task.url)
            elif action == "sync":
                source = task.options.get("source", task.url)
                dest = task.options.get("destination", "")
                data = self.sync(source, dest)
            elif action == "list":
                data = self.list_remote(task.url)
            else:
                data = self.download(task.url, out_dir)
            result.metadata = data
            result.status = DownloadStatus.VERIFYING
            if data.get("local_path") and os.path.exists(data["local_path"]):
                result.file_path = os.path.abspath(data["local_path"])
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        result.elapsed = time.monotonic() - start_time
        return result

    def on_verify(self, task=None, result=None):
        if not result.file_path or not os.path.exists(result.file_path):
            return result.metadata.get("success", False)
        return os.path.getsize(result.file_path) > 0

    def on_post_process(self, task=None, result=None):
        return result


def register() -> Tuple[str, AgentSkill]:
    skill = AgentSkill(
        name="cloud", platform="cloud",
        description="Cloud utility: upload/download/sync via S3/GCS/Azure/R2. AWS CLI + rclone.",
        supported_formats=CloudAgent.SUPPORTED_FORMATS,
        supported_qualities=CloudAgent.SUPPORTED_QUALITIES,
        max_concurrent=2, priority=DownloadPriority.LOW,
    )
    return ("cloud", skill)
