"""Helpers for surfacing richer exception diagnostics in logs."""

from __future__ import annotations


def _to_text(value: object) -> str:
    """Convert common exception field values to readable text."""
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def _trim(text: str, max_chars: int) -> str:
    """Trim long text blocks to keep logs readable."""
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}... [truncated {len(text) - max_chars} chars]"


def describe_exception(exc: Exception, max_chars: int = 4000) -> str:
    """Return a multi-line diagnostic string for an exception."""
    lines: list[str] = [
        f"type={type(exc).__name__}",
        f"message={_trim(_to_text(exc), max_chars)}",
        f"repr={_trim(repr(exc), max_chars)}",
    ]

    for attr in ("returncode", "cmd", "stderr", "stdout", "output"):
        if not hasattr(exc, attr):
            continue
        value = _to_text(getattr(exc, attr))
        if value:
            lines.append(f"{attr}={_trim(value, max_chars)}")

    if exc.args:
        rendered_args = ", ".join(_trim(_to_text(arg), max_chars) for arg in exc.args)
        lines.append(f"args=[{rendered_args}]")

    if exc.__cause__ is not None:
        lines.append(f"cause={type(exc.__cause__).__name__}: {_trim(_to_text(exc.__cause__), max_chars)}")
    if exc.__context__ is not None:
        lines.append(f"context={type(exc.__context__).__name__}: {_trim(_to_text(exc.__context__), max_chars)}")

    return "\n".join(lines)
