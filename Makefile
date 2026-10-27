.PHONY: setup test lint format data build check run

setup:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

format:
	uv run ruff format .

data:
	uv run dpec ingest
	uv run dpec build
	uv run dpec check

build:
	uv run dpec build

check:
	uv run dpec check

run:
	uv run dpec serve
