"""
RS Downloader v10.0.0 - Configuration Management
=================================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Enterprise-grade configuration with 25 frozen dataclass sections,
singleton manager, environment variable export, profiles, hot-reload,
version migration, and atomic file writes.
"""

from __future__ import annotations

import copy
import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field, fields
from datetime import datetime, timezone
from pathlib import Path
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

from core.logger import get_logger

logger = get_logger("config", enable_file=False)

# ---------------------------------------------------------------------------
# 25 Configuration Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeoutConfig:
    """Connection and operation timeout settings."""
    connect_timeout: float = 30.0
    read_timeout: float = 60.0
    write_timeout: float = 60.0
    pool_timeout: float = 30.0
    dns_timeout: float = 10.0
    redirect_timeout: float = 30.0
    total_timeout: float = 300.0
    retry_timeout_multiplier: float = 2.0
    slow_threshold: float = 30.0
    keep_alive_timeout: float = 60.0
    handshake_timeout: float = 15.0


@dataclass(frozen=True)
class RetryConfig:
    """Retry policy settings."""
    max_retries: int = 3
    backoff_factor: float = 2.0
    backoff_max: float = 300.0
    backoff_jitter: bool = True
    jitter_range: float = 0.5
    retry_on_status: Tuple[int, ...] = (429, 500, 502, 503, 504)
    retry_on_timeout: bool = True
    retry_on_connection_error: bool = True
    retry_budget_per_minute: int = 100
    circuit_breaker_threshold: int = 5
    circuit_breaker_recovery: float = 60.0
    circuit_breaker_success_threshold: int = 3


@dataclass(frozen=True)
class ProxyConfig:
    """Proxy settings."""
    enabled: bool = False
    rotation_strategy: str = "round_robin"
    proxy_list: Tuple[str, ...] = ()
    proxy_file: str = ""
    auth_username: str = ""
    auth_password: str = ""
    health_check_url: str = "https://httpbin.org/ip"
    health_check_interval: float = 300.0
    health_check_timeout: float = 10.0
    max_failures: int = 3
    auto_remove_dead: bool = True
    socks_enabled: bool = True
    geo_routing: bool = False
    sticky_session: bool = False


@dataclass(frozen=True)
class SSLConfig:
    """SSL/TLS settings."""
    verify: bool = True
    cert_path: str = ""
    key_path: str = ""
    ca_bundle: str = ""
    min_version: str = "TLSv1_2"
    max_version: str = "TLSv1_3"
    cipher_list: Tuple[str, ...] = ()
    pin_sha256: Tuple[str, ...] = ()
    client_cert_path: str = ""
    client_key_path: str = ""
    ocsp_check: bool = False
    sni_enabled: bool = True


@dataclass(frozen=True)
class ConnectionPoolConfig:
    """HTTP connection pooling settings."""
    pool_maxsize: int = 100
    pool_minsize: int = 10
    max_connections: int = 200
    max_per_host: int = 20
    keep_alive: bool = True
    keep_alive_expire: float = 60.0
    enable_reuse: bool = True
    max_reuse_count: int = 100


@dataclass(frozen=True)
class RateLimitConfig:
    """Rate limiting settings."""
    enabled: bool = False
    requests_per_second: float = 10.0
    burst_size: int = 20
    per_host_limit: float = 5.0
    adaptive: bool = True
    backoff_on_429: bool = True
    respect_retry_after: bool = True


@dataclass(frozen=True)
class UserAgentConfig:
    """User-Agent rotation settings."""
    user_agent: str = "RS-Downloader/10.0.0"
    rotation_enabled: bool = False
    agent_list: Tuple[str, ...] = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0",
    )
    randomize_order: bool = True
    per_site_agent: bool = False


@dataclass(frozen=True)
class BandwidthConfig:
    """Bandwidth management settings."""
    global_limit_kbps: float = 0.0
    per_download_limit_kbps: float = 0.0
    per_agent_limit_kbps: float = 0.0
    priority_allocation: bool = True
    schedule_enabled: bool = False
    peak_hours_start: int = 8
    peak_hours_end: int = 22
    peak_limit_kbps: float = 0.0
    off_peak_limit_kbps: float = 0.0
    burst_enabled: bool = True
    burst_size_kb: int = 1024
    token_bucket_rate: float = 0.0


