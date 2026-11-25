# Usage: make all                      (default config: 2022 World Cup, ~64 matches)
#        make all CONFIG=configs/leagues_2015_16.yaml
CONFIG ?= configs/default.yaml
RUN = uv run confshocks --config $(CONFIG)

.PHONY: setup lint format test audit ingest shocks estimate all clean

setup:      ## install everything and enable the git hooks
	uv sync --group notebooks
	uv run pre-commit install

lint:       ## static checks
	uv run ruff check .
	uv run ruff format --check .

format:     ## auto-fix style
	uv run ruff check --fix .
	uv run ruff format .

test:       ## unit + integration tests (synthetic data, no network)
	uv run pytest

audit:      ## print what the configured competitions actually contain
	$(RUN) audit

ingest:     ## download events and write tidy per-match tables to data/interim
	$(RUN) ingest

shocks:     ## build the shot-level shock table in data/processed
	$(RUN) shocks

estimate:   ## estimate effects, write results + figure to reports/
	$(RUN) estimate

all: ingest shocks estimate

clean:      ## remove generated outputs (keeps downloaded data)
	rm -rf reports/*/ data/processed/*/
