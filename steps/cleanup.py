"""Step 0 — Startup cleanup.

Clears all ephemeral files and directories from the previous run.
Never touches persistent files (memory.md, users.json).
"""

import logging
import shutil

from config import EPHEMERAL_DIRS, EPHEMERAL_FILES

logger = logging.getLogger(__name__)


def run() -> None:
    """Clear ephemeral data from the previous pipeline run."""
    for directory in EPHEMERAL_DIRS:
        if directory.exists():
            # Clear contents but keep the directory (avoids OneDrive/Windows lock issues)
            for child in directory.iterdir():
                try:
                    if child.is_file():
                        child.unlink()
                    elif child.is_dir():
                        shutil.rmtree(child)
                except PermissionError:
                    logger.warning("Could not delete %s (locked) — skipping", child.name)
            logger.info("Cleared %s", directory.name)
        directory.mkdir(parents=True, exist_ok=True)

    for filepath in EPHEMERAL_FILES:
        if filepath.exists():
            try:
                filepath.unlink()
                logger.info("Deleted %s", filepath.name)
            except PermissionError:
                logger.warning("Could not delete %s (locked) — skipping", filepath.name)

    logger.info("Step 0 complete — ephemeral data cleared")
