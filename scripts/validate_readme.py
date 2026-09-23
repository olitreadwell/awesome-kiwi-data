#!/usr/bin/env python3
"""Validate README.md structure.

Reuses the same parser as scripts/build_site.py and flags issues that
would break the site or the link check: malformed links, duplicate URLs,
relative or fragment-only URLs, inconsistent bullet nesting, and entries
missing the type and access tags from the README legend. Runs in CI on every
pull request.

Usage:
    python3 scripts/validate_readme.py
"""

from __future__ import annotations

import re
import sys
from collections import Counter
from urllib.parse import urlparse

from build_site import (
    README_PATH,
    TAG_ACCESS,
    TAG_TYPE,
    parse_bullet,
    parse_readme,
)

LINK_RE = re.compile(r"\[([^\]]+)\] ?\(([^)]+)\)")

# Sections whose bullets are in-page anchors rather than entries.
TOC_SECTIONS = {"Contents", "Table of Contents"}


def main() -> int:
    """Run all checks and return a process exit code."""
    errors: list[str] = []
    text = README_PATH.read_text(encoding="utf-8")
    doc = parse_readme(text)

    urls: list[str] = []
    for section in doc["sections"]:
        if section["name"] in TOC_SECTIONS:
            continue
        for item in section["items"]:
            if item["type"] != "entry":
                continue
            urls.append(item["url"])
            if item["url"].startswith("#"):
                errors.append(
                    f"entry '{item['name']}' points at an in-page fragment: {item['url']}"
                )
            elif item["url"].startswith(("/", "./", "../")):
                errors.append(
                    f"entry '{item['name']}' uses a relative URL: {item['url']}"
                )
            elif not urlparse(item["url"]).scheme:
                errors.append(
                    f"entry '{item['name']}' has no URL scheme: {item['url']}"
                )

    for url, count in Counter(urls).items():
        if count > 1:
            errors.append(f"duplicate link ({count}x): {url}")

    prev_level = -1
    in_code_block = False
    heading = ""
    for lineno, raw in enumerate(text.splitlines(), 1):
        stripped = raw.lstrip(" \t")
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block:
            continue
        if stripped.startswith("#"):
            heading = stripped.lstrip("#").strip()
            continue
        if not stripped.startswith("- ") or heading in TOC_SECTIONS:
            continue
        if stripped.startswith("- [") and not LINK_RE.match(stripped[2:]):
            errors.append(f"line {lineno}: malformed link: {raw.strip()}")
        item = parse_bullet(raw)
        if item["type"] == "entry" and not item["tags"]:
            errors.append(
                f"line {lineno}: entry '{item['name']}' has no tags; expected "
                f"one of {', '.join(TAG_TYPE)}"
            )
        if item["type"] == "entry" and item["tags"] and len(item["tags"]) < 2:
            errors.append(
                f"line {lineno}: entry '{item['name']}' has no access tag; "
                f"expected one of {', '.join(TAG_ACCESS)}"
            )
        if item["level"] > prev_level + 1:
            errors.append(f"line {lineno}: bullet jumps {prev_level} -> {item['level']} levels")
        prev_level = item["level"]

    if errors:
        print(f"{len(errors)} problem(s) found in {README_PATH.name}:")
        for error in errors:
            print(f"  - {error}")
        return 1
    print(
        f"OK: {README_PATH.name} parses cleanly "
        f"({len(urls)} links, {len(doc['sections'])} sections)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
