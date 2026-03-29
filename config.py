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
# RSS Feed URLs — Google News (topic feeds + targeted search feeds)
# ---------------------------------------------------------------------------
FEEDS: list[str] = [
    # Broad headlines (black swan safety net)
    "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss?hl=en-AU&gl=AU&ceid=AU:en",
    "https://news.google.com/rss/headlines/section/topic/WORLD?hl=en-US&gl=US&ceid=US:en",
    "https://news.google.com/rss/headlines/section/topic/BUSINESS?hl=en-US&gl=US&ceid=US:en",
    # Macro / rates
    "https://news.google.com/rss/search?q=federal+reserve+interest+rate&when:1d&ceid=US:en&hl=en-US&gl=US",
    "https://news.google.com/rss/search?q=RBA+interest+rate+australia&when:1d&ceid=AU:en&hl=en-AU&gl=AU",
    "https://news.google.com/rss/search?q=inflation+CPI+economy&when:1d&ceid=US:en&hl=en-US&gl=US",
    # Geopolitics
    "https://news.google.com/rss/search?q=war+sanctions+military+strike&when:1d&ceid=US:en&hl=en-US&gl=US",
    "https://news.google.com/rss/search?q=iran+china+russia+geopolitics&when:1d&ceid=US:en&hl=en-US&gl=US",
    "https://news.google.com/rss/search?q=tariff+trade+deal+sanctions&when:1d&ceid=US:en&hl=en-US&gl=US",
    # Energy / commodities
    "https://news.google.com/rss/search?q=oil+price+opec+gas+energy&when:1d&ceid=US:en&hl=en-US&gl=US",
    "https://news.google.com/rss/search?q=lithium+iron+ore+copper+commodities&when:1d&ceid=AU:en&hl=en-AU&gl=AU",
    # ASX / Australia
    "https://news.google.com/rss/search?q=ASX+australia+market+shares&when:1d&ceid=AU:en&hl=en-AU&gl=AU",
    "https://news.google.com/rss/search?q=woodside+BHP+rio+tinto+fortescue&when:1d&ceid=AU:en&hl=en-AU&gl=AU",
    # US markets
    "https://news.google.com/rss/search?q=nasdaq+sp500+wall+street+earnings&when:1d&ceid=US:en&hl=en-US&gl=US",
    "https://news.google.com/rss/search?q=tesla+nvidia+apple+microsoft+earnings&when:1d&ceid=US:en&hl=en-US&gl=US",
    # Currencies
    "https://news.google.com/rss/search?q=USD+AUD+JPY+dollar+currency&when:1d&ceid=US:en&hl=en-US&gl=US",
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
