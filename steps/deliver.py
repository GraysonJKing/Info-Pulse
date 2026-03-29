"""Step 6 — Delivery: post briefs to Microsoft Teams webhooks.

Reads each user's personalised brief markdown, converts to HTML,
and POSTs to their Teams webhook. Automatically chunks into multiple
messages if the payload exceeds the Teams size limit.
"""

import json
import logging
import os
import re
from urllib.request import Request, urlopen
from urllib.error import URLError

from config import PERSONALISED_DIR, USERS_FILE
from utils.io import read_json, read_text

logger = logging.getLogger(__name__)

MAX_PAYLOAD_BYTES = 18_000  # safe limit — Teams silently drops larger messages


def _get_teams_webhook(username: str) -> str:
    """Resolve Teams webhook URL for a user.

    Supported environment variable names:
    1) {username}_teams_webhook
    2) {USERNAME}_TEAMS_WEBHOOK
    """
    env_key_exact = f"{username}_teams_webhook"
    env_key_upper = f"{username.upper()}_TEAMS_WEBHOOK"

    return (
        os.environ.get(env_key_exact, "").strip()
        or os.environ.get(env_key_upper, "").strip()
    )


# ---------------------------------------------------------------------------
# Markdown → HTML conversion
# ---------------------------------------------------------------------------

def _md_to_html(md: str) -> str:
    """Convert a markdown brief into Teams-compatible HTML."""
    html = ""
    lines = md.split("\n")
    in_list = False

    for line in lines:
        stripped = line.strip()

        if not stripped:
            if in_list:
                html += "</ul>"
                in_list = False
            continue

        # --- separator
        if re.match(r"^-{3,}$", stripped):
            if in_list:
                html += "</ul>"
                in_list = False
            html += "<br><hr><br>"
            continue

        # ## Section heading (PORTFOLIO IMPACT, OPPORTUNITIES & RISKS)
        m = re.match(r"^##\s+(.+)$", stripped)
        if m:
            if in_list:
                html += "</ul>"
                in_list = False
            html += f'<p><span style="font-size:24px;font-weight:bold;color:#6264A7">{m.group(1)}</span></p>'
            continue

        # **Bold standalone line** (story headers)
        m = re.match(r"^\*\*(.+)\*\*$", stripped)
        if m:
            if in_list:
                html += "</ul>"
                in_list = False
            inner = m.group(1)
            inner = re.sub(
                r"\(Severity (\d+)\)",
                lambda x: f'<span style="color:#E74C3C">(Severity {x.group(1)})</span>',
                inner,
            )
            html += f'<p><span style="font-size:18px;font-weight:bold">{inner}</span></p><br>'
            continue

        # Bullet point
        m = re.match(r"^[-*]\s+(.+)$", stripped)
        if m:
            if not in_list:
                html += "<ul>"
                in_list = True
            bullet_text = _inline_formatting(m.group(1))
            html += f"<li>{bullet_text}</li>"
            continue

        # Regular text
        if in_list:
            html += "</ul>"
            in_list = False

        text = stripped
        # _Label:_ at start of line → bold coloured label
        text = re.sub(r"^_([^_]+?:)_\s*", r'<b style="color:#6264A7">\1</b> ', text)
        text = _inline_formatting(text)
        html += f"<p>{text}</p>"

    if in_list:
        html += "</ul>"

    return html


def _inline_formatting(text: str) -> str:
    """Apply inline bold and italic markdown to HTML."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"_([^_]+?)_", r"<i>\1</i>", text)
    return text


# ---------------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------------

def _build_payload(html: str) -> dict:
    """Wrap HTML in a Teams webhook payload."""
    return {"text": html}


def _payload_size(html: str) -> int:
    """Return the byte size of the JSON payload for a given HTML string."""
    return len(json.dumps(_build_payload(html)).encode("utf-8"))


TITLE_HTML = '<p><span style="font-size:30px;font-weight:bold;color:#6264A7">&#x1F4CA; MORNING MARKET BRIEF</span></p><hr>'


def _chunk_brief(markdown: str) -> list[str]:
    """Split a markdown brief into HTML chunks that fit within the Teams limit.

    Greedily packs as many story sections as possible into each chunk.
    First chunk includes the title header.
    """
    sections = [s.strip() for s in re.split(r"\n---\n", markdown) if s.strip()]

    # Try sending as a single message
    full_html = TITLE_HTML + _md_to_html(markdown)
    if _payload_size(full_html) <= MAX_PAYLOAD_BYTES:
        return [full_html]

    # Need to split — greedily pack sections
    chunks: list[str] = []
    current_sections: list[str] = []

    for section in sections:
        candidate = "\n\n---\n\n".join(current_sections + [section])
        prefix = TITLE_HTML if not chunks else ""
        candidate_html = prefix + _md_to_html(candidate)

        if _payload_size(candidate_html) <= MAX_PAYLOAD_BYTES:
            current_sections.append(section)
        else:
            # Flush current chunk
            if current_sections:
                prefix = TITLE_HTML if not chunks else ""
                chunks.append(prefix + _md_to_html("\n\n---\n\n".join(current_sections)))
            current_sections = [section]

    # Flush remaining
    if current_sections:
        prefix = TITLE_HTML if not chunks else ""
        chunks.append(prefix + _md_to_html("\n\n---\n\n".join(current_sections)))

    return chunks


# ---------------------------------------------------------------------------
# Posting
# ---------------------------------------------------------------------------

def _post_to_teams(webhook_url: str, html: str) -> bool:
    """POST an HTML message to a Teams webhook.

    Returns True on success, False on failure.
    """
    payload = _build_payload(html)
    data = json.dumps(payload).encode("utf-8")
    req = Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(req, timeout=30) as resp:
            if resp.status in (200, 202):
                return True
            logger.warning("Teams webhook returned status %d", resp.status)
            return False
    except URLError:
        logger.exception("Failed to POST to Teams webhook")
        return False


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run(quiet: bool = False) -> None:
    """Deliver briefs to all users via Teams webhooks.

    Args:
        quiet: If True, send a quiet brief (no notable stories).
    """
    if not USERS_FILE.exists():
        logger.error("users.json not found — skipping delivery")
        return

    users = read_json(USERS_FILE)
    if not isinstance(users, list):
        return

    for user in users:
        username = user.get("username", "unknown")
        webhook_url = _get_teams_webhook(username)

        # Read the brief
        brief_path = PERSONALISED_DIR / f"{username}.md"
        if brief_path.exists():
            brief_content = read_text(brief_path)
        elif quiet:
            brief_content = "No market-moving developments overnight. All quiet on your positions."
        else:
            logger.warning("No brief found for %s — skipping delivery", username)
            continue

        if not webhook_url:
            logger.info("No Teams webhook configured for %s — file output only", username)
            continue

        # Chunk and send
        chunks = _chunk_brief(brief_content)
        sent = 0
        for i, chunk_html in enumerate(chunks):
            if _post_to_teams(webhook_url, chunk_html):
                sent += 1
            else:
                logger.error("Failed to deliver message %d/%d for %s", i + 1, len(chunks), username)

        logger.info("Delivered %d/%d message(s) to %s via Teams", sent, len(chunks), username)

    logger.info("Step 6 complete — delivery finished")
