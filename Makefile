.PHONY: help install run test 

help:
	@echo "make run      — botni ishga tushirish (.env da BOT_TOKEN kerak)"
	@echo "make test     — testlar"
	@echo "make install  — .venv va kutubxonalar"

run: install .env
	@grep -q '^BOT_TOKEN=.\+' .env || { echo "XATO: .env faylida BOT_TOKEN bo'sh. @BotFather'dan token olib yozing."; exit 1; }
	$(PY) main.py

PY := .venv/bin/python

.venv/bin/python:
	@if command -v uv >/dev/null 2>&1; then uv venv -q --python 3.12 .venv; else python3 -m venv .venv; fi

.venv/.installed: requirements.txt | .venv/bin/python
	@echo "==> kutubxonalar o'rnatilmoqda"
	@if command -v uv >/dev/null 2>&1; then uv pip install -q -p $(PY) -r requirements.txt; else $(PY) -m pip install -q -r requirements.txt; fi
	@touch $@

install: .venv/.installed

.env:
	@cp .env.example .env
	@sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')|" .env
	@echo "==> .env yaratildi (.env.example asosida)"

test: install
	@bash scripts/ci.sh
