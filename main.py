"""Morning Market Intelligence Brief — main pipeline orchestrator.

Runs Steps 0–6 sequentially:
  0. Cleanup ephemeral data
  1. Fetch + dedup RSS feeds
  2. Triage (8x parallel Haiku agents)
  3. Analysis (Nx parallel Sonnet agents with web search)
  4. Memory curation (Haiku agent + Python safety net)
  5. Personalisation (Mx parallel Haiku agents)
  6. Delivery (Teams webhooks)
"""

import asyncio
import logging
import sys
import time

from steps import cleanup, fetch
from steps.deliver import run as deliver
from agents import triage, analysis, memory, personalise
from config import PERSONALISED_DIR
from utils.io import write_text


def _setup_logging() -> None:
    """Configure structured logging with timestamps."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


async def _run_pipeline() -> None:
    """Execute the full pipeline."""
    start = time.monotonic()

    # Step 0 — Cleanup
    logging.info("=" * 60)
    logging.info("STEP 0 — Cleanup")
    logging.info("=" * 60)
    cleanup.run()

    # Step 1 — Fetch
    logging.info("=" * 60)
    logging.info("STEP 1 — Fetch + Dedup")
    logging.info("=" * 60)
    articles = fetch.run()

    if not articles:
        logging.warning("No articles fetched — exiting early")
        return

    # Step 2 — Triage
    logging.info("=" * 60)
    logging.info("STEP 2 — Triage (8x parallel)")
    logging.info("=" * 60)
    notable = await triage.run()

    if not notable:
        logging.info("No notable stories — sending quiet briefs")
        # Write quiet brief for each user and deliver
        from config import USERS_FILE
        from utils.io import read_json
        if USERS_FILE.exists():
            users = read_json(USERS_FILE)
            if isinstance(users, list):
                for user in users:
                    username = user.get("username", "unknown")
                    write_text(
                        PERSONALISED_DIR / f"{username}.md",
                        "No market-moving developments overnight. All quiet on your positions.",
                    )
        deliver(quiet=True)
        elapsed = time.monotonic() - start
        logging.info("Pipeline complete (quiet brief) in %.1fs", elapsed)
        return

    # Step 3 — Analysis
    logging.info("=" * 60)
    logging.info("STEP 3 — Analysis (%dx parallel)", len(notable))
    logging.info("=" * 60)
    analyses = await analysis.run(notable)

    # Step 4 — Memory Curation
    logging.info("=" * 60)
    logging.info("STEP 4 — Memory Curation")
    logging.info("=" * 60)
    await memory.run()

    # Step 5 — Personalisation
    logging.info("=" * 60)
    logging.info("STEP 5 — Personalisation")
    logging.info("=" * 60)
    briefs = await personalise.run(analyses)

    # Step 6 — Delivery
    logging.info("=" * 60)
    logging.info("STEP 6 — Delivery")
    logging.info("=" * 60)
    deliver()

    elapsed = time.monotonic() - start
    logging.info("=" * 60)
    logging.info(
        "Pipeline complete — %d articles, %d notable, %d analysed, %d briefs in %.1fs",
        len(articles),
        len(notable),
        len(analyses),
        len(briefs),
        elapsed,
    )


def main() -> None:
    """Entry point."""
    _setup_logging()
    asyncio.run(_run_pipeline())


if __name__ == "__main__":
    main()
