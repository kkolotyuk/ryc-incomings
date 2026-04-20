.PHONY: init run

init:
	@test -f .env || cp .env.example .env
	docker compose run --rm --build setup

run:
	docker compose up --build app

shell:
	docker compose run --rm --build app python
