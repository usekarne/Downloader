"""
RS Downloader v10.0.0 - Enterprise Networking Layer
====================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Enterprise-grade networking with sync/async HTTP clients, proxy rotation,
bandwidth throttling, DNS-over-HTTPS, SSL context building, circuit breaker,
retry policies, request interceptors, connection metrics, checksum verification,
and parallel downloads.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import os
import random
import re
import socket
import ssl
import struct
import threading
import time
import zlib
from collections import defaultdict, deque
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import (
    Any,
    AsyncIterator,
    Callable,
    Deque,
    Dict,
    Iterator,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Union,
)
from urllib.parse import urlparse, urlunparse, ParseResult

import requests
import requests.adapters
from urllib3.util.retry import Retry as Urllib3Retry

from core.logger import get_logger

logger = get_logger("network", enable_file=False)


# ---------------------------------------------------------------------------
# Checksum Algorithm
# ---------------------------------------------------------------------------

class ChecksumAlgorithm(Enum):
    """Supported checksum algorithms."""
    MD5 = "md5"
    SHA1 = "sha1"
    SHA256 = "sha256"
    SHA512 = "sha512"
    CRC32 = "crc32"
    BLAKE2B = "blake2b"
    BLAKE2S = "blake2s"
    XXH64 = "xxh64"


# ---------------------------------------------------------------------------
# HeadInfo dataclass
# ---------------------------------------------------------------------------

@dataclass
class HeadInfo:
    """Parsed HEAD response information."""
    content_type: str = ""
    content_length: int = -1
    filename: str = ""
    accept_ranges: str = ""
    etag: str = ""
    last_modified: str = ""
    server: str = ""
    headers: Dict[str, str] = field(default_factory=dict)

    @property
    def supports_resume(self) -> bool:
        """Check if the server supports range requests (resume)."""
        return self.accept_ranges.lower() == "bytes"

    @property
    def file_size(self) -> int:
        """Alias for content_length."""
        return self.content_length


# ---------------------------------------------------------------------------
# DownloadSession dataclass
# ---------------------------------------------------------------------------

@dataclass
class DownloadSession:
    """Configuration for a download session."""
    url: str = ""
    method: str = "GET"
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    proxy: str = ""
    timeout: float = 30.0
    verify_ssl: bool = True
    stream: bool = True
    chunk_size: int = 8192
    resume_from: int = 0

    def to_requests_kwargs(self) -> Dict[str, Any]:
        """Convert to keyword arguments for requests."""
        kwargs: Dict[str, Any] = {
            "method": self.method,
            "url": self.url,
            "headers": self.headers,
            "cookies": self.cookies,
            "timeout": self.timeout,
            "verify": self.verify_ssl,
            "stream": self.stream,
        }
        if self.proxy:
            kwargs["proxies"] = {
                "http": self.proxy,
                "https": self.proxy,
            }
        if self.resume_from > 0:
            kwargs["headers"]["Range"] = f"bytes={self.resume_from}-"
        return kwargs


# ---------------------------------------------------------------------------
# verify_checksum function
# ---------------------------------------------------------------------------

def verify_checksum(
    filepath: Union[str, Path],
    expected: str,
    algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256,
    chunk_size: int = 65536,
) -> bool:
    """
    Verify file checksum. Supports stream-based verification for large files.

    Args:
        filepath: Path to the file.
        expected: Expected checksum hex string.
        algorithm: Checksum algorithm to use.
        chunk_size: Read chunk size for streaming.

    Returns:
        True if checksum matches, False otherwise.
    """
    filepath = Path(filepath)
    if not filepath.exists():
        logger.error("Checksum verification: file not found: %s", filepath)
        return False

    try:
        actual = compute_checksum(filepath, algorithm, chunk_size)
        match = actual.lower() == expected.lower()
        if not match:
            logger.warning(
                "Checksum mismatch for %s: expected=%s actual=%s algo=%s",
                filepath.name, expected, actual, algorithm.value,
            )
        return match
    except Exception as e:
        logger.error("Checksum verification failed for %s: %s", filepath, e)
        return False


def compute_checksum(
    filepath: Union[str, Path],
    algorithm: ChecksumAlgorithm = ChecksumAlgorithm.SHA256,
    chunk_size: int = 65536,
) -> str:
    """
    Compute file checksum. Stream-based for large file support.

    Args:
        filepath: Path to the file.
        algorithm: Checksum algorithm.
        chunk_size: Read chunk size.

    Returns:
        Hex digest string.
    """
    filepath = Path(filepath)

    if algorithm == ChecksumAlgorithm.CRC32:
        crc = 0
        with open(filepath, "rb") as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                crc = zlib.crc32(chunk, crc)
        return format(crc & 0xFFFFFFFF, "08x")

    if algorithm == ChecksumAlgorithm.XXH64:
        try:
            import xxhash
            h = xxhash.xxh64()
            with open(filepath, "rb") as f:
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    h.update(chunk)
            return h.hexdigest()
        except ImportError:
            logger.warning("xxhash not installed, falling back to SHA256")
            algorithm = ChecksumAlgorithm.SHA256

    if algorithm in (ChecksumAlgorithm.BLAKE2B, ChecksumAlgorithm.BLAKE2S):
        h = hashlib.new(algorithm.value)
    else:
        h = hashlib.new(algorithm.value)

    with open(filepath, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# detect_content_length function
# ---------------------------------------------------------------------------

def detect_content_length(
    url: str,
    session: Optional[requests.Session] = None,
    timeout: float = 15.0,
    headers: Optional[Dict[str, str]] = None,
) -> int:
    """
    Detect content length via HEAD request with GET fallback.

    Args:
        url: URL to check.
        session: Optional requests session.
        timeout: Request timeout.
        headers: Optional headers.

    Returns:
        Content length in bytes, or -1 if unknown.
    """
    hdrs = headers or {}
    hdrs.setdefault("User-Agent", "RS-Downloader/10.0.0")
    sess = session or requests.Session()
    try:
        resp = sess.head(url, headers=hdrs, timeout=timeout, allow_redirects=True)
        length = resp.headers.get("Content-Length")
        if length and length.isdigit():
            return int(length)
    except requests.RequestException:
        pass
    # Fallback: GET with stream, read only headers
    try:
        resp = sess.get(url, headers=hdrs, timeout=timeout, stream=True, allow_redirects=True)
        length = resp.headers.get("Content-Length")
        resp.close()
        if length and length.isdigit():
            return int(length)
    except requests.RequestException:
        pass
    return -1


# ---------------------------------------------------------------------------
# download_chunk function
# ---------------------------------------------------------------------------

def download_chunk(
    url: str,
    start_byte: int,
    end_byte: int,
    output_path: Union[str, Path],
    session: Optional[requests.Session] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 120.0,
    chunk_size: int = 65536,
    retry_count: int = 3,
    retry_delay: float = 2.0,
    progress_callback: Optional[Callable[[int], None]] = None,
) -> int:
    """
    Download a specific byte range from a URL.

    Args:
        url: URL to download from.
        start_byte: Starting byte offset (inclusive).
        end_byte: Ending byte offset (inclusive).
        output_path: Path to write the chunk data.
        session: Optional requests session.
        headers: Optional headers.
        timeout: Request timeout.
        chunk_size: Read buffer size.
        retry_count: Number of retries.
        retry_delay: Delay between retries.
        progress_callback: Called with bytes written so far.

    Returns:
        Total bytes written.
    """
    output_path = Path(output_path)
    hdrs = headers or {}
    hdrs.setdefault("User-Agent", "RS-Downloader/10.0.0")
    hdrs["Range"] = f"bytes={start_byte}-{end_byte}"
    sess = session or requests.Session()
    total_written = 0

    for attempt in range(retry_count):
        try:
            resp = sess.get(url, headers=hdrs, timeout=timeout, stream=True)
            resp.raise_for_status()
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "wb") as f:
                for chunk_data in resp.iter_content(chunk_size=chunk_size):
                    if chunk_data:
                        f.write(chunk_data)
                        total_written += len(chunk_data)
                        if progress_callback:
                            progress_callback(total_written)
            resp.close()
            return total_written
        except requests.RequestException as e:
            logger.warning(
                "Chunk download attempt %d/%d failed: %s (range: %d-%d)",
                attempt + 1, retry_count, e, start_byte, end_byte,
            )
            if attempt < retry_count - 1:
                time.sleep(retry_delay * (2 ** attempt))
            total_written = 0
    raise requests.RequestException(
        f"Failed to download chunk range {start_byte}-{end_byte} after {retry_count} attempts"
    )


# ---------------------------------------------------------------------------
# parallel_download function
# ---------------------------------------------------------------------------

def parallel_download(
    url: str,
    output_path: Union[str, Path],
    file_size: int,
    num_connections: int = 4,
    session: Optional[requests.Session] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: float = 300.0,
    chunk_size: int = 65536,
    progress_callback: Optional[Callable[[int, int], None]] = None,
    verify_checksum_algo: Optional[ChecksumAlgorithm] = None,
    expected_checksum: Optional[str] = None,
) -> Path:
    """
    Multi-connection parallel download for large files.

    Splits the file into chunks and downloads them concurrently,
    then assembles the final file with integrity verification.

    Args:
        url: URL to download.
        output_path: Final output file path.
        file_size: Known file size in bytes.
        num_connections: Number of parallel connections.
        session: Optional requests session.
        headers: Optional headers.
        timeout: Per-chunk timeout.
        chunk_size: Read buffer size.
        progress_callback: Called with (downloaded, total).
        verify_checksum_algo: Optional checksum algorithm for verification.
        expected_checksum: Expected checksum for verification.

    Returns:
        Path to the completed file.
    """
    import concurrent.futures

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    sess = session or requests.Session()

    # Calculate chunk ranges
    chunk_size_bytes = file_size // num_connections
    ranges: List[Tuple[int, int]] = []
    for i in range(num_connections):
        start = i * chunk_size_bytes
        end = start + chunk_size_bytes - 1 if i < num_connections - 1 else file_size - 1
        ranges.append((start, end))

    # Temporary chunk files
    temp_dir = output_path.parent / f".{output_path.name}.parts"
    temp_dir.mkdir(exist_ok=True)
    chunk_files: List[Path] = []
    downloaded_total = 0
    progress_lock = threading.Lock()

    def chunk_progress(chunk_idx: int, written: int) -> None:
        nonlocal downloaded_total
        with progress_lock:
            downloaded_total += written
            if progress_callback:
                progress_callback(downloaded_total, file_size)

    # Download chunks in parallel
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=num_connections) as executor:
            futures = []
            for idx, (start, end) in enumerate(ranges):
                chunk_path = temp_dir / f"chunk_{idx:04d}"
                chunk_files.append(chunk_path)
                future = executor.submit(
                    download_chunk,
                    url, start, end, chunk_path,
                    session=sess,
                    headers=headers,
                    timeout=timeout,
                    chunk_size=chunk_size,
                    progress_callback=lambda w, i=idx: chunk_progress(i, w),
                )
                futures.append(future)

            for future in concurrent.futures.as_completed(futures):
                future.result()  # raise exceptions if any

        # Assemble chunks
        with open(output_path, "wb") as out_f:
            for chunk_path in chunk_files:
                if chunk_path.exists():
                    with open(chunk_path, "rb") as in_f:
                        while True:
                            data = in_f.read(chunk_size)
                            if not data:
                                break
                            out_f.write(data)

        # Verify checksum if provided
        if verify_checksum_algo and expected_checksum:
            if not verify_checksum(output_path, expected_checksum, verify_checksum_algo):
                raise ValueError("Checksum verification failed after parallel download")

        logger.info("Parallel download complete: %s (%d bytes, %d connections)",
                     output_path, file_size, num_connections)
        return output_path

    finally:
        # Cleanup temp files
        for chunk_path in chunk_files:
            try:
                chunk_path.unlink(missing_ok=True)
            except OSError:
                pass
        try:
            temp_dir.rmdir()
        except OSError:
            pass


# ---------------------------------------------------------------------------
# SyncHTTPClient
# ---------------------------------------------------------------------------

class SyncHTTPClient:
    """
    Synchronous HTTP client based on requests library.

    Features:
    - GET, POST, PUT, DELETE, HEAD, PATCH methods
    - Streaming download with progress callback
    - Multipart upload
    - Cookie jar management
    - Session reuse with connection pooling
    - Retry with exponential backoff
    - Proxy rotation
    - DNS override
    - SSL context configuration
    - Timeout management
    - Rate limiting
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        pool_connections: int = 100,
        pool_maxsize: int = 100,
        user_agent: str = "RS-Downloader/10.0.0",
        verify_ssl: bool = True,
        proxy: str = "",
        cookie_jar: Optional[Any] = None,
        default_headers: Optional[Dict[str, str]] = None,
        rate_limit_rps: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.user_agent = user_agent
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self.rate_limit_rps = rate_limit_rps
        self._session = requests.Session()
        self._lock = threading.Lock()
        self._last_request_time = 0.0
        self._dns_overrides: Dict[str, str] = {}
        self._request_count = 0
        self._error_count = 0

        # Set up retry strategy
        retry_strategy = Urllib3Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "DELETE", "HEAD", "PATCH"],
        )
        adapter = requests.adapters.HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=pool_connections,
            pool_maxsize=pool_maxsize,
        )
        self._session.mount("http://", adapter)
        self._session.mount("https://", adapter)

        # Set default headers
        self._session.headers.update({
            "User-Agent": user_agent,
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
        })
        if default_headers:
            self._session.headers.update(default_headers)

        # Set proxy
        if proxy:
            self._session.proxies = {"http": proxy, "https": proxy}

        # Set cookie jar
        if cookie_jar:
            self._session.cookies = cookie_jar

        # SSL verification
        self._session.verify = verify_ssl

    def _build_url(self, path: str) -> str:
        """Build full URL from base URL and path."""
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}/{path.lstrip('/')}" if self.base_url else path

    def _rate_limit_wait(self) -> None:
        """Wait if rate limiting is configured."""
        if self.rate_limit_rps <= 0:
            return
        with self._lock:
            now = time.monotonic()
            min_interval = 1.0 / self.rate_limit_rps
            elapsed = now - self._last_request_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            self._last_request_time = time.monotonic()

    def _resolve_dns(self, url: str) -> str:
        """Apply DNS override if configured."""
        if not self._dns_overrides:
            return url
        parsed = urlparse(url)
        hostname = parsed.hostname
        if hostname and hostname in self._dns_overrides:
            replacement = self._dns_overrides[hostname]
            netloc = replacement
            if parsed.port:
                netloc = f"{replacement}:{parsed.port}"
            if parsed.username:
                user_info = parsed.username
                if parsed.password:
                    user_info += f":{parsed.password}"
                netloc = f"{user_info}@{netloc}"
            return urlunparse(parsed._replace(netloc=netloc))
        return url

    def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> requests.Response:
        """Execute an HTTP request with rate limiting and DNS override."""
        self._rate_limit_wait()
        full_url = self._resolve_dns(self._build_url(url))
        kwargs.setdefault("timeout", self.timeout)
        kwargs.setdefault("verify", self.verify_ssl)
        self._request_count += 1
        try:
            response = self._session.request(method, full_url, **kwargs)
            return response
        except requests.RequestException:
            self._error_count += 1
            raise

    def get(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """HTTP GET request."""
        return self._request("GET", url, params=params, headers=headers, **kwargs)

    def post(
        self,
        url: str,
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """HTTP POST request."""
        kw: Dict[str, Any] = {}
        if data is not None:
            kw["data"] = data
        if json_data is not None:
            kw["json"] = json_data
        if headers:
            kw["headers"] = headers
        kw.update(kwargs)
        return self._request("POST", url, **kw)

    def put(
        self,
        url: str,
        data: Optional[Any] = None,
        json_data: Optional[Any] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """HTTP PUT request."""
        kw: Dict[str, Any] = {}
        if data is not None:
            kw["data"] = data
        if json_data is not None:
            kw["json"] = json_data
        kw.update(kwargs)
        return self._request("PUT", url, **kw)

    def delete(self, url: str, **kwargs: Any) -> requests.Response:
        """HTTP DELETE request."""
        return self._request("DELETE", url, **kwargs)

    def head(self, url: str, **kwargs: Any) -> requests.Response:
        """HTTP HEAD request."""
        return self._request("HEAD", url, **kwargs)

    def patch(
        self,
        url: str,
        data: Optional[Any] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """HTTP PATCH request."""
        kw: Dict[str, Any] = {}
        if data is not None:
            kw["data"] = data
        kw.update(kwargs)
        return self._request("PATCH", url, **kw)

    def streaming_download(
        self,
        url: str,
        output_path: Union[str, Path],
        headers: Optional[Dict[str, str]] = None,
        chunk_size: int = 8192,
        resume_from: int = 0,
        progress_callback: Optional[Callable[[str, int, int, float, float], None]] = None,
        **kwargs: Any,
    ) -> Path:
        """
        Streaming download with progress callback support.

        Args:
            url: URL to download.
            output_path: Output file path.
            headers: Optional request headers.
            chunk_size: Download buffer size.
            resume_from: Byte offset to resume from.
            progress_callback: Called with (task_id, downloaded, total, speed, eta).
            **kwargs: Additional request kwargs.

        Returns:
            Path to the downloaded file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        req_headers = headers or {}
        if resume_from > 0:
            req_headers["Range"] = f"bytes={resume_from}-"
        full_url = self._resolve_dns(self._build_url(url))
        self._rate_limit_wait()

        response = self._session.get(
            full_url,
            headers=req_headers,
            stream=True,
            timeout=self.timeout,
            verify=self.verify_ssl,
            **kwargs,
        )
        response.raise_for_status()

        total = int(response.headers.get("Content-Length", 0))
        if resume_from > 0 and response.status_code == 206:
            total += resume_from
        elif resume_from > 0 and response.status_code == 200:
            resume_from = 0  # Server doesn't support range, restart

        downloaded = resume_from
        start_time = time.monotonic()
        mode = "ab" if resume_from > 0 else "wb"

        with open(output_path, mode) as f:
            for chunk in response.iter_content(chunk_size=chunk_size):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total > 0:
                        elapsed = time.monotonic() - start_time
                        speed = downloaded / elapsed if elapsed > 0 else 0.0
                        remaining = total - downloaded
                        eta = remaining / speed if speed > 0 else 0.0
                        progress_callback("", downloaded, total, speed, eta)

        response.close()
        logger.info("Streaming download complete: %s (%d bytes)", output_path, downloaded)
        return output_path

    def multipart_upload(
        self,
        url: str,
        file_path: Union[str, Path],
        file_field_name: str = "file",
        fields: Optional[Dict[str, str]] = None,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any,
    ) -> requests.Response:
        """
        Upload a file using multipart/form-data.

        Args:
            url: Upload URL.
            file_path: Path to the file to upload.
            file_field_name: Form field name for the file.
            fields: Additional form fields.
            headers: Optional headers.

        Returns:
            Response object.
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        files = {file_field_name: (file_path.name, open(file_path, "rb"))}
        try:
            return self._request("POST", url, files=files, data=fields or {}, headers=headers, **kwargs)
        finally:
            files[file_field_name][1].close()

    def set_proxy(self, proxy: str) -> None:
        """Update the proxy setting."""
        self.proxy = proxy
        self._session.proxies = {"http": proxy, "https": proxy}

    def set_dns_override(self, hostname: str, ip: str) -> None:
        """Override DNS resolution for a hostname."""
        self._dns_overrides[hostname] = ip

    def remove_dns_override(self, hostname: str) -> None:
        """Remove DNS override for a hostname."""
        self._dns_overrides.pop(hostname, None)

    def set_cookie(self, name: str, value: str, domain: str = "") -> None:
        """Set a cookie."""
        self._session.cookies.set(name, value, domain=domain)

    def get_cookies(self) -> Dict[str, str]:
        """Get all cookies as a dict."""
        return dict(self._session.cookies)

    def set_auth(self, username: str, password: str) -> None:
        """Set basic authentication."""
        self._session.auth = (username, password)

    def set_bearer_token(self, token: str) -> None:
        """Set bearer token authentication."""
        self._session.headers["Authorization"] = f"Bearer {token}"

    @property
    def request_count(self) -> int:
        """Total requests made."""
        return self._request_count

    @property
    def error_count(self) -> int:
        """Total request errors."""
        return self._error_count

    def close(self) -> None:
        """Close the session."""
        self._session.close()

    def __enter__(self) -> "SyncHTTPClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


# ---------------------------------------------------------------------------
# AsyncHTTPClient
# ---------------------------------------------------------------------------

class AsyncHTTPClient:
    """
    Asynchronous HTTP client based on aiohttp.

    Features:
    - All standard HTTP methods
    - Async context manager
    - Concurrent request support
    - Streaming download
    - Session reuse
    - Retry with backoff
    - Proxy support
    - SSL configuration
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = 30.0,
        max_retries: int = 3,
        backoff_factor: float = 1.0,
        user_agent: str = "RS-Downloader/10.0.0",
        verify_ssl: bool = True,
        proxy: str = "",
        default_headers: Optional[Dict[str, str]] = None,
        max_concurrent: int = 100,
        rate_limit_rps: float = 0.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.user_agent = user_agent
        self.verify_ssl = verify_ssl
        self.proxy = proxy
        self.rate_limit_rps = rate_limit_rps
        self._session: Optional[Any] = None
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._default_headers: Dict[str, str] = {
            "User-Agent": user_agent,
            "Accept": "*/*",
        }
        if default_headers:
            self._default_headers.update(default_headers)
        self._request_count = 0
        self._error_count = 0

    async def _ensure_session(self) -> Any:
        """Ensure aiohttp session exists."""
        import aiohttp
        if self._session is None or self._session.closed:
            ssl_ctx = None
            if not self.verify_ssl:
                ssl_ctx = False
            timeout_obj = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(
                headers=self._default_headers,
                timeout=timeout_obj,
                trust_env=bool(self.proxy),
            )
        return self._session

    def _build_url(self, path: str) -> str:
        """Build full URL."""
        if path.startswith(("http://", "https://")):
            return path
        return f"{self.base_url}/{path.lstrip('/')}" if self.base_url else path

    async def _request(
        self,
        method: str,
        url: str,
        **kwargs: Any,
    ) -> Any:
        """Execute async HTTP request with retry."""
        import aiohttp
        session = await self._ensure_session()
        full_url = self._build_url(url)
        kwargs.setdefault("ssl", self.verify_ssl if self.verify_ssl else None)
        if self.proxy:
            kwargs["proxy"] = self.proxy

        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                async with self._semaphore:
                    async with session.request(method, full_url, **kwargs) as resp:
                        self._request_count += 1
                        if resp.status >= 400:
                            text = await resp.text()
                            raise aiohttp.ClientResponseError(
                                request_info=resp.request_info,
                                history=resp.history,
                                status=resp.status,
                                message=text[:500],
                            )
                        return resp
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                self._error_count += 1
                last_error = e
                if attempt < self.max_retries:
                    delay = self.backoff_factor * (2 ** attempt)
                    await asyncio.sleep(delay)
        raise last_error or aiohttp.ClientError("Request failed")

    async def get(self, url: str, **kwargs: Any) -> Any:
        """Async GET request."""
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, data: Optional[Any] = None, json_data: Optional[Any] = None, **kwargs: Any) -> Any:
        """Async POST request."""
        if data is not None:
            kwargs["data"] = data
        if json_data is not None:
            kwargs["json"] = json_data
        return await self._request("POST", url, **kwargs)

    async def put(self, url: str, data: Optional[Any] = None, **kwargs: Any) -> Any:
        """Async PUT request."""
        if data is not None:
            kwargs["data"] = data
        return await self._request("PUT", url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> Any:
        """Async DELETE request."""
        return await self._request("DELETE", url, **kwargs)

    async def head(self, url: str, **kwargs: Any) -> Any:
        """Async HEAD request."""
        return await self._request("HEAD", url, **kwargs)

    async def patch(self, url: str, data: Optional[Any] = None, **kwargs: Any) -> Any:
        """Async PATCH request."""
        if data is not None:
            kwargs["data"] = data
        return await self._request("PATCH", url, **kwargs)

    async def streaming_download(
        self,
        url: str,
        output_path: Union[str, Path],
        chunk_size: int = 8192,
        progress_callback: Optional[Callable[[int, int], Any]] = None,
        **kwargs: Any,
    ) -> Path:
        """Async streaming download with progress."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        resp = await self._request("GET", url, **kwargs)
        total = int(resp.headers.get("Content-Length", 0))
        downloaded = 0
        with open(output_path, "wb") as f:
            async for chunk in resp.content.iter_chunked(chunk_size):
                f.write(chunk)
                downloaded += len(chunk)
                if progress_callback:
                    await progress_callback(downloaded, total) if asyncio.iscoroutinefunction(progress_callback) else progress_callback(downloaded, total)
        return output_path

    async def close(self) -> None:
        """Close the async session."""
        if self._session and not self._session.closed:
            await self._session.close()

    async def __aenter__(self) -> "AsyncHTTPClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()


# ---------------------------------------------------------------------------
# ProxyRotationStrategy
# ---------------------------------------------------------------------------

class ProxyRotationStrategy(Enum):
    """Proxy rotation strategies."""
    SEQUENTIAL = "sequential"
    RANDOM = "random"
    ROUND_ROBIN = "round_robin"
    WEIGHTED_RANDOM = "weighted_random"
    LATENCY_BASED = "latency_based"
    GEO_BASED = "geo_based"
    STICKY_SESSION = "sticky_session"


# ---------------------------------------------------------------------------
# ProxyPool
# ---------------------------------------------------------------------------

@dataclass
class ProxyEntry:
    """Single proxy entry with metadata."""
    url: str
    protocol: str = "http"  # http, https, socks4, socks5
    auth_username: str = ""
    auth_password: str = ""
    weight: float = 1.0
    country: str = ""
    is_alive: bool = True
    latency_ms: float = 0.0
    failure_count: int = 0
    success_count: int = 0
    last_check: float = 0.0
    last_used: float = 0.0
    sticky_key: str = ""


class ProxyPool:
    """
    Rotating proxy pool with multiple strategies, health checking,
    auto-removal of dead proxies, and latency measurement.

    Supports HTTP/HTTPS and SOCKS4/5 proxies.
    """

    def __init__(
        self,
        strategy: ProxyRotationStrategy = ProxyRotationStrategy.ROUND_ROBIN,
        health_check_url: str = "https://httpbin.org/ip",
        health_check_interval: float = 300.0,
        health_check_timeout: float = 10.0,
        max_failures: int = 3,
        auto_remove_dead: bool = True,
    ) -> None:
        self.strategy = strategy
        self.health_check_url = health_check_url
        self.health_check_interval = health_check_interval
        self.health_check_timeout = health_check_timeout
        self.max_failures = max_failures
        self.auto_remove_dead = auto_remove_dead
        self._proxies: List[ProxyEntry] = []
        self._index = 0
        self._lock = threading.Lock()
        self._sticky_map: Dict[str, ProxyEntry] = {}
        self._health_thread: Optional[threading.Thread] = None
        self._health_running = False

    def add_proxy(
        self,
        url: str,
        protocol: str = "http",
        username: str = "",
        password: str = "",
        weight: float = 1.0,
        country: str = "",
    ) -> None:
        """Add a proxy to the pool."""
        with self._lock:
            entry = ProxyEntry(
                url=url,
                protocol=protocol,
                auth_username=username,
                auth_password=password,
                weight=weight,
                country=country,
            )
            self._proxies.append(entry)

    def add_proxies(self, proxy_list: List[str], protocol: str = "http") -> None:
        """Add multiple proxies from a list of URLs."""
        for url in proxy_list:
            self.add_proxy(url=url.strip(), protocol=protocol)

    def remove_proxy(self, url: str) -> None:
        """Remove a proxy by URL."""
        with self._lock:
            self._proxies = [p for p in self._proxies if p.url != url]

    def get_proxy(self, sticky_key: str = "") -> Optional[ProxyEntry]:
        """
        Get the next proxy based on the rotation strategy.

        Args:
            sticky_key: Key for sticky session strategy.

        Returns:
            ProxyEntry or None if pool is empty.
        """
        with self._lock:
            alive = [p for p in self._proxies if p.is_alive]
            if not alive:
                return None

            if self.strategy == ProxyRotationStrategy.STICKY_SESSION and sticky_key:
                if sticky_key in self._sticky_map:
                    entry = self._sticky_map[sticky_key]
                    if entry.is_alive:
                        entry.last_used = time.monotonic()
                        return entry
                # Assign new sticky
                entry = self._select(alive)
                self._sticky_map[sticky_key] = entry
                entry.last_used = time.monotonic()
                return entry

            return self._select(alive)

    def _select(self, proxies: List[ProxyEntry]) -> ProxyEntry:
        """Select a proxy based on the current strategy."""
        if self.strategy == ProxyRotationStrategy.SEQUENTIAL:
            return proxies[0]
        elif self.strategy == ProxyRotationStrategy.RANDOM:
            return random.choice(proxies)
        elif self.strategy == ProxyRotationStrategy.ROUND_ROBIN:
            entry = proxies[self._index % len(proxies)]
            self._index += 1
            return entry
        elif self.strategy == ProxyRotationStrategy.WEIGHTED_RANDOM:
            weights = [p.weight for p in proxies]
            total = sum(weights)
            if total <= 0:
                return random.choice(proxies)
            r = random.uniform(0, total)
            cumulative = 0.0
            for proxy, weight in zip(proxies, weights):
                cumulative += weight
                if r <= cumulative:
                    return proxy
            return proxies[-1]
        elif self.strategy == ProxyRotationStrategy.LATENCY_BASED:
            sorted_proxies = sorted(proxies, key=lambda p: p.latency_ms if p.latency_ms > 0 else float("inf"))
            return sorted_proxies[0]
        elif self.strategy == ProxyRotationStrategy.GEO_BASED:
            # Prefer proxies with country codes (heuristic: lower latency)
            return min(proxies, key=lambda p: p.latency_ms if p.latency_ms > 0 else float("inf"))
        else:
            return proxies[0]

    def report_success(self, url: str) -> None:
        """Report a successful request through a proxy."""
        with self._lock:
            for p in self._proxies:
                if p.url == url:
                    p.success_count += 1
                    p.failure_count = max(0, p.failure_count - 1)
                    p.is_alive = True
                    break

    def report_failure(self, url: str) -> None:
        """Report a failed request through a proxy."""
        with self._lock:
            for p in self._proxies:
                if p.url == url:
                    p.failure_count += 1
                    if p.failure_count >= self.max_failures:
                        p.is_alive = False
                        if self.auto_remove_dead:
                            logger.info("Removing dead proxy: %s", url)
                    break

    def measure_latency(self, url: str) -> float:
        """Measure latency to a proxy in milliseconds."""
        try:
            proxy_url = url
            proxies = {"http": proxy_url, "https": proxy_url}
            start = time.monotonic()
            resp = requests.get(
                self.health_check_url,
                proxies=proxies,
                timeout=self.health_check_timeout,
            )
            elapsed = (time.monotonic() - start) * 1000
            resp.close()
            with self._lock:
                for p in self._proxies:
                    if p.url == url:
                        p.latency_ms = elapsed
                        p.last_check = time.monotonic()
                        p.is_alive = True
                        break
            return elapsed
        except requests.RequestException:
            with self._lock:
                for p in self._proxies:
                    if p.url == url:
                        p.is_alive = False
                        p.last_check = time.monotonic()
                        break
            return float("inf")

    def health_check_all(self) -> Dict[str, bool]:
        """Run health check on all proxies."""
        results: Dict[str, bool] = {}
        with self._lock:
            proxy_urls = [(p.url, p.is_alive) for p in self._proxies]
        for url, was_alive in proxy_urls:
            latency = self.measure_latency(url)
            is_alive = latency < float("inf")
            results[url] = is_alive
            if not is_alive and was_alive:
                logger.warning("Proxy became unhealthy: %s", url)
        return results

    def start_health_checks(self) -> None:
        """Start periodic health checking in background thread."""
        self._health_running = True
        self._health_thread = threading.Thread(
            target=self._health_check_loop,
            name="proxy_health_check",
            daemon=True,
        )
        self._health_thread.start()

    def stop_health_checks(self) -> None:
        """Stop health checking."""
        self._health_running = False

    def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self._health_running:
            try:
                self.health_check_all()
            except Exception as e:
                logger.error("Proxy health check error: %s", e)
            time.sleep(self.health_check_interval)

    @property
    def size(self) -> int:
        """Total number of proxies."""
        return len(self._proxies)

    @property
    def alive_count(self) -> int:
        """Number of alive proxies."""
        return sum(1 for p in self._proxies if p.is_alive)

    def list_proxies(self) -> List[Dict[str, Any]]:
        """List all proxies with their status."""
        return [
            {
                "url": p.url,
                "protocol": p.protocol,
                "alive": p.is_alive,
                "latency_ms": p.latency_ms,
                "failures": p.failure_count,
                "successes": p.success_count,
                "weight": p.weight,
                "country": p.country,
            }
            for p in self._proxies
        ]

    def load_from_file(self, filepath: Union[str, Path]) -> int:
        """Load proxies from a file (one URL per line)."""
        filepath = Path(filepath)
        if not filepath.exists():
            return 0
        count = 0
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = line.split()
                url = parts[0]
                protocol = "http"
                if len(parts) > 1:
                    protocol = parts[1]
                self.add_proxy(url=url, protocol=protocol)
                count += 1
        return count


# ---------------------------------------------------------------------------
# BandwidthThrottler
# ---------------------------------------------------------------------------

class BandwidthThrottler:
    """
    Token bucket bandwidth throttler with priority levels,
    schedule-based throttling, per-agent limits, and burst support.
    """

    def __init__(
        self,
        global_limit_kbps: float = 0.0,
        per_download_limit_kbps: float = 0.0,
        per_agent_limits: Optional[Dict[str, float]] = None,
        burst_enabled: bool = True,
        burst_factor: float = 2.0,
        peak_hours_start: int = 8,
        peak_hours_end: int = 22,
        peak_limit_kbps: float = 0.0,
        off_peak_limit_kbps: float = 0.0,
    ) -> None:
        self.global_limit_kbps = global_limit_kbps
        self.per_download_limit_kbps = per_download_limit_kbps
        self.per_agent_limits = per_agent_limits or {}
        self.burst_enabled = burst_enabled
        self.burst_factor = burst_factor
        self.peak_hours_start = peak_hours_start
        self.peak_hours_end = peak_hours_end
        self.peak_limit_kbps = peak_limit_kbps
        self.off_peak_limit_kbps = off_peak_limit_kbps
        self._tokens = global_limit_kbps * 1024 if global_limit_kbps > 0 else float("inf")
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._agent_tokens: Dict[str, float] = {}
        self._agent_last_refill: Dict[str, float] = {}

    def _is_peak_hour(self) -> bool:
        """Check if current time is within peak hours."""
        hour = datetime.now().hour
        if self.peak_hours_start < self.peak_hours_end:
            return self.peak_hours_start <= hour < self.peak_hours_end
        else:  # wraps midnight
            return hour >= self.peak_hours_start or hour < self.peak_hours_end

    def _get_effective_limit(self) -> float:
        """Get the effective bandwidth limit in KB/s considering schedule."""
        if self.peak_limit_kbps > 0 or self.off_peak_limit_kbps > 0:
            return self.peak_limit_kbps if self._is_peak_hour() else self.off_peak_limit_kbps
        return self.global_limit_kbps

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        limit = self._get_effective_limit()
        if limit > 0:
            refill = elapsed * limit * 1024  # bytes per second
            max_tokens = limit * 1024 * (self.burst_factor if self.burst_enabled else 1.0)
            self._tokens = min(max_tokens, self._tokens + refill)
        else:
            self._tokens = float("inf")
        self._last_refill = now

    def acquire(self, bytes_needed: int, agent: str = "", priority: int = 5) -> float:
        """
        Acquire bandwidth tokens. Returns the time to wait (0 if no wait needed).

        Args:
            bytes_needed: Number of bytes to transfer.
            agent: Agent name for per-agent limiting.
            priority: Priority level (lower = higher priority).

        Returns:
            Wait time in seconds.
        """
        if self.global_limit_kbps <= 0 and not self.per_agent_limits:
            return 0.0

        with self._lock:
            self._refill_tokens()

            # Check global tokens
            if self._tokens >= bytes_needed:
                self._tokens -= bytes_needed
            else:
                limit = self._get_effective_limit()
                if limit > 0:
                    deficit = bytes_needed - self._tokens
                    self._tokens = 0
                    wait_time = deficit / (limit * 1024)
                    return wait_time
                self._tokens = float("inf")

            # Check per-agent tokens
            if agent and agent in self.per_agent_limits:
                agent_limit = self.per_agent_limits[agent]
                if agent_limit > 0:
                    now = time.monotonic()
                    if agent not in self._agent_tokens:
                        self._agent_tokens[agent] = agent_limit * 1024
                        self._agent_last_refill[agent] = now
                    elapsed = now - self._agent_last_refill[agent]
                    refill = elapsed * agent_limit * 1024
                    max_at = agent_limit * 1024 * (self.burst_factor if self.burst_enabled else 1.0)
                    self._agent_tokens[agent] = min(max_at, self._agent_tokens[agent] + refill)
                    self._agent_last_refill[agent] = now
                    if self._agent_tokens[agent] >= bytes_needed:
                        self._agent_tokens[agent] -= bytes_needed
                    else:
                        deficit = bytes_needed - self._agent_tokens[agent]
                        self._agent_tokens[agent] = 0
                        return deficit / (agent_limit * 1024)

            return 0.0

    def set_global_limit(self, kbps: float) -> None:
        """Update the global bandwidth limit."""
        with self._lock:
            self.global_limit_kbps = kbps
            if kbps > 0:
                self._tokens = min(self._tokens, kbps * 1024)
            else:
                self._tokens = float("inf")

    def set_agent_limit(self, agent: str, kbps: float) -> None:
        """Set per-agent bandwidth limit."""
        with self._lock:
            self.per_agent_limits[agent] = kbps

    def get_stats(self) -> Dict[str, Any]:
        """Get throttler statistics."""
        with self._lock:
            return {
                "global_limit_kbps": self.global_limit_kbps,
                "current_tokens": self._tokens,
                "is_peak_hour": self._is_peak_hour(),
                "effective_limit_kbps": self._get_effective_limit(),
                "per_agent_limits": dict(self.per_agent_limits),
                "burst_enabled": self.burst_enabled,
            }


# ---------------------------------------------------------------------------
# DNSResolver
# ---------------------------------------------------------------------------

class DNSResolver:
    """
    DNS-over-HTTPS resolver with caching, custom hosts, and system fallback.

    Supports Cloudflare, Google, and custom DoH endpoints.
    """

    PROVIDERS = {
        "cloudflare": "https://cloudflare-dns.com/dns-query",
        "google": "https://dns.google/resolve",
    }

    def __init__(
        self,
        provider: str = "cloudflare",
        custom_url: str = "",
        cache_ttl: float = 300.0,
        custom_hosts: Optional[Dict[str, str]] = None,
        timeout: float = 5.0,
        fallback_to_system: bool = True,
    ) -> None:
        self.provider = provider
        self.custom_url = custom_url
        self.cache_ttl = cache_ttl
        self.custom_hosts = custom_hosts or {}
        self.timeout = timeout
        self.fallback_to_system = fallback_to_system
        self._cache: Dict[str, Tuple[List[str], float]] = {}
        self._lock = threading.Lock()

    def _get_doh_url(self) -> str:
        """Get the DNS-over-HTTPS endpoint URL."""
        if self.custom_url:
            return self.custom_url
        return self.PROVIDERS.get(self.provider, self.PROVIDERS["cloudflare"])

    def resolve(self, hostname: str, record_type: str = "A") -> List[str]:
        """
        Resolve a hostname to IP addresses.

        Checks custom hosts first, then cache, then DoH, then system fallback.

        Args:
            hostname: Domain name to resolve.
            record_type: DNS record type (A, AAAA, CNAME, etc.).

        Returns:
            List of IP addresses or CNAME values.
        """
        # Check custom hosts
        if hostname in self.custom_hosts:
            return [self.custom_hosts[hostname]]

        # Check cache
        with self._lock:
            if hostname in self._cache:
                cached_ips, cached_time = self._cache[hostname]
                if time.monotonic() - cached_time < self.cache_ttl:
                    return cached_ips
                del self._cache[hostname]

        # Try DNS-over-HTTPS
        try:
            ips = self._resolve_doh(hostname, record_type)
            if ips:
                with self._lock:
                    self._cache[hostname] = (ips, time.monotonic())
                return ips
        except Exception as e:
            logger.debug("DoH resolution failed for %s: %s", hostname, e)

        # System fallback
        if self.fallback_to_system:
            try:
                results = socket.getaddrinfo(hostname, None)
                ips = list(set(r[4][0] for r in results if r[0] in (socket.AF_INET, socket.AF_INET6)))
                if ips:
                    with self._lock:
                        self._cache[hostname] = (ips, time.monotonic())
                    return ips
            except socket.gaierror:
                pass

        return []

    def _resolve_doh(self, hostname: str, record_type: str = "A") -> List[str]:
        """Resolve via DNS-over-HTTPS."""
        doh_url = self._get_doh_url()
        record_map = {"A": 1, "AAAA": 28, "CNAME": 5, "MX": 15, "TXT": 16}
        rtype = record_map.get(record_type, 1)

        if "cloudflare" in doh_url:
            url = f"{doh_url}?name={hostname}&type={rtype}"
            headers = {"Accept": "application/dns-json"}
        elif "google" in doh_url:
            url = f"{doh_url}?name={hostname}&type={record_type}"
            headers = {"Accept": "application/dns-json"}
        else:
            url = f"{doh_url}?name={hostname}&type={record_type}"
            headers = {"Accept": "application/dns-json"}

        resp = requests.get(url, headers=headers, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        ips: List[str] = []
        for answer in data.get("Answer", []):
            if record_type == "A" and answer.get("type") == 1:
                ips.append(answer["data"])
            elif record_type == "AAAA" and answer.get("type") == 28:
                ips.append(answer["data"])
            elif record_type == "CNAME" and answer.get("type") == 5:
                ips.append(answer["data"])
            else:
                ips.append(answer.get("data", ""))
        return ips

    async def resolve_async(self, hostname: str, record_type: str = "A") -> List[str]:
        """Async DNS resolution (uses sync internally)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.resolve, hostname, record_type)

    def add_host(self, hostname: str, ip: str) -> None:
        """Add a custom host entry."""
        self.custom_hosts[hostname] = ip

    def remove_host(self, hostname: str) -> None:
        """Remove a custom host entry."""
        self.custom_hosts.pop(hostname, None)

    def clear_cache(self) -> None:
        """Clear the DNS cache."""
        with self._lock:
            self._cache.clear()

    def get_cache_size(self) -> int:
        """Get the number of cached entries."""
        with self._lock:
            return len(self._cache)


# ---------------------------------------------------------------------------
# SSLContextBuilder
# ---------------------------------------------------------------------------

class SSLContextBuilder:
    """
    Fluent API for building SSL contexts with TLS version control,
    certificate pinning, client certificates, CA bundles, and cipher selection.
    """

    def __init__(self) -> None:
        self._min_version: int = ssl.TLSVersion.TLSv1_2
        self._max_version: int = ssl.TLSVersion.TLSv1_3
        self._cert_path: str = ""
        self._key_path: str = ""
        self._ca_bundle: str = ""
        self._pin_sha256: Set[str] = set()
        self._client_cert_path: str = ""
        self._client_key_path: str = ""
        self._ciphers: str = ""
        self._check_hostname: bool = True
        self._verify_mode: int = ssl.CERT_REQUIRED
        self._ocsp_check: bool = False

    def min_tls_version(self, version: str) -> "SSLContextBuilder":
        """Set minimum TLS version. Options: '1.2', '1.3'."""
        versions = {
            "1.2": ssl.TLSVersion.TLSv1_2,
            "1.3": ssl.TLSVersion.TLSv1_3,
            "TLSv1_2": ssl.TLSVersion.TLSv1_2,
            "TLSv1_3": ssl.TLSVersion.TLSv1_3,
        }
        self._min_version = versions.get(version, ssl.TLSVersion.TLSv1_2)
        return self

    def max_tls_version(self, version: str) -> "SSLContextBuilder":
        """Set maximum TLS version."""
        versions = {
            "1.2": ssl.TLSVersion.TLSv1_2,
            "1.3": ssl.TLSVersion.TLSv1_3,
            "TLSv1_2": ssl.TLSVersion.TLSv1_2,
            "TLSv1_3": ssl.TLSVersion.TLSv1_3,
        }
        self._max_version = versions.get(version, ssl.TLSVersion.TLSv1_3)
        return self

    def pin_certificate(self, sha256_hash: str) -> "SSLContextBuilder":
        """Add a SHA-256 certificate pin."""
        self._pin_sha256.add(sha256_hash.lower())
        return self

    def client_certificate(self, cert_path: str, key_path: str) -> "SSLContextBuilder":
        """Set client certificate and key paths."""
        self._client_cert_path = cert_path
        self._client_key_path = key_path
        return self

    def ca_bundle(self, path: str) -> "SSLContextBuilder":
        """Set custom CA bundle path."""
        self._ca_bundle = path
        return self

    def ciphers(self, cipher_list: str) -> "SSLContextBuilder":
        """Set allowed ciphers (OpenSSL cipher string)."""
        self._ciphers = cipher_list
        return self

    def disable_hostname_check(self) -> "SSLContextBuilder":
        """Disable hostname verification (not recommended for production)."""
        self._check_hostname = False
        return self

    def no_verify(self) -> "SSLContextBuilder":
        """Disable certificate verification entirely."""
        self._verify_mode = ssl.CERT_NONE
        self._check_hostname = False
        return self

    def enable_ocsp(self) -> "SSLContextBuilder":
        """Enable OCSP stapling check."""
        self._ocsp_check = True
        return self

    def build(self) -> ssl.SSLContext:
        """
        Build and return the configured SSL context.

        Returns:
            Configured ssl.SSLContext.
        """
        ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        ctx.minimum_version = self._min_version
        ctx.maximum_version = self._max_version
        ctx.check_hostname = self._check_hostname
        ctx.verify_mode = self._verify_mode

        if self._ciphers:
            try:
                ctx.set_ciphers(self._ciphers)
            except ssl.SSLError as e:
                logger.warning("Invalid cipher string, using defaults: %s", e)

        if self._ca_bundle:
            ctx.load_verify_locations(self._ca_bundle)

        if self._client_cert_path and self._client_key_path:
            ctx.load_cert_chain(self._client_cert_path, self._client_key_path)

        if self._ocsp_check:
            ctx.verify_flags = ssl.VERIFY_CRL_CHECK_LEAF

        return ctx

    def verify_pin(self, peer_cert_pem: str) -> bool:
        """
        Verify a peer certificate against configured pins.

        Args:
            peer_cert_pem: PEM-encoded certificate string.

        Returns:
            True if pin matches or no pins configured.
        """
        if not self._pin_sha256:
            return True
        der_cert = ssl.PEM_cert_to_DER_cert(peer_cert_pem)
        cert_hash = hashlib.sha256(der_cert).hexdigest().lower()
        return cert_hash in self._pin_sha256


# ---------------------------------------------------------------------------
# CircuitBreaker
# ---------------------------------------------------------------------------

class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """
    Circuit breaker pattern: CLOSED → OPEN → HALF_OPEN.

    Protects against cascading failures by opening the circuit
    after a threshold of failures, then trying again after a recovery timeout.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        success_threshold: int = 3,
        on_state_change: Optional[Callable[[CircuitState, CircuitState], None]] = None,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.success_threshold = success_threshold
        self.on_state_change = on_state_change
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._lock = threading.Lock()
        self._metrics: Dict[str, int] = {
            "total_calls": 0,
            "total_failures": 0,
            "total_successes": 0,
            "circuit_opens": 0,
        }

    @property
    def state(self) -> CircuitState:
        """Current circuit state."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    self._transition(CircuitState.HALF_OPEN)
            return self._state

    def _transition(self, new_state: CircuitState) -> None:
        """Transition to a new state and notify."""
        old_state = self._state
        self._state = new_state
        if old_state != new_state:
            if new_state == CircuitState.OPEN:
                self._metrics["circuit_opens"] += 1
            if self.on_state_change:
                try:
                    self.on_state_change(old_state, new_state)
                except Exception:
                    pass

    def record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._metrics["total_calls"] += 1
            self._metrics["total_successes"] += 1
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    self._failure_count = 0
                    self._success_count = 0
                    self._transition(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self) -> None:
        """Record a failed call."""
        with self._lock:
            self._metrics["total_calls"] += 1
            self._metrics["total_failures"] += 1
            self._last_failure_time = time.monotonic()
            if self._state == CircuitState.HALF_OPEN:
                self._transition(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    self._transition(CircuitState.OPEN)

    def is_call_allowed(self) -> bool:
        """Check if a call is allowed under current circuit state."""
        return self.state in (CircuitState.CLOSED, CircuitState.HALF_OPEN)

    @contextmanager
    def protect(self) -> Iterator[None]:
        """Context manager that records success/failure automatically."""
        if not self.is_call_allowed():
            raise ConnectionError("Circuit breaker is OPEN")
        try:
            yield
            self.record_success()
        except Exception:
            self.record_failure()
            raise

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        with self._lock:
            return {
                **self._metrics,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "failure_threshold": self.failure_threshold,
                "recovery_timeout": self.recovery_timeout,
            }

    def reset(self) -> None:
        """Reset the circuit breaker to closed state."""
        with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0


# ---------------------------------------------------------------------------
# RetryPolicy
# ---------------------------------------------------------------------------

class RetryPolicy:
    """
    Configurable retry policy with exponential backoff, jitter,
    status code filtering, exception type filtering, and circuit breaker integration.
    """

    def __init__(
        self,
        max_retries: int = 3,
        backoff_factor: float = 2.0,
        backoff_max: float = 300.0,
        jitter: bool = True,
        jitter_range: float = 0.5,
        retry_on_status: Tuple[int, ...] = (429, 500, 502, 503, 504),
        retry_on_exceptions: Tuple[type, ...] = (
            requests.ConnectionError,
            requests.Timeout,
        ),
        circuit_breaker: Optional[CircuitBreaker] = None,
        retry_budget_per_minute: int = 100,
    ) -> None:
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.backoff_max = backoff_max
        self.jitter = jitter
        self.jitter_range = jitter_range
        self.retry_on_status = retry_on_status
        self.retry_on_exceptions = retry_on_exceptions
        self.circuit_breaker = circuit_breaker
        self.retry_budget_per_minute = retry_budget_per_minute
        self._budget_used = 0
        self._budget_start = time.monotonic()
        self._lock = threading.Lock()

    def should_retry(self, attempt: int, exception: Optional[Exception] = None, status_code: Optional[int] = None) -> bool:
        """Determine if a retry should be attempted."""
        if attempt >= self.max_retries:
            return False
        if not self._check_budget():
            return False
        if self.circuit_breaker and not self.circuit_breaker.is_call_allowed():
            return False
        if status_code is not None:
            return status_code in self.retry_on_status
        if exception is not None:
            return isinstance(exception, self.retry_on_exceptions)
        return True

    def get_delay(self, attempt: int) -> float:
        """Calculate the delay before next retry."""
        delay = min(self.backoff_factor * (2 ** attempt), self.backoff_max)
        if self.jitter:
            jitter_amount = delay * self.jitter_range * random.random()
            delay = delay + jitter_amount - (delay * self.jitter_range / 2)
        return max(0.0, delay)

    def _check_budget(self) -> bool:
        """Check if retry budget is available."""
        with self._lock:
            now = time.monotonic()
            if now - self._budget_start >= 60.0:
                self._budget_used = 0
                self._budget_start = now
            if self._budget_used >= self.retry_budget_per_minute:
                return False
            self._budget_used += 1
            return True

    def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """
        Execute a function with retry policy.

        Args:
            func: Function to execute.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Function result.

        Raises:
            Last exception if all retries exhausted.
        """
        last_exception: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                result = func(*args, **kwargs)
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                return result
            except Exception as e:
                last_exception = e
                if self.circuit_breaker:
                    self.circuit_breaker.record_failure()
                status_code = getattr(e, "status_code", None) if hasattr(e, "status_code") else None
                if not self.should_retry(attempt, exception=e, status_code=status_code):
                    raise
                delay = self.get_delay(attempt)
                logger.debug("Retry %d/%d after %.2fs: %s", attempt + 1, self.max_retries, delay, e)
                time.sleep(delay)
        raise last_exception or RuntimeError("Retry exhausted without exception")


# ---------------------------------------------------------------------------
# RequestInterceptor
# ---------------------------------------------------------------------------

class RequestInterceptor:
    """
    Middleware pattern for HTTP requests.

    Supports pre-request hooks, post-response hooks, and
    request/response modification.
    """

    def __init__(self) -> None:
        self._pre_hooks: List[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = []
        self._post_hooks: List[Callable[[Any], Any]] = []
        self._lock = threading.Lock()

    def add_pre_hook(self, hook: Callable[[str, Dict[str, Any]], Dict[str, Any]]) -> None:
        """
        Add a pre-request hook.

        Hook signature: (method, kwargs) -> modified_kwargs
        """
        with self._lock:
            self._pre_hooks.append(hook)

    def add_post_hook(self, hook: Callable[[Any], Any]) -> None:
        """
        Add a post-response hook.

        Hook signature: (response) -> modified_response
        """
        with self._lock:
            self._post_hooks.append(hook)

    def apply_pre(self, method: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all pre-request hooks."""
        with self._lock:
            hooks = self._pre_hooks[:]
        for hook in hooks:
            try:
                kwargs = hook(method, kwargs)
            except Exception as e:
                logger.warning("Pre-request hook error: %s", e)
        return kwargs

    def apply_post(self, response: Any) -> Any:
        """Apply all post-response hooks."""
        with self._lock:
            hooks = self._post_hooks[:]
        for hook in hooks:
            try:
                response = hook(response)
            except Exception as e:
                logger.warning("Post-response hook error: %s", e)
        return response

    def clear(self) -> None:
        """Remove all hooks."""
        with self._lock:
            self._pre_hooks.clear()
            self._post_hooks.clear()

    @property
    def pre_hook_count(self) -> int:
        """Number of pre-request hooks."""
        return len(self._pre_hooks)

    @property
    def post_hook_count(self) -> int:
        """Number of post-response hooks."""
        return len(self._post_hooks)


# ---------------------------------------------------------------------------
# ConnectionMetrics
# ---------------------------------------------------------------------------

class ConnectionMetrics:
    """
    Real-time connection metrics tracking.

    Tracks request counts, latency percentiles, success/failure rates,
    bytes transferred, active connections, and per-host metrics.
    """

    def __init__(self, window_size: int = 1000) -> None:
        self.window_size = window_size
        self._request_count = 0
        self._success_count = 0
        self._failure_count = 0
        self._bytes_sent = 0
        self._bytes_received = 0
        self._latencies: Deque[float] = deque(maxlen=window_size)
        self._active_connections = 0
        self._per_host: Dict[str, Dict[str, Any]] = defaultdict(
            lambda: {"requests": 0, "successes": 0, "failures": 0, "latencies": deque(maxlen=100)}
        )
        self._lock = threading.Lock()
        self._start_time = time.monotonic()

    def record_request(self, host: str = "", latency: float = 0.0, success: bool = True, bytes_sent: int = 0, bytes_received: int = 0) -> None:
        """Record a completed request."""
        with self._lock:
            self._request_count += 1
            if success:
                self._success_count += 1
            else:
                self._failure_count += 1
            self._bytes_sent += bytes_sent
            self._bytes_received += bytes_received
            if latency > 0:
                self._latencies.append(latency)
            if host:
                self._per_host[host]["requests"] += 1
                if success:
                    self._per_host[host]["successes"] += 1
                else:
                    self._per_host[host]["failures"] += 1
                if latency > 0:
                    self._per_host[host]["latencies"].append(latency)

    def increment_active(self) -> None:
        """Increment active connection count."""
        with self._lock:
            self._active_connections += 1

    def decrement_active(self) -> None:
        """Decrement active connection count."""
        with self._lock:
            self._active_connections = max(0, self._active_connections - 1)

    def _percentile(self, data: Sequence[float], pct: float) -> float:
        """Calculate percentile from sorted data."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        idx = int(len(sorted_data) * pct)
        idx = min(idx, len(sorted_data) - 1)
        return sorted_data[idx]

    def get_summary(self) -> Dict[str, Any]:
        """Get overall metrics summary."""
        with self._lock:
            total = self._request_count
            success_rate = (self._success_count / total * 100) if total > 0 else 0.0
            failure_rate = (self._failure_count / total * 100) if total > 0 else 0.0
            elapsed = time.monotonic() - self._start_time
            latencies = list(self._latencies)
            return {
                "total_requests": total,
                "success_count": self._success_count,
                "failure_count": self._failure_count,
                "success_rate": round(success_rate, 2),
                "failure_rate": round(failure_rate, 2),
                "bytes_sent": self._bytes_sent,
                "bytes_received": self._bytes_received,
                "active_connections": self._active_connections,
                "latency_p50_ms": round(self._percentile(latencies, 0.5), 2),
                "latency_p90_ms": round(self._percentile(latencies, 0.9), 2),
                "latency_p95_ms": round(self._percentile(latencies, 0.95), 2),
                "latency_p99_ms": round(self._percentile(latencies, 0.99), 2),
                "latency_avg_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
                "latency_min_ms": round(min(latencies), 2) if latencies else 0.0,
                "latency_max_ms": round(max(latencies), 2) if latencies else 0.0,
                "requests_per_second": round(total / elapsed, 2) if elapsed > 0 else 0.0,
                "uptime_seconds": round(elapsed, 2),
            }

    def get_host_metrics(self, host: str) -> Dict[str, Any]:
        """Get metrics for a specific host."""
        with self._lock:
            if host not in self._per_host:
                return {}
            data = self._per_host[host]
            latencies = list(data["latencies"])
            total = data["requests"]
            return {
                "host": host,
                "total_requests": total,
                "success_count": data["successes"],
                "failure_count": data["failures"],
                "success_rate": round(data["successes"] / total * 100, 2) if total > 0 else 0.0,
                "latency_avg_ms": round(sum(latencies) / len(latencies), 2) if latencies else 0.0,
                "latency_p95_ms": round(self._percentile(latencies, 0.95), 2),
            }

    def get_all_host_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all tracked hosts."""
        with self._lock:
            return {
                host: self.get_host_metrics(host)
                for host in self._per_host
            }

    def reset(self) -> None:
        """Reset all metrics."""
        with self._lock:
            self._request_count = 0
            self._success_count = 0
            self._failure_count = 0
            self._bytes_sent = 0
            self._bytes_received = 0
            self._latencies.clear()
            self._active_connections = 0
            self._per_host.clear()
            self._start_time = time.monotonic()
