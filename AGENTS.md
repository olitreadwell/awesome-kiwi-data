# Agent instructions

This repository is a curated list of New Zealand data sources. The list is
`README.md`, and the rules it follows live in the engine at
<https://github.com/olitreadwell/awesome-list-template>.

## Before you change anything

```bash
uv sync --group dev
make hooks-install 2>/dev/null || git config core.hooksPath .githooks
make check
```

## Rules

- Add links in the shape `- [Name](https://example.govt.nz/) - ▦ Data - ○ Open - what it holds.`
  Every entry needs a type tag and an access tag from `awesome.toml`.
- Link the page that holds the data or the documentation, not a department
  homepage or a press release.
- Do not write entry text with a model. Descriptions come from a human.
- Run `make toc` after moving a heading, and never hand-edit table of contents
  lines.
- Point retired tools at where the data lives now, or move them out. Never keep
  an archived tool in the main list.
