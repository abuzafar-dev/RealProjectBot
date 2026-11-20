.PHONY: help install run test lint format docker-up docker-down docker-logs

PY := .venv/bin/python

help:
	@echo "make run          — botni ishga tushirish (.env da BOT_TOKEN kerak)"
	@echo "make test         — lint + format + testlar (CI bilan bir xil)"
	@echo "make lint         — ruff check"
	@echo "make format       — kodni avtomatik formatlash"
	@echo "make docker-up    — Docker'da ishga tushirish"
	@echo "make docker-logs  — Docker loglari"
	@echo "make docker-down  — Docker'ni to'xtatish"

.venv/bin/python:
	@if command -v uv >/dev/null 2>&1; then uv venv -q --python 3.12 .venv; else python3 -m venv .venv; fi

.venv/.installed: requirements.txt requirements-dev.txt | .venv/bin/python
	@echo "==> kutubxonalar o'rnatilmoqda"
	@if command -v uv >/dev/null 2>&1; then uv pip install -q -p $(PY) -r requirements-dev.txt; else $(PY) -m pip install -q -r requirements-dev.txt; fi
	@touch $@

install: .venv/.installed

.env:
	@cp .env.example .env
	@echo "==> .env yaratildi — ichiga BOT_TOKEN yozing"

run: install .env
	@grep -q '^BOT_TOKEN=.\+' .env || { echo "XATO: .env faylida BOT_TOKEN bo'sh. @BotFather'dan token olib yozing."; exit 1; }
	$(PY) main.py

test:
	@bash scripts/ci.sh

lint: install
	.venv/bin/ruff check .

format: install
	.venv/bin/ruff format .
	.venv/bin/ruff check --fix .

docker-up: .env
	docker compose up --build -d

docker-logs:
	docker compose logs -f bot

docker-down:
	docker compose down
