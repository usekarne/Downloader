"""
RS Downloader v10.0.0 - Database Layer
========================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Enterprise SQLite database with WAL mode, 9 tables, full CRUD,
advanced search, statistics, export, caching, config history,
migration, backup/restore, 20+ indexes, and thread-safe access.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import sqlite3
import threading
import time
from collections import OrderedDict
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import (
    Any,
    Dict,
    Generator,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
)

from core.logger import get_logger

logger = get_logger("database", enable_file=False)


# ---------------------------------------------------------------------------
# Schema version
# ---------------------------------------------------------------------------

SCHEMA_VERSION = 10


# ---------------------------------------------------------------------------
# Table creation SQL
# ---------------------------------------------------------------------------

CREATE_TABLES_SQL = """
-- Downloads table
CREATE TABLE IF NOT EXISTS downloads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT UNIQUE NOT NULL,
    url TEXT NOT NULL,
    filename TEXT NOT NULL DEFAULT '',
    output_path TEXT NOT NULL DEFAULT '',
    file_size INTEGER DEFAULT 0,
    downloaded_size INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',
    platform TEXT DEFAULT '',
    agent_name TEXT DEFAULT '',
    quality TEXT DEFAULT '',
    format TEXT DEFAULT '',
    content_type TEXT DEFAULT '',
    error TEXT DEFAULT '',
    checksum TEXT DEFAULT '',
    checksum_algo TEXT DEFAULT 'sha256',
    checksum_verified INTEGER DEFAULT 0,
    resume_used INTEGER DEFAULT 0,
    average_speed REAL DEFAULT 0.0,
    elapsed REAL DEFAULT 0.0,
    retry_count INTEGER DEFAULT 0,
    priority INTEGER DEFAULT 5,
    tags TEXT DEFAULT '',
    source_url TEXT DEFAULT '',
    download_method TEXT DEFAULT '',
    thumbnail_url TEXT DEFAULT '',
    duration REAL DEFAULT 0.0,
    metadata TEXT DEFAULT '{}',
    started_at TEXT,
    completed_at TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Agent runs table
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    duration REAL DEFAULT 0.0,
    error TEXT DEFAULT '',
    result TEXT DEFAULT '{}',
    metadata TEXT DEFAULT '{}'
);

-- Schedules table
CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cron_expr TEXT NOT NULL,
    url TEXT NOT NULL,
    agent_hint TEXT DEFAULT '',
    platform_hint TEXT DEFAULT '',
    enabled INTEGER DEFAULT 1,
    last_run TEXT,
    next_run TEXT,
    run_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    last_error TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- Proxies table
CREATE TABLE IF NOT EXISTS proxies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    url TEXT UNIQUE NOT NULL,
    protocol TEXT DEFAULT 'http',
    username TEXT DEFAULT '',
    password TEXT DEFAULT '',
    weight REAL DEFAULT 1.0,
    country TEXT DEFAULT '',
    is_alive INTEGER DEFAULT 1,
    latency_ms REAL DEFAULT 0.0,
    failure_count INTEGER DEFAULT 0,
    success_count INTEGER DEFAULT 0,
    last_check TEXT,
    last_used TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

-- Cache entries table
CREATE TABLE IF NOT EXISTS cache_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    key TEXT UNIQUE NOT NULL,
    value TEXT NOT NULL,
    content_type TEXT DEFAULT '',
    compressed INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    expires_at TEXT,
    access_count INTEGER DEFAULT 0,
    last_accessed TEXT DEFAULT (datetime('now')),
    size_bytes INTEGER DEFAULT 0
);

-- Config history table
CREATE TABLE IF NOT EXISTS config_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section TEXT NOT NULL,
    key TEXT NOT NULL,
    old_value TEXT DEFAULT '',
    new_value TEXT DEFAULT '',
    changed_by TEXT DEFAULT 'system',
    changed_at TEXT DEFAULT (datetime('now'))
);

-- Metrics table
CREATE TABLE IF NOT EXISTS metrics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    labels TEXT DEFAULT '{}',
    timestamp TEXT DEFAULT (datetime('now')),
    source TEXT DEFAULT ''
);

-- Tags table
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT NOT NULL,
    tag TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(task_id, tag)
);

-- Meta table
CREATE TABLE IF NOT EXISTS _meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

# ---------------------------------------------------------------------------
# Indexes
# ---------------------------------------------------------------------------

