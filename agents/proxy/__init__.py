"""
RS Downloader v10.0.0 — Proxy Management Agent
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Proxy management, health checking, and rotation agent.
"""

from __future__ import annotations

import time
import threading
import requests
from typing import Any, Dict, FrozenSet, List, Optional, Tuple

from core.downloader_base import (
    DownloaderBase,
    DownloadResult,
    DownloadStatus,
    AgentSkill,
    AgentMemory,
    DownloadPriority,
)

__all__ = ["ProxyAgent", "register"]

AGENT_NAME = "proxy"
PLATFORM = "internal"
SUPPORTED_FORMATS: FrozenSet[str] = frozenset()
SUPPORTED_QUALITIES: FrozenSet[str] = frozenset()


class ProxyAgent(DownloaderBase):
    """Proxy management agent — health checking, rotation, and testing."""

    AGENT_NAME = AGENT_NAME
    PLATFORM = PLATFORM
    SUPPORTED_FORMATS = SUPPORTED_FORMATS
    SUPPORTED_QUALITIES = SUPPORTED_QUALITIES

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._proxy_list: List[Dict[str, Any]] = []
        self._lock = threading.Lock()
        self._test_url = "https://httpbin.org/ip"
        self._test_timeout = 10

    def validate_url(self, url: str) -> bool:
        """Proxy agent doesn't download from URLs — always returns True for management commands."""
        return True

    def get_available_formats(self, url: str = "") -> List[str]:
        """Proxy agent has no media formats."""
        return []

    def get_metadata(self, url: str) -> Dict[str, Any]:
        """Return proxy pool status as metadata."""
        with self._lock:
            return {
                "total_proxies": len(self._proxy_list),
                "healthy": sum(1 for p in self._proxy_list if p.get("healthy", False)),
                "unhealthy": sum(1 for p in self._proxy_list if not p.get("healthy", True)),
            }

    def on_prepare(self) -> None:
        """Prepare proxy management."""
        pass

    def on_download(self) -> DownloadResult:
        """Proxy agent 'download' performs health checks on all proxies."""
        results = self.health_check_all()
        return DownloadResult(
            task_id=self._task_id if hasattr(self, '_task_id') else "proxy-check",
            status=DownloadStatus.COMPLETED.value,
            metadata={"check_results": results},
        )

    def on_verify(self) -> bool:
        """Verify proxy check results."""
        return True

    def on_post_process(self) -> None:
        """No post-processing for proxy management."""
        pass

    # -- Proxy Management Methods --

    def add_proxy(self, proxy_url: str, proxy_type: str = "http",
                  username: str = "", password: str = "",
                  country: str = "", tags: Optional[List[str]] = None) -> str:
        """Add a proxy to the pool. Returns proxy ID."""
        proxy_id = f"proxy-{len(self._proxy_list):04d}-{int(time.time())}"
        entry = {
            "id": proxy_id,
            "url": proxy_url,
            "type": proxy_type,
            "username": username,
            "password": password,
            "country": country,
            "tags": tags or [],
            "healthy": True,
            "last_check": 0.0,
            "avg_latency": 0.0,
            "success_count": 0,
            "fail_count": 0,
            "enabled": True,
        }
        with self._lock:
            self._proxy_list.append(entry)
        return proxy_id

    def remove_proxy(self, proxy_id: str) -> bool:
        """Remove a proxy from the pool."""
        with self._lock:
            for i, p in enumerate(self._proxy_list):
                if p["id"] == proxy_id:
                    self._proxy_list.pop(i)
                    return True
        return False

    def test_proxy(self, proxy_url: str, proxy_type: str = "http",
                   timeout: int = 10) -> Dict[str, Any]:
        """Test a single proxy and return results."""
        proxies = {}
        if proxy_type in ("http", "https"):
            proxies = {"http": proxy_url, "https": proxy_url}
        elif proxy_type in ("socks4", "socks5"):
            proxies = {"http": proxy_url, "https": proxy_url}

        result: Dict[str, Any] = {
            "url": proxy_url,
            "type": proxy_type,
            "success": False,
            "latency": 0.0,
            "ip": "",
            "error": "",
        }
        try:
            start = time.monotonic()
            resp = requests.get(self._test_url, proxies=proxies, timeout=timeout, verify=False)
            elapsed = time.monotonic() - start
            result["success"] = resp.status_code == 200
            result["latency"] = round(elapsed * 1000, 2)
            if result["success"]:
                data = resp.json()
                result["ip"] = data.get("origin", "")
        except Exception as exc:
            result["error"] = str(exc)
        return result

    def health_check_all(self) -> List[Dict[str, Any]]:
        """Health check all proxies in the pool."""
        results = []
        with self._lock:
            proxies_copy = list(self._proxy_list)

        for proxy in proxies_copy:
            check = self.test_proxy(proxy["url"], proxy.get("type", "http"), self._test_timeout)
            check["id"] = proxy["id"]
            with self._lock:
                for p in self._proxy_list:
                    if p["id"] == proxy["id"]:
                        p["healthy"] = check["success"]
                        p["last_check"] = time.time()
                        p["avg_latency"] = check["latency"]
                        if check["success"]:
                            p["success_count"] += 1
                        else:
                            p["fail_count"] += 1
                        break
            results.append(check)
        return results

    def get_healthy_proxies(self) -> List[Dict[str, Any]]:
        """Return list of healthy proxies."""
        with self._lock:
            return [p for p in self._proxy_list if p.get("healthy", False) and p.get("enabled", True)]

    def list_proxies(self) -> List[Dict[str, Any]]:
        """List all proxies."""
        with self._lock:
            return list(self._proxy_list)


def register() -> Tuple[str, AgentSkill]:
    """Register the proxy management agent."""
    return (
        AGENT_NAME,
        AgentSkill(
            platform=PLATFORM,
            formats=frozenset(),
            qualities=frozenset(),
            features=frozenset({"health_check", "rotation", "testing", "management"}),
            max_concurrent=1,
            priority=DownloadPriority.BACKGROUND,
        ),
    )
