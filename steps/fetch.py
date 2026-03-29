"""Step 1 — RSS fetch, dedup, age filter, and chunking.

Polls 8 Google News RSS feeds, deduplicates by GUID, discards articles
older than 24 hours, writes the full list to articles.json, and splits
into 8 chunk files for parallel triage.
"""

import logging
import math
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import feedparser

from config import (
    ARTICLE_MAX_AGE_HOURS,
    ARTICLES_FILE,
    FEEDS,
    FEEDS_DIR,
    TRIAGE_CHUNK_COUNT,
)
from utils.io import write_json

logger = logging.getLogger(__name__)


def _parse_entry(entry: dict, feed_name: str) -> dict | None:
    """Parse a single RSS entry into our article schema.

    Returns None if the entry is missing required fields or is too old.
    """
    guid = entry.get("id", entry.get("link", ""))
    if not guid:
        return None

    title = entry.get("title", "").strip()
    if not title:
        return None

    # Parse publication date and enforce age limit
    published_str = entry.get("published", "")
    if not published_str:
        return None

    try:
        pub_dt = parsedate_to_datetime(published_str)
    except (ValueError, TypeError):
        return None

    # Ensure timezone-aware for comparison
    if pub_dt.tzinfo is None:
        pub_dt = pub_dt.replace(tzinfo=timezone.utc)

    age_hours = (datetime.now(timezone.utc) - pub_dt).total_seconds() / 3600
    if age_hours > ARTICLE_MAX_AGE_HOURS:
        return None

    # Extract source info
    source_tag = entry.get("source", {})
    source = source_tag.get("title", "") if isinstance(source_tag, dict) else str(source_tag)
    source_url = source_tag.get("href", "") if isinstance(source_tag, dict) else ""

    return {
        "guid": guid,
        "title": title,
        "link": entry.get("link", ""),
        "source": source,
        "source_url": source_url,
        "published": pub_dt.isoformat(),
        "feed_name": feed_name,
    }


def run() -> list[dict]:
    """Fetch, dedup, filter, chunk, and return all articles.

    Returns:
        List of all deduplicated, age-filtered articles.
    """
    seen_guids: set[str] = set()
    articles: list[dict] = []

    for feed_cfg in FEEDS:
        name = feed_cfg["name"]
        url = feed_cfg["url"]
        logger.info("Fetching %s ...", name)

        try:
            parsed = feedparser.parse(url)
        except Exception:
            logger.exception("Failed to fetch feed %s", name)
            continue

        count = 0
        for entry in parsed.entries:
            article = _parse_entry(entry, name)
            if article is None:
                continue
            if article["guid"] in seen_guids:
                continue
            seen_guids.add(article["guid"])
            articles.append(article)
            count += 1

        logger.info("  %s: %d articles after dedup + age filter", name, count)

    logger.info("Total articles: %d", len(articles))

    # Write full article list
    write_json(ARTICLES_FILE, articles)

    # Split into chunks for parallel triage
    chunk_size = max(1, math.ceil(len(articles) / TRIAGE_CHUNK_COUNT))
    for i in range(TRIAGE_CHUNK_COUNT):
        chunk = articles[i * chunk_size : (i + 1) * chunk_size]
        write_json(FEEDS_DIR / f"chunk_{i}.json", chunk)
        logger.info("  chunk_%d: %d articles", i, len(chunk))

    logger.info("Step 1 complete — %d articles across %d chunks", len(articles), TRIAGE_CHUNK_COUNT)
    return articles
