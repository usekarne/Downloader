<p align="center">
<pre>
  ╔══════════════════════════════════════════════════════════════════════╗
  ║                                                                      ║
  ║     ██████╗ ███████╗███████╗██████╗  ██████╗ ███████╗               ║
  ║    ██╔════╝ ██╔════╝██╔════╝██╔══██╗██╔═══██╗██╔════╝               ║
  ║    ██║  ███╗█████╗  █████╗  ██████╔╝██║   ██║███████╗               ║
  ║    ██║   ██║██╔══╝  ██╔══╝  ██╔══██╗██║   ██║╚════██║               ║
  ║    ╚██████╔╝███████╗███████╗██║  ██║╚██████╔╝███████║               ║
  ║     ╚═════╝ ╚══════╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝               ║
  ║                                                                      ║
  ║   ██████╗ ██████╗  █████╗  ██████╗██╗  ██╗███████╗██████╗           ║
  ║   ██╔══██╗██╔══██╗██╔══██╗██╔════╝██║ ██╔╝██╔════╝██╔══██╗          ║
  ║   ██║  ██║██████╔╝███████║██║     █████╔╝ █████╗  ██║  ██║          ║
  ║   ██║  ██║██╔══██╗██╔══██║██║     ██╔═██╗ ██╔══╝  ██║  ██║          ║
  ║   ██████╔╝██║  ██║██║  ██║╚██████╗██║  ██╗███████╗██████╔╝          ║
  ║   ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝           ║
  ║                                                                      ║
  ╚══════════════════════════════════════════════════════════════════════╝
</pre>
</p>

<h1 align="center">RS DOWNLOADER</h1>

<p align="center">
  <strong>v10.0.0</strong> &mdash; <em>INFINITE HYPERNOVA SOVEREIGN NEXUS</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/version-10.0.0-cyan?style=for-the-badge&logo=semantic-release" alt="Version">
  <img src="https://img.shields.io/badge/license-MIT-green?style=for-the-badge" alt="License">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/platform-Linux%20%7C%20macOS%20%7C%20Windows-lightgrey?style=for-the-badge" alt="Platform">
  <a href="https://youtube.com/@T3rmuxk1ng"><img src="https://img.shields.io/badge/YouTube-T3rmuxk1ng-red?style=for-the-badge&logo=youtube&logoColor=white" alt="YouTube"></a>
</p>

<p align="center">
  The Ultimate Enterprise-Grade Download Toolkit by <a href="https://github.com/usekarne/Downloader"><strong>RAJSARASWATI JATAV (RS)</strong></a>
</p>

---

## Table of Contents

