"""Step 4 — Memory curation: single Haiku agent + Python safety net.

The LLM curator updates memory.md with today's notable stories (ADD,
UPDATE, CLOSE decisions). Python then enforces hard time limits and
the 15-story cap.
"""

import json
import logging
import re
from datetime import datetime, timezone, timedelta

from claude_agent_sdk import ResultMessage, query

from agents.definitions import memory_options
from config import MAX_ACTIVE_STORIES, MEMORY_FILE, NOTABLES_FILE, PURGE_CLOSED_DAYS, STALE_CLOSE_DAYS
from utils.io import read_text, write_text, read_json

logger = logging.getLogger(__name__)


async def _curate_with_llm(memory_text: str, notables_text: str) -> str:
    """Ask the curator agent to update memory.md.

    Args:
        memory_text: Current memory.md content.
        notables_text: Today's notable stories as JSON.

    Returns:
        Updated memory.md content from the agent.
    """
    prompt = (
        f"## Current memory.md\n{memory_text}\n\n"
        f"## Today's Notable Stories\n{notables_text}\n\n"
        f"Today's date is {datetime.now(timezone.utc).strftime('%Y-%m-%d')}.\n"
        f"Max active stories: {MAX_ACTIVE_STORIES}."
    )

    options = memory_options()
    result_text = ""

    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result_text = message.result

    return result_text.strip()


def _python_safety_net(memory_content: str) -> str:
    """Enforce hard time limits and story cap on memory content.

    - Hard-close anything not updated in STALE_CLOSE_DAYS days
    - Purge closed stories older than PURGE_CLOSED_DAYS days
    - Enforce MAX_ACTIVE_STORIES cap
    """
    today = datetime.now(timezone.utc).date()
    sections = re.split(r"(?=^### )", memory_content, flags=re.MULTILINE)

    header = ""
    stories: list[str] = []
    for section in sections:
        if section.strip().startswith("### "):
            stories.append(section)
        else:
            header += section

    active: list[tuple[str, int, str]] = []  # (section, severity, last_updated)
    kept_closed: list[str] = []
    modified = False

    for story in stories:
        is_closed = bool(re.search(r"\*\*Status:\*\*\s*CLOSED", story, re.IGNORECASE))

        # Extract last updated date
        last_match = re.search(r"\*\*Last Updated:\*\*\s*(\d{4}-\d{2}-\d{2})", story)
        last_updated = last_match.group(1) if last_match else None

        # Extract closed date
        closed_match = re.search(r"\*\*Closed:\*\*.*?(\d{4}-\d{2}-\d{2})", story)
        closed_date = closed_match.group(1) if closed_match else None

        # Extract severity
        sev_match = re.search(r"\*\*Severity:\*\*\s*(\d+)", story)
        severity = int(sev_match.group(1)) if sev_match else 0

        if is_closed:
            # Purge closed stories older than PURGE_CLOSED_DAYS
            if closed_date:
                closed_dt = datetime.strptime(closed_date, "%Y-%m-%d").date()
                if (today - closed_dt).days > PURGE_CLOSED_DAYS:
                    logger.info("Purging closed story older than %d days", PURGE_CLOSED_DAYS)
                    modified = True
                    continue
            kept_closed.append(story)
        else:
            # Hard-close stale stories
            if last_updated:
                last_dt = datetime.strptime(last_updated, "%Y-%m-%d").date()
                if (today - last_dt).days > STALE_CLOSE_DAYS:
                    story = re.sub(
                        r"(\*\*Status:\*\*)\s*\S+",
                        f"\\1 CLOSED",
                        story,
                    )
                    story = story.rstrip() + f"\n- **Closed:** {today.isoformat()} | Reason: Stale — no update in {STALE_CLOSE_DAYS}+ days\n"
                    kept_closed.append(story)
                    logger.info("Hard-closed stale story")
                    modified = True
                    continue

            active.append((story, severity, last_updated or ""))

    # Enforce cap — close least severe if over limit
    if len(active) > MAX_ACTIVE_STORIES:
        active.sort(key=lambda x: x[1], reverse=True)
        for story_text, sev, _ in active[MAX_ACTIVE_STORIES:]:
            closed_story = re.sub(
                r"(\*\*Status:\*\*)\s*\S+",
                f"\\1 CLOSED",
                story_text,
            )
            closed_story = closed_story.rstrip() + f"\n- **Closed:** {today.isoformat()} | Reason: Cap exceeded — lowest severity\n"
            kept_closed.append(closed_story)
            logger.info("Closed story (cap exceeded, severity %d)", sev)
            modified = True
        active = active[:MAX_ACTIVE_STORIES]

    # Reassemble
    result = header
    for story_text, _, _ in active:
        result += story_text
    for story_text in kept_closed:
        result += story_text

    if modified:
        logger.info("Python safety net made modifications to memory")

    return result


async def run() -> None:
    """Run memory curation: LLM curator then Python safety net."""
    memory_text = read_text(MEMORY_FILE) if MEMORY_FILE.exists() else ""

    # Load today's notable stories
    if NOTABLES_FILE.exists():
        notables = read_json(NOTABLES_FILE)
        notables_text = json.dumps(notables, indent=2)
    else:
        notables_text = "[]"
        notables = []

    if not notables:
        logger.info("No notable stories today — running safety net only")
        updated = _python_safety_net(memory_text)
        write_text(MEMORY_FILE, updated)
        logger.info("Step 4 complete — safety net only (no new stories)")
        return

    # LLM curation
    try:
        llm_result = await _curate_with_llm(memory_text, notables_text)
        if llm_result:
            memory_text = llm_result
            logger.info("LLM curator returned updated memory")
        else:
            logger.warning("LLM curator returned empty — using existing memory")
    except Exception:
        logger.exception("LLM curator failed — falling back to existing memory")

    # Python safety net always runs
    final = _python_safety_net(memory_text)
    write_text(MEMORY_FILE, final)
    logger.info("Step 4 complete — memory updated")