CREATE_INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_downloads_task_id ON downloads(task_id);
CREATE INDEX IF NOT EXISTS idx_downloads_url ON downloads(url);
CREATE INDEX IF NOT EXISTS idx_downloads_status ON downloads(status);
CREATE INDEX IF NOT EXISTS idx_downloads_platform ON downloads(platform);
CREATE INDEX IF NOT EXISTS idx_downloads_agent ON downloads(agent_name);
CREATE INDEX IF NOT EXISTS idx_downloads_created_at ON downloads(created_at);
CREATE INDEX IF NOT EXISTS idx_downloads_priority ON downloads(priority);
CREATE INDEX IF NOT EXISTS idx_downloads_filename ON downloads(filename);
CREATE INDEX IF NOT EXISTS idx_agent_runs_name ON agent_runs(agent_name);
CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
CREATE INDEX IF NOT EXISTS idx_agent_runs_task_id ON agent_runs(task_id);
CREATE INDEX IF NOT EXISTS idx_schedules_enabled ON schedules(enabled);
CREATE INDEX IF NOT EXISTS idx_schedules_next_run ON schedules(next_run);
CREATE INDEX IF NOT EXISTS idx_proxies_alive ON proxies(is_alive);
CREATE INDEX IF NOT EXISTS idx_proxies_protocol ON proxies(protocol);
CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_entries(key);
CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at);
CREATE INDEX IF NOT EXISTS idx_config_history_section ON config_history(section);
CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
CREATE INDEX IF NOT EXISTS idx_tags_task_id ON tags(task_id);
CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
CREATE INDEX IF NOT EXISTS idx_downloads_file_size ON downloads(file_size);
CREATE INDEX IF NOT EXISTS idx_downloads_completed_at ON downloads(completed_at);
"""


# ---------------------------------------------------------------------------
# Database class
# ---------------------------------------------------------------------------

class Database:
    """
    Enterprise SQLite database manager with WAL mode, connection pooling,
    thread-safe access, full CRUD, advanced search, statistics,
    export, caching, migration, and backup/restore.

    Usage:
        db = Database("downloads.db")
        db.initialize()
        db.insert_download(task_id="abc", url="https://example.com", ...)
        results = db.search_downloads(status="completed")
        stats = db.get_aggregate_stats()
    """

    def __init__(
        self,
        db_path: Union[str, Path] = "rs_downloader.db",
        wal_mode: bool = True,
        busy_timeout: int = 30000,
        journal_mode: str = "WAL",
        synchronous: str = "NORMAL",
        cache_size: int = -64000,
        pool_size: int = 5,
    ) -> None:
        self.db_path = Path(db_path)
        self.wal_mode = wal_mode
        self.busy_timeout = busy_timeout
        self.journal_mode = journal_mode
        self.synchronous = synchronous
        self.cache_size = cache_size
        self.pool_size = pool_size
        self._local = threading.local()
        self._lock = threading.Lock()
        self._initialized = False

    def _get_connection(self) -> sqlite3.Connection:
        """Get a thread-local database connection."""
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self.db_path),
                timeout=self.busy_timeout / 1000.0,
                check_same_thread=False,
            )
            conn.row_factory = sqlite3.Row
            conn.execute(f"PRAGMA journal_mode={self.journal_mode}")
            conn.execute(f"PRAGMA synchronous={self.synchronous}")
            conn.execute(f"PRAGMA cache_size={self.cache_size}")
            conn.execute(f"PRAGMA busy_timeout={self.busy_timeout}")
            conn.execute("PRAGMA foreign_keys=ON")
            self._local.conn = conn
        return self._local.conn

    @contextmanager
    def _cursor(self) -> Generator[sqlite3.Cursor, None, None]:
        """Context manager for database cursor with automatic commit/rollback."""
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()

    def initialize(self) -> None:
        """Initialize the database schema."""
        if self._initialized:
            return
        with self._lock:
            with self._cursor() as cur:
                cur.executescript(CREATE_TABLES_SQL)
                cur.executescript(CREATE_INDEXES_SQL)
                # Set schema version
                cur.execute(
                    "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
                    ("schema_version", str(SCHEMA_VERSION)),
                )
            self._initialized = True
            logger.info("Database initialized: %s (schema v%d)", self.db_path, SCHEMA_VERSION)

    # -------------------------------------------------------------------
    # Downloads CRUD
    # -------------------------------------------------------------------

    def insert_download(
        self,
        task_id: str,
        url: str,
        filename: str = "",
        output_path: str = "",
        file_size: int = 0,
        status: str = "pending",
        platform: str = "",
        agent_name: str = "",
        quality: str = "",
        format: str = "",
        content_type: str = "",
        priority: int = 5,
        tags: str = "",
        source_url: str = "",
        download_method: str = "",
        checksum: str = "",
        checksum_algo: str = "sha256",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert a new download record. Returns the row ID."""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO downloads
                   (task_id, url, filename, output_path, file_size, status,
                    platform, agent_name, quality, format, content_type, priority,
                    tags, source_url, download_method, checksum, checksum_algo, metadata)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (task_id, url, filename, output_path, file_size, status,
                 platform, agent_name, quality, format, content_type, priority,
                 tags, source_url, download_method, checksum, checksum_algo,
                 json.dumps(metadata or {})),
            )
            row_id = cur.lastrowid or 0
            # Insert tags
            if tags:
                for tag in tags.split(","):
                    tag = tag.strip()
                    if tag:
                        cur.execute(
                            "INSERT OR IGNORE INTO tags (task_id, tag) VALUES (?, ?)",
                            (task_id, tag),
                        )
            return row_id

    def get_download(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a download by task_id."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM downloads WHERE task_id = ?", (task_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def get_download_by_id(self, row_id: int) -> Optional[Dict[str, Any]]:
        """Get a download by row ID."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM downloads WHERE id = ?", (row_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_download(self, task_id: str, **kwargs: Any) -> bool:
        """Update download fields by task_id."""
        if not kwargs:
            return False
        kwargs["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [task_id]
        with self._cursor() as cur:
            cur.execute(
                f"UPDATE downloads SET {set_clause} WHERE task_id = ?",
                values,
            )
            return cur.rowcount > 0

    def delete_download(self, task_id: str) -> bool:
        """Delete a download by task_id."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM tags WHERE task_id = ?", (task_id,))
            cur.execute("DELETE FROM downloads WHERE task_id = ?", (task_id,))
            return cur.rowcount > 0

    def list_downloads(
        self,
        limit: int = 100,
        offset: int = 0,
        order_by: str = "created_at DESC",
    ) -> List[Dict[str, Any]]:
        """List downloads with pagination."""
        with self._cursor() as cur:
            cur.execute(
                f"SELECT * FROM downloads ORDER BY {order_by} LIMIT ? OFFSET ?",
                (limit, offset),
            )
            return [dict(row) for row in cur.fetchall()]

    def count_downloads(self, status: Optional[str] = None) -> int:
        """Count downloads, optionally filtered by status."""
        with self._cursor() as cur:
            if status:
                cur.execute("SELECT COUNT(*) FROM downloads WHERE status = ?", (status,))
            else:
                cur.execute("SELECT COUNT(*) FROM downloads")
            return cur.fetchone()[0]

    # -------------------------------------------------------------------
    # Advanced Search
    # -------------------------------------------------------------------

    def search_downloads(
        self,
        status: Optional[str] = None,
        platform: Optional[str] = None,
        agent: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        min_size: Optional[int] = None,
        max_size: Optional[int] = None,
        query: Optional[str] = None,
        tag: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Advanced download search with multiple filter criteria.

        Args:
            status: Filter by status.
            platform: Filter by platform.
            agent: Filter by agent name.
            date_from: Filter by start date (ISO format).
            date_to: Filter by end date (ISO format).
            min_size: Minimum file size in bytes.
            max_size: Maximum file size in bytes.
            query: Search in filename and URL.
            tag: Filter by tag.
            limit: Result limit.
            offset: Result offset.

        Returns:
            List of matching download records.
        """
        conditions: List[str] = []
        params: List[Any] = []

        if status:
            conditions.append("d.status = ?")
            params.append(status)
        if platform:
            conditions.append("d.platform = ?")
            params.append(platform)
        if agent:
            conditions.append("d.agent_name = ?")
            params.append(agent)
        if date_from:
            conditions.append("d.created_at >= ?")
            params.append(date_from)
        if date_to:
            conditions.append("d.created_at <= ?")
            params.append(date_to)
        if min_size is not None:
            conditions.append("d.file_size >= ?")
            params.append(min_size)
        if max_size is not None:
            conditions.append("d.file_size <= ?")
            params.append(max_size)
        if query:
            conditions.append("(d.filename LIKE ? OR d.url LIKE ?)")
            params.extend([f"%{query}%", f"%{query}%"])
        if tag:
            conditions.append("d.task_id IN (SELECT task_id FROM tags WHERE tag = ?)")
            params.append(tag)

        where = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])

        with self._cursor() as cur:
            cur.execute(
                f"SELECT d.* FROM downloads d WHERE {where} "
                f"ORDER BY d.created_at DESC LIMIT ? OFFSET ?",
                params,
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Agent Runs CRUD
    # -------------------------------------------------------------------

    def insert_agent_run(
        self,
        agent_name: str,
        task_id: str = "",
        status: str = "running",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert an agent run record."""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO agent_runs (agent_name, task_id, status, metadata)
                   VALUES (?, ?, ?, ?)""",
                (agent_name, task_id, status, json.dumps(metadata or {})),
            )
            return cur.lastrowid or 0

    def update_agent_run(self, run_id: int, **kwargs: Any) -> bool:
        """Update an agent run record."""
        if not kwargs:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [run_id]
        with self._cursor() as cur:
            cur.execute(f"UPDATE agent_runs SET {set_clause} WHERE id = ?", values)
            return cur.rowcount > 0

    def get_agent_run(self, run_id: int) -> Optional[Dict[str, Any]]:
        """Get an agent run by ID."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM agent_runs WHERE id = ?", (run_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def list_agent_runs(
        self,
        agent_name: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """List agent runs with optional filters."""
        conditions: List[str] = []
        params: List[Any] = []
        if agent_name:
            conditions.append("agent_name = ?")
            params.append(agent_name)
        if status:
            conditions.append("status = ?")
            params.append(status)
        where = " AND ".join(conditions) if conditions else "1=1"
        params.extend([limit, offset])
        with self._cursor() as cur:
            cur.execute(
                f"SELECT * FROM agent_runs WHERE {where} ORDER BY started_at DESC LIMIT ? OFFSET ?",
                params,
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Schedules CRUD
    # -------------------------------------------------------------------

    def insert_schedule(
        self,
        name: str,
        cron_expr: str,
        url: str,
        agent_hint: str = "",
        platform_hint: str = "",
        enabled: bool = True,
    ) -> int:
        """Insert a schedule record."""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO schedules (name, cron_expr, url, agent_hint, platform_hint, enabled)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (name, cron_expr, url, agent_hint, platform_hint, 1 if enabled else 0),
            )
            return cur.lastrowid or 0

    def get_schedule(self, schedule_id: int) -> Optional[Dict[str, Any]]:
        """Get a schedule by ID."""
        with self._cursor() as cur:
            cur.execute("SELECT * FROM schedules WHERE id = ?", (schedule_id,))
            row = cur.fetchone()
            return dict(row) if row else None

    def update_schedule(self, schedule_id: int, **kwargs: Any) -> bool:
        """Update a schedule."""
        kwargs["updated_at"] = datetime.now(tz=timezone.utc).isoformat()
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [schedule_id]
        with self._cursor() as cur:
            cur.execute(f"UPDATE schedules SET {set_clause} WHERE id = ?", values)
            return cur.rowcount > 0

    def delete_schedule(self, schedule_id: int) -> bool:
        """Delete a schedule."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM schedules WHERE id = ?", (schedule_id,))
            return cur.rowcount > 0

    def list_schedules(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """List all schedules."""
        with self._cursor() as cur:
            if enabled_only:
                cur.execute("SELECT * FROM schedules WHERE enabled = 1 ORDER BY name")
            else:
                cur.execute("SELECT * FROM schedules ORDER BY name")
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Proxies CRUD
    # -------------------------------------------------------------------

    def insert_proxy(
        self,
        url: str,
        protocol: str = "http",
        username: str = "",
        password: str = "",
        weight: float = 1.0,
        country: str = "",
    ) -> int:
        """Insert a proxy record."""
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR IGNORE INTO proxies
                   (url, protocol, username, password, weight, country)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (url, protocol, username, password, weight, country),
            )
            return cur.lastrowid or 0

    def update_proxy(self, proxy_url: str, **kwargs: Any) -> bool:
        """Update a proxy by URL."""
        if not kwargs:
            return False
        set_clause = ", ".join(f"{k} = ?" for k in kwargs)
        values = list(kwargs.values()) + [proxy_url]
        with self._cursor() as cur:
            cur.execute(f"UPDATE proxies SET {set_clause} WHERE url = ?", values)
            return cur.rowcount > 0

    def delete_proxy(self, proxy_url: str) -> bool:
        """Delete a proxy by URL."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM proxies WHERE url = ?", (proxy_url,))
            return cur.rowcount > 0

    def list_proxies(self, alive_only: bool = False) -> List[Dict[str, Any]]:
        """List all proxies."""
        with self._cursor() as cur:
            if alive_only:
                cur.execute("SELECT * FROM proxies WHERE is_alive = 1 ORDER BY latency_ms")
            else:
                cur.execute("SELECT * FROM proxies ORDER BY url")
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Cache CRUD (with TTL and LRU)
    # -------------------------------------------------------------------

    def cache_set(
        self,
        key: str,
        value: str,
        ttl_seconds: float = 3600.0,
        content_type: str = "",
    ) -> None:
        """Set a cache entry with TTL."""
        expires_at = (
            datetime.now(tz=timezone.utc) + timedelta(seconds=ttl_seconds)
        ).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """INSERT OR REPLACE INTO cache_entries
                   (key, value, content_type, expires_at, size_bytes, access_count, last_accessed)
                   VALUES (?, ?, ?, ?, ?, 0, datetime('now'))""",
                (key, value, content_type, expires_at, len(value.encode("utf-8"))),
            )

    def cache_get(self, key: str) -> Optional[str]:
        """Get a cache entry by key. Returns None if expired or missing."""
        with self._cursor() as cur:
            cur.execute(
                "SELECT value, expires_at FROM cache_entries WHERE key = ?",
                (key,),
            )
            row = cur.fetchone()
            if not row:
                return None
            # Check expiration
            expires_at = row["expires_at"]
            if expires_at:
                try:
                    exp_dt = datetime.fromisoformat(expires_at)
                    if exp_dt.tzinfo is None:
                        exp_dt = exp_dt.replace(tzinfo=timezone.utc)
                    if datetime.now(tz=timezone.utc) > exp_dt:
                        cur.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
                        return None
                except (ValueError, TypeError):
                    pass
            # Update access stats
            cur.execute(
                "UPDATE cache_entries SET access_count = access_count + 1, last_accessed = datetime('now') WHERE key = ?",
                (key,),
            )
            return row["value"]

    def cache_delete(self, key: str) -> bool:
        """Delete a cache entry."""
        with self._cursor() as cur:
            cur.execute("DELETE FROM cache_entries WHERE key = ?", (key,))
            return cur.rowcount > 0

    def cache_clear(self) -> int:
        """Clear all cache entries. Returns count deleted."""
        with self._cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM cache_entries")
            count = cur.fetchone()[0]
            cur.execute("DELETE FROM cache_entries")
            return count

    def cache_cleanup(self) -> int:
        """Remove expired cache entries. Returns count removed."""
        now = datetime.now(tz=timezone.utc).isoformat()
        with self._cursor() as cur:
            cur.execute("DELETE FROM cache_entries WHERE expires_at < ?", (now,))
            return cur.rowcount

    def cache_lru_evict(self, max_size_mb: float = 500.0) -> int:
        """Evict LRU cache entries if total size exceeds max_size_mb."""
        max_bytes = int(max_size_mb * 1024 * 1024)
        with self._cursor() as cur:
            cur.execute("SELECT COALESCE(SUM(size_bytes), 0) FROM cache_entries")
            total_size = cur.fetchone()[0]
            if total_size <= max_bytes:
                return 0
            evicted = 0
            cur.execute(
                "SELECT key, size_bytes FROM cache_entries ORDER BY last_accessed ASC"
            )
            for row in cur.fetchall():
                if total_size <= max_bytes:
                    break
                cur2 = self._get_connection().cursor()
                cur2.execute("DELETE FROM cache_entries WHERE key = ?", (row["key"],))
                cur2.close()
                total_size -= row["size_bytes"]
                evicted += 1
            self._get_connection().commit()
            return evicted

    # -------------------------------------------------------------------
    # Config History
    # -------------------------------------------------------------------

    def record_config_change(
        self,
        section: str,
        key: str,
        old_value: str,
        new_value: str,
        changed_by: str = "system",
    ) -> int:
        """Record a configuration change in the audit trail."""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO config_history (section, key, old_value, new_value, changed_by)
                   VALUES (?, ?, ?, ?, ?)""",
                (section, key, old_value, new_value, changed_by),
            )
            return cur.lastrowid or 0

    def get_config_history(
        self,
        section: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get configuration change history."""
        with self._cursor() as cur:
            if section:
                cur.execute(
                    "SELECT * FROM config_history WHERE section = ? ORDER BY changed_at DESC LIMIT ?",
                    (section, limit),
                )
            else:
                cur.execute(
                    "SELECT * FROM config_history ORDER BY changed_at DESC LIMIT ?",
                    (limit,),
                )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Metrics CRUD
    # -------------------------------------------------------------------

    def record_metric(
        self,
        metric_name: str,
        metric_value: float,
        labels: Optional[Dict[str, str]] = None,
        source: str = "",
    ) -> int:
        """Record a metric data point."""
        with self._cursor() as cur:
            cur.execute(
                """INSERT INTO metrics (metric_name, metric_value, labels, source)
                   VALUES (?, ?, ?, ?)""",
                (metric_name, metric_value, json.dumps(labels or {}), source),
            )
            return cur.lastrowid or 0

    def get_metrics(
        self,
        metric_name: str,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Get metric data points by name and time range."""
        conditions = ["metric_name = ?"]
        params: List[Any] = [metric_name]
        if start_time:
            conditions.append("timestamp >= ?")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= ?")
            params.append(end_time)
        where = " AND ".join(conditions)
        params.append(limit)
        with self._cursor() as cur:
            cur.execute(
                f"SELECT * FROM metrics WHERE {where} ORDER BY timestamp DESC LIMIT ?",
                params,
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Tags CRUD
    # -------------------------------------------------------------------

    def add_tag(self, task_id: str, tag: str) -> bool:
        """Add a tag to a download."""
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR IGNORE INTO tags (task_id, tag) VALUES (?, ?)",
                (task_id, tag),
            )
            return cur.rowcount > 0

    def remove_tag(self, task_id: str, tag: str) -> bool:
        """Remove a tag from a download."""
        with self._cursor() as cur:
            cur.execute(
                "DELETE FROM tags WHERE task_id = ? AND tag = ?",
                (task_id, tag),
            )
            return cur.rowcount > 0

    def get_tags(self, task_id: str) -> List[str]:
        """Get all tags for a download."""
        with self._cursor() as cur:
            cur.execute("SELECT tag FROM tags WHERE task_id = ?", (task_id,))
            return [row["tag"] for row in cur.fetchall()]

    def get_downloads_by_tag(self, tag: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Get all downloads with a specific tag."""
        with self._cursor() as cur:
            cur.execute(
                """SELECT d.* FROM downloads d
                   JOIN tags t ON d.task_id = t.task_id
                   WHERE t.tag = ?
                   ORDER BY d.created_at DESC LIMIT ?""",
                (tag, limit),
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Statistics
    # -------------------------------------------------------------------

    def get_aggregate_stats(self) -> Dict[str, Any]:
        """Get aggregate download statistics."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT
                    COUNT(*) as total_downloads,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status = 'downloading' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status = 'pending' OR status = 'queued' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'paused' THEN 1 ELSE 0 END) as paused,
                    COALESCE(SUM(file_size), 0) as total_bytes,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN file_size ELSE 0 END), 0) as completed_bytes,
                    COALESCE(AVG(CASE WHEN status = 'completed' THEN average_speed END), 0) as avg_speed
                FROM downloads
            """)
            row = cur.fetchone()
            if row:
                total = row["total_downloads"]
                completed = row["completed"]
                return {
                    "total_downloads": total,
                    "completed": completed,
                    "failed": row["failed"],
                    "active": row["active"],
                    "pending": row["pending"],
                    "paused": row["paused"],
                    "total_bytes": row["total_bytes"],
                    "completed_bytes": row["completed_bytes"],
                    "success_rate": round(completed / total * 100, 2) if total > 0 else 0.0,
                    "average_speed": round(row["avg_speed"], 2),
                }
            return {}

    def get_speed_stats(self) -> Dict[str, float]:
        """Get speed statistics for completed downloads."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT
                    AVG(average_speed) as avg_speed,
                    MIN(average_speed) as min_speed,
                    MAX(average_speed) as max_speed,
                    AVG(elapsed) as avg_elapsed
                FROM downloads
                WHERE status = 'completed' AND average_speed > 0
            """)
            row = cur.fetchone()
            if row and row["avg_speed"] is not None:
                return {
                    "avg_speed_kbps": round(row["avg_speed"] / 1024, 2),
                    "min_speed_kbps": round(row["min_speed"] / 1024, 2),
                    "max_speed_kbps": round(row["max_speed"] / 1024, 2),
                    "avg_elapsed_seconds": round(row["avg_elapsed"], 2),
                }
            return {"avg_speed_kbps": 0.0, "min_speed_kbps": 0.0, "max_speed_kbps": 0.0, "avg_elapsed_seconds": 0.0}

    def get_hourly_distribution(self, days: int = 30) -> Dict[int, int]:
        """Get download count by hour of day."""
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """SELECT CAST(strftime('%H', created_at) AS INTEGER) as hour, COUNT(*) as count
                   FROM downloads
                   WHERE created_at >= ?
                   GROUP BY hour
                   ORDER BY hour""",
                (cutoff,),
            )
            result = {row["hour"]: row["count"] for row in cur.fetchall()}
            # Fill all 24 hours
            return {h: result.get(h, 0) for h in range(24)}

    def get_agent_stats(self) -> List[Dict[str, Any]]:
        """Get statistics grouped by agent."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT
                    agent_name,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                    AVG(CASE WHEN status = 'completed' THEN average_speed END) as avg_speed,
                    AVG(CASE WHEN status = 'completed' THEN elapsed END) as avg_elapsed
                FROM downloads
                WHERE agent_name != ''
                GROUP BY agent_name
                ORDER BY total DESC
            """)
            return [
                {
                    "agent_name": row["agent_name"],
                    "total": row["total"],
                    "completed": row["completed"],
                    "failed": row["failed"],
                    "success_rate": round(row["completed"] / row["total"] * 100, 2) if row["total"] > 0 else 0.0,
                    "avg_speed": round(row["avg_speed"] or 0, 2),
                    "avg_elapsed": round(row["avg_elapsed"] or 0, 2),
                }
                for row in cur.fetchall()
            ]

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get disk usage statistics."""
        with self._cursor() as cur:
            cur.execute("""
                SELECT
                    COALESCE(SUM(file_size), 0) as total_size,
                    COALESCE(SUM(CASE WHEN status = 'completed' THEN file_size ELSE 0 END), 0) as completed_size,
                    COUNT(*) as total_files,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_files
                FROM downloads
                WHERE file_size > 0
            """)
            row = cur.fetchone()
            if row:
                return {
                    "total_size_bytes": row["total_size"],
                    "total_size_mb": round(row["total_size"] / (1024 * 1024), 2),
                    "completed_size_bytes": row["completed_size"],
                    "completed_size_mb": round(row["completed_size"] / (1024 * 1024), 2),
                    "total_files": row["total_files"],
                    "completed_files": row["completed_files"],
                }
            return {}

    def get_success_rates(self, days: int = 30) -> Dict[str, float]:
        """Get success rates for different time periods."""
        rates: Dict[str, float] = {}
        periods = {"daily": 1, "weekly": 7, "monthly": 30}
        for name, d in periods.items():
            cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=d)).isoformat()
            with self._cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) as total, SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as ok FROM downloads WHERE created_at >= ?",
                    (cutoff,),
                )
                row = cur.fetchone()
                if row and row["total"] > 0:
                    rates[name] = round(row["ok"] / row["total"] * 100, 2)
                else:
                    rates[name] = 0.0
        return rates

    def get_daily_trend(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get daily download counts."""
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """SELECT DATE(created_at) as date, COUNT(*) as count,
                          SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
                          SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
                   FROM downloads
                   WHERE created_at >= ?
                   GROUP BY DATE(created_at)
                   ORDER BY date""",
                (cutoff,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_weekly_trend(self, weeks: int = 12) -> List[Dict[str, Any]]:
        """Get weekly download counts."""
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(weeks=weeks)).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """SELECT strftime('%Y-W%W', created_at) as week, COUNT(*) as count,
                          SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
                   FROM downloads
                   WHERE created_at >= ?
                   GROUP BY week
                   ORDER BY week""",
                (cutoff,),
            )
            return [dict(row) for row in cur.fetchall()]

    def get_monthly_trend(self, months: int = 12) -> List[Dict[str, Any]]:
        """Get monthly download counts."""
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=months * 30)).isoformat()
        with self._cursor() as cur:
            cur.execute(
                """SELECT strftime('%Y-%m', created_at) as month, COUNT(*) as count,
                          SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed
                   FROM downloads
                   WHERE created_at >= ?
                   GROUP BY month
                   ORDER BY month""",
                (cutoff,),
            )
            return [dict(row) for row in cur.fetchall()]

    # -------------------------------------------------------------------
    # Export
    # -------------------------------------------------------------------

    def export_csv(
        self,
        output_path: Union[str, Path],
        status: Optional[str] = None,
        include_headers: bool = True,
    ) -> int:
        """Export downloads to CSV file. Returns count of exported rows."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        downloads = self.search_downloads(status=status, limit=100000)
        if not downloads:
            return 0
        fieldnames = list(downloads[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            if include_headers:
                writer.writeheader()
            writer.writerows(downloads)
        return len(downloads)

    def export_json(
        self,
        output_path: Union[str, Path],
        status: Optional[str] = None,
        indent: int = 2,
    ) -> int:
        """Export downloads to JSON file. Returns count of exported rows."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        downloads = self.search_downloads(status=status, limit=100000)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump({"downloads": downloads, "exported_at": datetime.now(tz=timezone.utc).isoformat()}, f, indent=indent, default=str)
        return len(downloads)

    def export_html(
        self,
        output_path: Union[str, Path],
        status: Optional[str] = None,
        title: str = "RS Downloader - Download History",
    ) -> int:
        """Export downloads to HTML file. Returns count of exported rows."""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        downloads = self.search_downloads(status=status, limit=10000)
        if not downloads:
            return 0
        html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body {{ font-family: -apple-system, sans-serif; margin: 20px; background: #1a1a2e; color: #eee; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ padding: 8px 12px; border: 1px solid #333; text-align: left; }}
th {{ background: #16213e; }}
tr:nth-child(even) {{ background: #1a1a2e; }}
tr:nth-child(odd) {{ background: #0f3460; }}
.status-completed {{ color: #4ecca3; }}
.status-failed {{ color: #e74c3c; }}
.status-downloading {{ color: #f39c12; }}
</style></head><body><h1>{title}</h1><table>
<thead><tr><th>ID</th><th>Task</th><th>Filename</th><th>Status</th><th>Size</th><th>Speed</th><th>Platform</th><th>Agent</th><th>Created</th></tr></thead><tbody>"""
        for d in downloads:
            size_mb = d.get("file_size", 0) / (1024 * 1024)
            speed_kbps = d.get("average_speed", 0) / 1024
            status_class = f"status-{d.get('status', '')}"
            html += (
                f"<tr><td>{d.get('id', '')}</td>"
                f"<td>{d.get('task_id', '')[:8]}</td>"
                f"<td>{d.get('filename', '')}</td>"
                f"<td class='{status_class}'>{d.get('status', '')}</td>"
                f"<td>{size_mb:.2f} MB</td>"
                f"<td>{speed_kbps:.1f} KB/s</td>"
                f"<td>{d.get('platform', '')}</td>"
                f"<td>{d.get('agent_name', '')}</td>"
                f"<td>{d.get('created_at', '')}</td></tr>"
            )
        html += "</tbody></table></body></html>"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html)
        return len(downloads)

    # -------------------------------------------------------------------
    # Migration
    # -------------------------------------------------------------------

    def migrate(self, from_version: int) -> None:
        """
        Migrate the database schema from an older version.

        Supports: v5 → v6 → v7 → v8 → v9 → v10
        """
        current = from_version
        while current < SCHEMA_VERSION:
            logger.info("Migrating database from v%d to v%d", current, current + 1)
            migration_method = getattr(self, f"_migrate_{current}_to_{current + 1}", None)
            if migration_method:
                migration_method()
            else:
                logger.warning("No migration path from v%d to v%d", current, current + 1)
            current += 1
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO _meta (key, value) VALUES (?, ?)",
                ("schema_version", str(SCHEMA_VERSION)),
            )
        logger.info("Database migration complete: v%d → v%d", from_version, SCHEMA_VERSION)

    def _migrate_5_to_6(self) -> None:
        """Migrate from v5 to v6: Add tags table."""
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    tag TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now')),
                    UNIQUE(task_id, tag)
                );
                CREATE INDEX IF NOT EXISTS idx_tags_task_id ON tags(task_id);
                CREATE INDEX IF NOT EXISTS idx_tags_tag ON tags(tag);
            """)

    def _migrate_6_to_7(self) -> None:
        """Migrate from v6 to v7: Add schedules table."""
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS schedules (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    cron_expr TEXT NOT NULL,
                    url TEXT NOT NULL,
                    agent_hint TEXT DEFAULT '',
                    platform_hint TEXT DEFAULT '',
                    enabled INTEGER DEFAULT 1,
                    last_run TEXT,
                    next_run TEXT,
                    run_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT DEFAULT '',
                    created_at TEXT DEFAULT (datetime('now')),
                    updated_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def _migrate_7_to_8(self) -> None:
        """Migrate from v7 to v8: Add config_history and proxies."""
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS config_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    section TEXT NOT NULL,
                    key TEXT NOT NULL,
                    old_value TEXT DEFAULT '',
                    new_value TEXT DEFAULT '',
                    changed_by TEXT DEFAULT 'system',
                    changed_at TEXT DEFAULT (datetime('now'))
                );
                CREATE TABLE IF NOT EXISTS proxies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT UNIQUE NOT NULL,
                    protocol TEXT DEFAULT 'http',
                    username TEXT DEFAULT '',
                    password TEXT DEFAULT '',
                    weight REAL DEFAULT 1.0,
                    country TEXT DEFAULT '',
                    is_alive INTEGER DEFAULT 1,
                    latency_ms REAL DEFAULT 0.0,
                    failure_count INTEGER DEFAULT 0,
                    success_count INTEGER DEFAULT 0,
                    last_check TEXT,
                    last_used TEXT,
                    created_at TEXT DEFAULT (datetime('now'))
                );
            """)

    def _migrate_8_to_9(self) -> None:
        """Migrate from v8 to v9: Add metrics table and new columns."""
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT NOT NULL,
                    metric_value REAL NOT NULL,
                    labels TEXT DEFAULT '{}',
                    timestamp TEXT DEFAULT (datetime('now')),
                    source TEXT DEFAULT ''
                );
                CREATE INDEX IF NOT EXISTS idx_metrics_name ON metrics(metric_name);
                CREATE INDEX IF NOT EXISTS idx_metrics_timestamp ON metrics(timestamp);
            """)
            # Add new columns to downloads if they don't exist
            try:
                cur.execute("ALTER TABLE downloads ADD COLUMN thumbnail_url TEXT DEFAULT ''")
            except sqlite3.OperationalError:
                pass
            try:
                cur.execute("ALTER TABLE downloads ADD COLUMN duration REAL DEFAULT 0.0")
            except sqlite3.OperationalError:
                pass

    def _migrate_9_to_10(self) -> None:
        """Migrate from v9 to v10: Add agent_runs, cache_entries, new indexes."""
        with self._cursor() as cur:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS agent_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    agent_name TEXT NOT NULL,
                    task_id TEXT,
                    status TEXT NOT NULL DEFAULT 'running',
                    started_at TEXT DEFAULT (datetime('now')),
                    completed_at TEXT,
                    duration REAL DEFAULT 0.0,
                    error TEXT DEFAULT '',
                    result TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}'
                );
                CREATE TABLE IF NOT EXISTS cache_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    key TEXT UNIQUE NOT NULL,
                    value TEXT NOT NULL,
                    content_type TEXT DEFAULT '',
                    compressed INTEGER DEFAULT 0,
                    created_at TEXT DEFAULT (datetime('now')),
                    expires_at TEXT,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TEXT DEFAULT (datetime('now')),
                    size_bytes INTEGER DEFAULT 0
                );
                CREATE INDEX IF NOT EXISTS idx_agent_runs_name ON agent_runs(agent_name);
                CREATE INDEX IF NOT EXISTS idx_agent_runs_status ON agent_runs(status);
                CREATE INDEX IF NOT EXISTS idx_cache_key ON cache_entries(key);
                CREATE INDEX IF NOT EXISTS idx_cache_expires ON cache_entries(expires_at);
            """)
            # Add new columns
            for col, coltype in [("download_method", "TEXT DEFAULT ''"), ("metadata", "TEXT DEFAULT '{}'")]:
                try:
                    cur.execute(f"ALTER TABLE downloads ADD COLUMN {col} {coltype}")
                except sqlite3.OperationalError:
                    pass

    def get_schema_version(self) -> int:
        """Get the current schema version from _meta table."""
        try:
            with self._cursor() as cur:
                cur.execute("SELECT value FROM _meta WHERE key = 'schema_version'")
                row = cur.fetchone()
                return int(row["value"]) if row else 0
        except sqlite3.OperationalError:
            return 0

    # -------------------------------------------------------------------
    # Backup / Restore
    # -------------------------------------------------------------------

    def backup(
        self,
        backup_path: Union[str, Path],
        compress: bool = True,
    ) -> Path:
        """
        Create a full database backup.

        Args:
            backup_path: Path for the backup file.
            compress: Whether to gzip compress the backup.

        Returns:
            Path to the created backup file.
        """
        backup_path = Path(backup_path)
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        if compress and not backup_path.suffix.endswith(".gz"):
            backup_path = backup_path.with_suffix(backup_path.suffix + ".gz")

        # Use SQLite backup API for consistent snapshot
        conn = self._get_connection()
        if compress:
            with gzip.open(backup_path, "wb") as gz_f:
                temp_path = backup_path.with_suffix(".tmp")
                backup_conn = sqlite3.connect(str(temp_path))
                conn.backup(backup_conn)
                backup_conn.close()
                with open(temp_path, "rb") as f:
                    gz_f.write(f.read())
                temp_path.unlink()
        else:
            backup_conn = sqlite3.connect(str(backup_path))
            conn.backup(backup_conn)
            backup_conn.close()

        logger.info("Database backup created: %s", backup_path)
        return backup_path

    def restore(
        self,
        backup_path: Union[str, Path],
        verify: bool = True,
    ) -> bool:
        """
        Restore database from a backup file.

        Args:
            backup_path: Path to the backup file.
            verify: Whether to verify backup integrity before restoring.

        Returns:
            True if restore was successful.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            logger.error("Backup file not found: %s", backup_path)
            return False

        try:
            # Decompress if needed
            temp_db = backup_path.with_suffix(".restore.tmp")
            if backup_path.suffix == ".gz":
                with gzip.open(backup_path, "rb") as gz_f:
                    with open(temp_db, "wb") as f:
                        f.write(gz_f.read())
            else:
                shutil.copy2(backup_path, temp_db)

            # Verify the backup is a valid SQLite database
            if verify:
                try:
                    test_conn = sqlite3.connect(str(temp_db))
                    test_conn.execute("SELECT COUNT(*) FROM sqlite_master")
                    test_conn.execute("PRAGMA integrity_check")
                    test_conn.close()
                except sqlite3.OperationalError as e:
                    logger.error("Backup integrity check failed: %s", e)
                    temp_db.unlink(missing_ok=True)
                    return False

            # Close current connection and replace
            if hasattr(self._local, "conn") and self._local.conn:
                self._local.conn.close()
                self._local.conn = None

            shutil.move(str(temp_db), str(self.db_path))
            self._initialized = False
            self.initialize()
            logger.info("Database restored from: %s", backup_path)
            return True
        except Exception as e:
            logger.error("Database restore failed: %s", e)
            return False

    def incremental_backup(
        self,
        backup_dir: Union[str, Path],
        max_backups: int = 10,
    ) -> Path:
        """
        Create an incremental backup (full copy with timestamp).

        Args:
            backup_dir: Directory for backup files.
            max_backups: Maximum number of backups to keep.

        Returns:
            Path to the created backup.
        """
        backup_dir = Path(backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"rs_downloader_{timestamp}.db.gz"

        result = self.backup(backup_file, compress=True)

        # Cleanup old backups
        backups = sorted(backup_dir.glob("rs_downloader_*.db.gz"), reverse=True)
        for old in backups[max_backups:]:
            try:
                old.unlink()
            except OSError:
                pass

        return result

    # -------------------------------------------------------------------
    # Meta table operations
    # -------------------------------------------------------------------

    def set_meta(self, key: str, value: str) -> None:
        """Set a meta key-value pair."""
        with self._cursor() as cur:
            cur.execute(
                "INSERT OR REPLACE INTO _meta (key, value, updated_at) VALUES (?, ?, datetime('now'))",
                (key, value),
            )

    def get_meta(self, key: str, default: str = "") -> str:
        """Get a meta value by key."""
        with self._cursor() as cur:
            cur.execute("SELECT value FROM _meta WHERE key = ?", (key,))
            row = cur.fetchone()
            return row["value"] if row else default

    # -------------------------------------------------------------------
    # Maintenance
    # -------------------------------------------------------------------

    def vacuum(self) -> None:
        """Run VACUUM to optimize database."""
        conn = self._get_connection()
        conn.execute("VACUUM")
        logger.info("Database vacuumed")

    def analyze(self) -> None:
        """Run ANALYZE to update query planner statistics."""
        conn = self._get_connection()
        conn.execute("ANALYZE")
        logger.info("Database analyzed")

    def integrity_check(self) -> bool:
        """Run integrity check on the database."""
        conn = self._get_connection()
        result = conn.execute("PRAGMA integrity_check").fetchone()
        is_ok = result[0] == "ok"
        if not is_ok:
            logger.error("Database integrity check failed: %s", result[0])
        return is_ok

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """Get column info for a table."""
        with self._cursor() as cur:
            cur.execute(f"PRAGMA table_info({table_name})")
            return [dict(row) for row in cur.fetchall()]

    def get_table_count(self, table_name: str) -> int:
        """Get row count for a table."""
        with self._cursor() as cur:
            cur.execute(f"SELECT COUNT(*) FROM {table_name}")
            return cur.fetchone()[0]

    def get_database_size(self) -> Dict[str, Any]:
        """Get database file size information."""
        try:
            size = self.db_path.stat().st_size
            return {
                "path": str(self.db_path),
                "size_bytes": size,
                "size_mb": round(size / (1024 * 1024), 2),
                "exists": True,
            }
        except OSError:
            return {"path": str(self.db_path), "size_bytes": 0, "size_mb": 0, "exists": False}

    def cleanup_old_records(self, days: int = 90) -> Dict[str, int]:
        """Clean up records older than specified days."""
        cutoff = (datetime.now(tz=timezone.utc) - timedelta(days=days)).isoformat()
        cleaned: Dict[str, int] = {}
        with self._cursor() as cur:
            cur.execute("DELETE FROM downloads WHERE status = 'completed' AND completed_at < ?", (cutoff,))
            cleaned["downloads"] = cur.rowcount
            cur.execute("DELETE FROM agent_runs WHERE completed_at < ?", (cutoff,))
            cleaned["agent_runs"] = cur.rowcount
            cur.execute("DELETE FROM metrics WHERE timestamp < ?", (cutoff,))
            cleaned["metrics"] = cur.rowcount
            cur.execute("DELETE FROM config_history WHERE changed_at < ?", (cutoff,))
            cleaned["config_history"] = cur.rowcount
        total = sum(cleaned.values())
        if total > 0:
            logger.info("Cleaned up %d old records (older than %d days)", total, days)
        return cleaned

    def close(self) -> None:
        """Close the database connection."""
        if hasattr(self._local, "conn") and self._local.conn:
            try:
                self._local.conn.close()
            except Exception:
                pass
            self._local.conn = None

    def __del__(self) -> None:
        self.close()
