"""
RS Downloader v10.0.0 - Core Package
=====================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

The core engine providing download orchestration, networking,
configuration management, database persistence, and structured logging.
"""

from __future__ import annotations

__version__ = "10.0.0"
__author__ = "RAJSARASWATI JATAV (RS) / T3rmuxk1ng"
__codename__ = "INFINITE HYPERNOVA SOVEREIGN NEXUS"

# Core base types and orchestrator
from core.downloader_base import (
    VERSION,
    QueueFullError,
    QueueEmptyError,
    LifecycleError,
    DownloadError,
    AgentNotFoundError,
    CheckpointCorruptedError,
    DownloadPriority,
    DownloadStatus,
    DownloadResult,
    DownloadTask,
    ProgressCallback,
    DownloadQueue,
    detect_content_type,
    suggest_filename,
    DownloadSpeedTracker,
    DownloadScheduler,
    DownloadLifecycle,
    AgentSkill,
    AgentMemory,
    AgentRegistry,
    DownloadEventEmitter,
    CheckpointManager,
    ConcurrentDownloadManager,
    BandwidthMonitor,
    DownloadOrchestrator,
    DownloaderBase,
)

# Networking layer
from core.network import (
    ChecksumAlgorithm,
    HeadInfo,
    DownloadSession,
    SyncHTTPClient,
    AsyncHTTPClient,
    ProxyRotationStrategy,
    ProxyPool,
    BandwidthThrottler,
    DNSResolver,
    SSLContextBuilder,
    CircuitBreaker,
    RetryPolicy,
    RequestInterceptor,
    ConnectionMetrics,
    verify_checksum,
    detect_content_length,
    download_chunk,
    parallel_download,
)

# Configuration management
from core.config import (
    TimeoutConfig,
    RetryConfig,
    ProxyConfig,
    SSLConfig,
    ConnectionPoolConfig,
    RateLimitConfig,
    UserAgentConfig,
    BandwidthConfig,
    StorageConfig,
    SecurityConfig,
    LoggingConfig,
    UIConfig,
    PluginConfig,
    CloudConfig,
    TorrentConfig,
    AIConfig,
    SchedulerConfig,
    LiveStreamConfig,
    CacheConfig,
    NotificationConfig,
    VenvConfig,
    AgentConfig,
    EncryptionConfig,
    MetricsConfig,
    DebConfig,
    ConfigManager,
)

# Database persistence
from core.database import Database

# Logging
from core.logger import get_logger, RSLogger

__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__codename__",
    # Base types
    "VERSION",
    "QueueFullError",
    "QueueEmptyError",
    "LifecycleError",
    "DownloadError",
    "AgentNotFoundError",
    "CheckpointCorruptedError",
    "DownloadPriority",
    "DownloadStatus",
    "DownloadResult",
    "DownloadTask",
    "ProgressCallback",
    "DownloadQueue",
    "detect_content_type",
    "suggest_filename",
    "DownloadSpeedTracker",
    "DownloadScheduler",
    "DownloadLifecycle",
    "AgentSkill",
    "AgentMemory",
    "AgentRegistry",
    "DownloadEventEmitter",
    "CheckpointManager",
    "ConcurrentDownloadManager",
    "BandwidthMonitor",
    "DownloadOrchestrator",
    "DownloaderBase",
    # Networking
    "ChecksumAlgorithm",
    "HeadInfo",
    "DownloadSession",
    "SyncHTTPClient",
    "AsyncHTTPClient",
    "ProxyRotationStrategy",
    "ProxyPool",
    "BandwidthThrottler",
    "DNSResolver",
    "SSLContextBuilder",
    "CircuitBreaker",
    "RetryPolicy",
    "RequestInterceptor",
    "ConnectionMetrics",
    "verify_checksum",
    "detect_content_length",
    "download_chunk",
    "parallel_download",
    # Config
    "TimeoutConfig",
    "RetryConfig",
    "ProxyConfig",
    "SSLConfig",
    "ConnectionPoolConfig",
    "RateLimitConfig",
    "UserAgentConfig",
    "BandwidthConfig",
    "StorageConfig",
    "SecurityConfig",
    "LoggingConfig",
    "UIConfig",
    "PluginConfig",
    "CloudConfig",
    "TorrentConfig",
    "AIConfig",
    "SchedulerConfig",
    "LiveStreamConfig",
    "CacheConfig",
    "NotificationConfig",
    "VenvConfig",
    "AgentConfig",
    "EncryptionConfig",
    "MetricsConfig",
    "DebConfig",
    "ConfigManager",
    # Database
    "Database",
    # Logger
    "get_logger",
    "RSLogger",
]