- [About](#about)
- [What's New in v10](#whats-new-in-v10)
- [Features](#features)
  - [90+ Download Agents](#90-download-agents)
  - [Core Engine](#core-engine)
  - [Network Layer](#network-layer)
  - [Database](#database)
  - [Configuration](#configuration)
  - [CLI](#cli)
  - [Security](#security)
  - [Cloud Storage](#cloud-storage)
  - [BitTorrent](#bittorrent)
  - [AI Features](#ai-features)
  - [Virtual Environment](#virtual-environment)
  - [Debian Packaging](#debian-packaging)
  - [Metrics & Monitoring](#metrics--monitoring)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration Reference](#configuration-reference)
- [Agent Reference](#agent-reference)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)
- [Credits](#credits)

---

## About

**RS Downloader** is an enterprise-grade, Python-powered download toolkit engineered for performance, reliability, and extensibility. Version 10.0.0 — codenamed **INFINITE HYPERNOVA SOVEREIGN NEXUS** — represents a ground-up rewrite from v9, delivering 90+ platform-specific download agents, a 9-table SQLite database with WAL mode, 25 frozen dataclass configuration sections, a 13-state download lifecycle, circuit breaker patterns, parallel multi-connection downloads, proxy rotation with 7 strategies, AI-powered categorization, live stream recording, BitTorrent support, cloud storage integration, and a beautiful terminal UI with gradient banners and 7 spinner styles.

### Key Highlights

| Category | Details |
|---|---|
| **Agents** | 90+ platform-specific download agents |
| **Database** | 9 tables, 22+ indexes, WAL mode, full CRUD, backup/restore |
| **Config** | 25 frozen dataclass sections, profiles, hot-reload, env export |
| **CLI** | 40+ commands with Rich formatting and tab completion |
| **Networking** | Sync + async HTTP, 7 proxy strategies, circuit breaker, DNS-over-HTTPS |
| **Speed Tracking** | Current, average, min, max, median, P95, P99 speed metrics |
| **Security** | 8 checksum algorithms (incl. XXH64), filename sanitization, domain blocking |
| **Platform Detection** | 17 URL detectors with confidence scoring |
| **Validation** | ValidationResult tuples with warnings for every input |
| **UI** | Gradient text, 5 banner styles, animated banners, 7 spinner styles, non-TTY progress |
| **Priority System** | 7 levels: CRITICAL, HIGH, NORMAL, LOW, BACKGROUND, STREAMING, REALTIME |
| **Lifecycle** | 13 states: PENDING → SCHEDULING → QUEUED → DOWNLOADING → VERIFYING → EXTRACTING → CONVERTING → UPLOADING → COMPLETED (and more) |
| **Debian** | Full .deb packaging with systemd service, postinst/prerm/postrm scripts |

---

## What's New in v10

RS Downloader v10.0.0 is a **major rewrite** from v9. Here's what changed:

| Feature | v9 | v10 |
|---|---|---|
| Download Agents | 88 | **90+** |
| Database Tables | 8 | **9** (new: `tags`) |
| Checksum Algorithms | 7 | **8** (new: `xxh64`) |
| Python Requirement | 3.8+ | **3.10+** |
| Priority Levels | 6 | **7** (new: `REALTIME`) |
| Download Statuses | 12 | **13** (new: `RETRYING`) |
| Speed Metrics | 4 (avg, min, max, current) | **7** (new: `median`, `P95`, `P99`) |
| Spinner Styles | 5 | **7** (new: `wave`, `braille`) |
| Platform URL Detectors | 15 | **17** (new: `is_magnet_url`, `is_live_stream_url`) |
| Validation Results | bool | **ValidationResult tuples** (valid, value, error, warnings) |
| Banner System | Static | **Animated banners + gradient text + 5 styles** |
| Non-TTY Progress | None | **PlainProgress for CI/CD and pipes** |
| Config Profiles | 3 | **4** (dev, staging, prod, testing) |
| Speed Test | None | **`rsdl speed-test` command** |
| Config Migration | v8 | **v5 → v6 → v7 → v8 → v9 → v10** full chain |

---

## Features

### 90+ Download Agents

Agents are organized by content category. Each agent handles platform-specific URL parsing, quality selection, metadata extraction, and download orchestration.

#### Video Platforms

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 1 | `youtube` | YouTube | Videos, Shorts, Live, Playlists, Channels, Embeds |
| 2 | `youtube_music` | YouTube Music | Tracks, Albums, Playlists |
| 3 | `vimeo` | Vimeo | Videos, Channels, On Demand |
| 4 | `vimeo_enterprise` | Vimeo Enterprise | Private/Enterprise videos |
| 5 | `dailymotion` | Dailymotion | Videos, Playlists |
| 6 | `twitch` | Twitch | VODs, Clips, Live streams |
| 7 | `tiktok` | TikTok | Videos, Profiles |
| 8 | `bilibili` | Bilibili | Videos, Bangumi, Live |
| 9 | `rumble` | Rumble | Videos, Channels |
| 10 | `bitchute` | BitChute | Videos |
| 11 | `odysee` | Odysee (LBRY) | Videos, Channels |
| 12 | `kick` | Kick | VODs, Clips, Live |
| 13 | `douyin` | Douyin (Chinese TikTok) | Videos |
| 14 | `niconico` | Niconico (ニコニコ) | Videos, Playlists |
| 15 | `periscope` | Periscope | Archived streams |
| 16 | `likee` | Likee | Videos |
| 17 | `loom` | Loom | Recorded videos |
| 18 | `wistia` | Wistia | Marketing videos |
| 19 | `stage` | Stage | Video content |
| 20 | `ok` | OK.ru | Videos |
| 21 | `kakao` | KakaoTV | Videos |
| 22 | `naver` | Naver | Videos, Clips |

#### Social Media

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 23 | `instagram` | Instagram | Posts, Reels, Stories, IGTV |
| 24 | `facebook` | Facebook | Videos, Posts, Watch |
| 25 | `twitter` | Twitter/X | Posts, Spaces, Live |
| 26 | `reddit` | Reddit | Posts, Videos, Images |
| 27 | `tumblr` | Tumblr | Posts, Images, Videos |
| 28 | `pinterest` | Pinterest | Pins, Boards |
| 29 | `snapchat` | Snapchat | Spotlight, Stories |
| 30 | `vk` | VK | Videos, Photos, Posts |
| 31 | `weibo` | Weibo (微博) | Posts, Videos |
| 32 | `discord` | Discord CDN | Attachments, Images, Files |

#### Audio & Music

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 33 | `spotify` | Spotify | Tracks, Albums, Playlists, Podcasts |
| 34 | `soundcloud` | SoundCloud | Tracks, Playlists, Sets |
| 35 | `bandcamp` | Bandcamp | Tracks, Albums |
| 36 | `deezer` | Deezer | Tracks, Albums, Playlists |
| 37 | `tidal` | Tidal | Tracks, Albums, Videos |
| 38 | `apple_music` | Apple Music | Tracks, Albums, Playlists |
| 39 | `amazon_music` | Amazon Music | Tracks, Albums |
| 40 | `mixcloud` | Mixcloud | Shows, Playlists |
| 41 | `reverbnation` | ReverbNation | Tracks |
| 42 | `soundclick` | SoundClick | Tracks |
| 43 | `audible` | Audible | Audiobooks |

#### Image & Art

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 44 | `unsplash` | Unsplash | Photos, Collections |
| 45 | `pexels` | Pexels | Photos, Videos |
| 46 | `flickr` | Flickr | Photos, Albums |
| 47 | `imgur` | Imgur | Images, Albums, GIFs |
| 48 | `giphy` | GIPHY | GIFs, Stickers |
| 49 | `tenor` | Tenor | GIFs |
| 50 | `deviantart` | DeviantArt | Art, Collections |
| 51 | `artstation` | ArtStation | Artwork, Projects |

#### Messaging & Communication

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 52 | `telegram` | Telegram | Files, Videos, Voice, Channels |
| 53 | `whatsapp` | WhatsApp | Status, Media |

#### Educational & Course

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 54 | `udemy` | Udemy | Course videos |
| 55 | `coursera` | Coursera | Course videos, Materials |
| 56 | `skillshare` | Skillshare | Class videos |
| 57 | `ted` | TED | Talks, Playlists |

#### Books & Literature

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 58 | `gutenberg` | Project Gutenberg | Ebooks |
| 59 | `librivox` | LibriVox | Audiobooks |
| 60 | `ebook` | Generic Ebook | EPUB, PDF, MOBI downloads |
| 61 | `archive_org` | Internet Archive | Books, Audio, Video, Software |

#### Podcasts

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 62 | `podcast` | Generic Podcast | RSS-based podcast downloads |

#### Creator & Subscription Platforms

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 63 | `onlyfans` | OnlyFans | Media, Posts |
| 64 | `patreon` | Patreon | Posts, Media |

#### Cloud & File Storage

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 65 | `google_drive` | Google Drive | Files, Folders |
| 66 | `dropbox` | Dropbox | Files, Folders |
| 67 | `onedrive` | OneDrive | Files, Folders |
| 68 | `mega` | MEGA | Files, Folders |
| 69 | `s3` | Amazon S3 | Objects, Buckets |
| 70 | `cloud` | Generic Cloud | S3-compatible storage |
| 71 | `webdav` | WebDAV | Files, Folders |

#### P2P & Decentralized

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 72 | `torrent` | BitTorrent | Torrent files, Magnet links |
| 73 | `ipfs` | IPFS | Content-addressed files |
| 74 | `tor` | Tor / Onion | .onion hidden services |

#### Utility & System Agents

| # | Agent | Category | Capabilities |
|---|---|---|---|
| 75 | `batch` | System | Batch URL file processing |
| 76 | `playlist` | System | Multi-video playlist handling |
| 77 | `live` | System | Live stream recording |
| 78 | `stream` | System | Generic stream capture |
| 79 | `convert` | System | Audio/video format conversion |
| 80 | `subtitle` | System | Subtitle download & embed |
| 81 | `thumbnail` | System | Thumbnail extraction |
| 82 | `metadata` | System | Metadata extraction & tagging |
| 83 | `proxy` | System | Proxy testing & management |
| 84 | `scheduler` | System | Cron-based download scheduling |
| 85 | `search` | System | Multi-platform content search |
| 86 | `ai` | System | AI-powered categorization & smart retry |
| 87 | `analytics` | System | Download analytics & reporting |
| 88 | `ebook` | System | Ebook format conversion |

#### Additional Platform Agents

| # | Agent | Platform | Capabilities |
|---|---|---|---|
| 89 | `kick` | Kick Streaming | Live, VODs, Clips |
| 90 | `stage` | Stage | Video platform |
| 91 | `loom` | Loom | Screen recordings |
| 92 | `wistia` | Wistia | Business video |
| 93 | `periscope` | Periscope | Live archives |

---

### Core Engine

The download engine is the heart of RS Downloader, implemented in `core/downloader_base.py`.

| Component | Description |
|---|---|
| `DownloadPriority` | 7-level IntEnum: CRITICAL(0), HIGH(1), NORMAL(5), LOW(10), BACKGROUND(20), STREAMING(15), REALTIME(0) |
| `DownloadStatus` | 13-state Enum: PENDING, SCHEDULING, QUEUED, DOWNLOADING, PAUSED, VERIFYING, EXTRACTING, CONVERTING, UPLOADING, COMPLETED, FAILED, CANCELLED, RETRYING |
| `DownloadResult` | Dataclass with 22 fields including speed_samples, metadata, timestamps |
| `DownloadTask` | Priority-ordered dataclass with heap-based scheduling, tags, checksum |
| `DownloadQueue` | Thread-safe priority queue with put, get, peek, drain, reorder, cancel_all |
| `DownloadSpeedTracker` | Window-based speed tracker: current, avg, min, max, median, P95, P99 |
| `DownloadScheduler` | Cron expression parser + background thread for recurring/one-off tasks |
| `DownloadLifecycle` | 13-state state machine with validated transitions and time-in-state metrics |
| `AgentSkill` | Skill capability enumeration for agent matching |
| `AgentRegistry` | Auto-discovery and registration of download agents |
| `EventEmitter` | Pub/sub event system for download lifecycle events |
| `CheckpointManager` | Download state persistence for resume across restarts |
| `ConcurrentManager` | ThreadPoolExecutor-based concurrent download orchestration |
| `BandwidthMonitor` | Real-time bandwidth monitoring with token-bucket rate limiting |
| `DownloadOrchestrator` | Top-level orchestrator connecting queue, agents, lifecycle, and persistence |
| `DownloaderBase` | Abstract base class for all download agents |

Custom Exceptions:
- `QueueFullError` / `QueueEmptyError` — Queue boundary conditions
- `LifecycleError` — Invalid state transitions
- `DownloadError` — General download failures
- `AgentNotFoundError` — No agent matches the URL
- `CheckpointCorruptedError` — Corrupted checkpoint data

---

### Network Layer

The networking layer (`core/network.py`) provides enterprise-grade HTTP capabilities.

| Component | Description |
|---|---|
| `ChecksumAlgorithm` | 8 algorithms: MD5, SHA1, SHA256, SHA512, CRC32, BLAKE2B, BLAKE2S, XXH64 |
| `HeadInfo` | Parsed HEAD response: content_type, content_length, filename, accept_ranges, etag |
| `DownloadSession` | Session config: URL, method, headers, cookies, proxy, timeout, resume_from |
| `verify_checksum()` | Stream-based checksum verification with large file support |
| `compute_checksum()` | Multi-algorithm checksum computation |
| `detect_content_length()` | HEAD + GET fallback content length detection |
| `download_chunk()` | Byte-range chunk download with retry and progress callback |
| `parallel_download()` | Multi-connection parallel download with chunk assembly and verification |
| `SyncHTTPClient` | Synchronous HTTP client: GET/POST/PUT/DELETE/HEAD/PATCH, streaming, multipart upload, proxy, DNS override, rate limiting |
| `AsyncHTTPClient` | Asynchronous HTTP client (aiohttp): all methods, streaming, concurrency semaphore |
| `ProxyRotationStrategy` | 7 strategies: SEQUENTIAL, RANDOM, ROUND_ROBIN, WEIGHTED_RANDOM, LATENCY_BASED, GEO_BASED, STICKY_SESSION |
| `ProxyPool` | Rotating proxy pool with health checking, auto-removal, latency measurement |
| `ProxyEntry` | Proxy metadata: URL, protocol, auth, weight, country, alive status, latency |
| `CircuitBreaker` | Circuit breaker pattern: CLOSED → OPEN → HALF_OPEN with recovery |
| `BandwidthThrottler` | Token-bucket bandwidth throttling per-download and global |
| `DNSOverHTTPS` | DNS-over-HTTPS resolver for censorship-resistant name resolution |
| `SSLContextBuilder` | Custom SSL context with cipher selection, pinning, and version control |
| `RequestInterceptor` | Pre/post request interceptor chain for logging, auth, headers |
| `ConnectionMetrics` | Request count, error count, latency tracking, throughput |

---

### Database

Enterprise SQLite database (`core/database.py`) with WAL mode, 9 tables, and 22+ indexes.

#### Tables

| # | Table | Purpose | Key Columns |
|---|---|---|---|
| 1 | `downloads` | Download records | task_id, url, filename, file_size, status, platform, agent_name, quality, checksum, priority, tags, metadata |
| 2 | `agent_runs` | Agent execution log | agent_name, task_id, status, duration, error, result, metadata |
| 3 | `schedules` | Cron schedules | name, cron_expr, url, agent_hint, enabled, last_run, next_run, run_count |
| 4 | `proxies` | Proxy pool | url, protocol, username, password, weight, country, is_alive, latency_ms |
| 5 | `cache_entries` | HTTP cache | key, value, content_type, compressed, expires_at, access_count, size_bytes |
| 6 | `config_history` | Config audit trail | section, key, old_value, new_value, changed_by, changed_at |
| 7 | `metrics` | Time-series metrics | metric_name, metric_value, labels, timestamp, source |
| 8 | `tags` | Download tags (NEW v10) | task_id, tag (UNIQUE composite) |
| 9 | `_meta` | Schema metadata | key, value, updated_at |

#### Features

- **WAL Mode** — Write-Ahead Logging for concurrent read/write
- **Thread-Safe** — Thread-local connections with RLock
- **Full CRUD** — Insert, Get, Update, Delete for all tables
- **Advanced Search** — Multi-criteria search: status, platform, agent, date range, size, query, tags
- **Statistics** — Aggregate stats, speed stats, hourly distribution, agent stats, disk usage, success rates, daily trends
- **Cache with TTL** — Set/Get with expiration, LRU eviction, cleanup
- **Config Audit** — Full change history tracking
- **Metrics Recording** — Time-series data with labels and source
- **Tag System** — Add/remove/query downloads by tags (NEW in v10)
- **Backup/Restore** — Gzip-compressed backup with timestamp
- **Export** — JSON and CSV export for all data
- **Migration** — Schema version tracking, v5→v6→v7→v8→v9→v10 chain
- **22+ Indexes** — Optimized queries on task_id, url, status, platform, agent, created_at, priority, filename, and more

---

### Configuration

25 frozen dataclass sections managed by a thread-safe singleton `ConfigManager` (`core/config.py`).

| # | Section | Dataclass | Key Fields |
|---|---|---|---|
| 1 | `timeout` | `TimeoutConfig` | connect, read, write, pool, dns, redirect, total, keep_alive, handshake |
| 2 | `retry` | `RetryConfig` | max_retries, backoff_factor, backoff_max, jitter, retry_on_status, circuit_breaker_threshold |
| 3 | `proxy` | `ProxyConfig` | enabled, rotation_strategy, proxy_list, auth, health_check, socks_enabled, geo_routing |
| 4 | `ssl` | `SSLConfig` | verify, cert_path, ca_bundle, min_version, max_version, cipher_list, pin_sha256, ocsp_check |
| 5 | `connection_pool` | `ConnectionPoolConfig` | pool_maxsize, max_connections, max_per_host, keep_alive, max_reuse_count |
| 6 | `rate_limit` | `RateLimitConfig` | enabled, requests_per_second, burst_size, per_host_limit, adaptive, backoff_on_429 |
| 7 | `user_agent` | `UserAgentConfig` | user_agent, rotation_enabled, agent_list, randomize_order, per_site_agent |
| 8 | `bandwidth` | `BandwidthConfig` | global_limit, per_download_limit, priority_allocation, schedule, peak/off_peak, token_bucket |
| 9 | `storage` | `StorageConfig` | download_dir, temp_dir, max_file_size, duplicate_handling, organize_by, cleanup, permissions |
| 10 | `security` | `SecurityConfig` | verify_checksums, checksum_algo, malware_scan, blocked_domains/extensions, enforce_https, sanitize |
| 11 | `logging` | `LoggingConfig` | level, log_dir, format, file/console, sensitive_filter, rotation, compress, remote, audit |
| 12 | `ui` | `UIConfig` | theme, progress_style, show_speed/eta/size, compact_mode, color, web_interface, refresh_interval |
| 13 | `plugin` | `PluginConfig` | enabled, plugin_dir, auto_discover, sandbox_mode, trusted_sources, disabled_plugins |
| 14 | `cloud` | `CloudConfig` | enabled, provider, bucket, region, access_key, auto_upload, encryption, multipart |
| 15 | `torrent` | `TorrentConfig` | enabled, listen_port, max_connections, seed_ratio, dht, pex, encryption, trackers |
| 16 | `ai` | `AIConfig` | enabled, auto_categorize, smart_retry, predict_errors, model, api_key, auto_quality |
| 17 | `scheduler` | `SchedulerConfig` | enabled, max_concurrent, time_based, start/end_hour, cron_jobs, stagger_interval |
| 18 | `live_stream` | `LiveStreamConfig` | enabled, format, segment_duration, reconnect_attempts, buffer_size, quality, hls_live_edge |
| 19 | `cache` | `CacheConfig` | enabled, max_size_mb, ttl_default/success/failure, eviction_policy, persist, compress |
| 20 | `notification` | `NotificationConfig` | enabled, on_complete/error/pause, desktop, webhook, email, telegram |
| 21 | `venv` | `VenvConfig` | enabled, venv_dir, python_version, auto_create, pip_index |
| 22 | `agent` | `AgentConfig` | max_concurrent_per_agent, default_agent, timeout, auto_discover, memory_persist, health_check |
| 23 | `encryption` | `EncryptionConfig` | enabled, algorithm, key_derivation, auto_encrypt, key_rotation_days, compression |
| 24 | `metrics` | `MetricsConfig` | enabled, collect_interval, retention_days, export_format, prometheus, track_bandwidth/latency |
| 25 | `deb` | `DebConfig` | package_name, version, maintainer, depends, section, architecture, systemd_service |

#### ConfigManager Features

- **Singleton** with thread-safe access (RLock)
- **25 frozen dataclass** sections — immutable until explicitly replaced
- **4 built-in profiles**: `dev`, `staging`, `prod`, `testing`
- **Hot-reload** — File watcher thread auto-reloads on config change
- **Environment variable export/import** — `RS_DL_{SECTION}_{KEY}` format
- **Atomic file writes** — Write to `.tmp`, then `replace()` for safety
- **Sensitive data masking** — Passwords, keys, tokens masked in logs
- **Diff from defaults** — Compare current vs. default values
- **Change notifications** — Register callbacks for config changes
- **Version migration** — Full chain: v5 → v6 → v7 → v8 → v9 → v10
- **Validation** — Type checking, range validation, port validation

---

### CLI

The command-line interface provides 40+ commands via the `rsdl` entry point.

| # | Command | Description |
|---|---|---|
| 1 | `rsdl download <url>` | Download from URL (auto-detect agent) |
| 2 | `rsdl video <url>` | Download video with quality selection |
| 3 | `rsdl audio <url>` | Download/extract audio |
| 4 | `rsdl playlist <url>` | Download entire playlist |
| 5 | `rsdl batch <file>` | Batch download from URL list file |
| 6 | `rsdl live <url>` | Record live stream |
| 7 | `rsdl search <query>` | Search across platforms |
| 8 | `rsdl torrent <magnet/file>` | Download via BitTorrent |
| 9 | `rsdl subtitle <url>` | Download subtitles |
| 10 | `rsdl thumbnail <url>` | Download thumbnail |
| 11 | `rsdl metadata <url>` | Extract metadata without downloading |
| 12 | `rsdl convert <file> <fmt>` | Convert media format |
| 13 | `rsdl speed-test` | Run network speed test (NEW v10) |
| 14 | `rsdl pause <task_id>` | Pause active download |
| 15 | `rsdl resume <task_id>` | Resume paused download |
| 16 | `rsdl cancel <task_id>` | Cancel download |
| 17 | `rsdl retry <task_id>` | Retry failed download |
| 18 | `rsdl status` | Show download queue status |
| 19 | `rsdl history` | Show download history |
| 20 | `rsdl info <task_id>` | Detailed task information |
| 21 | `rsdl list` | List all downloads |
| 22 | `rsdl clear` | Clear completed downloads from display |
| 23 | `rsdl schedule add <cron> <url>` | Add scheduled download |
| 24 | `rsdl schedule list` | List schedules |
| 25 | `rsdl schedule remove <id>` | Remove schedule |
| 26 | `rsdl schedule enable <id>` | Enable schedule |
| 27 | `rsdl schedule disable <id>` | Disable schedule |
| 28 | `rsdl proxy add <url>` | Add proxy to pool |
| 29 | `rsdl proxy list` | List proxies with health status |
| 30 | `rsdl proxy remove <url>` | Remove proxy |
| 31 | `rsdl proxy test` | Test all proxies |
| 32 | `rsdl config get <section.key>` | Get config value |
| 33 | `rsdl config set <section.key> <value>` | Set config value |
| 34 | `rsdl config show` | Show full configuration |
| 35 | `rsdl config profile <name>` | Switch config profile |
| 36 | `rsdl config reset <section>` | Reset section to defaults |
| 37 | `rsdl config diff` | Show diff from defaults |
| 38 | `rsdl config export` | Export config as environment variables |
| 39 | `rsdl config migrate <version>` | Migrate config from older version |
| 40 | `rsdl cloud upload <file>` | Upload to cloud storage |
| 41 | `rsdl cloud download <key>` | Download from cloud storage |
| 42 | `rsdl cloud list` | List cloud storage objects |
| 43 | `rsdl agent list` | List available agents |
| 44 | `rsdl agent info <name>` | Agent capabilities |
| 45 | `rsdl stats` | Download statistics |
| 46 | `rsdl tags add <task_id> <tag>` | Add tag to download (NEW v10) |
| 47 | `rsdl tags remove <task_id> <tag>` | Remove tag (NEW v10) |
| 48 | `rsdl tags search <tag>` | Search by tag (NEW v10) |
| 49 | `rsdl update` | Check for and apply updates |
| 50 | `rsdl version` | Show version info |
| 51 | `rsdl doctor` | Run diagnostics |

---

### Security

| Feature | Details |
|---|---|
| **Checksum Verification** | 8 algorithms: MD5, SHA1, SHA256, SHA512, CRC32, BLAKE2B, BLAKE2S, XXH64 |
| **Filename Sanitization** | Strips `<>:"\|?*` and control characters |
| **Domain Blocking** | Configurable blocked/allowed domain lists |
| **Extension Blocking** | Default block: `.exe`, `.scr`, `.bat`, `.cmd`, `.vbs`, `.js` |
| **HTTPS Enforcement** | Optional HTTPS-only mode |
| **Max Redirects** | Configurable redirect limit (default: 10) |
| **Safe Redirect Domains** | Whitelist for redirect destinations |
| **SSL/TLS Configuration** | Min TLSv1.2, certificate pinning, custom CA bundles |
| **Sensitive Data Masking** | Passwords, keys, tokens masked in logs and exports |
| **Private IP Protection** | Warns on private/reserved IP addresses in URLs |
| **Dangerous TLD Warnings** | Flags suspicious TLDs (.tk, .ml, .ga, .cf, .gq, etc.) |
| **Path Traversal Detection** | Blocks `..` in URL paths |
| **Input Validation** | ValidationResult tuples with warnings for all inputs |

---

### Cloud Storage

Cloud storage integration via `agents/cloud/` with provider-specific agents.

| Provider | Agent | Features |
|---|---|---|
| **Amazon S3** | `s3` | Buckets, objects, multipart upload, SSE encryption |
| **Google Cloud Storage** | `google_drive` | Files, folders, OAuth2, shared drives |
| **Azure Blob Storage** | `cloud` | Containers, blobs, SAS tokens |
| **Dropbox** | `dropbox` | Files, folders, shared links |
| **OneDrive** | `onedrive` | Files, folders, SharePoint |
| **MEGA** | `mega` | Encrypted storage, folders |
| **WebDAV** | `webdav` | Generic WebDAV servers |

Install cloud extras:
```bash
pip install rs-downloader[cloud]
```

---

### BitTorrent

BitTorrent support via `agents/torrent/`.

| Feature | Details |
|---|---|
| **Magnet Links** | Full magnet link parsing and validation |
| **Torrent Files** | `.torrent` file parsing |
| **DHT** | Distributed Hash Table for trackerless downloads |
| **PEX** | Peer Exchange |
| **Encryption** | Protocol encryption (prefer/require) |
| **Seed Ratio** | Configurable seeding ratio |
| **Bandwidth Control** | Upload/download limits |
| **Tracker List** | Custom tracker configuration |
| **Proxy** | SOCKS5 proxy for torrent traffic |

Install torrent extras:
```bash
pip install rs-downloader[torrent]
```

---

### AI Features

AI-powered features via `agents/ai/`.

| Feature | Description |
|---|---|
| **Auto-Categorization** | Automatically categorize downloads by content type |
| **Smart Retry** | AI-informed retry strategies based on error patterns |
| **Error Prediction** | Predict potential download failures before they happen |
| **Auto Quality Selection** | Select optimal quality based on network conditions |
| **Classification Confidence** | 0.8 default confidence threshold for categorization |

Install AI extras:
```bash
pip install rs-downloader[ai]
```

---

### Virtual Environment

Built-in virtual environment management (`auto_venv_setup.py`).

```bash
# Auto-create and activate venv
rsdl config set venv.enabled true
rsdl config set venv.auto_create true
```

| Setting | Default | Description |
|---|---|---|
| `venv.enabled` | `false` | Enable virtual environment |
| `venv.venv_dir` | `.venv` | Venv directory name |
| `venv.python_version` | `""` | Specific Python version |
| `venv.auto_create` | `false` | Auto-create if missing |
| `venv.auto_activate` | `false` | Auto-activate on start |
| `venv.requirements_file` | `requirements.txt` | Requirements file path |
| `venv.pip_index` | `https://pypi.org/simple` | PyPI index URL |

---

### Debian Packaging

Full Debian package support (`build_deb.sh`, `debian/`).

```bash
./build_deb.sh
sudo dpkg -i rs-downloader_10.0.0_amd64.deb
```

| File | Purpose |
|---|---|
| `debian/control` | Package metadata, dependencies, description |
| `debian/postinst` | Post-install: create user, set permissions, enable service |
| `debian/prerm` | Pre-remove: stop service |
| `debian/postrm` | Post-remove: purge config, logs |

| Setting | Default |
|---|---|
| Package name | `rs-downloader` |
| Version | `10.0.0` |
| Architecture | `amd64` |
| Install dir | `/opt/rs-downloader` |
| Config dir | `/etc/rs-downloader` |
| Log dir | `/var/log/rs-downloader` |
| Systemd service | Yes |

---

### Metrics & Monitoring

| Feature | Details |
|---|---|
| **Collection Interval** | Configurable (default: 10s) |
| **Retention** | 90 days default |
| **Export Formats** | JSON, CSV |
| **Prometheus** | Optional `/metrics` endpoint on configurable port (default: 9090) |
| **Bandwidth Tracking** | Global and per-download bandwidth metrics |
| **Latency Tracking** | Request latency percentiles |
| **Error Tracking** | Error rates by agent, platform, status code |
| **Queue Stats** | Queue depth, wait times, throughput |
| **Database Metrics** | Query performance, cache hit rates |
| **Agent Metrics** | Per-agent success/failure rates, average speed |

---

## Installation

### One-Line Install

```bash
curl -sSL https://raw.githubusercontent.com/usekarne/Downloader/main/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/usekarne/Downloader.git
cd Downloader
pip install .
```

### Install with pip (from source)

```bash
pip install git+https://github.com/usekarne/Downloader.git
```

### Kali Linux / Debian

```bash
# Build and install .deb package
git clone https://github.com/usekarne/Downloader.git
cd Downloader
chmod +x build_deb.sh
./build_deb.sh
sudo dpkg -i rs-downloader_10.0.0_amd64.deb
```

### Virtual Environment

```bash
git clone https://github.com/usekarne/Downloader.git
cd Downloader
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

Or use the built-in venv setup:

```bash
python3 auto_venv_setup.py
```

### Install with Extras

```bash
# Cloud storage support (S3, GCS, Azure)
pip install rs-downloader[cloud]

# BitTorrent support
pip install rs-downloader[torrent]

# AI features (OpenAI, LangChain)
pip install rs-downloader[ai]

# Development tools (pytest, black, mypy, flake8)
pip install rs-downloader[dev]

# Everything
pip install rs-downloader[all]
```

### Requirements

| Requirement | Minimum | Recommended |
|---|---|---|
| **Python** | 3.10 | 3.12 |
| **pip** | 22.0+ | Latest |
| **ffmpeg** | Any | Latest (for conversions) |
| **aria2c** | Optional | Latest (for faster downloads) |

### Update

```bash
rsdl update
# or
pip install --upgrade rs-downloader
```

### Uninstall

```bash
# Using pip
pip uninstall rs-downloader

# Using uninstall script
./uninstall.sh

# Remove .deb package
sudo dpkg --remove rs-downloader
```

---

## Usage

### Quick Start

```bash
# Download a video (auto-detect platform)
rsdl download https://www.youtube.com/watch?v=dQw4w9WgXcQ

# Download with quality selection
rsdl video https://www.youtube.com/watch?v=dQw4w9WgXcQ -q 1080p

# Extract audio
rsdl audio https://www.youtube.com/watch?v=dQw4w9WgXcQ -f flac

# Download a playlist
rsdl playlist https://www.youtube.com/playlist?list=PLxxxxxx

# Batch download from file
rsdl batch urls.txt

# Record a live stream
rsdl live https://www.twitch.tv/channel_name
```

### Platform-Specific Examples

```bash
# Instagram
rsdl download https://www.instagram.com/p/ABC123/

# TikTok
rsdl video https://www.tiktok.com/@user/video/123456789

# Twitter/X
rsdl download https://x.com/user/status/123456789

# Spotify
rsdl audio https://open.spotify.com/track/xxxxxx

# SoundCloud
rsdl audio https://soundcloud.com/artist/track

# Reddit
rsdl download https://www.reddit.com/r/subreddit/comments/abc123/

# Facebook
rsdl video https://www.facebook.com/watch/?v=123456789

# Twitch
rsdl video https://www.twitch.tv/videos/123456789

# Torrent
rsdl torrent magnet:?xt=urn:btih:xxxxxx
```

### Config Management

```bash
# View current config
rsdl config show

# Get a specific value
rsdl config get timeout.connect_timeout

# Set a value
rsdl config set storage.download_dir ~/MyDownloads

# Switch profile
rsdl config profile prod

# Show diff from defaults
rsdl config diff

# Export as environment variables
rsdl config export

# Reset a section
rsdl config reset security

# Migrate from v9 config
rsdl config migrate 9
```

### Proxy Management

```bash
# Add proxies
rsdl proxy add http://proxy1:8080
rsdl proxy add socks5://user:pass@proxy2:1080

# List with health status
rsdl proxy list

# Test all proxies
rsdl proxy test

# Remove a proxy
rsdl proxy remove http://proxy1:8080
```

### Scheduler

```bash
# Add recurring schedule (cron format: min hour day month weekday)
rsdl schedule add "daily_news" "0 8 * * *" "https://example.com/daily-video.mp4"

# Add one-off schedule
rsdl schedule add "tonight" "0 22 25 12 *" "https://example.com/special.mp4"

# List schedules
rsdl schedule list

# Disable/enable
rsdl schedule disable <id>
rsdl schedule enable <id>
```

### Cloud Storage

```bash
# Upload to S3
rsdl cloud upload video.mp4

# Download from Google Drive
rsdl cloud download <file_key>

# List objects
rsdl cloud list
```

### History & Statistics

```bash
# View download history
rsdl history

# View statistics
rsdl stats

# Tag management (NEW v10)
rsdl tags add abc123 "music"
rsdl tags add abc123 "favorite"
rsdl tags search "music"
rsdl tags remove abc123 "favorite"
```

---

## Configuration Reference

### Config Profiles

| Profile | Use Case | Logging | Security | Concurrency |
|---|---|---|---|---|
| `dev` | Local development | DEBUG, console | Checksums off | 5/agent |
| `staging` | Pre-production | INFO, console | Checksums on | 3/agent |
| `prod` | Production server | WARNING, file only | Full security | 3/agent |
| `testing` | CI/CD testing | DEBUG, no file | Checksums off | 10/agent |

### Environment Variables

All config values can be set via environment variables using the `RS_DL_` prefix:

```bash
# Format: RS_DL_{SECTION}_{KEY}=value

# Timeout
export RS_DL_TIMEOUT_CONNECT_TIMEOUT=60
export RS_DL_TIMEOUT_READ_TIMEOUT=120

# Storage
export RS_DL_STORAGE_DOWNLOAD_DIR=/data/downloads

# Proxy
export RS_DL_PROXY_ENABLED=true
export RS_DL_PROXY_ROTATION_STRATEGY=latency_based

# Security
export RS_DL_SECURITY_ENFORCE_HTTPS=true
export RS_DL_SECURITY_VERIFY_CHECKSUMS=true

# UI
export RS_DL_UI_THEME=light
export RS_DL_UI_COMPACT_MODE=true

# Bandwidth
export RS_DL_BANDWIDTH_GLOBAL_LIMIT_KBPS=50000

# Logging
export RS_DL_LOGGING_LEVEL=WARNING
export RS_DL_LOGGING_ENABLE_FILE=true
```

### Config File

Default: `config.json` in the working directory.

```json
{
  "timeout": {
    "connect_timeout": 30.0,
    "read_timeout": 60.0
  },
  "storage": {
    "download_dir": "~/Downloads/RS_Downloader",
    "duplicate_handling": "rename"
  },
  "security": {
    "verify_checksums": true,
    "default_checksum_algo": "sha256"
  },
  "_meta": {
    "version": "10.0.0",
    "profile": "dev",
    "saved_at": "2025-01-01T00:00:00+00:00"
  }
}
```

---

## Agent Reference

Complete reference of all 90+ download agents:

| # | Agent ID | Platform | Type | Key Capabilities |
|---|---|---|---|---|
| 1 | `youtube` | YouTube | Video | Videos, Shorts, Live, Playlists, Channels, Embeds |
| 2 | `youtube_music` | YouTube Music | Audio | Tracks, Albums, Playlists |
| 3 | `vimeo` | Vimeo | Video | Videos, Channels, On Demand |
| 4 | `vimeo_enterprise` | Vimeo Enterprise | Video | Private/Enterprise videos |
| 5 | `dailymotion` | Dailymotion | Video | Videos, Playlists |
| 6 | `twitch` | Twitch | Video/Live | VODs, Clips, Live streams |
| 7 | `tiktok` | TikTok | Video | Videos, Profiles |
| 8 | `bilibili` | Bilibili | Video | Videos, Bangumi, Live |
| 9 | `rumble` | Rumble | Video | Videos, Channels |
| 10 | `bitchute` | BitChute | Video | Videos |
| 11 | `odysee` | Odysee | Video | Videos, Channels |
| 12 | `kick` | Kick | Video/Live | VODs, Clips, Live |
| 13 | `douyin` | Douyin | Video | Videos |
| 14 | `niconico` | Niconico | Video | Videos, Playlists |
| 15 | `periscope` | Periscope | Video | Archived streams |
| 16 | `likee` | Likee | Video | Videos |
| 17 | `loom` | Loom | Video | Screen recordings |
| 18 | `wistia` | Wistia | Video | Business videos |
| 19 | `stage` | Stage | Video | Video content |
| 20 | `ok` | OK.ru | Video | Videos |
| 21 | `kakao` | KakaoTV | Video | Videos |
| 22 | `naver` | Naver | Video | Videos, Clips |
| 23 | `instagram` | Instagram | Social | Posts, Reels, Stories, IGTV |
| 24 | `facebook` | Facebook | Social | Videos, Posts, Watch |
| 25 | `twitter` | Twitter/X | Social | Posts, Spaces, Live |
| 26 | `reddit` | Reddit | Social | Posts, Videos, Images |
| 27 | `tumblr` | Tumblr | Social | Posts, Images, Videos |
| 28 | `pinterest` | Pinterest | Social | Pins, Boards |
| 29 | `snapchat` | Snapchat | Social | Spotlight, Stories |
| 30 | `vk` | VK | Social | Videos, Photos, Posts |
| 31 | `weibo` | Weibo | Social | Posts, Videos |
| 32 | `discord` | Discord CDN | Social | Attachments, Files |
| 33 | `spotify` | Spotify | Audio | Tracks, Albums, Playlists, Podcasts |
| 34 | `soundcloud` | SoundCloud | Audio | Tracks, Playlists, Sets |
| 35 | `bandcamp` | Bandcamp | Audio | Tracks, Albums |
| 36 | `deezer` | Deezer | Audio | Tracks, Albums, Playlists |
| 37 | `tidal` | Tidal | Audio | Tracks, Albums, Videos |
| 38 | `apple_music` | Apple Music | Audio | Tracks, Albums, Playlists |
| 39 | `amazon_music` | Amazon Music | Audio | Tracks, Albums |
| 40 | `mixcloud` | Mixcloud | Audio | Shows, Playlists |
| 41 | `reverbnation` | ReverbNation | Audio | Tracks |
| 42 | `soundclick` | SoundClick | Audio | Tracks |
| 43 | `audible` | Audible | Audio | Audiobooks |
| 44 | `unsplash` | Unsplash | Image | Photos, Collections |
| 45 | `pexels` | Pexels | Image | Photos, Videos |
| 46 | `flickr` | Flickr | Image | Photos, Albums |
| 47 | `imgur` | Imgur | Image | Images, Albums, GIFs |
| 48 | `giphy` | GIPHY | Image | GIFs, Stickers |
| 49 | `tenor` | Tenor | Image | GIFs |
| 50 | `deviantart` | DeviantArt | Image | Art, Collections |
| 51 | `artstation` | ArtStation | Image | Artwork, Projects |
| 52 | `telegram` | Telegram | Messaging | Files, Videos, Voice, Channels |
| 53 | `whatsapp` | WhatsApp | Messaging | Status, Media |
| 54 | `udemy` | Udemy | Education | Course videos |
| 55 | `coursera` | Coursera | Education | Course videos, Materials |
| 56 | `skillshare` | Skillshare | Education | Class videos |
| 57 | `ted` | TED | Education | Talks, Playlists |
| 58 | `gutenberg` | Project Gutenberg | Books | Ebooks |
| 59 | `librivox` | LibriVox | Books | Audiobooks |
| 60 | `ebook` | Generic Ebook | Books | EPUB, PDF, MOBI |
| 61 | `archive_org` | Internet Archive | Books | Books, Audio, Video, Software |
| 62 | `podcast` | Generic Podcast | Podcast | RSS-based podcast downloads |
| 63 | `onlyfans` | OnlyFans | Creator | Media, Posts |
| 64 | `patreon` | Patreon | Creator | Posts, Media |
| 65 | `google_drive` | Google Drive | Cloud | Files, Folders |
| 66 | `dropbox` | Dropbox | Cloud | Files, Folders |
| 67 | `onedrive` | OneDrive | Cloud | Files, Folders |
| 68 | `mega` | MEGA | Cloud | Encrypted files, Folders |
| 69 | `s3` | Amazon S3 | Cloud | Objects, Buckets |
| 70 | `cloud` | Generic Cloud | Cloud | S3-compatible storage |
| 71 | `webdav` | WebDAV | Cloud | Files, Folders |
| 72 | `torrent` | BitTorrent | P2P | Torrent files, Magnet links |
| 73 | `ipfs` | IPFS | P2P | Content-addressed files |
| 74 | `tor` | Tor/Onion | P2P | .onion hidden services |
| 75 | `batch` | System | Utility | Batch URL file processing |
| 76 | `playlist` | System | Utility | Multi-video playlist handling |
| 77 | `live` | System | Utility | Live stream recording |
| 78 | `stream` | System | Utility | Generic stream capture |
| 79 | `convert` | System | Utility | Audio/video format conversion |
| 80 | `subtitle` | System | Utility | Subtitle download & embed |
| 81 | `thumbnail` | System | Utility | Thumbnail extraction |
| 82 | `metadata` | System | Utility | Metadata extraction & tagging |
| 83 | `proxy` | System | Utility | Proxy testing & management |
| 84 | `scheduler` | System | Utility | Cron-based download scheduling |
| 85 | `search` | System | Utility | Multi-platform content search |
| 86 | `ai` | System | Utility | AI categorization & smart retry |
| 87 | `analytics` | System | Utility | Download analytics & reporting |
| 88 | `ebook` | System | Utility | Ebook format conversion |
| 89 | `kick` | Kick Streaming | Video | Live, VODs, Clips |
| 90 | `stage` | Stage | Video | Video platform |
| 91 | `loom` | Loom | Video | Screen recordings |
| 92 | `wistia` | Wistia | Video | Business video |
| 93 | `periscope` | Periscope | Video | Live archives |

---

## Architecture

### Directory Tree

```
Downloader_v10/
├── rs_toolkit.py              # Main CLI entry point
├── setup.py                   # Setuptools configuration
├── pyproject.toml             # Modern Python project config
├── requirements.txt           # Python dependencies
├── install.sh                 # One-line installer script
├── uninstall.sh               # Uninstaller script
├── auto_venv_setup.py         # Virtual environment setup
├── config_generator.py        # Interactive config generator
├── build_deb.sh               # Debian package builder
├── LICENSE                    # MIT License
│
├── core/                      # Core Engine
│   ├── __init__.py
│   ├── config.py              # 25-section ConfigManager singleton
│   ├── database.py            # 9-table SQLite database with WAL
│   ├── downloader_base.py     # Download engine (queue, lifecycle, agents)
│   ├── logger.py              # Structured logging with rotation
│   └── network.py             # HTTP clients, proxy pool, checksums
│
├── agents/                    # 90+ Download Agents
│   ├── __init__.py
│   ├── youtube/               # YouTube agent
│   ├── youtube_music/         # YouTube Music agent
│   ├── vimeo/                 # Vimeo agent
│   ├── vimeo_enterprise/      # Vimeo Enterprise agent
│   ├── dailymotion/           # Dailymotion agent
│   ├── twitch/                # Twitch agent
│   ├── tiktok/                # TikTok agent
│   ├── bilibili/              # Bilibili agent
│   ├── rumble/                # Rumble agent
│   ├── bitchute/              # BitChute agent
│   ├── odysee/                # Odysee agent
│   ├── kick/                  # Kick agent
│   ├── douyin/                # Douyin agent
│   ├── niconico/              # Niconico agent
│   ├── periscope/             # Periscope agent
│   ├── likee/                 # Likee agent
│   ├── loom/                  # Loom agent
│   ├── wistia/                # Wistia agent
│   ├── stage/                 # Stage agent
│   ├── ok/                    # OK.ru agent
│   ├── kakao/                 # KakaoTV agent
│   ├── naver/                 # Naver agent
│   ├── instagram/             # Instagram agent
│   ├── facebook/              # Facebook agent
│   ├── twitter/               # Twitter/X agent
│   ├── reddit/                # Reddit agent
│   ├── tumblr/                # Tumblr agent
│   ├── pinterest/             # Pinterest agent
│   ├── snapchat/              # Snapchat agent
│   ├── vk/                    # VK agent
│   ├── weibo/                 # Weibo agent
│   ├── discord/               # Discord CDN agent
│   ├── spotify/               # Spotify agent
│   ├── soundcloud/            # SoundCloud agent
│   ├── bandcamp/              # Bandcamp agent
│   ├── deezer/                # Deezer agent
│   ├── tidal/                 # Tidal agent
│   ├── apple_music/           # Apple Music agent
│   ├── amazon_music/          # Amazon Music agent
│   ├── mixcloud/              # Mixcloud agent
│   ├── reverbnation/          # ReverbNation agent
│   ├── soundclick/            # SoundClick agent
│   ├── audible/               # Audible agent
│   ├── unsplash/              # Unsplash agent
│   ├── pexels/                # Pexels agent
│   ├── flickr/                # Flickr agent
│   ├── imgur/                 # Imgur agent
│   ├── giphy/                 # GIPHY agent
│   ├── tenor/                 # Tenor agent
│   ├── deviantart/            # DeviantArt agent
│   ├── artstation/            # ArtStation agent
│   ├── telegram/              # Telegram agent
│   ├── whatsapp/              # WhatsApp agent
│   ├── udemy/                 # Udemy agent
│   ├── coursera/              # Coursera agent
│   ├── skillshare/            # Skillshare agent
│   ├── ted/                   # TED agent
│   ├── gutenberg/             # Project Gutenberg agent
│   ├── librivox/              # LibriVox agent
│   ├── ebook/                 # Generic Ebook agent
│   ├── archive_org/           # Internet Archive agent
│   ├── podcast/               # Generic Podcast agent
│   ├── onlyfans/              # OnlyFans agent
│   ├── patreon/               # Patreon agent
│   ├── google_drive/          # Google Drive agent
│   ├── dropbox/               # Dropbox agent
│   ├── onedrive/              # OneDrive agent
│   ├── mega/                  # MEGA agent
│   ├── s3/                    # Amazon S3 agent
│   ├── cloud/                 # Generic Cloud agent
│   ├── webdav/                # WebDAV agent
│   ├── torrent/               # BitTorrent agent
│   ├── ipfs/                  # IPFS agent
│   ├── tor/                   # Tor/Onion agent
│   ├── batch/                 # Batch processing agent
│   ├── playlist/              # Playlist agent
│   ├── live/                  # Live stream agent
│   ├── stream/                # Stream capture agent
│   ├── convert/               # Format conversion agent
│   ├── subtitle/              # Subtitle agent
│   ├── thumbnail/             # Thumbnail agent
│   ├── metadata/              # Metadata agent
│   ├── proxy/                 # Proxy management agent
│   ├── scheduler/             # Scheduler agent
│   ├── search/                # Search agent
│   ├── ai/                    # AI agent
│   └── analytics/             # Analytics agent
│
├── utils/                     # Utility Modules
│   ├── __init__.py
│   ├── banner.py              # ASCII art banners, 5 styles, animation
│   ├── colors.py              # Terminal colors, gradient text, rainbow text
│   ├── helpers.py             # General helper functions
│   ├── progress.py            # Progress bars, spinners, multi-progress
│   └── validator.py           # Input validation, platform detection
│
├── config/                    # Configuration
│   └── profiles/
│       ├── default.json       # Default profile
│       └── production.json    # Production profile
│
└── debian/                    # Debian Packaging
    ├── control                # Package metadata
    ├── postinst               # Post-install script
    ├── prerm                  # Pre-remove script
    └── postrm                 # Post-remove script
```

### Data Flow

```
                          ┌─────────────────┐
                          │   CLI (rsdl)     │
                          │  40+ Commands    │
                          └────────┬────────┘
                                   │
                          ┌────────▼────────┐
                          │ ConfigManager    │
                          │ 25 Sections      │◄──── Environment Variables
                          │ 4 Profiles       │◄──── config.json
                          │ Hot-Reload       │
                          └────────┬────────┘
                                   │
                  ┌────────────────┼────────────────┐
                  │                │                 │
         ┌────────▼───────┐ ┌─────▼──────┐ ┌───────▼───────┐
         │   Validator     │ │  Logger    │ │   Database     │
         │ ValidationResult│ │ Structured │ │ 9 Tables      │
         │ 17 Detectors    │ │ Rotating   │ │ WAL Mode      │
         └────────┬───────┘ └────────────┘ │ 22+ Indexes   │
                  │                         └───────┬───────┘
         ┌────────▼─────────────────────────────────▼───────┐
         │              Download Orchestrator                │
         │  ┌──────────┐  ┌───────────┐  ┌──────────────┐  │
         │  │  Queue   │  │ Lifecycle  │  │ Speed Tracker │  │
         │  │ Priority │  │ 13 States │  │ P95/P99/Med  │  │
         │  │ Heap     │  │ FSM       │  │ Window-based │  │
         │  └────┬─────┘  └─────┬─────┘  └──────┬───────┘  │
         └───────┼──────────────┼───────────────┼───────────┘
                 │              │               │
         ┌───────▼──────────────▼───────────────▼───────────┐
         │              Agent Registry                       │
         │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │
         │  │YouTube │ │Spotify │ │Torrent │ │  AI    │   │
         │  │TikTok  │ │Bandcamp│ │IPFS    │ │Search  │   │
         │  │Twitter │ │Deezer  │ │Tor     │ │Convert │   │
         │  │  ...   │ │  ...   │ │  ...   │ │  ...   │   │
         │  └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘   │
         └──────┼──────────┼──────────┼──────────┼─────────┘
                │          │          │          │
         ┌──────▼──────────▼──────────▼──────────▼─────────┐
         │              Network Layer                       │
         │  ┌──────────────┐  ┌──────────────────────────┐ │
         │  │ SyncHTTPCli  │  │ AsyncHTTPClient           │ │
         │  │ Streaming DL │  │ Concurrent Requests       │ │
         │  │ Multipart UP │  │ Async Streaming           │ │
         │  └──────────────┘  └──────────────────────────┘ │
         │  ┌──────────────┐  ┌──────────────────────────┐ │
         │  │  ProxyPool   │  │  CircuitBreaker          │ │
         │  │ 7 Strategies │  │ CLOSED→OPEN→HALF_OPEN    │ │
         │  └──────────────┘  └──────────────────────────┘ │
         │  ┌──────────────┐  ┌──────────────────────────┐ │
         │  │ Parallel DL  │  │ BandwidthThrottler       │ │
         │  │ Multi-Conn   │  │ Token-Bucket Rate Limit  │ │
         │  └──────────────┘  └──────────────────────────┘ │
         └─────────────────────────────────────────────────┘
                               │
                  ┌────────────▼────────────┐
                  │     Progress Display     │
                  │  ┌─────┐ ┌────────────┐ │
                  │  │Bars │ │  Spinners   │ │
                  │  │8 st.│ │  7 styles   │ │
                  │  └─────┘ └────────────┘ │
                  │  ┌────────────────────┐ │
                  │  │  MultiProgress     │ │
                  │  │  Concurrent Track  │ │
                  │  └────────────────────┘ │
                  │  ┌────────────────────┐ │
                  │  │  PlainProgress     │ │
                  │  │  Non-TTY/CI/CD     │ │
                  │  └────────────────────┘ │
                  └─────────────────────────┘
```

---

## Contributing

Contributions are welcome! Please follow these steps:

### 1. Fork

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/Downloader.git
cd Downloader
```

### 2. Branch

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/your-fix-name
```

### 3. Develop

```bash
# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Make your changes...
```

### 4. Test

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=rs_toolkit --cov-report=html

# Run specific test categories
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
pytest -m network       # Network-dependent tests

# Type checking
mypy rs_toolkit.py core/ utils/ agents/

# Linting
flake8 rs_toolkit.py core/ utils/ agents/
black --check rs_toolkit.py core/ utils/ agents/
isort --check-only rs_toolkit.py core/ utils/ agents/
```

### 5. Commit

```bash
# Follow conventional commits
git commit -m "feat: add new agent for XYZ platform"
git commit -m "fix: resolve timeout issue in SyncHTTPClient"
git commit -m "docs: update README with new CLI commands"
```

### 6. Push

```bash
git push origin feature/your-feature-name
```

### 7. Pull Request

- Open a PR against the `main` branch
- Describe the changes clearly
- Reference any related issues
- Ensure CI passes

### Code Style

- **Line length**: 100 characters (Black default)
- **Type hints**: Required for all function signatures
- **Docstrings**: Google-style docstrings for all public functions/classes
- **Imports**: Sorted with isort (Black-compatible profile)
- **Python version**: Minimum 3.10 (use `from __future__ import annotations`)

---

## License

```
MIT License

Copyright (c) 2025 RAJSARASWATI JATAV

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Credits

<p align="center">
  <strong>RAJSARASWATI JATAV (RS)</strong> / <strong>T3rmuxk1ng</strong>
</p>

<p align="center">
  <a href="https://github.com/usekarne/Downloader">
    <img src="https://img.shields.io/badge/GitHub-Downloader-181717?style=for-the-badge&logo=github" alt="GitHub">
  </a>
  <a href="https://youtube.com/@T3rmuxk1ng">
    <img src="https://img.shields.io/badge/YouTube-T3rmuxk1ng-FF0000?style=for-the-badge&logo=youtube" alt="YouTube">
  </a>
</p>

<p align="center">
  <em>INFINITE HYPERNOVA SOVEREIGN NEXUS</em><br>
  v10.0.0 &mdash; The Ultimate Download Toolkit<br><br>
  Built with ❤️ by RS from India
</p>
