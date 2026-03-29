"""JSON and markdown read/write helpers."""

import json
from pathlib import Path


def read_json(path: Path) -> list | dict:
    """Read and parse a JSON file."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: list | dict) -> None:
    """Write data as pretty-printed JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def read_text(path: Path) -> str:
    """Read a text/markdown file."""
    return path.read_text(encoding="utf-8")


def write_text(path: Path, content: str) -> None:
    """Write a text/markdown file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def parse_llm_json(raw: str) -> list | dict:
    """Parse JSON from an LLM response, handling markdown fences.

    Tries direct parse first, then extracts from ```json fences,
    then finds the first [ or { as a fallback.
    """
    text = raw.strip()

    # Direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Extract from markdown code fence
    if "```" in text:
        parts = text.split("```")
        for part in parts[1::2]:  # odd-indexed parts are inside fences
            content = part.strip()
            if content.startswith("json"):
                content = content[4:].strip()
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                continue

    # Find first [ or {
    for i, ch in enumerate(text):
        if ch in ("[", "{"):
            closing = "]" if ch == "[" else "}"
            depth = 0
            for j in range(i, len(text)):
                if text[j] == ch:
                    depth += 1
                elif text[j] == closing:
                    depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[i : j + 1])
                    except json.JSONDecodeError:
                        break

    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")