@dataclass(frozen=True)
class StorageConfig:
    """File storage settings."""
    download_dir: str = "~/Downloads/RS_Downloader"
    temp_dir: str = ""
    max_file_size: int = 0
    min_free_space_gb: float = 5.0
    auto_create_dirs: bool = True
    filename_template: str = "{filename}"
    duplicate_handling: str = "rename"  # rename, skip, overwrite
    organize_by_platform: bool = False
    organize_by_date: bool = False
    organize_by_type: bool = False
    cleanup_temp_on_exit: bool = True
    move_after_complete: bool = False
    completed_dir: str = ""
    preserve_permissions: bool = True
    symlinks: bool = False


@dataclass(frozen=True)
class SecurityConfig:
    """Security settings."""
    verify_checksums: bool = True
    default_checksum_algo: str = "sha256"
    scan_for_malware: bool = False
    malware_scan_command: str = ""
    blocked_domains: Tuple[str, ...] = ()
    blocked_extensions: Tuple[str, ...] = (".exe", ".scr", ".bat", ".cmd", ".vbs", ".js")
    allowed_domains: Tuple[str, ...] = ()
    enforce_https: bool = False
    strip_query_params: bool = False
    sanitize_filenames: bool = True
    max_redirects: int = 10
    safe_redirect_domains: Tuple[str, ...] = ()


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""
    level: str = "DEBUG"
    log_dir: str = "logs"
    log_format: str = "color"
    enable_file: bool = True
    enable_console: bool = True
    sensitive_filter: bool = True
    rate_limit: int = 0
    rotation_max_bytes: int = 10485760
    rotation_backup_count: int = 30
    rotation_when: str = "midnight"
    compress_rotated: bool = True
    enable_remote: bool = False
    remote_url: str = ""
    remote_min_level: str = "ERROR"
    audit_enabled: bool = False


@dataclass(frozen=True)
class UIConfig:
    """User interface settings."""
    theme: str = "dark"
    show_progress: bool = True
    progress_style: str = "bar"
    show_speed: bool = True
    show_eta: bool = True
    show_size: bool = True
    compact_mode: bool = False
    color_output: bool = True
    unicode_supported: bool = True
    refresh_interval: float = 0.5
    max_visible_downloads: int = 20
    sort_uploads_by: str = "priority"
    web_interface: bool = False
    web_port: int = 8080
    web_host: str = "127.0.0.1"


@dataclass(frozen=True)
class PluginConfig:
    """Plugin system settings."""
    enabled: bool = True
    plugin_dir: str = "plugins"
    auto_discover: bool = True
    auto_update: bool = False
    update_url: str = ""
    sandbox_mode: bool = True
    max_load_time: float = 10.0
    trusted_sources: Tuple[str, ...] = ()
    disabled_plugins: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CloudConfig:
    """Cloud storage integration settings."""
    enabled: bool = False
    provider: str = ""
    bucket: str = ""
    region: str = "us-east-1"
    access_key: str = ""
    secret_key: str = ""
    endpoint_url: str = ""
    auto_upload: bool = False
    upload_on_complete: bool = False
    prefix: str = "rs-downloader/"
    storage_class: str = "STANDARD"
    encryption: bool = True
    multipart_threshold: int = 104857600
    multipart_chunksize: int = 8388608


@dataclass(frozen=True)
class TorrentConfig:
    """Torrent download settings."""
    enabled: bool = False
    listen_port: int = 6881
    max_connections: int = 200
    max_uploads: int = 4
    download_limit: int = 0
    upload_limit: int = 0
    seed_ratio: float = 1.0
    seed_time: float = 0.0
    dht_enabled: bool = True
    pex_enabled: bool = True
    encryption: str = "prefer"
    tracker_list: Tuple[str, ...] = ()
    proxy_enabled: bool = False


@dataclass(frozen=True)
class AIConfig:
    """AI-powered features settings."""
    enabled: bool = False
    auto_categorize: bool = True
    smart_retry: bool = True
    predict_errors: bool = False
    model: str = "local"
    api_key: str = ""
    api_url: str = ""
    classification_confidence: float = 0.8
    auto_quality_select: bool = False


@dataclass(frozen=True)
class SchedulerConfig:
    """Download scheduler settings."""
    enabled: bool = False
    max_concurrent: int = 3
    time_based: bool = False
    start_hour: int = 0
    end_hour: int = 24
    cron_jobs: Tuple[str, ...] = ()
    auto_retry_scheduled: bool = True
    priority_boost_on_retry: bool = True
    stagger_interval: float = 2.0
    queue_timeout: float = 3600.0


