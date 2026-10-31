.PHONY: install db dev migrate migration seed admin test lint format check

PYTHON ?= .venv/bin/python

install:            ## Create the virtualenv and install all dependencies
	python3 -m venv .venv
	$(PYTHON) -m pip install -r requirements-dev.txt

db:                 ## Start PostgreSQL in Docker
	docker compose up -d db

dev:                ## Run the API with auto-reload on http://localhost:8000
	$(PYTHON) -m uvicorn app.main:app --reload

migrate:            ## Apply all pending database migrations
	$(PYTHON) -m alembic upgrade head

migration:          ## Create a migration after changing models: make migration m="add fit column"
	$(PYTHON) -m alembic revision --autogenerate -m "$(m)"

seed:               ## Load sample categories and products
	$(PYTHON) -m scripts.seed

admin:              ## Create an admin: make admin phone=03001234567 name="Umer"
	$(PYTHON) -m scripts.create_admin --phone "$(phone)" --name "$(name)"

test:               ## Run the test suite
	$(PYTHON) -m pytest

lint:               ## Check code style
	$(PYTHON) -m ruff check app tests scripts migrations/env.py
	$(PYTHON) -m ruff format --check app tests scripts

format:             ## Auto-format code
	$(PYTHON) -m ruff check --fix app tests scripts
	$(PYTHON) -m ruff format app tests scripts

check: lint test    ## Everything CI runs
