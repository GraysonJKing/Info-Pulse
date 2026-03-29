"""Title to filesystem-safe slug conversion."""

import re


def slugify(title: str, max_length: int = 80) -> str:
    """Convert a title string to a filesystem-safe slug.

    Args:
        title: The article/story title.
        max_length: Maximum slug length.

    Returns:
        Lowercase, hyphen-separated slug.
    """
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9\s-]", "", slug)
    slug = re.sub(r"[\s-]+", "-", slug).strip("-")
    return slug[:max_length]
