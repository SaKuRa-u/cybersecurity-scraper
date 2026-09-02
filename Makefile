.PHONY: up down build logs shell-backend shell-db migrate seed test clean

up:
	docker compose up -d

down:
	docker compose down

build:
	docker compose build

logs:
	docker compose logs -f

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec postgres psql -U scraper_user -d cybersec_scraper

migrate:
	docker compose exec backend alembic upgrade head

seed:
	docker compose exec backend python -m scripts.seed_sources

test:
	docker compose exec backend pytest tests/ -v

clean:
	docker compose down -v
	rm -rf logs/* exports/*
