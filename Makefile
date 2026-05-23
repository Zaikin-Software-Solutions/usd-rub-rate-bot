.PHONY: help install lint format typecheck test check run docker-build docker-up docker-down clean

help:
	@echo "Targets:"
	@echo "  install      - sync dev dependencies via uv"
	@echo "  lint         - ruff check"
	@echo "  format       - ruff format (in place)"
	@echo "  typecheck    - mypy"
	@echo "  test         - pytest"
	@echo "  check        - lint + format-check + typecheck + test"
	@echo "  run          - run the bot locally (needs .env)"
	@echo "  docker-build - build the runtime image"
	@echo "  docker-up    - start via docker compose"
	@echo "  docker-down  - stop and remove the container"
	@echo "  clean        - remove caches"

install:
	uv sync --extra dev

lint:
	uv run ruff check .

format:
	uv run ruff format .

typecheck:
	uv run mypy

test:
	uv run pytest -q

check:
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy
	uv run pytest -q

run:
	uv run python -m usd_rub_rate_bot

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down

clean:
	rm -rf .pytest_cache .ruff_cache .mypy_cache .coverage htmlcov
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