@dataclass(frozen=True)
class LiveStreamConfig:
    """Live stream recording settings."""
    enabled: bool = False
    format: str = "ts"
    segment_duration: float = 10.0
    reconnect_attempts: int = 5
    reconnect_delay: float = 5.0
    buffer_size: int = 4096
    record_on_start: bool = False
    auto_detect: bool = True
    quality: str = "best"
    hls_live_edge: int = 3


@dataclass(frozen=True)
class CacheConfig:
    """Caching settings."""
    enabled: bool = True
    max_size_mb: float = 500.0
    ttl_default: float = 3600.0
    ttl_success: float = 7200.0
    ttl_failure: float = 300.0
    eviction_policy: str = "lru"
    persist_to_disk: bool = True
    cache_dir: str = "cache"
    cache_headers: Tuple[str, ...] = ("etag", "last-modified", "content-length")
    compress_values: bool = False


@dataclass(frozen=True)
class NotificationConfig:
    """Notification settings."""
    enabled: bool = False
    on_complete: bool = True
    on_error: bool = True
    on_pause: bool = False
    on_schedule: bool = False
    desktop_notifications: bool = True
    sound: bool = False
    webhook_url: str = ""
    email_enabled: bool = False
    email_smtp: str = ""
    email_from: str = ""
    email_to: Tuple[str, ...] = ()
    email_subject_template: str = "[RS Downloader] {event}: {filename}"
    telegram_enabled: bool = False
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


@dataclass(frozen=True)
class VenvConfig:
    """Virtual environment settings."""
    enabled: bool = False
    venv_dir: str = ".venv"
    python_version: str = ""
    auto_create: bool = False
    auto_activate: bool = False
    requirements_file: str = "requirements.txt"
    pip_index: str = "https://pypi.org/simple"
    extra_indexes: Tuple[str, ...] = ()


@dataclass(frozen=True)
class AgentConfig:
    """Download agent settings."""
    max_concurrent_per_agent: int = 3
    default_agent: str = "generic"
    agent_timeout: float = 300.0
    agent_dir: str = "agents"
    auto_discover: bool = True
    memory_persist: bool = True
    memory_dir: str = "agent_memory"
    health_check_interval: float = 60.0
    restart_on_failure: bool = True
    max_restart_attempts: int = 3


@dataclass(frozen=True)
class EncryptionConfig:
    """Encryption settings."""
    enabled: bool = False
    algorithm: str = "aes-256-gcm"
    key_derivation: str = "pbkdf2"
    key_file: str = ""
    auto_encrypt: bool = False
    encrypt_on_complete: bool = False
    encrypted_dir: str = ""
    key_rotation_days: int = 90
    compression_before_encrypt: bool = True


@dataclass(frozen=True)
class MetricsConfig:
    """Metrics collection settings."""
    enabled: bool = True
    collect_interval: float = 10.0
    retention_days: int = 90
    export_format: str = "json"
    export_dir: str = "metrics"
    prometheus_enabled: bool = False
    prometheus_port: int = 9090
    track_bandwidth: bool = True
    track_latency: bool = True
    track_errors: bool = True
    track_queue_stats: bool = True


@dataclass(frozen=True)
class DebConfig:
    """Debian package build settings."""
    package_name: str = "rs-downloader"
    version: str = "10.0.0"
    maintainer: str = "RAJSARASWATI JATAV <rs@t3rmuxk1ng.dev>"
    description: str = "RS Downloader - Enterprise Download Manager"
    depends: Tuple[str, ...] = ("python3", "python3-pip")
    section: str = "net"
    priority: str = "optional"
    architecture: str = "amd64"
    install_dir: str = "/opt/rs-downloader"
    systemd_service: bool = True
    config_dir: str = "/etc/rs-downloader"
    log_dir: str = "/var/log/rs-downloader"


# ---------------------------------------------------------------------------
# All sections registry
# ---------------------------------------------------------------------------

CONFIG_SECTIONS: Dict[str, type] = {
    "timeout": TimeoutConfig,
    "retry": RetryConfig,
    "proxy": ProxyConfig,
    "ssl": SSLConfig,
    "connection_pool": ConnectionPoolConfig,
    "rate_limit": RateLimitConfig,
    "user_agent": UserAgentConfig,
    "bandwidth": BandwidthConfig,
    "storage": StorageConfig,
    "security": SecurityConfig,
    "logging": LoggingConfig,
    "ui": UIConfig,
    "plugin": PluginConfig,
    "cloud": CloudConfig,
    "torrent": TorrentConfig,
    "ai": AIConfig,
    "scheduler": SchedulerConfig,
    "live_stream": LiveStreamConfig,
    "cache": CacheConfig,
    "notification": NotificationConfig,
    "venv": VenvConfig,
    "agent": AgentConfig,
    "encryption": EncryptionConfig,
    "metrics": MetricsConfig,
    "deb": DebConfig,
}


