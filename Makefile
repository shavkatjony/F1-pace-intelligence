.PHONY: setup test lint format data build check run freeze score snapshot public image image-run

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
# A race weekend (decision 0015). After qualifying: make freeze ROUND=19. After the race: make score ROUND=19
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

# The public copy (decision 0018)
snapshot:
	uv run dpec snapshot

public:
	uv run dpec serve --config config/public.yaml

image: snapshot
	rm -rf snapshot && mkdir snapshot
	tar -xzf $$(ls -t dist/dpec-data-*.tar.gz | head -1) -C snapshot
	docker build -t dpec-public .

image-run:
	docker run --rm -p 7860:7860 dpec-public
