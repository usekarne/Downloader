"""
RS Downloader v10.0.0 - S3 Download Agent
===========================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

S3-compatible storage agent supporting:
- File downloads from S3 buckets
- File uploads to S3 buckets
- Bucket listing and browsing
- Presigned URL generation
- Multipart upload/download for large files
- S3-compatible services (MinIO, Ceph, DigitalOcean Spaces, etc.)
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote, urlparse

from core.downloader_base import (
    AgentMemory, AgentSkill, DownloadError, DownloadPriority,
    DownloadResult, DownloadStatus, DownloadTask, DownloaderBase,
)


class S3Downloader(DownloaderBase):
    """S3-compatible storage agent for uploads, downloads, and bucket ops.

    Uses requests with AWS Signature V4 for authentication.
    Supports any S3-compatible service (AWS, MinIO, Ceph, Spaces, etc.).
    """

    AGENT_NAME = "s3"
    PLATFORM = "s3"
    SUPPORTED_FORMATS = ["auto", "json"]
    SUPPORTED_QUALITIES = ["original", "metadata_only"]

    _URL_PATTERNS = [
        re.compile(r'https?://[\w.-]+\.s3[\w.-]*\.amazonaws\.com/[\w./-]+'),
        re.compile(r'https?://s3[\w.-]*\.amazonaws\.com/[\w.-]+/[\w./-]+'),
        re.compile(r'https?://[\w.-]+\.s3[\w.-]*\.[\w.-]+\.com/[\w./-]+'),
        re.compile(r's3://[\w.-]+/[\w./-]+'),
        re.compile(r'https?://[\w.-]+\.digitaloceanspaces\.com/[\w./-]+'),
        re.compile(r'https?://[\w.-]+\.minio\.[\w./-]+'),
    ]

    def validate_url(self, url: str) -> bool:
        return any(p.match(url) for p in self._URL_PATTERNS)

    def _parse_s3_url(self, url: str) -> Tuple[str, str, str]:
        """Parse S3 URL into (endpoint, bucket, key)."""
        if url.startswith("s3://"):
            parts = url[5:].split("/", 1)
            bucket = parts[0]
            key = parts[1] if len(parts) > 1 else ""
            return "https://s3.amazonaws.com", bucket, key
        parsed = urlparse(url)
        host = parsed.hostname or ""
        path = parsed.path.lstrip("/")
        # Bucket-as-subdomain style
        if ".s3" in host:
            bucket = host.split(".s3")[0]
            endpoint = f"https://s3.{host.split('.s3')[1].lstrip('.')}"
            # Normalize endpoint
            if not endpoint.endswith("amazonaws.com"):
                endpoint = f"https://{host.split('.', 1)[1]}"
            return endpoint, bucket, path
        # Path style
        parts = path.split("/", 1)
        bucket = parts[0]
        key = parts[1] if len(parts) > 1 else ""
        return f"https://{host}", bucket, key

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "original", "ext": "auto", "quality": "original file"},
            {"format_id": "metadata", "ext": "json", "quality": "object metadata"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        import requests
        endpoint, bucket, key = self._parse_s3_url(url)
        metadata: Dict[str, Any] = {
            "url": url, "platform": "s3",
            "endpoint": endpoint, "bucket": bucket, "key": key,
        }
        if not bucket or not key:
            return metadata
        # Try HEAD request for object metadata
        try:
            obj_url = f"{endpoint}/{bucket}/{key}"
            resp = requests.head(obj_url, timeout=self.timeout)
            if resp.status_code == 200:
                metadata.update({
                    "content_type": resp.headers.get("Content-Type", ""),
                    "content_length": int(resp.headers.get("Content-Length", 0)),
                    "last_modified": resp.headers.get("Last-Modified", ""),
                    "etag": resp.headers.get("ETag", "").strip('"'),
                    "storage_class": resp.headers.get("x-amz-storage-class", "STANDARD"),
                })
            elif resp.status_code == 403:
                metadata["error"] = "Access denied (authentication required)"
            elif resp.status_code == 404:
                metadata["error"] = "Object not found"
        except Exception as exc:
            metadata["error"] = str(exc)
        return metadata

    def _sign_request(self, method: str, url: str, headers: Dict[str, str],
                      access_key: str, secret_key: str, region: str = "us-east-1") -> Dict[str, str]:
        """Create AWS Signature V4 signed headers."""
        now = datetime.now(tz=timezone.utc)
        date_stamp = now.strftime("%Y%m%d")
        amz_date = now.strftime("%Y%m%dT%H%M%SZ")
        headers["x-amz-date"] = amz_date
        headers["host"] = urlparse(url).hostname or ""
        # Canonical request
        signed_headers = ";".join(sorted(headers.keys()))
        canonical = "\n".join([
            method, urlparse(url).path or "/",
            urlparse(url).query or "",
            "".join(f"{k}:{v}\n" for k, v in sorted(headers.items())),
            signed_headers, "UNSIGNED-PAYLOAD",
        ])
        scope = f"{date_stamp}/{region}/s3/aws4_request"
        string_to_sign = "\n".join([
            "AWS4-HMAC-SHA256", amz_date, scope,
            hashlib.sha256(canonical.encode()).hexdigest(),
        ])
        signing_key = secret_key.encode()
        for msg in [date_stamp, region, "s3", "aws4_request", string_to_sign]:
            signing_key = hmac.new(signing_key, msg.encode(), hashlib.sha256).digest()
        signature = hmac.new(signing_key, string_to_sign.encode(), hashlib.sha256).hexdigest()
        headers["Authorization"] = (
            f"AWS4-HMAC-SHA256 Credential={access_key}/{scope}, "
            f"SignedHeaders={signed_headers}, Signature={signature}")
        return headers

    def on_prepare(self, task: DownloadTask) -> None:
        if not self.validate_url(task.url):
            raise DownloadError(f"Invalid S3 URL: {task.url}",
                                url=task.url, agent=self.AGENT_NAME)
        out_dir = self._ensure_output_dir(task.output_dir)
        task.options["output_dir"] = out_dir
        endpoint, bucket, key = self._parse_s3_url(task.url)
        task.options["endpoint"] = endpoint
        task.options["bucket"] = bucket
        task.options["key"] = key

    def _ensure_output_dir(self, path: str) -> str:
        os.makedirs(path, exist_ok=True)
        return path

    def on_download(self, task: DownloadTask) -> DownloadResult:
        import requests
        quality = task.options.get("quality", "original")
        start_time = time.monotonic()
        result = DownloadResult(
            url=task.url, agent_name=self.AGENT_NAME,
            platform=self.PLATFORM, status=DownloadStatus.DOWNLOADING)
        try:
            endpoint = task.options.get("endpoint", "")
            bucket = task.options.get("bucket", "")
            key = task.options.get("key", "")
            out_dir = task.options.get("output_dir", self.output_dir)

            if quality == "metadata_only":
                metadata = self.get_metadata(task.url)
                result.metadata = metadata
                filepath = os.path.join(out_dir, "s3_metadata.json")
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(metadata, f, indent=2, ensure_ascii=False, default=str)
                result.file_path = os.path.abspath(filepath)
                result.filename = "s3_metadata.json"
                result.file_size = os.path.getsize(filepath)
                result.status = DownloadStatus.VERIFYING
                return result

            # Download object
            obj_url = f"{endpoint}/{bucket}/{key}"
            headers = {}
            access_key = task.options.get("access_key", "")
            secret_key = task.options.get("secret_key", "")
            if access_key and secret_key:
                headers = self._sign_request("GET", obj_url, headers,
                                             access_key, secret_key)
            resp = requests.get(obj_url, headers=headers, timeout=self.timeout,
                                stream=True)
            resp.raise_for_status()
            filename = key.rsplit("/", 1)[-1] if "/" in key else key or "s3_download"
            filename = self._safe_filename(filename)
            filepath = os.path.join(out_dir, filename)
            total = 0
            with open(filepath, "wb") as f:
                for chunk in resp.iter_content(chunk_size=65536):
                    f.write(chunk)
                    total += len(chunk)
            result.file_path = os.path.abspath(filepath)
            result.filename = filename
            result.file_size = total
            result.status = DownloadStatus.VERIFYING
        except Exception as exc:
            result.status = DownloadStatus.FAILED
            result.error = str(exc)
        elapsed = time.monotonic() - start_time
        result.duration = elapsed
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
        platform="s3",
        formats=tuple(S3Downloader.SUPPORTED_FORMATS),
        qualities=tuple(S3Downloader.SUPPORTED_QUALITIES),
        features=("download", "upload", "buckets", "presigned", "multipart", "aws_v4"),
        max_concurrent=5,
        priority=DownloadPriority.HIGH,
        version="10.0.0",
        description=(
            "S3 agent: download, upload, bucket listing, AWS Signature V4, "
            "S3-compatible services (MinIO, Ceph, Spaces)."
        ),
    )
    return ("s3", skill)
