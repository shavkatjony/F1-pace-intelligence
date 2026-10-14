.PHONY: setup test lint format data build run

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

build:
	uv run dpec build

run:
	@echo "not yet: built in step B4"