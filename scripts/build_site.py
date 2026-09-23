#!/usr/bin/env python3
"""Build a static GitHub Pages site from README.md.

Parses the README's heading and bullet structure and renders a single
self-contained index.html (search, dark mode, table of contents, entry
cards) plus machine-readable exports into site/. Pure Python stdlib, no
dependencies.

Entries carry the type/access/status tags from the README's Legend section.
They are parsed into chips on the page, a ``tags`` field in data.json, and a
tags column in data.csv.

Outputs:
    site/index.html      - the browsable site
    site/data.json       - structured copy of the list
    site/data.csv        - flattened copy of the list
    site/sitemap.xml     - single-URL sitemap for the site
    site/opensearch.xml  - search plugin (URLs like ?q=linz pre-filter)
    site/404.html        - friendly not-found page

Usage:
    python3 scripts/build_site.py
"""

from __future__ import annotations

import html
import json
import re
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
README_PATH = ROOT / "README.md"
OUT_DIR = ROOT / "site"
OUT_HTML = OUT_DIR / "index.html"
OUT_JSON = OUT_DIR / "data.json"
OUT_CSV = OUT_DIR / "data.csv"
OUT_SITEMAP = OUT_DIR / "sitemap.xml"
OUT_OPENSEARCH = OUT_DIR / "opensearch.xml"
OUT_404 = OUT_DIR / "404.html"

# Where the site is published. Change this when deploying elsewhere.
SITE_URL = "https://olitreadwell.github.io/awesome-kiwi-data/"
# Where the README that generates this site lives.
GITHUB_REPO_URL = "https://github.com/olitreadwell/awesome-kiwi-data"
GITHUB_README_URL = "https://github.com/olitreadwell/awesome-kiwi-data/blob/main/README.md"

LINK_RE = re.compile(r"\[([^\]]+)\] ?\(([^)]+)\)")
DESC_SEP_RE = re.compile(r"^[-–—:]\s*")

# Entry tags, written in the README between the link and the description:
#   - [Name](url) - Data - Open - description
#   - [Name](url) - API - Key - Legacy - description
TAG_TYPE = ("API", "Data", "Portal", "Register", "Docs")
TAG_ACCESS = ("Open", "Key", "Login", "Paid")
TAG_STATUS = ("Legacy", "Archived")

# One glyph per tag value, so a tag can be told apart without relying on
# colour. Type shapes say what a thing is, access shapes are a fill
# progression (empty = open, solid = paid), status shapes say whether the
# tool is still current. The site colours the glyph by axis (see TAG_AXIS).
TAG_GLYPHS = {
    "API": "⇄",
    "Data": "▦",
    "Portal": "☰",
    "Register": "☑",
    "Docs": "¶",
    "Open": "○",
    "Key": "◑",
    "Login": "◕",
    "Paid": "●",
    "Legacy": "⟳",
    "Archived": "▣",
}
# Which axis a tag belongs to. Drives the chip colour, so shape carries the
# meaning and colour is only a reinforcement.
TAG_AXIS = (
    {tag: "type" for tag in TAG_TYPE}
    | {tag: "access" for tag in TAG_ACCESS}
    | {tag: "status" for tag in TAG_STATUS}
)

# An optional leading glyph, so "Data - Open" and the glyph-prefixed form
# both parse. Built from the real glyph set to avoid eating list separators.
GLYPH_OPT = r"(?:(?:[" + "".join(re.escape(g) for g in TAG_GLYPHS.values()) + r"])\s*)?"
TAG_RE = re.compile(
    rf"^{GLYPH_OPT}(?P<type>API|Data|Portal|Register|Docs)"
    rf"(?:\s+-\s+{GLYPH_OPT}(?P<access>Open|Key|Login|Paid))?"
    rf"(?:\s+-\s+{GLYPH_OPT}(?P<status>Legacy|Archived))?"
    rf"(?:\s+-\s+(?P<desc>.+?))?"
    r"\.?$",
    re.DOTALL,
)


