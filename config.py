"""Central configuration for the Morning Market Intelligence Brief pipeline.

All tuneable values, paths, feed URLs, asset tags, and model selections
live here. Every other module imports from this file.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT: Path = Path(__file__).parent
DATA_DIR: Path = PROJECT_ROOT / "data"
FEEDS_DIR: Path = DATA_DIR / "feeds"
TRIAGE_DIR: Path = DATA_DIR / "triage"
ANALYSIS_DIR: Path = DATA_DIR / "analysis"
PERSONALISED_DIR: Path = DATA_DIR / "personalised"
PROMPTS_DIR: Path = PROJECT_ROOT / "prompts"

ARTICLES_FILE: Path = DATA_DIR / "articles.json"
NOTABLES_FILE: Path = DATA_DIR / "todays_notable.json"
MEMORY_FILE: Path = DATA_DIR / "memory.md"
USERS_FILE: Path = DATA_DIR / "users.json"

# Ephemeral paths — safe to clear on each run
EPHEMERAL_DIRS: list[Path] = [FEEDS_DIR, TRIAGE_DIR, ANALYSIS_DIR, PERSONALISED_DIR]
EPHEMERAL_FILES: list[Path] = [ARTICLES_FILE, NOTABLES_FILE]

# ---------------------------------------------------------------------------
# API Keys
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY: str = os.environ.get("ANTHROPIC_API_KEY", "")

# ---------------------------------------------------------------------------
# Models (Claude model identifiers for Agent SDK)
# ---------------------------------------------------------------------------
HAIKU_MODEL: str = "claude-haiku-4-5"
SONNET_MODEL: str = "claude-sonnet-4-6"

# ---------------------------------------------------------------------------
# RSS Feed URLs — Google News
# ---------------------------------------------------------------------------
FEEDS: list[dict[str, str]] = [
    {"name": "us_headlines", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-US&topic=h&num=100&gl=US&ceid=US:en"},
    {"name": "us_world", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-US&topic=w&num=100&gl=US&ceid=US:en"},
    {"name": "us_business", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-US&topic=b&num=100&gl=US&ceid=US:en"},
    {"name": "us_technology", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-US&topic=tc&num=100&gl=US&ceid=US:en"},
    {"name": "au_headlines", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-AU&topic=h&num=100&gl=AU&ceid=AU:en"},
    {"name": "au_world", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-AU&topic=w&num=100&gl=AU&ceid=AU:en"},
    {"name": "au_business", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-AU&topic=b&num=100&gl=AU&ceid=AU:en"},
    {"name": "us_science", "url": "https://news.google.com/rss?pz=1&cf=all&hl=en-US&topic=snc&num=100&gl=US&ceid=US:en"},
]

# ---------------------------------------------------------------------------
# Triage
# ---------------------------------------------------------------------------
TRIAGE_CHUNK_COUNT: int = 8
ARTICLE_MAX_AGE_HOURS: int = 24

# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------
MAX_ACTIVE_STORIES: int = 15
STALE_CLOSE_DAYS: int = 21
PURGE_CLOSED_DAYS: int = 30

# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------
MAX_WEB_SEARCHES_PER_STORY: int = 3

# ---------------------------------------------------------------------------
# Personalisation
# ---------------------------------------------------------------------------
MAX_PERSONALISE_STORIES: int = 8
MIN_PERSONALISE_SEVERITY: int = 7

# ---------------------------------------------------------------------------
# Asset Tag Taxonomy
# Included in triage prompts to ensure consistent tagging across agents.
# ---------------------------------------------------------------------------
ASSET_TAGS: list[str] = [
    "equities_us", "equities_tech", "equities_eu", "equities_au",
    "equities_em", "equities_japan",
    "bonds_us", "bonds_eu", "bonds_au", "bonds_em",
    "usd", "eur", "aud", "gbp", "jpy", "cny", "em_fx",
    "gold", "silver", "oil", "natural_gas",
    "commodities_iron", "commodities_copper", "commodities_agri",
    "crypto_btc", "crypto_eth", "crypto_broad",
    "real_estate_us", "real_estate_au",
]