# ---------------------------------------------------------------------------
# Profile definitions
# ---------------------------------------------------------------------------

PROFILES: Dict[str, Dict[str, Dict[str, Any]]] = {
    "dev": {
        "logging": {"level": "DEBUG", "enable_console": True, "rate_limit": 0},
        "storage": {"download_dir": "~/Downloads/RS_Downloader_dev", "duplicate_handling": "overwrite"},
        "security": {"verify_checksums": False, "sanitize_filenames": True},
        "retry": {"max_retries": 1, "backoff_factor": 1.0},
        "bandwidth": {"global_limit_kbps": 0.0},
        "metrics": {"enabled": True, "collect_interval": 5.0},
        "cache": {"ttl_default": 60.0},
        "agent": {"max_concurrent_per_agent": 5},
    },
    "staging": {
        "logging": {"level": "INFO", "enable_console": True, "rate_limit": 100},
        "storage": {"download_dir": "~/Downloads/RS_Downloader_staging"},
        "security": {"verify_checksums": True},
        "retry": {"max_retries": 2, "backoff_factor": 1.5},
        "bandwidth": {"global_limit_kbps": 50000.0},
        "metrics": {"enabled": True, "collect_interval": 15.0},
        "cache": {"ttl_default": 1800.0},
    },
    "prod": {
        "logging": {"level": "WARNING", "enable_console": False, "enable_file": True, "rate_limit": 200},
        "storage": {"download_dir": "/opt/rs-downloader/downloads", "duplicate_handling": "rename"},
        "security": {"verify_checksums": True, "enforce_https": True, "scan_for_malware": True},
        "retry": {"max_retries": 5, "backoff_factor": 2.0, "circuit_breaker_threshold": 3},
        "bandwidth": {"global_limit_kbps": 100000.0, "schedule_enabled": True},
        "metrics": {"enabled": True, "collect_interval": 30.0, "prometheus_enabled": True},
        "cache": {"ttl_default": 3600.0, "max_size_mb": 2000.0},
        "notification": {"enabled": True, "on_error": True, "on_complete": True},
    },
    "testing": {
        "logging": {"level": "DEBUG", "enable_console": True, "enable_file": False},
        "storage": {"download_dir": "/tmp/rs_downloader_test", "duplicate_handling": "overwrite"},
        "security": {"verify_checksums": False},
        "retry": {"max_retries": 1, "backoff_factor": 0.1},
        "cache": {"ttl_default": 10.0, "persist_to_disk": False},
        "agent": {"max_concurrent_per_agent": 10},
    },
}


# ---------------------------------------------------------------------------
# Deep merge utility
# ---------------------------------------------------------------------------

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries. Override values take precedence.
    Nested dicts are merged recursively.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def flatten_dict(d: Dict[str, Any], prefix: str = "", sep: str = "_") -> Dict[str, Any]:
    """Flatten a nested dictionary with prefixed keys."""
    items: Dict[str, Any] = {}
    for k, v in d.items():
        new_key = f"{prefix}{sep}{k}" if prefix else k
        if isinstance(v, dict):
            items.update(flatten_dict(v, new_key, sep))
        else:
            items[new_key] = v
    return items


# ---------------------------------------------------------------------------
# ConfigManager - Singleton
# ---------------------------------------------------------------------------

