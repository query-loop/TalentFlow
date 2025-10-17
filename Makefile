.PHONY: dev-up dev-down dev-logs dev

dev-up:
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh

dev-logs:
	tail -f .run/backend.log .run/frontend.log

dev:
	bash scripts/dev.sh

.PHONY: up down logs ps token health

up:
	docker compose up -d

down:
	docker compose down -v

logs:
	docker compose logs -f --tail=200

ps:
	docker compose ps

token:
	python -c "from server.app.utils.auth import create_access_token; print(create_access_token('devuser'))"

health:
	curl -sf http://localhost:9002/api/health && echo OK
