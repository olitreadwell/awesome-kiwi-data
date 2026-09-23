"""Invariants for this list. The rules live in the engine; these are the checks
that matter most for this particular readme, kept close to it."""

from __future__ import annotations

from pathlib import Path

from awesome_list.config.load_list_config import load_list_config
from awesome_list.parse.parse_readme import parse_readme
from awesome_list.rules.run_rules import run_rules

ROOT = Path(__file__).resolve().parents[1]


def document() -> object:
    config = load_list_config(ROOT / "awesome.toml")
    text = (ROOT / config.readme).read_text(encoding="utf-8")
    return parse_readme(text, vocabulary=config.tags), text, config


def test_no_rule_violations() -> None:
    parsed, text, config = document()
    violations = run_rules(
        parsed, text, config.tags, file=config.readme, entry_sections=config.sections
    )

    assert [violation.render() for violation in violations] == []


def test_entry_count_does_not_shrink() -> None:
    parsed, _text, _config = document()

    assert len(parsed.entries) >= 100


def test_every_entry_has_a_type_and_an_access_tag() -> None:
    parsed, _text, _config = document()
    missing = [
        entry.name
        for entry in parsed.entries
        if {tag.axis for tag in entry.tags} < {"type", "access"}
    ]

    assert missing == []


def test_no_duplicate_urls() -> None:
    parsed, _text, _config = document()
    urls = [entry.url for entry in parsed.entries]

    assert len(urls) == len(set(urls))
