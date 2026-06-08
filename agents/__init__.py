"""
RS Downloader v10.0.0 - Agent Registry
=========================================

Codename: INFINITE HYPERNOVA SOVEREIGN NEXUS
Author: RAJSARASWATI JATAV (RS) / T3rmuxk1ng

Central agent registry that imports and registers ALL download agents.
Provides get_registry(), list_all_agents(), and AGENT_COUNT.
Handles import errors gracefully - agents that fail to import are skipped.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from core.downloader_base import (
    AgentRegistry,
    AgentSkill,
)

logger = logging.getLogger("agent_registry")

# ---------------------------------------------------------------------------
# Agent count constant (updated as agents are added)
# ---------------------------------------------------------------------------
AGENT_COUNT: int = 90  # Total expected agents across all categories

# ---------------------------------------------------------------------------
# Registry singleton
# ---------------------------------------------------------------------------
_registry: Optional[AgentRegistry] = None


# ---------------------------------------------------------------------------
# Agent import list - ALL 90 agent modules
# ---------------------------------------------------------------------------

# --- Images & Art (8) ---
_AGENT_MODULES = [
    # Images & Art
    ("agents.unsplash", "unsplash"),
    ("agents.pexels", "pexels"),
    ("agents.imgur", "imgur"),
    ("agents.giphy", "giphy"),
    ("agents.tenor", "tenor"),
    ("agents.flickr", "flickr"),
    ("agents.deviantart", "deviantart"),
    ("agents.artstation", "artstation"),

    # Books & Audio
    ("agents.librivox", "librivox"),
    ("agents.gutenberg", "gutenberg"),
    ("agents.audible", "audible"),
    ("agents.podcast", "podcast"),
    ("agents.ebook", "ebook"),

    # Asian Platforms
    ("agents.bilibili", "bilibili"),
    ("agents.douyin", "douyin"),
    ("agents.naver", "naver"),
    ("agents.kakao", "kakao"),

    # P2P & Privacy
    ("agents.torrent", "torrent"),
    ("agents.tor", "tor"),
    ("agents.ipfs", "ipfs"),

    # Content Creators
    ("agents.patreon", "patreon"),
    ("agents.onlyfans", "onlyfans"),

    # Content & Archive
    ("agents.archive_org", "archive_org"),

    # Utility Agents
    ("agents.metadata", "metadata"),
    ("agents.subtitle", "subtitle"),
    ("agents.thumbnail", "thumbnail"),
    ("agents.convert", "convert"),
    ("agents.search", "search"),
    ("agents.stream", "stream"),
    ("agents.ai", "ai"),
    ("agents.analytics", "analytics"),
    ("agents.batch", "batch"),
    ("agents.playlist", "playlist"),
    ("agents.cloud", "cloud"),

    # --- Pre-existing agents (56) ---
    # Video Platforms
    ("agents.youtube", "youtube"),
    ("agents.vimeo", "vimeo"),
    ("agents.dailymotion", "dailymotion"),
    ("agents.tiktok", "tiktok"),
    ("agents.facebook", "facebook"),
    ("agents.twitter", "twitter"),
    ("agents.instagram", "instagram"),
    ("agents.reddit", "reddit"),
    ("agents.tumblr", "tumblr"),
    ("agents.twitch", "twitch"),
    ("agents.kick", "kick"),
    ("agents.rumble", "rumble"),
    ("agents.bitchute", "bitchute"),
    ("agents.odysee", "odysee"),
    ("agents.niconico", "niconico"),
    ("agents.vimeo_enterprise", "vimeo_enterprise"),
    ("agents.loom", "loom"),
    ("agents.periscope", "periscope"),
    ("agents.wistia", "wistia"),
    ("agents.live", "live"),
    ("agents.weibo", "weibo"),
    ("agents.vk", "vk"),
    ("agents.ok", "ok"),
    ("agents.likee", "likee"),
    ("agents.snapchat", "snapchat"),
    ("agents.discord", "discord"),
    ("agents.telegram", "telegram"),
    ("agents.whatsapp", "whatsapp"),
    ("agents.ted", "ted"),
    ("agents.skillshare", "skillshare"),
    ("agents.coursera", "coursera"),
    ("agents.udemy", "udemy"),

    # Audio & Music
    ("agents.spotify", "spotify"),
    ("agents.soundcloud", "soundcloud"),
    ("agents.bandcamp", "bandcamp"),
    ("agents.youtube_music", "youtube_music"),
    ("agents.apple_music", "apple_music"),
    ("agents.tidal", "tidal"),
    ("agents.deezer", "deezer"),
    ("agents.amazon_music", "amazon_music"),
    ("agents.mixcloud", "mixcloud"),
    ("agents.reverbnation", "reverbnation"),
    ("agents.soundclick", "soundclick"),

    # Cloud & Storage
    ("agents.google_drive", "google_drive"),
    ("agents.dropbox", "dropbox"),
    ("agents.onedrive", "onedrive"),
    ("agents.mega", "mega"),
    ("agents.s3", "s3"),
    ("agents.webdav", "webdav"),
]


def _import_and_register(registry: AgentRegistry) -> Tuple[int, int, List[str]]:
    """
    Import all agent modules and register them with the registry.
    
    Returns:
        Tuple of (success_count, fail_count, failed_modules)
    """
    success_count = 0
    fail_count = 0
    failed_modules: List[str] = []

    for module_path, agent_name in _AGENT_MODULES:
        try:
            import importlib
            module = importlib.import_module(module_path)
            if hasattr(module, "register"):
                name, skill = module.register()
                registry.register(name, skill)
                success_count += 1
                logger.debug("Registered agent: %s", name)
            else:
                logger.warning("Agent module %s has no register() function", module_path)
                fail_count += 1
                failed_modules.append(agent_name)
        except ImportError as exc:
            logger.warning("Failed to import agent %s: %s", agent_name, exc)
            fail_count += 1
            failed_modules.append(agent_name)
        except Exception as exc:
            logger.warning("Failed to register agent %s: %s", agent_name, exc)
            fail_count += 1
            failed_modules.append(agent_name)

    return success_count, fail_count, failed_modules


def get_registry() -> AgentRegistry:
    """
    Get the global agent registry, creating it if necessary.
    
    Returns:
        AgentRegistry with all available agents registered.
    """
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
        success, failed, failed_names = _import_and_register(_registry)
        logger.info(
            "Agent registry initialized: %d agents registered, %d failed [%s]",
            success, failed, ", ".join(failed_names) if failed_names else "none",
        )
    return _registry


def list_all_agents() -> List[Dict[str, Any]]:
    """
    List all registered agents with their capabilities.
    
    Returns:
        List of agent info dicts.
    """
    registry = get_registry()
    return registry.list_all()


def get_agent_by_name(name: str) -> Optional[Dict[str, Any]]:
    """
    Get a specific agent by name.
    
    Args:
        name: Agent name (e.g., "youtube", "spotify").
        
    Returns:
        Agent info dict or None.
    """
    registry = get_registry()
    return registry.get(name)


def get_agents_by_platform(platform: str) -> List[Dict[str, Any]]:
    """
    Find all agents supporting a specific platform.
    
    Args:
        platform: Platform name (e.g., "youtube", "spotify").
        
    Returns:
        List of matching agent info dicts.
    """
    registry = get_registry()
    return registry.find_by_platform(platform)


def get_agents_by_format(fmt: str) -> List[Dict[str, Any]]:
    """
    Find all agents supporting a specific format.
    
    Args:
        fmt: Format name (e.g., "mp4", "mp3").
        
    Returns:
        List of matching agent info dicts.
    """
    registry = get_registry()
    return registry.find_by_format(fmt)


def get_agents_by_feature(feature: str) -> List[Dict[str, Any]]:
    """
    Find all agents with a specific feature.
    
    Args:
        feature: Feature name (e.g., "playlist", "livestream").
        
    Returns:
        List of matching agent info dicts.
    """
    registry = get_registry()
    return registry.find_by_feature(feature)


def reset_registry() -> None:
    """Reset the registry (useful for testing or hot-reload)."""
    global _registry
    _registry = None


# ---------------------------------------------------------------------------
# Agent category mappings for UI organization
# ---------------------------------------------------------------------------

AGENT_CATEGORIES: Dict[str, List[str]] = {
    "Images & Art": [
        "unsplash", "pexels", "imgur", "giphy", "tenor",
        "flickr", "deviantart", "artstation",
    ],
    "Books & Audio": [
        "librivox", "gutenberg", "audible", "podcast", "ebook",
    ],
    "Asian Platforms": [
        "bilibili", "douyin", "naver", "kakao",
    ],
    "P2P & Privacy": [
        "torrent", "tor", "ipfs",
    ],
    "Content Creators": [
        "patreon", "onlyfans",
    ],
    "Content & Archive": [
        "archive_org",
    ],
    "Video Platforms": [
        "youtube", "vimeo", "dailymotion", "tiktok", "facebook", "twitter",
        "instagram", "reddit", "tumblr", "twitch", "kick", "rumble",
        "bitchute", "odysee", "niconico", "vimeo_enterprise", "loom",
        "periscope", "wistia", "live", "weibo", "vk", "ok", "likee",
        "snapchat", "discord", "telegram", "whatsapp", "ted",
        "skillshare", "coursera", "udemy",
    ],
    "Audio & Music": [
        "spotify", "soundcloud", "bandcamp", "youtube_music",
        "apple_music", "tidal", "deezer", "amazon_music",
        "mixcloud", "reverbnation", "soundclick",
    ],
    "Cloud & Storage": [
        "google_drive", "dropbox", "onedrive", "mega", "s3", "webdav",
    ],
    "Utility": [
        "metadata", "subtitle", "thumbnail", "convert", "search",
        "stream", "ai", "analytics", "batch", "playlist", "cloud",
    ],
}


def get_category_for_agent(agent_name: str) -> str:
    """Get the category for a given agent name."""
    for category, agents in AGENT_CATEGORIES.items():
        if agent_name in agents:
            return category
    return "Other"


def get_agents_in_category(category: str) -> List[str]:
    """Get all agent names in a given category."""
    return AGENT_CATEGORIES.get(category, [])


def get_all_categories() -> List[str]:
    """Get all agent category names."""
    return list(AGENT_CATEGORIES.keys())


# ---------------------------------------------------------------------------
# Convenience exports
# ---------------------------------------------------------------------------

__all__ = [
    "AGENT_COUNT",
    "get_registry",
    "list_all_agents",
    "get_agent_by_name",
    "get_agents_by_platform",
    "get_agents_by_format",
    "get_agents_by_feature",
    "reset_registry",
    "AGENT_CATEGORIES",
    "get_category_for_agent",
    "get_agents_in_category",
    "get_all_categories",
]
