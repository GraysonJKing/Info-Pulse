"""Step 2 — Triage: 8x parallel Haiku agents scoring articles.

Each agent receives one chunk of articles plus memory.md context,
scores them for market relevance, and returns notable stories.
Python merges shards, deduplicates, and writes todays_notable.json.
"""

import asyncio
import json
import logging

from claude_agent_sdk import ResultMessage, query

from claude_agent_sdk import ClaudeAgentOptions

from agents.definitions import triage_options
from config import ASSET_TAGS, FEEDS_DIR, HAIKU_MODEL, MEMORY_FILE, NOTABLES_FILE, TRIAGE_CHUNK_COUNT, TRIAGE_DIR
from utils.error_logging import describe_exception
from utils.io import parse_llm_json, read_json, read_text, write_json

logger = logging.getLogger(__name__)


async def _triage_chunk(chunk_index: int, memory_text: str) -> list[dict]:
    """Run a single triage agent on one chunk.

    Args:
        chunk_index: Which chunk file to process (0–7).
        memory_text: Current contents of memory.md.

    Returns:
        List of notable article dicts from this chunk.
    """
    chunk_path = FEEDS_DIR / f"chunk_{chunk_index}.json"
    if not chunk_path.exists():
        logger.warning("Chunk file %s does not exist, skipping", chunk_path)
        return []

    articles = read_json(chunk_path)
    if not articles:
        return []

    prompt = (
        f"## Asset Tag Taxonomy\n{json.dumps(ASSET_TAGS)}\n\n"
        f"## Current Memory (ongoing stories)\n{memory_text}\n\n"
        f"## Articles to Triage ({len(articles)} items)\n{json.dumps(articles, indent=2)}"
    )

    options = triage_options()
    result_text = ""

    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result
    except Exception as exc:
        logger.exception("Shard %d: triage query failed\n%s", chunk_index, describe_exception(exc))
        raise

    if not result_text.strip():
        logger.warning("Shard %d: agent returned empty response", chunk_index)
        return []

    try:
        notable = parse_llm_json(result_text)
    except (ValueError, json.JSONDecodeError):
        logger.exception("Shard %d: failed to parse agent response", chunk_index)
        return []

    if not isinstance(notable, list):
        logger.warning("Shard %d: expected list, got %s", chunk_index, type(notable).__name__)
        return []

    logger.info("Shard %d: %d notable stories", chunk_index, len(notable))
    return notable


async def run() -> list[dict]:
    """Run all 8 triage agents in parallel, merge, dedup, and sort.

    Returns:
        Sorted list of notable stories (highest severity first).
    """
    memory_text = read_text(MEMORY_FILE) if MEMORY_FILE.exists() else ""

    tasks = [_triage_chunk(i, memory_text) for i in range(TRIAGE_CHUNK_COUNT)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Merge shards and write individual shard files
    all_notable: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Shard %d failed\n%s", i, describe_exception(result))
            shard_data = []
        else:
            shard_data = result

        write_json(TRIAGE_DIR / f"shard_{i}.json", shard_data)
        all_notable.extend(shard_data)

    # Deduplicate by guid
    seen: set[str] = set()
    deduped: list[dict] = []
    for story in all_notable:
        guid = story.get("guid", "")
        if guid and guid not in seen:
            seen.add(guid)
            deduped.append(story)

    # Sort by severity descending
    deduped.sort(key=lambda s: s.get("severity", 0), reverse=True)

    # Topic-level dedup: cluster articles about the same event
    if len(deduped) > 1:
        deduped = await _cluster_by_topic(deduped)

    write_json(NOTABLES_FILE, deduped)
    logger.info("Step 2 complete — %d notable stories after topic clustering", len(deduped))

    return deduped


async def _cluster_by_topic(stories: list[dict]) -> list[dict]:
    """Use Haiku to cluster articles by topic and keep one per cluster.

    For each cluster, keeps the article with the highest severity.
    Merges source info from duplicates into the representative article.
    """
    # Build a lightweight summary for the LLM (just index, title, source)
    story_list = "\n".join(
        f"{i}: [{s.get('severity', '?')}] {s.get('title', '')} — {s.get('source', '')}"
        for i, s in enumerate(stories)
    )

    prompt = (
        "Below is a numbered list of news articles with severity scores.\n"
        "Many articles cover the SAME underlying story from different outlets.\n\n"
        "Group them into clusters by topic. For each cluster, return the index "
        "of the BEST representative article (prefer the highest severity, then "
        "the most informative title).\n\n"
        f"## Articles\n{story_list}\n\n"
        "## Output\n"
        "Return a JSON array of objects, one per cluster:\n"
        '[{"topic": "short topic name", "representative": 0, "duplicates": [1, 3, 5]}]\n\n'
        "representative = index of the best article to keep.\n"
        "duplicates = indices of other articles in the same cluster (can be empty []).\n"
        "Every article index must appear exactly once across all clusters.\n"
        "Return ONLY the JSON array."
    )

    options = ClaudeAgentOptions(
        model=HAIKU_MODEL,
        allowed_tools=[],
        max_turns=1,
    )

    result_text = ""
    try:
        async for message in query(prompt=prompt, options=options):
            if isinstance(message, ResultMessage):
                result_text = message.result
    except Exception as exc:
        logger.exception("Topic clustering query failed\n%s", describe_exception(exc))
        return stories

    if not result_text.strip():
        logger.warning("Topic clustering returned empty — skipping")
        return stories

    try:
        clusters = parse_llm_json(result_text)
    except (ValueError, json.JSONDecodeError):
        logger.exception("Topic clustering: failed to parse response — skipping")
        return stories

    if not isinstance(clusters, list):
        logger.warning("Topic clustering: expected list, got %s — skipping", type(clusters).__name__)
        return stories

    # Build result: one article per cluster, merge sources from duplicates
    result: list[dict] = []
    for cluster in clusters:
        rep_idx = cluster.get("representative")
        if not isinstance(rep_idx, int) or rep_idx >= len(stories):
            continue

        article = stories[rep_idx].copy()

        # Merge asset_tags from duplicates
        dup_indices = cluster.get("duplicates", [])
        all_tags = set(article.get("asset_tags", []))
        max_severity = article.get("severity", 0)
        for idx in dup_indices:
            if isinstance(idx, int) and idx < len(stories):
                all_tags.update(stories[idx].get("asset_tags", []))
                max_severity = max(max_severity, stories[idx].get("severity", 0))

        article["asset_tags"] = sorted(all_tags)
        article["severity"] = max_severity
        result.append(article)

    # Sort by severity descending
    result.sort(key=lambda s: s.get("severity", 0), reverse=True)

    logger.info("Topic clustering: %d articles -> %d distinct topics", len(stories), len(result))
    return result