class ConfigManager:
    """
    Singleton configuration manager with thread-safe access,
    environment variable export, profiles, hot-reload, and migration.

    Usage:
        config = ConfigManager()
        config.load()
        timeout = config.get("timeout", "connect_timeout")
        config.set("timeout", "connect_timeout", 60.0)
    """

    _instance: Optional["ConfigManager"] = None
    _instance_lock = threading.Lock()

    def __new__(cls, *args: Any, **kwargs: Any) -> "ConfigManager":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(
        self,
        config_file: Union[str, Path] = "config.json",
        config_dir: Union[str, Path] = ".",
        profile: str = "dev",
    ) -> None:
        if self._initialized:
            return
        self._initialized = True
        self._config_file = Path(config_dir) / config_file
        self._config_dir = Path(config_dir)
        self._profile = profile
        self._sections: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._change_callbacks: List[Callable[[str, str, Any, Any], None]] = []
        self._watcher_thread: Optional[threading.Thread] = None
        self._watcher_running = False
        self._last_modified: float = 0.0
        self._env_prefix = "RS_DL"
        self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default values from all config section dataclasses."""
        for name, cls in CONFIG_SECTIONS.items():
            self._sections[name] = cls()

    def load(self, path: Optional[Union[str, Path]] = None) -> None:
        """
        Load configuration from JSON file.
        Applies profile overrides, then file overrides on top.
        """
        config_path = Path(path) if path else self._config_file
        with self._lock:
            self._load_defaults()
            self._apply_profile(self._profile)
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        file_data = json.load(f)
                    self._apply_overrides(file_data)
                    self._last_modified = config_path.stat().st_mtime
                    logger.info("Config loaded from %s", config_path)
                except (json.JSONDecodeError, OSError) as e:
                    logger.error("Failed to load config from %s: %s", config_path, e)
            else:
                logger.info("Config file not found, using defaults with profile '%s'", self._profile)

    def save(self, path: Optional[Union[str, Path]] = None) -> None:
        """
        Save configuration to JSON file with atomic write.
        """
        config_path = Path(path) if path else self._config_file
        with self._lock:
            data = self.to_dict()
            config_path.parent.mkdir(parents=True, exist_ok=True)
            tmp_path = config_path.with_suffix(".tmp")
            try:
                with open(tmp_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2, ensure_ascii=False, default=str)
                tmp_path.replace(config_path)
                self._last_modified = config_path.stat().st_mtime
                logger.info("Config saved to %s", config_path)
            except OSError as e:
                logger.error("Failed to save config: %s", e)
                if tmp_path.exists():
                    try:
                        tmp_path.unlink()
                    except OSError:
                        pass

    def _apply_profile(self, profile: str) -> None:
        """Apply profile overrides to current configuration."""
        if profile not in PROFILES:
            logger.warning("Unknown profile '%s', using defaults", profile)
            return
        overrides = PROFILES[profile]
        for section_name, section_overrides in overrides.items():
            if section_name not in self._sections:
                continue
            current = asdict(self._sections[section_name])
            for key, value in section_overrides.items():
                if key in current:
                    current[key] = value
            section_cls = CONFIG_SECTIONS[section_name]
            try:
                self._sections[section_name] = section_cls(**current)
            except TypeError:
                logger.warning("Invalid profile override for %s.%s", section_name, key)

    def _apply_overrides(self, data: Dict[str, Any]) -> None:
        """Apply dictionary overrides to configuration sections."""
        for section_name, section_data in data.items():
            if section_name not in self._sections:
                logger.warning("Unknown config section: %s", section_name)
                continue
            if not isinstance(section_data, dict):
                continue
            current = asdict(self._sections[section_name])
            for key, value in section_data.items():
                if key in current:
                    old_value = current[key]
                    current[key] = value
                    self._notify_change(section_name, key, old_value, value)
                else:
                    logger.warning("Unknown config key: %s.%s", section_name, key)
            section_cls = CONFIG_SECTIONS[section_name]
            try:
                self._sections[section_name] = section_cls(**current)
            except TypeError as e:
                logger.warning("Invalid config override for %s: %s", section_name, e)

    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            section: Section name (e.g., 'timeout', 'retry').
            key: Key within the section.
            default: Default value if key not found.

        Returns:
            The configuration value, or default.
        """
        with self._lock:
            if section not in self._sections:
                return default
            section_data = self._sections[section]
            data_dict = asdict(section_data)
            return data_dict.get(key, default)

    def set(self, section: str, key: str, value: Any) -> None:
        """
        Set a configuration value and notify listeners.

        Note: Since dataclasses are frozen, this replaces the entire section.
        """
        with self._lock:
            if section not in self._sections:
                logger.warning("Unknown config section: %s", section)
                return
            current = asdict(self._sections[section])
            if key not in current:
                logger.warning("Unknown config key: %s.%s", section, key)
                return
            old_value = current[key]
            current[key] = value
            section_cls = CONFIG_SECTIONS[section]
            try:
                self._sections[section] = section_cls(**current)
                self._notify_change(section, key, old_value, value)
            except TypeError as e:
                logger.warning("Invalid config value for %s.%s: %s", section, key, e)
                # Restore old value
                current[key] = old_value
                self._sections[section] = section_cls(**current)

    def get_section(self, section: str) -> Dict[str, Any]:
        """Get all values in a section as a dictionary."""
        with self._lock:
            if section not in self._sections:
                return {}
            return asdict(self._sections[section])

    def set_section(self, section: str, values: Dict[str, Any]) -> None:
        """Set multiple values in a section."""
        with self._lock:
            if section not in self._sections:
                return
            current = asdict(self._sections[section])
            for key, value in values.items():
                if key in current:
                    old_value = current[key]
                    current[key] = value
                    self._notify_change(section, key, old_value, value)
            section_cls = CONFIG_SECTIONS[section]
            try:
                self._sections[section] = section_cls(**current)
            except TypeError:
                pass

    def reset_section(self, section: str) -> None:
        """Reset a section to its default values."""
        with self._lock:
            if section in CONFIG_SECTIONS:
                self._sections[section] = CONFIG_SECTIONS[section]()
                logger.info("Config section '%s' reset to defaults", section)

    def reset_all(self) -> None:
        """Reset all sections to defaults."""
        with self._lock:
            self._load_defaults()
            self._apply_profile(self._profile)
            logger.info("All config reset to defaults (profile: %s)", self._profile)

    def to_dict(self) -> Dict[str, Any]:
        """Export full configuration as a nested dictionary."""
        with self._lock:
            result: Dict[str, Any] = {}
            for name, section in self._sections.items():
                result[name] = asdict(section)
            result["_meta"] = {
                "version": "10.0.0",
                "profile": self._profile,
                "saved_at": datetime.now(tz=timezone.utc).isoformat(),
            }
            return result

    def to_json(self, indent: int = 2) -> str:
        """Export configuration as JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False, default=str)

    def diff_from_defaults(self) -> Dict[str, Dict[str, Tuple[Any, Any]]]:
        """
        Compare current config with defaults.
        Returns a dict of {section: {key: (default_value, current_value)}}.
        """
        result: Dict[str, Dict[str, Tuple[Any, Any]]] = {}
        with self._lock:
            for name, section in self._sections.items():
                defaults = CONFIG_SECTIONS[name]()
                current = asdict(section)
                default_dict = asdict(defaults)
                diff: Dict[str, Tuple[Any, Any]] = {}
                for key in default_dict:
                    if current.get(key) != default_dict[key]:
                        diff[key] = (default_dict[key], current.get(key))
                if diff:
                    result[name] = diff
        return result

    def mask_sensitive(self) -> Dict[str, Any]:
        """
        Export configuration with sensitive data masked.
        Used for logging and debugging.
        """
        sensitive_keys = {
            "auth_password", "secret_key", "access_key", "api_key",
            "client_key_path", "key_path", "telegram_bot_token",
        }
        data = self.to_dict()
        for section_name, section_data in data.items():
            if isinstance(section_data, dict):
                for key, value in section_data.items():
                    if key in sensitive_keys and isinstance(value, str) and value:
                        section_data[key] = "****MASKED****"
        return data

    def export_env(self, prefix: str = "") -> Dict[str, str]:
        """
        Export configuration as environment variable names and values.

        Format: RS_DL_{SECTION}_{KEY}=value (uppercased)
        """
        p = prefix or self._env_prefix
        flat = flatten_dict(self.to_dict(), p)
        env_vars: Dict[str, str] = {}
        for key, value in flat.items():
            env_key = key.upper()
            if isinstance(value, bool):
                env_vars[env_key] = "1" if value else "0"
            elif isinstance(value, (list, tuple)):
                env_vars[env_key] = ",".join(str(v) for v in value)
            elif value is None:
                env_vars[env_key] = ""
            else:
                env_vars[env_key] = str(value)
        return env_vars

    def load_from_env(self, prefix: str = "") -> None:
        """
        Load configuration overrides from environment variables.

        Format: RS_DL_{SECTION}_{KEY}=value
        """
        p = prefix or self._env_prefix
        for section_name in CONFIG_SECTIONS:
            section_cls = CONFIG_SECTIONS[section_name]
            current = asdict(self._sections[section_name])
            changed = False
            for key in current:
                env_key = f"{p}_{section_name}_{key}".upper()
                env_value = os.environ.get(env_key)
                if env_value is not None:
                    typed_value = self._parse_env_value(env_value, type(current[key]))
                    if typed_value is not None:
                        current[key] = typed_value
                        changed = True
            if changed:
                try:
                    self._sections[section_name] = section_cls(**current)
                except TypeError:
                    pass

    def _parse_env_value(self, value: str, target_type: type) -> Any:
        """Parse environment variable string into the target type."""
        try:
            if target_type == bool:
                return value.lower() in ("1", "true", "yes", "on")
            elif target_type == int:
                return int(value)
            elif target_type == float:
                return float(value)
            elif target_type == str:
                return value
            else:
                return value
        except (ValueError, TypeError):
            return None

    # -- Profile management --

    def set_profile(self, profile: str) -> None:
        """Switch to a different configuration profile."""
        if profile not in PROFILES:
            logger.warning("Unknown profile: %s", profile)
            return
        with self._lock:
            self._profile = profile
            self._load_defaults()
            self._apply_profile(profile)
            logger.info("Switched to profile: %s", profile)

    def get_profile(self) -> str:
        """Get the current profile name."""
        return self._profile

    def list_profiles(self) -> List[str]:
        """List available profile names."""
        return list(PROFILES.keys())

    # -- Change notifications --

    def on_change(self, callback: Callable[[str, str, Any, Any], None]) -> None:
        """Register a callback for config changes. Callback receives (section, key, old_value, new_value)."""
        with self._lock:
            self._change_callbacks.append(callback)

    def remove_on_change(self, callback: Callable[[str, str, Any, Any], None]) -> None:
        """Remove a change callback."""
        with self._lock:
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)

    def _notify_change(self, section: str, key: str, old_value: Any, new_value: Any) -> None:
        """Notify all registered callbacks of a config change."""
        for callback in self._change_callbacks:
            try:
                callback(section, key, old_value, new_value)
            except Exception as e:
                logger.error("Config change callback error: %s", e)

    # -- File watching / hot-reload --

    def start_watching(self, interval: float = 5.0) -> None:
        """Start watching the config file for changes and hot-reload."""
        if self._watcher_running:
            return
        self._watcher_running = True
        self._watcher_thread = threading.Thread(
            target=self._watch_loop,
            args=(interval,),
            name="config_watcher",
            daemon=True,
        )
        self._watcher_thread.start()
        logger.info("Config file watching started (interval: %.1fs)", interval)

    def stop_watching(self) -> None:
        """Stop watching the config file."""
        self._watcher_running = False
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=10.0)
        logger.info("Config file watching stopped")

    def _watch_loop(self, interval: float) -> None:
        """Watch loop for file changes."""
        while self._watcher_running:
            try:
                if self._config_file.exists():
                    mtime = self._config_file.stat().st_mtime
                    if mtime > self._last_modified:
                        logger.info("Config file changed, reloading...")
                        self.load()
            except OSError:
                pass
            time.sleep(interval)

    # -- Version migration --

    def migrate(self, from_version: str) -> None:
        """
        Migrate configuration from an older version.

        Supports migration paths: v5 → v6 → v7 → v8 → v9 → v10
        """
        migrations: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {
            "5": self._migrate_v5_to_v6,
            "6": self._migrate_v6_to_v7,
            "7": self._migrate_v7_to_v8,
            "8": self._migrate_v8_to_v9,
            "9": self._migrate_v9_to_v10,
        }
        major = from_version.split(".")[0]
        data = self.to_dict()
        version = major
        while version in migrations:
            logger.info("Migrating config from v%s to v%s", version, int(version) + 1)
            data = migrations[version](data)
            version = str(int(version) + 1)
        self._apply_overrides(data)
        logger.info("Config migration complete (from v%s to v10)", major)

    def _migrate_v5_to_v6(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v5 to v6."""
        if "general" in data:
            general = data.pop("general")
            if "timeout" not in data:
                data["timeout"] = {}
            data["timeout"]["connect_timeout"] = general.get("connect_timeout", 30.0)
            data["timeout"]["read_timeout"] = general.get("read_timeout", 60.0)
        if "network" in data:
            network = data.pop("network")
            if "proxy" not in data:
                data["proxy"] = {}
            data["proxy"]["enabled"] = network.get("use_proxy", False)
            data["proxy"]["proxy_list"] = network.get("proxy_list", ())
        return data

    def _migrate_v6_to_v7(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v6 to v7."""
        if "download" in data:
            download = data.pop("download")
            if "storage" not in data:
                data["storage"] = {}
            data["storage"]["download_dir"] = download.get("download_dir", "~/Downloads/RS_Downloader")
            data["storage"]["max_file_size"] = download.get("max_file_size", 0)
            data["storage"]["duplicate_handling"] = download.get("duplicate_handling", "rename")
        if "cache" not in data:
            data["cache"] = {"enabled": True, "ttl_default": 3600.0}
        return data

    def _migrate_v7_to_v8(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v7 to v8."""
        if "security" in data:
            sec = data["security"]
            if "default_checksum" in sec:
                sec["default_checksum_algo"] = sec.pop("default_checksum")
        if "bandwidth" not in data:
            data["bandwidth"] = {"global_limit_kbps": 0.0}
        if "notification" not in data:
            data["notification"] = {"enabled": False}
        return data

    def _migrate_v8_to_v9(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v8 to v9."""
        if "agent" not in data:
            data["agent"] = {"max_concurrent_per_agent": 3, "default_agent": "generic"}
        if "cloud" not in data:
            data["cloud"] = {"enabled": False}
        if "encryption" not in data:
            data["encryption"] = {"enabled": False}
        return data

    def _migrate_v9_to_v10(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate from v9 to v10."""
        if "ai" not in data:
            data["ai"] = {"enabled": False, "auto_categorize": True}
        if "live_stream" not in data:
            data["live_stream"] = {"enabled": False}
        if "deb" not in data:
            data["deb"] = {"package_name": "rs-downloader", "version": "10.0.0"}
        if "venv" not in data:
            data["venv"] = {"enabled": False}
        if "metrics" not in data:
            data["metrics"] = {"enabled": True, "collect_interval": 10.0}
        # Update any version references
        if "deb" in data:
            data["deb"]["version"] = "10.0.0"
        return data

    # -- Validation --

    def validate(self) -> Dict[str, List[str]]:
        """
        Validate all configuration values.
        Returns a dict of {section: [error_messages]}.
        """
        errors: Dict[str, List[str]] = {}
        with self._lock:
            for name, section in self._sections.items():
                section_errors: List[str] = []
                data = asdict(section)
                # Type-specific validation
                for key, value in data.items():
                    if value is None:
                        continue
                    if "timeout" in key.lower() and isinstance(value, (int, float)):
                        if value < 0:
                            section_errors.append(f"{key}: timeout cannot be negative ({value})")
                    if "limit" in key.lower() and isinstance(value, (int, float)):
                        if value < 0:
                            section_errors.append(f"{key}: limit cannot be negative ({value})")
                    if "max_" in key.lower() and isinstance(value, int):
                        if value < 0:
                            section_errors.append(f"{key}: max value cannot be negative ({value})")
                    if "port" in key.lower() and isinstance(value, int):
                        if not (0 <= value <= 65535):
                            section_errors.append(f"{key}: invalid port number ({value})")
                if name == "storage":
                    if data.get("min_free_space_gb", 0) < 0:
                        section_errors.append("min_free_space_gb cannot be negative")
                    if data.get("duplicate_handling") not in ("rename", "skip", "overwrite"):
                        section_errors.append(f"invalid duplicate_handling: {data.get('duplicate_handling')}")
                if name == "security":
                    if data.get("default_checksum_algo") not in (
                        "md5", "sha1", "sha256", "sha512", "crc32", "blake2b", "blake2s", "xxh64"
                    ):
                        section_errors.append(f"invalid checksum algorithm: {data.get('default_checksum_algo')}")
                if section_errors:
                    errors[name] = section_errors
        return errors

    # -- Convenience properties --

    @property
    def timeout(self) -> TimeoutConfig:
        """Access timeout config section."""
        return self._sections["timeout"]

    @property
    def retry(self) -> RetryConfig:
        """Access retry config section."""
        return self._sections["retry"]

    @property
    def proxy(self) -> ProxyConfig:
        """Access proxy config section."""
        return self._sections["proxy"]

    @property
    def ssl(self) -> SSLConfig:
        """Access SSL config section."""
        return self._sections["ssl"]

    @property
    def storage(self) -> StorageConfig:
        """Access storage config section."""
        return self._sections["storage"]

    @property
    def security(self) -> SecurityConfig:
        """Access security config section."""
        return self._sections["security"]

    @property
    def bandwidth(self) -> BandwidthConfig:
        """Access bandwidth config section."""
        return self._sections["bandwidth"]

    @property
    def agent(self) -> AgentConfig:
        """Access agent config section."""
        return self._sections["agent"]

    @property
    def logging_cfg(self) -> LoggingConfig:
        """Access logging config section."""
        return self._sections["logging"]

    def __repr__(self) -> str:
        return f"ConfigManager(profile={self._profile!r}, sections={len(self._sections)})"

    def __del__(self) -> None:
        self.stop_watching()
