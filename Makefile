.PHONY: install up down logs status restart clean test

# Default target
install:
	@bash install.sh

up:
	docker compose up -d

up-voice:
	docker compose --profile voice up -d

up-vision:
	docker compose --profile vision up -d

up-home:
	docker compose --profile home up -d

up-telegram:
	docker compose --profile telegram up -d

up-full:
	docker compose --profile voice --profile vision --profile home --profile telegram up -d

down:
	docker compose --profile voice --profile vision --profile home --profile telegram down

logs:
	docker compose logs -f

status:
	@docker compose ps
	@echo ""
	@echo "=== Health ==="
	@curl -s http://localhost:5002/api/health 2>/dev/null | python3 -m json.tool || echo "API not running"

restart:
	docker compose restart

clean:
	docker compose --profile voice --profile vision --profile home --profile telegram down -v --rmi local
	@echo "Cleaned. Data preserved in ./data/"

test:
	cd tests && python3 -m pytest -v

dev-api:
	cd core/api && pip install -r requirements.txt && uvicorn server:app --reload --host 0.0.0.0 --port 5002

dev-rag:
	cd core/rag && pip install -r requirements.txt && uvicorn rag_server:app --reload --host 0.0.0.0 --port 5001
