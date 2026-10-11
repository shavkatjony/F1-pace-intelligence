.PHONY: setup test lint format data run

setup:
	uv sync

test:
	uv run pytest -q

lint:
	uv run ruff check .

format:
	uv run ruff format .

data:
	@echo "not yet: built in step A3"

run:
	@echo "not yet: built in step B4"