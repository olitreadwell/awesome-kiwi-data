# Contributing

Thanks for helping keep this list of New Zealand data and APIs useful. There
are two ways to contribute: open an issue (no coding needed) or open a pull
request.

## Option 1: suggest a link via issue

Use the [suggest-a-link issue form](../../issues/new?template=add-link.yml).
Fill in what you know. Someone will verify it and add it as a pull request.

## Option 2: add a link via pull request

### 1. Edit README.md

Find the section that fits and add your link as a bullet:

```markdown
- [Name](https://example.govt.nz/) - ▦ Data - ○ Open - one-line description of what it is.
```

The glyphs are optional, and the site adds them anyway, but including them
keeps the README and the site looking the same.

If the link belongs to a group (for example an agency with several
datasets), add it as an indented bullet under the group name.

### 2. Tag the entry

Every entry needs a type and an access level, and a status if the tool has
been superseded. Each tag carries a glyph so the tags can be told apart
without relying on colour. The full list is in the
[legend](README.md#legend):

- Type: `⇄ API`, `▦ Data`, `☰ Portal`, `☑ Register`, `¶ Docs`
- Access: `○ Open`, `◑ Key`, `◕ Login`, `● Paid`
- Status: `⟳ Legacy`, `▣ Archived` (omit for anything current)

`python3 scripts/validate_readme.py` rejects entries without tags, so run it
before opening a pull request.

### 3. Point at the data, not the front door

Link the page that actually holds the dataset or the API docs. A department
homepage, a press release, or a soft 404 that returns HTTP 200 is not a
useful entry. If a tool has moved, link the new home rather than the landing
page it redirects from.

### 4. Run the checks

Open every link you add and confirm it resolves to a live page. If you find a
dead link elsewhere in the list, fix or remove it in the same pull request.

```bash
python3 scripts/validate_readme.py   # tags and list structure
python3 scripts/build_site.py        # the site still builds
npx -y awesome-lint                  # awesome list conventions
lychee README.md                     # links resolve (optional, needs lychee)
```

### 5. Open a pull request

Include what you verified and how in the PR description.

## How links are maintained

The [weekly link check workflow](.github/workflows/linkcheck.yml) checks every
link in `README.md` once a week. If it finds genuinely dead links (404, DNS
failure, refused connection) it opens a tracking issue and keeps it updated;
when the links recover, the issue closes automatically. Bot-blocked links
(403 / 999, common for LinkedIn) are not treated as failures.

## Commit messages

Use [Conventional Commits](https://www.conventionalcommits.org/) style, plain
language, one idea per line:

```
feat: add Stats NZ API link

- Added the Aotearoa Data Explorer under Central government and agencies,
  verified against stats.govt.nz.
```

Don't add a `Co-Authored-By` trailer for AI tools: the tool is a
facilitator, not a co-author.
