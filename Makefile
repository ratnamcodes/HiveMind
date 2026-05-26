.PHONY: up logs down api-shell

up:
	docker compose up -d

logs:
	docker compose logs -f

down:
	docker compose down

api-shell:
	docker compose exec api /bin/bash
