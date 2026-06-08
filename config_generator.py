#!/usr/bin/env python3
"""
RS Downloader v10.0.0 - Interactive Configuration Generator
Author: RAJSARASWATI JATAV (RS)
License: MIT

Generates a complete config.json with all 25 sections through
an interactive questionnaire or from defaults.
"""

import json
import sys
import shutil
from pathlib import Path
from datetime import datetime
from typing import Any

# Paths
SCRIPT_DIR = Path(__file__).parent.resolve()
DEFAULT_CONFIG = SCRIPT_DIR / "config" / "profiles" / "default.json"
OUTPUT_PATH = SCRIPT_DIR / "config.json"

# Colors
RED = "\033[0;31m"
GREEN = "\033[0;32m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
CYAN = "\033[0;36m"
BOLD = "\033[1m"
DIM = "\033[2m"
NC = "\033[0m"


def info(msg: str) -> None:
    print(f"{BLUE}[INFO]{NC} {msg}")


def success(msg: str) -> None:
    print(f"{GREEN}[OK]{NC} {msg}")


def warn(msg: str) -> None:
    print(f"{YELLOW}[WARN]{NC} {msg}")


def error(msg: str) -> None:
    print(f"{RED}[ERROR]{NC} {msg}")


def ask(question: str, default: Any = "", value_type: type = str) -> Any:
    """Ask a question with a default value."""
    default_str = str(default) if default != "" else ""
    prompt = f"  {CYAN}?{NC} {question}"
    if default_str:
        prompt += f" [{DIM}{default_str}{NC}]"

    try:
        answer = input(f"{prompt}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return default

    if not answer:
        return default

    try:
        if value_type == bool:
            return answer.lower() in ("y", "yes", "true", "1")
        elif value_type == int:
            return int(answer)
        elif value_type == float:
            return float(answer)
        return answer
    except (ValueError, TypeError):
        return default


def ask_yes_no(question: str, default: bool = False) -> bool:
    """Ask a yes/no question."""
    hint = "Y/n" if default else "y/N"
    answer = ask(f"{question} ({hint})", "y" if default else "n", str)
    if isinstance(answer, str):
        return answer.lower() in ("y", "yes", "true", "1")
    return default


def section_header(title: str) -> None:
    """Print a section header."""
    print(f"\n{BOLD}{CYAN}━━━ {title} ━━━{NC}")


def load_default_config() -> dict:
    """Load the default configuration file."""
    if DEFAULT_CONFIG.exists():
        with open(DEFAULT_CONFIG, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def generate_download_config(defaults: dict) -> dict:
    """Generate download configuration."""
    section_header("Download Settings")
    d = defaults.get("download", {})
    return {
        "output_dir": ask("Output directory", d.get("output_dir", "~/Downloads/rs-downloader")),
        "temp_dir": ask("Temp directory", d.get("temp_dir", "/tmp/rs-downloader")),
        "filename_template": ask("Filename template", d.get("filename_template", "%(title)s.%(ext)s")),
        "max_concurrent_downloads": ask("Max concurrent downloads", d.get("max_concurrent_downloads", 3), int),
        "max_retries": ask("Max retries", d.get("max_retries", 3), int),
        "retry_delay_seconds": ask("Retry delay (seconds)", d.get("retry_delay_seconds", 5), int),
        "timeout_seconds": ask("Timeout (seconds)", d.get("timeout_seconds", 300), int),
        "chunk_size": ask("Chunk size", d.get("chunk_size", 8192), int),
        "resume_partial": ask_yes_no("Resume partial downloads?", d.get("resume_partial", True)),
        "overwrite_existing": ask_yes_no("Overwrite existing files?", d.get("overwrite_existing", False)),
        "auto_convert": ask_yes_no("Auto convert format?", d.get("auto_convert", False)),
    }


def generate_video_config(defaults: dict) -> dict:
    """Generate video configuration."""
    section_header("Video Settings")
    d = defaults.get("video", {})
    return {
        "preferred_format": ask("Preferred video format", d.get("preferred_format", "bestvideo+bestaudio/best")),
        "preferred_quality": ask("Preferred quality (2160/1080/720/480)", d.get("preferred_quality", "1080")),
        "preferred_codec": ask("Preferred codec (auto/h264/h265/av1)", d.get("preferred_codec", "auto")),
        "merge_output_format": ask("Merge output format (mp4/mkv/webm)", d.get("merge_output_format", "mp4")),
        "prefer_free_formats": ask_yes_no("Prefer free formats?", d.get("prefer_free_formats", False)),
        "embed_thumbnail": ask_yes_no("Embed thumbnail?", d.get("embed_thumbnail", True)),
        "embed_subtitle": ask_yes_no("Embed subtitles?", d.get("embed_subtitle", False)),
        "subtitle_langs": ask("Subtitle languages (comma-separated)", d.get("subtitle_langs", ["en"])),
        "embed_metadata": ask_yes_no("Embed metadata?", d.get("embed_metadata", True)),
        "write_description": ask_yes_no("Write description file?", d.get("write_description", False)),
        "write_info_json": ask_yes_no("Write info JSON?", d.get("write_info_json", False)),
        "write_annotations": ask_yes_no("Write annotations?", d.get("write_annotations", False)),
        "sponsorblock_mark": ask("SponsorBlock mark categories", d.get("sponsorblock_mark", "")),
        "sponsorblock_remove": ask("SponsorBlock remove categories", d.get("sponsorblock_remove", "")),
    }


def generate_audio_config(defaults: dict) -> dict:
    """Generate audio configuration."""
    section_header("Audio Settings")
    d = defaults.get("audio", {})
    return {
        "preferred_format": ask("Preferred audio format", d.get("preferred_format", "best")),
        "preferred_quality": ask("Audio quality (320/256/192/128)", d.get("preferred_quality", "320")),
        "preferred_codec": ask("Audio codec (auto/mp3/aac/opus/flac)", d.get("preferred_codec", "auto")),
        "output_format": ask("Output format (mp3/flac/opus/aac)", d.get("output_format", "mp3")),
        "embed_thumbnail": ask_yes_no("Embed thumbnail?", d.get("embed_thumbnail", True)),
        "embed_metadata": ask_yes_no("Embed metadata?", d.get("embed_metadata", True)),
        "write_playlist": ask_yes_no("Write playlist file?", d.get("write_playlist", False)),
        "add_album_art": ask_yes_no("Add album art?", d.get("add_album_art", True)),
        "normalize_audio": ask_yes_no("Normalize audio?", d.get("normalize_audio", False)),
    }


def generate_playlist_config(defaults: dict) -> dict:
    """Generate playlist configuration."""
    section_header("Playlist Settings")
    d = defaults.get("playlist", {})
    return {
        "download_full_playlist": ask_yes_no("Download full playlists?", d.get("download_full_playlist", True)),
        "playlist_start": ask("Playlist start index", d.get("playlist_start", 1), int),
        "playlist_end": ask("Playlist end index (-1 for all)", d.get("playlist_end", -1), int),
        "playlist_items": ask("Specific playlist items (e.g., 1,3,5-10)", d.get("playlist_items", "")),
        "playlist_reverse": ask_yes_no("Reverse playlist order?", d.get("playlist_reverse", False)),
        "playlist_random": ask_yes_no("Randomize playlist order?", d.get("playlist_random", False)),
        "create_playlist_folder": ask_yes_no("Create playlist folder?", d.get("create_playlist_folder", True)),
        "number_episodes": ask_yes_no("Number episodes?", d.get("number_episodes", True)),
        "max_playlist_items": ask("Max playlist items (0=unlimited)", d.get("max_playlist_items", 0), int),
        "playlist_output_template": ask("Playlist output template", d.get("playlist_output_template",
            "%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s")),
    }


def generate_batch_config(defaults: dict) -> dict:
    """Generate batch configuration."""
    section_header("Batch Download Settings")
    d = defaults.get("batch", {})
    return {
        "batch_file": ask("Batch file path", d.get("batch_file", "")),
        "batch_delay_seconds": ask("Delay between batch items (seconds)", d.get("batch_delay_seconds", 1), int),
        "batch_mode": ask("Batch mode (sequential/parallel)", d.get("batch_mode", "sequential")),
        "batch_max_parallel": ask("Max parallel batch downloads", d.get("batch_max_parallel", 3), int),
        "batch_continue_on_error": ask_yes_no("Continue on error?", d.get("batch_continue_on_error", True)),
        "batch_log_errors": ask_yes_no("Log batch errors?", d.get("batch_log_errors", True)),
        "batch_save_progress": ask_yes_no("Save batch progress?", d.get("batch_save_progress", True)),
        "batch_progress_file": ask("Progress file path", d.get("batch_progress_file",
            "~/.rs-downloader/batch_progress.json")),
    }


def generate_network_config(defaults: dict) -> dict:
    """Generate network configuration."""
    section_header("Network Settings")
    d = defaults.get("network", {})
    return {
        "proxy": ask("Proxy URL (e.g., socks5://127.0.0.1:9050)", d.get("proxy", "")),
        "proxy_username": ask("Proxy username", d.get("proxy_username", "")),
        "proxy_password": ask("Proxy password", d.get("proxy_password", "")),
        "source_address": ask("Source IP address", d.get("source_address", "")),
        "use_ipv4": ask_yes_no("Force IPv4?", d.get("use_ipv4", False)),
        "use_ipv6": ask_yes_no("Force IPv6?", d.get("use_ipv6", False)),
        "connection_timeout": ask("Connection timeout (seconds)", d.get("connection_timeout", 30), int),
        "read_timeout": ask("Read timeout (seconds)", d.get("read_timeout", 60), int),
        "max_connections": ask("Max connections", d.get("max_connections", 10), int),
        "rate_limit": ask("Rate limit (e.g., 1M for 1MB/s)", d.get("rate_limit", "")),
        "throttle_delay": ask("Throttle delay (ms)", d.get("throttle_delay", 0), int),
        "cookies_file": ask("Cookies file path", d.get("cookies_file", "")),
        "cookies_from_browser": ask("Extract cookies from browser (chrome/firefox/edge)", d.get("cookies_from_browser", "")),
        "user_agent": ask("Custom User-Agent", d.get("user_agent", "")),
        "referer": ask("Custom Referer", d.get("referer", "")),
    }


def generate_simple_section(name: str, defaults: dict) -> dict:
    """Generate a simple section using defaults with yes/no for enabled."""
    section_header(f"{name.title()} Settings")
    d = defaults.get(name, {})
    return dict(d) if d else {}


def generate_full_config(interactive: bool = True) -> dict:
    """Generate the full configuration with all 25 sections."""
    defaults = load_default_config()

    if not interactive:
        info("Using default configuration (non-interactive mode)")
        return defaults

    print(f"\n{BOLD}{CYAN}{'=' * 55}")
    print("  RS Downloader v10.0.0 - Configuration Generator")
    print(f"{'=' * 55}{NC}\n")
    info("Press Enter to accept default values shown in brackets.")
    info("Answer questions to customize your configuration.\n")

    config = {
        "_meta": {
            "name": "RS Downloader Custom Configuration",
            "version": "10.0.0",
            "author": "RAJSARASWATI JATAV (RS)",
            "description": "Custom configuration generated interactively",
            "created": datetime.now().isoformat(),
        },
        "download": generate_download_config(defaults),
        "video": generate_video_config(defaults),
        "audio": generate_audio_config(defaults),
        "playlist": generate_playlist_config(defaults),
        "batch": generate_batch_config(defaults),
        "network": generate_network_config(defaults),
        "authentication": generate_simple_section("authentication", defaults),
        "conversion": generate_simple_section("conversion", defaults),
        "storage": generate_simple_section("storage", defaults),
        "ui": generate_simple_section("ui", defaults),
        "logging": generate_simple_section("logging", defaults),
        "scheduling": generate_simple_section("scheduling", defaults),
        "notifications": generate_simple_section("notifications", defaults),
        "cloud": generate_simple_section("cloud", defaults),
        "torrent": generate_simple_section("torrent", defaults),
        "ai": generate_simple_section("ai", defaults),
        "security": generate_simple_section("security", defaults),
        "advanced": generate_simple_section("advanced", defaults),
        "performance": generate_simple_section("performance", defaults),
        "monitoring": generate_simple_section("monitoring", defaults),
        "plugins": generate_simple_section("plugins", defaults),
        "updates": generate_simple_section("updates", defaults),
        "regional": generate_simple_section("regional", defaults),
    }

    return config


def save_config(config: dict, output_path: Path) -> None:
    """Save the configuration to a JSON file."""
    # Backup existing config
    if output_path.exists():
        backup_path = output_path.with_suffix(".json.bak")
        shutil.copy2(output_path, backup_path)
        info(f"Existing config backed up to {backup_path}")

    # Ensure parent directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write config
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)

    success(f"Configuration saved to {output_path}")


def main() -> int:
    """Main entry point."""
    # Parse simple CLI args
    interactive = True
    output = OUTPUT_PATH

    for arg in sys.argv[1:]:
        if arg in ("--non-interactive", "-n", "--defaults"):
            interactive = False
        elif arg in ("--help", "-h"):
            print("RS Downloader v10.0.0 - Configuration Generator")
            print()
            print("Usage: python config_generator.py [OPTIONS]")
            print()
            print("Options:")
            print("  --non-interactive, -n   Use default values (no questions)")
            print("  --output PATH           Output file path")
            print("  --help, -h              Show this help")
            return 0
        elif arg == "--output" and len(sys.argv) > sys.argv.index(arg) + 1:
            output = Path(sys.argv[sys.argv.index(arg) + 1])

    try:
        config = generate_full_config(interactive=interactive)
        save_config(config, output)
        print(f"\n{GREEN}Configuration generated successfully!{NC}")
        return 0
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Configuration generation cancelled.{NC}")
        return 1
    except Exception as e:
        error(f"Configuration generation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