def tag_chip_html(tag: str) -> str:
    """Render one tag as a glyph chip, coloured by axis."""
    axis = TAG_AXIS.get(tag, "type")
    return (
        f'<span class="tag tag-{axis} tag-{tag.lower()}">'
        f'<span class="tag-glyph" aria-hidden="true">{esc(TAG_GLYPHS.get(tag, ""))}</span>'
        f"{esc(tag)}</span>"
    )

# Sections that are meta content, rendered at the bottom of the page rather
# than inside the category they appear under in the README.
META_SECTIONS = {"Contents", "Legend", "Start here", "Acknowledgements", "Contributing"}


def esc(text: str) -> str:
    """HTML-escape text for safe embedding in the page."""
    return html.escape(text, quote=True)


def slugify(name: str) -> str:
    """Turn a heading into a URL fragment id."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "section"


CODE_SPAN_RE = re.compile(r"`([^`]+)`")


def render_inline(text: str) -> str:
    """Render prose: markdown links as anchors, backticks as code.

    A backticked word that names a tag (``Data``, ``Open``, ``Legacy``) is
    rendered as the same chip used on an entry, so the Legend shows the
    real thing rather than a picture of it.
    """
    out: list[str] = []
    last = 0
    for match in CODE_SPAN_RE.finditer(text):
        out.append(linkify(text[last : match.start()]))
        value = match.group(1).strip()
        # Accept both "Data" and "▦ Data" in the README prose.
        name = value
        for glyph in TAG_GLYPHS.values():
            if name.startswith(glyph):
                name = name[len(glyph) :].strip()
                break
        if name in TAG_GLYPHS:
            out.append(tag_chip_html(name))
        else:
            out.append(f"<code>{esc(value)}</code>")
        last = match.end()
    out.append(linkify(text[last:]))
    return "".join(out)


def linkify(text: str) -> str:
    """Turn markdown links in plain text into HTML anchors."""
    parts: list[str] = []
    last = 0
    for m in LINK_RE.finditer(text):
        parts.append(esc(text[last : m.start()]))
        name = m.group(1).strip().replace("`", "")
        url = m.group(2).strip()
        if not re.match(r"^[a-z][a-z0-9+.-]*://", url) and not url.startswith("#"):
            rel = url[2:] if url.startswith("./") else url[1:] if url.startswith("/") else url
            url = f"{GITHUB_REPO_URL}/blob/main/{rel}"
        parts.append(
            f'<a href="{esc(url)}" target="_blank" rel="noopener">'
            f"{esc(name)}</a>"
        )
        last = m.end()
    parts.append(esc(text[last:]))
    return "".join(parts)


def split_entry_tags(rest: str) -> tuple[list[str], str | None]:
    """Split leading type/access/status tags off an entry description."""
    if not rest:
        return [], None
    match = TAG_RE.match(rest)
    if not match:
        return [], rest
    tags = [match.group("type")]
    for group in ("access", "status"):
        if match.group(group):
            tags.append(match.group(group))
    desc = (match.group("desc") or "").strip()
    return tags, desc or None


def parse_bullet(line: str) -> dict:
    """Parse a markdown bullet into an item dict."""
    stripped = line.lstrip(" \t")
    level = 1 if len(line) - len(stripped) > 0 else 0
    body = stripped[2:] if stripped.startswith("- ") else stripped[1:]
    if body.startswith("["):
        match = LINK_RE.match(body)
        if match:
            name = match.group(1).strip().replace("`", "")
            url = match.group(2).strip()
            rest = DESC_SEP_RE.sub("", body[match.end():].strip())
            if rest in {".", ":", "-", "–", "—"}:
                rest = ""
            tags, desc = split_entry_tags(rest.replace("`", ""))
            return {
                "type": "entry",
                "name": name,
                "url": url,
                "tags": tags,
                "desc": desc,
                "level": level,
            }
    return {"type": "text", "text": body.strip(), "level": level, "bullet": True}


def parse_readme(text: str) -> dict:
    """Parse the README into a structured document."""
    title = "New Zealand Data & APIs"
    tagline = ""
    sections: list[dict] = []
    current: dict | None = None
    current_sub: dict | None = None
    in_code_block = False
    code_lines: list[str] = []

    for raw in text.splitlines():
        line = raw.rstrip()
        if line.strip().startswith("```"):
            if in_code_block:
                # Closing fence: keep the example as a code block so it
                # renders as code instead of leaking backticks into prose.
                if current is not None:
                    current["items"].append(
                        {
                            "type": "text",
                            "text": "\n".join(code_lines),
                            "level": 0,
                            "bullet": False,
                            "code": True,
                        }
                    )
                code_lines = []
            in_code_block = not in_code_block
            continue
        if in_code_block:
            code_lines.append(raw)
            continue
        if not line.strip() or line.startswith("[!["):
            continue
        if line.startswith("# "):
            # Drop trailing badges: "# Awesome Kiwi Data [![Awesome](...)]"
            title = re.split(r"\s*\[!\[", line[2:].strip())[0].strip()
        elif line.startswith("### "):
            name = line[4:].strip()
            current = {
                "name": name,
                "meta": name in META_SECTIONS,
                "subs": [],
                "items": [],
            }
            sections.append(current)
            current_sub = None
        elif line.startswith("## "):
            name = line[3:].strip()
            # "Contents" is the README's own table of contents; the site has
            # its own nav, so it is marked meta like the other front matter.
            current = {"name": name, "meta": name in META_SECTIONS, "subs": [], "items": []}
            sections.append(current)
            current_sub = None
        elif line.startswith("#### "):
            name = line[5:].strip()
            if name in META_SECTIONS:
                current = {"name": name, "meta": True, "subs": [], "items": []}
                sections.append(current)
                current_sub = None
            elif current is not None:
                current_sub = {"name": name, "items": []}
                current["subs"].append(current_sub)
        elif line.lstrip(" \t").startswith("- "):
            item = parse_bullet(line)
            if current_sub is not None:
                current_sub["items"].append(item)
            elif current is not None:
                current["items"].append(item)
        elif current is not None:
            text = line.strip()
            items = current["items"]
            # Only join wrapped lines of the same paragraph. A bullet or a
            # code block ends the paragraph it sits in, so prose that follows
            # one starts a new block instead of being absorbed into it.
            previous = items[-1] if items else None
            if (
                previous is not None
                and previous["type"] == "text"
                and not previous.get("bullet")
                and not previous.get("code")
            ):
                previous["text"] += " " + text
            else:
                items.append({"type": "text", "text": text, "level": 0})
        elif not tagline:
            tagline = line.strip().lstrip("> ").strip()

    return {"title": title, "tagline": tagline, "sections": sections}


def collect_search(items: list[dict]) -> list[str]:
    """Collect searchable text for an item and its nested children."""
    parts: list[str] = []
    for item in items:
        if item["type"] == "entry":
            parts.append(item["name"])
            parts.extend(item.get("tags", []))
            if item["desc"]:
                parts.append(item["desc"])
        else:
            parts.append(item["text"])
    return parts


def render_entry(item: dict) -> str:
    """Render a single entry line, with its type/access/status tags as chips."""
    indent = item["level"] * 18
    style = f' style="padding-left:{indent}px"' if indent else ""
    name = esc(item["name"])
    url = esc(item["url"])
    chips = "".join(tag_chip_html(tag) for tag in item.get("tags", []))
    desc = f'<span class="desc">{esc(item["desc"])}</span>' if item["desc"] else ""
    return (
        f'<div class="entry"{style}>'
        f'<a class="link" href="{url}" target="_blank" rel="noopener">{name}</a>'
        f"{chips}{desc}</div>"
    )


def render_text(item: dict) -> str:
    """Render a plain-text item, with links, code spans and tag chips."""
    if item.get("code"):
        return f'<pre class="code"><code>{esc(item["text"])}</code></pre>'
    return f'<p class="note">{render_inline(item["text"])}</p>'


def render_items(items: list[dict]) -> str:
    """Render top-level items with their nested children."""
    out: list[str] = []
    i = 0
    while i < len(items):
        item = items[i]
        children: list[dict] = []
        j = i + 1
        while j < len(items) and items[j]["level"] > 0:
            children.append(items[j])
            j += 1

        if item["type"] == "text":
            if children:
                search = " ".join(collect_search([item] + children)).lower()
                out.append(f'<div class="group" data-search="{esc(search)}">')
                out.append(f'<h4 class="group-name">{esc(item["text"])}</h4>')
                out.append('<div class="sub">')
                out.extend(render_entry(child) for child in children)
                out.append("</div></div>")
            else:
                out.append(render_text(item))
        else:
            search = " ".join(collect_search([item] + children)).lower()
            out.append(f'<div class="item" data-search="{esc(search)}">')
            out.append(render_entry(item))
            if children:
                out.append('<div class="sub">')
                out.extend(render_entry(child) for child in children)
                out.append("</div>")
            out.append("</div>")
        i = j
    return "\n".join(out)


def render_section(section: dict) -> str:
    """Render one section of the page."""
    body = render_items(section["items"])
    for sub in section["subs"]:
        body += (
            f'\n<h3 id="{slugify(sub["name"])}">{esc(sub["name"])}</h3>\n'
            + render_items(sub["items"])
        )
    static = " data-static" if section["meta"] else ""
    return (
        f'<section id="{slugify(section["name"])}"'
        f' data-section="{esc(section["name"])}"{static}>\n'
        f"<h2>{esc(section['name'])}</h2>\n{body}</section>"
    )


def flatten(doc: dict) -> list[dict]:
    """Flatten all entry items with their section names."""
    rows = []
    for section in doc["sections"]:
        for item in section["items"]:
            if item["type"] == "entry" and not item["url"].startswith("#"):
                rows.append(
                    {
                        "name": item["name"],
                        "url": item["url"],
                        "description": item["desc"] or "",
                        "tags": " ".join(item.get("tags", [])),
                        "category": section["name"],
                    }
                )
    return rows


def csv_encode(value: str) -> str:
    """Quote a CSV field when needed."""
    if any(ch in value for ch in '",\n\r'):
        return '"' + value.replace('"', '""') + '"'
    return value


def render_csv(rows: list[dict]) -> str:
    """Render the list as CSV."""
    header = ["name", "url", "description", "tags", "category"]
    lines = [",".join(header)]
    for row in rows:
        lines.append(",".join(csv_encode(row[k]) for k in header))
    return "\n".join(lines) + "\n"


def to_json(doc: dict) -> dict:
    """Shape the parsed document for data.json."""
    sections = []
    for section in doc["sections"]:
        items = []
        for item in section["items"]:
            if item["type"] == "entry":
                if item["url"].startswith("#"):
                    continue
                items.append(
                    {
                        "name": item["name"],
                        "url": item["url"],
                        "description": item["desc"],
                        "tags": item.get("tags", []),
                    }
                )
            else:
                items.append({"text": item["text"]})
        sections.append({"name": section["name"], "items": items})
    return {"title": doc["title"], "tagline": doc["tagline"], "sections": sections}


PAGE_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<meta name="description" content="__TAGLINE__">
<meta name="color-scheme" content="light dark">
<link rel="search" type="application/opensearchdescription+xml" title="__TITLE__" href="opensearch.xml">
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "WebSite",
  "name": "__TITLE__",
  "description": "__TAGLINE__",
  "url": "__SITE_URL__",
  "potentialAction": {
    "@type": "SearchAction",
    "target": "__SITE_URL__?q={search_term_string}",
    "query-input": "required name=search_term_string"
  }
}
</script>
<style>
:root {
  --bg: #f6f8fa;
  --surface: #ffffff;
  --text: #1f2937;
  --muted: #6b7280;
  --accent: #0f766e;
  --accent-soft: #ccfbf1;
  --border: #e5e7eb;
  --radius: 10px;
  --shadow: 0 1px 2px rgba(16, 24, 40, 0.06);
  /* Tag axis colours, drawn from the Okabe-Ito colour-blind safe palette.
     Shape carries the meaning; colour only reinforces which axis a tag is. */
  --tag-type: #0072b2;
  --tag-access: #007a5c;
  --tag-status: #b45309;
}
[data-theme="dark"] {
  --bg: #0f172a;
  --surface: #1e293b;
  --text: #e2e8f0;
  --muted: #94a3b8;
  --accent: #2dd4bf;
  --accent-soft: #134e4a;
  --border: #334155;
  --shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  --tag-type: #56b4e9;
  --tag-access: #34d399;
  --tag-status: #fbbf24;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto,
    "Helvetica Neue", Arial, sans-serif;
  background: var(--bg);
  color: var(--text);
  line-height: 1.55;
}
.wrap { max-width: 1100px; margin: 0 auto; padding: 0 20px; }
.scroll-progress {
  position: fixed;
  top: 0;
  left: 0;
  height: 3px;
  width: 0;
  background: var(--accent);
  z-index: 30;
}
.site-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  box-shadow: var(--shadow);
}
.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  padding-top: 14px;
  padding-bottom: 14px;
}
h1 { font-size: 1.35rem; margin: 0; }
.tagline { margin: 2px 0 0; color: var(--muted); font-size: 0.95rem; }
.stats { margin-top: 4px; font-size: 0.85rem; color: var(--muted); }
.header-actions { display: flex; gap: 10px; align-items: center; }
#search {
  width: 260px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 8px;
  font-size: 0.95rem;
  background: var(--bg);
  color: var(--text);
}
#search:focus { outline: 2px solid var(--accent); outline-offset: -1px; background: var(--surface); }
.btn, .theme-btn {
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
  white-space: nowrap;
  cursor: pointer;
}
.btn {
  background: var(--accent);
  color: #fff;
  text-decoration: none;
}
.btn:hover { background: #115e59; }
.theme-btn {
  background: var(--surface);
  color: var(--text);
  border: 1px solid var(--border);
}
.theme-btn:hover { border-color: var(--accent); color: var(--accent); }
.layout {
  display: grid;
  grid-template-columns: 240px 1fr;
  gap: 32px;
  padding-top: 24px;
  padding-bottom: 48px;
}
.toc {
  position: sticky;
  top: 90px;
  align-self: start;
  max-height: calc(100vh - 120px);
  overflow: auto;
}
.toc-title {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--muted);
  margin: 0 0 8px;
}
.toc ul { list-style: none; margin: 0; padding: 0; }
.toc a {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  padding: 5px 8px;
  border-radius: 6px;
  color: var(--text);
  text-decoration: none;
  font-size: 0.9rem;
}
.toc a:hover { background: var(--accent-soft); color: var(--accent); }
.toc-count { color: var(--muted); font-size: 0.8rem; }
section[data-section] { margin-bottom: 28px; }
section[data-section] h2 {
  font-size: 1.15rem;
  margin: 0 0 12px;
  padding-bottom: 8px;
  border-bottom: 2px solid var(--accent);
  display: inline-block;
}
h3 { font-size: 1rem; margin: 20px 0 10px; color: var(--accent); }
.item, .group {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 14px;
  margin-bottom: 8px;
  box-shadow: var(--shadow);
}
.group-name { margin: 0 0 6px; font-size: 0.95rem; font-weight: 700; }
.entry { padding: 2px 0; }
.entry .link { color: var(--accent); text-decoration: none; font-weight: 600; }
.entry .link:hover { text-decoration: underline; }
.entry .desc { color: var(--muted); font-size: 0.9rem; }
.entry .desc::before { content: "\\2013  "; color: var(--border); }
.tag {
  display: inline-block;
  margin-left: 8px;
  padding: 1px 8px;
  border-radius: 999px;
  border: 1px solid currentColor;
  background: var(--surface);
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.02em;
  vertical-align: 1px;
  white-space: nowrap;
}
.tag-type { color: var(--tag-type); }
.tag-access { color: var(--tag-access); }
.tag-status { color: var(--tag-status); }
.tag-glyph {
  margin-right: 4px;
  font-size: 0.9em;
  /* Keep the glyph on one line and stop the browser swapping in an emoji. */
  font-variant-emoji: text;
}
.note .tag { background: var(--bg); }
.note {
  color: var(--muted);
  font-size: 0.92rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 10px 14px;
}
.note a { color: var(--accent); }
.note code, .code {
  font-family: ui-monospace, SFMono-Regular, "SF Mono", Menlo, Consolas,
    monospace;
  font-size: 0.85em;
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 5px;
  padding: 1px 5px;
  color: var(--text);
}
.code {
  display: block;
  white-space: pre;
  overflow-x: auto;
  margin: 10px 0 0;
  padding: 10px 14px;
  line-height: 1.5;
}
.code code { background: none; border: 0; padding: 0; }
.result-count { color: var(--muted); font-size: 0.9rem; margin: 0 0 16px; }
.site-footer {
  margin-top: 40px;
  padding-top: 16px;
  border-top: 1px solid var(--border);
  color: var(--muted);
  font-size: 0.85rem;
}
.site-footer a { color: var(--accent); }
.back-to-top {
  position: fixed;
  right: 20px;
  bottom: 20px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--accent);
  font-size: 1.1rem;
  cursor: pointer;
  box-shadow: var(--shadow);
}
.back-to-top:hover { background: var(--accent-soft); }
@media (max-width: 800px) {
  .layout { grid-template-columns: 1fr; }
  .toc { position: static; max-height: none; }
  #search { width: 100%; }
  .header-inner { flex-direction: column; align-items: stretch; }
}
@media print {
  .site-header, .toc, .back-to-top, .result-count, .scroll-progress { display: none; }
  .layout { display: block; }
  .item, .group { break-inside: avoid; }
}
</style>
</head>
<body>
<div id="progress" class="scroll-progress" aria-hidden="true"></div>
<header class="site-header">
  <div class="wrap header-inner">
    <div>
      <h1>__TITLE__</h1>
      <p class="tagline">__TAGLINE__</p>
      <p class="stats">__STATS__</p>
    </div>
    <div class="header-actions">
      <input id="search" type="search" placeholder="Search datasets and APIs…"
        autocomplete="off" aria-label="Search datasets and APIs">
      <button id="theme" class="theme-btn" aria-label="Toggle dark mode">Dark</button>
      <a class="btn" href="https://github.com/olitreadwell/awesome-kiwi-data"
        target="_blank" rel="noopener">View on GitHub</a>
    </div>
  </div>
</header>
<main class="wrap layout">
  <nav class="toc" aria-label="Table of contents">
    <p class="toc-title">Contents</p>
    <ul id="toc-list"></ul>
  </nav>
  <div class="content">
    <p class="result-count" id="count" role="status"></p>
__SECTIONS__
    <footer class="site-footer">
      <p>Generated from
        <a href="https://github.com/olitreadwell/awesome-kiwi-data/blob/main/README.md">README.md</a>
        by <code>scripts/build_site.py</code>. Machine-readable copies:
        <a href="data.json">data.json</a>, <a href="data.csv">data.csv</a>.
        Found a dead link or a missing dataset? Open an issue or pull request
        on <a href="https://github.com/olitreadwell/awesome-kiwi-data">GitHub</a>.</p>
    </footer>
  </div>
</main>
<button id="top" class="back-to-top" aria-label="Back to top" hidden>&#8593;</button>
<script>
const search = document.getElementById("search");
const count = document.getElementById("count");
const topBtn = document.getElementById("top");
const progress = document.getElementById("progress");
const themeBtn = document.getElementById("theme");
const sections = Array.from(document.querySelectorAll("[data-section]"));
const tocList = document.getElementById("toc-list");

sections.forEach((section) => {
  // Front matter (Contents, Legend, Start here, Acknowledgements,
  // Contributing) has no countable links, so it is left out of the nav.
  if (section.dataset.static !== undefined) {
    return;
  }
  const li = document.createElement("li");
  const a = document.createElement("a");
  a.href = "#" + section.id;
  a.textContent = section.dataset.section;
  const span = document.createElement("span");
  span.className = "toc-count";
  span.textContent = section.querySelectorAll(".item, .group").length;
  a.appendChild(span);
  li.appendChild(a);
  tocList.appendChild(li);
});

const total = document.querySelectorAll(".item, .group").length;
count.textContent = total + " links";

function update() {
  const q = search.value.trim().toLowerCase();
  let visible = 0;
  sections.forEach((section) => {
    if (section.dataset.static !== undefined) {
      section.hidden = !!q;
      return;
    }
    let any = false;
    section.querySelectorAll("[data-search]").forEach((el) => {
      const hit = !q || el.dataset.search.includes(q);
      el.hidden = !hit;
      if (hit) any = true;
    });
    section.hidden = !any;
    if (any) {
      visible += section.querySelectorAll("[data-search]:not([hidden])").length;
    }
  });
  count.textContent = q ? visible + " of " + total + " links match" : total + " links";
}

search.addEventListener("input", update);

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  themeBtn.textContent = theme === "dark" ? "Light" : "Dark";
}
const savedTheme = localStorage.getItem("theme");
const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
applyTheme(savedTheme || (prefersDark ? "dark" : "light"));
themeBtn.addEventListener("click", () => {
  const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  localStorage.setItem("theme", next);
  applyTheme(next);
});

window.addEventListener("scroll", () => {
  const doc = document.documentElement;
  const max = doc.scrollHeight - doc.clientHeight;
  progress.style.width = (max > 0 ? (doc.scrollTop / max) * 100 : 0) + "%";
  topBtn.hidden = window.scrollY < 400;
});
topBtn.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));

document.addEventListener("keydown", (e) => {
  if (e.key === "/" && document.activeElement !== search) {
    e.preventDefault();
    search.focus();
  }
});

const params = new URLSearchParams(window.location.search);
const q = params.get("q");
if (q) {
  search.value = q;
  update();
}
</script>
</body>
</html>
"""

