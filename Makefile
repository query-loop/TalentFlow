.PHONY: dev-up dev-down dev-logs

dev-up:
	bash scripts/dev-up.sh

dev-down:
	bash scripts/dev-down.sh

dev-logs:
	tail -f .run/backend.log .run/frontend.log
