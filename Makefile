SHELL := /bin/bash
.DEFAULT_GOAL := check

.PHONY: check check-fast list-check toc toc-check test links fix

check: list-check toc-check test

check-fast: list-check toc-check

list-check:
	uv run --project . python -m awesome_list.cli.run_list_check

toc:
	uv run --project . python -m awesome_list.cli.run_toc

toc-check:
	uv run --project . python -m awesome_list.cli.run_toc --check

test:
	uv run --project . pytest

links:
	lychee --config lychee.toml README.md

fix:
	tools/node_modules/.bin/prettier --write README.md 2>/dev/null || true
