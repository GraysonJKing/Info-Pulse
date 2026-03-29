"""Step 5 — Personalisation: M x parallel Haiku agents.

One personaliser agent per user. Each receives all analysis results,
memory context, and the user's positions, then produces a tailored brief.
"""

import asyncio
import json
import logging

from claude_agent_sdk import ResultMessage, query

from agents.definitions import personalise_options
from config import ANALYSIS_DIR, MAX_PERSONALISE_STORIES, MEMORY_FILE, MIN_PERSONALISE_SEVERITY, PERSONALISED_DIR, USERS_FILE
from utils.io import read_json, read_text, write_text

logger = logging.getLogger(__name__)


def _load_analyses() -> str:
    """Load analysis JSON files, filtered by severity floor, capped at MAX_STORIES."""
    analysis_files = sorted(ANALYSIS_DIR.glob("*.json"))
    if not analysis_files:
        return "[]"

    analyses = []
    for path in analysis_files:
        try:
            analyses.append(read_json(path))
        except Exception:
            logger.exception("Failed to read analysis file %s", path.name)

    # Filter by severity floor, sort descending, cap
    analyses = [a for a in analyses if a.get("severity", 0) >= MIN_PERSONALISE_SEVERITY]
    analyses.sort(key=lambda a: a.get("severity", 0), reverse=True)
    analyses = analyses[:MAX_PERSONALISE_STORIES]
    logger.info("Sending %d stories to personaliser (severity >= %d, max %d)", len(analyses), MIN_PERSONALISE_SEVERITY, MAX_PERSONALISE_STORIES)

    return json.dumps(analyses, indent=2)


async def _personalise_for_user(user: dict, analyses_text: str, memory_text: str) -> str | None:
    """Run a personaliser agent for one user.

    Args:
        user: User dict from users.json.
        analyses_text: All analysis results as JSON string.
        memory_text: Current memory.md content.

    Returns:
        The personalised brief as markdown, or None on failure.
    """
    username = user.get("username", "unknown")
    display_name = user.get("display_name", username)
    positions = user.get("positions", [])

    prompt = (
        f"## User: {display_name}\n\n"
        f"### Positions\n{json.dumps(positions, indent=2)}\n\n"
        f"### Current Memory (ongoing stories)\n{memory_text}\n\n"
        f"### Today's Analysis Results\n{analyses_text}"
    )

    options = personalise_options()
    result_text = ""

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result_text = message.result

    if not result_text.strip():
        logger.warning("Personaliser for '%s' returned empty response", username)
        return None

    # Write to file
    output_path = PERSONALISED_DIR / f"{username}.md"
    write_text(output_path, result_text)
    logger.info("Personalised brief written for %s", username)

    return result_text


async def run(analyses: list[dict]) -> dict[str, str]:
    """Run personaliser agents in parallel for all users.

    Args:
        analyses: List of analysis dicts (used to check if any exist).

    Returns:
        Dict mapping username to brief content.
    """
    if not USERS_FILE.exists():
        logger.error("users.json not found — skipping personalisation")
        return {}

    users = read_json(USERS_FILE)
    if not isinstance(users, list) or not users:
        logger.warning("No users configured in users.json")
        return {}

    analyses_text = _load_analyses()
    memory_text = read_text(MEMORY_FILE) if MEMORY_FILE.exists() else ""

    tasks = [_personalise_for_user(user, analyses_text, memory_text) for user in users]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    briefs: dict[str, str] = {}
    for i, result in enumerate(results):
        username = users[i].get("username", f"user_{i}")
        if isinstance(result, Exception):
            logger.error("Personaliser for '%s' failed: %s", username, result)
        elif result is not None:
            briefs[username] = result

    logger.info("Step 5 complete — %d/%d briefs generated", len(briefs), len(users))
    return briefs
