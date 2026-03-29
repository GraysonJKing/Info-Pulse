"""Step 3 — Analysis: N x parallel Sonnet agents with web search.

One analyst agent per notable story. Each performs web searches,
reasons about impacts, finds historical analogues, and writes
structured JSON to data/analysis/{slug}.json.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone

from claude_agent_sdk import ResultMessage, query

from agents.definitions import analyst_options
from config import ANALYSIS_DIR
from utils.io import parse_llm_json, write_json
from utils.slugify import slugify

logger = logging.getLogger(__name__)


async def _analyse_story(story: dict) -> dict | None:
    """Run a single analyst agent on one story.

    Args:
        story: Notable story dict from triage output.

    Returns:
        Enriched analysis dict, or None on failure.
    """
    title = story.get("title", "Unknown")
    slug = slugify(title)

    prompt = (
        f"## Story to Analyse\n"
        f"**Title:** {title}\n"
        f"**Source:** {story.get('source', 'Unknown')}\n"
        f"**Published:** {story.get('published', 'Unknown')}\n"
        f"**Triage Severity:** {story.get('severity', 'N/A')}\n"
        f"**Triage Rationale:** {story.get('rationale', 'N/A')}\n"
        f"**Asset Tags:** {json.dumps(story.get('asset_tags', []))}\n\n"
        f"Use the slug: {slug}\n"
        f"Set analysed_at to: {datetime.now(timezone.utc).isoformat()}"
    )

    options = analyst_options()
    result_text = ""

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result_text = message.result

    if not result_text.strip():
        logger.warning("Analyst for '%s' returned empty response", title)
        return None

    try:
        analysis = parse_llm_json(result_text)
    except (ValueError, json.JSONDecodeError):
        logger.exception("Analyst for '%s': failed to parse response", title)
        return None

    if not isinstance(analysis, dict):
        logger.warning("Analyst for '%s': expected dict, got %s", title, type(analysis).__name__)
        return None

    # Ensure slug is set
    analysis.setdefault("slug", slug)

    # Write to file
    output_path = ANALYSIS_DIR / f"{slug}.json"
    write_json(output_path, analysis)
    logger.info("Analysed: %s (severity %s)", title, analysis.get("severity", "?"))

    return analysis


async def run(notable_stories: list[dict]) -> list[dict]:
    """Run analyst agents in parallel for all notable stories.

    Args:
        notable_stories: List of stories from triage output.

    Returns:
        List of analysis dicts (failures filtered out).
    """
    if not notable_stories:
        logger.info("Step 3 skipped — no notable stories to analyse")
        return []

    tasks = [_analyse_story(story) for story in notable_stories]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    analyses: list[dict] = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            logger.error("Analyst %d failed: %s", i, result)
        elif result is not None:
            analyses.append(result)

    logger.info("Step 3 complete — %d/%d stories analysed", len(analyses), len(notable_stories))
    return analyses