NOT_FOUND_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Page not found — __TITLE__</title>
<meta name="robots" content="noindex">
<style>
  body {
    margin: 0;
    min-height: 100vh;
    display: grid;
    place-items: center;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: var(--bg, #f6f8fa);
    color: var(--text, #1f2937);
    text-align: center;
  }
  .card { max-width: 480px; padding: 24px; }
  h1 { font-size: 2.5rem; margin: 0 0 8px; color: var(--accent, #0f766e); }
  p { color: var(--muted, #6b7280); }
  a { color: var(--accent, #0f766e); }
</style>
</head>
<body>
  <div class="card">
    <h1>404</h1>
    <p>That page doesn't exist, but the list of New Zealand data and APIs is
    all on one page anyway.</p>
    <p><a href="./">Back to the list</a></p>
  </div>
</body>
</html>
"""


def main() -> int:
    """Build the site and exports from the README."""
    if not README_PATH.exists():
        print(f"error: {README_PATH} not found", file=sys.stderr)
        return 1
    doc = parse_readme(README_PATH.read_text(encoding="utf-8"))
    rows = flatten(doc)
    sections_html = "\n".join(render_section(s) for s in doc["sections"])
    categories = [s["name"] for s in doc["sections"] if not s["meta"]]
    stats = f"{len(rows)} links across {len(categories)} categories"
    page = (
        PAGE_TEMPLATE.replace("__TITLE__", esc(doc["title"]))
        .replace("__TAGLINE__", esc(doc["tagline"]))
        .replace("__SITE_URL__", esc(SITE_URL.rstrip("/")))
        .replace("__STATS__", esc(stats))
        .replace("__SECTIONS__", sections_html)
    )
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(page, encoding="utf-8")
    OUT_JSON.write_text(
        json.dumps(to_json(doc), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    OUT_CSV.write_text(render_csv(rows), encoding="utf-8")
    OUT_SITEMAP.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        f"  <url><loc>{esc(SITE_URL)}</loc>"
        f"<lastmod>{date.today().isoformat()}</lastmod></url>\n"
        "</urlset>\n",
        encoding="utf-8",
    )
    OUT_OPENSEARCH.write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/">\n'
        f"  <ShortName>{esc(doc['title'])}</ShortName>\n"
        f"  <Description>{esc(doc['tagline'])}</Description>\n"
        f'  <Url type="text/html" template="{esc(SITE_URL)}?q={{searchTerms}}" />\n'
        "  <InputEncoding>UTF-8</InputEncoding>\n"
        "</OpenSearchDescription>\n",
        encoding="utf-8",
    )
    OUT_404.write_text(
        NOT_FOUND_TEMPLATE.replace("__TITLE__", esc(doc["title"])),
        encoding="utf-8",
    )
    print(
        f"wrote {len(list(OUT_DIR.iterdir()))} files to {OUT_DIR.relative_to(ROOT)} "
        f"({len(categories)} categories, {len(rows)} links)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
