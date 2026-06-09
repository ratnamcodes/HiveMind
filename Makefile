.PHONY: up down logs
up:            ## one command: bring up the whole stack + instrumented apps
	bash scripts/start.sh
down:          ## stop local api/web/apps (leaves redis+phoenix)
	bash scripts/stop.sh
logs:
	docker compose logs -f
