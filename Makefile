.PHONY: setup test lint format data build check run freeze score

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
# A race weekend (Lesson 17). After qualifying: make freeze ROUND=19. After the race: make score ROUND=19
SEASON ?= 2026
CHECKPOINT ?= after_quali

freeze:
	uv run dpec ingest --season $(SEASON) --round $(ROUND)
	uv run dpec build
	uv run dpec check
	uv run dpec freeze --season $(SEASON) --round $(ROUND) --checkpoint $(CHECKPOINT)

score:
	uv run dpec ingest --season $(SEASON) --round $(ROUND)
	uv run dpec build
	uv run dpec check
	uv run dpec score --season $(SEASON) --round $(ROUND)