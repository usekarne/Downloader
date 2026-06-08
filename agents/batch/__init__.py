"""
RS Downloader v10.0.0 - Batch Utility Agent
==============================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Batch utility agent providing:
- Batch URL processing from text files
- URL list parsing and validation
- Support for TXT, CSV, JSON batch files
- Progress tracking for batch operations
"""

from __future__ import annotations

import csv
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


class BatchAgent(DownloaderBase):
    """Batch utility agent for processing multiple URLs from files."""

    AGENT_NAME = "batch"
    PLATFORM = "batch"
    SUPPORTED_FORMATS = ["txt", "csv", "json"]
    SUPPORTED_QUALITIES = ["sequential", "parallel"]

    def validate_url(self, url: str) -> bool:
        return os.path.exists(url) or url.startswith("file://") or url == "batch"

    def parse_batch_file(self, filepath: str) -> List[Dict[str, Any]]:
        """Parse a batch file (TXT/CSV/JSON) into a list of URL entries."""
        filepath = filepath.replace("file://", "")
        if not os.path.exists(filepath):
            raise DownloadError(f"Batch file not found: {filepath}", url=filepath, agent=self.AGENT_NAME)
        ext = Path(filepath).suffix.lower()
        entries = []
        if ext == ".json":
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, str):
                        entries.append({"url": item})
                    elif isinstance(item, dict):
                        entries.append(item)
            elif isinstance(data, dict):
                for url in data.get("urls", []):
                    if isinstance(url, str):
                        entries.append({"url": url})
                    elif isinstance(url, dict):
                        entries.append(url)
        elif ext == ".csv":
            with open(filepath, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    url = row.get("url", row.get("URL", ""))
                    if url:
                        entries.append(dict(row))
        else:
            # TXT file: one URL per line
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and line.startswith("http"):
                        entries.append({"url": line})
        return entries

    def validate_batch(self, entries: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Validate a batch of URL entries."""
        valid = []
        invalid = []
        duplicates = set()
        seen = set()
        for entry in entries:
            url = entry.get("url", "")
            if not url:
                invalid.append({"entry": entry, "reason": "no URL"})
                continue
            if url in seen:
                duplicates.add(url)
                continue
            seen.add(url)
            if url.startswith("http") or url.startswith("magnet:") or os.path.exists(url):
                valid.append(entry)
            else:
                invalid.append({"entry": entry, "reason": "invalid URL format"})
        return {
            "total": len(entries),
            "valid": len(valid),
            "invalid": len(invalid),
            "duplicates": len(duplicates),
            "valid_entries": valid,
            "invalid_entries": invalid,
        }

    def process_batch(self, filepath: str, output_dir: str = "") -> Dict[str, Any]:
        """Process a batch file and return results."""
        entries = self.parse_batch_file(filepath)
        validation = self.validate_batch(entries)
        return {
            "source_file": filepath,
            "entries_found": len(entries),
            "valid_urls": validation["valid"],
            "invalid_urls": validation["invalid"],
            "duplicates": validation["duplicates"],
            "ready_to_download": validation["valid_entries"],
        }

    def get_available_formats(self, url: str) -> List[Dict[str, Any]]:
        return [
            {"format_id": "txt", "ext": "txt", "quality": "plain text URLs"},
            {"format_id": "csv", "ext": "csv", "quality": "CSV with metadata"},
            {"format_id": "json", "ext": "json", "quality": "structured JSON"},
        ]

    def get_metadata(self, url: str) -> Dict[str, Any]:
        if os.path.exists(url.replace("file://", "")):
            return self.process_batch(url.replace("file://", ""))
        return {"platform": "batch"}

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
            filepath = task.url.replace("file://", "")
            if os.path.exists(filepath):
                batch_result = self.process_batch(filepath, out_dir)
            else:
                batch_result = {"error": "No batch file specified", "entries_found": 0}
            result.metadata = batch_result
            filename = self._safe_filename("batch_result.json")
            filepath_out = os.path.join(out_dir, filename)
            with open(filepath_out, "w", encoding="utf-8") as f:
                json.dump(batch_result, f, indent=2, ensure_ascii=False, default=str)
            result.file_path = os.path.abspath(filepath_out)
            result.filename = filename
            result.file_size = os.path.getsize(filepath_out)
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
        name="batch", platform="batch",
        description="Batch utility: process URL files (TXT/CSV/JSON), validate, parse, batch download.",
        supported_formats=BatchAgent.SUPPORTED_FORMATS,
        supported_qualities=BatchAgent.SUPPORTED_QUALITIES,
        max_concurrent=1, priority=DownloadPriority.HIGH,
    )
    return ("batch", skill)
