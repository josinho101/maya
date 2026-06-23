.PHONY: test lint format dev requirements check-ollama frontend-dev frontend-test frontend-lint

test:
	uv run pytest

lint:
	uv run ruff check .

format:
	uv run black src tests
	uv run ruff check --fix .

dev:
	uv run uvicorn maya.api.main:app --reload --port 9091

requirements:
	uv pip compile pyproject.toml -o requirements.txt
	uv pip compile pyproject.toml --extra dev -o requirements-dev.txt

check-ollama:
	uv run python scripts/check_ollama.py

frontend-dev:
	cd frontend && npm run dev

frontend-test:
	cd frontend && npm run test

frontend-lint:
	cd frontend && npm run lint
