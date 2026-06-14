.PHONY: verify train eval model-service api help

help:
	@echo "make verify   - run all quality gates (rubocop, rspec, ruff, mypy, pytest)"
	@echo "make train    - train the model and regenerate docs/TEST_RESULTS.md"
	@echo "make model-service - run the Python model service on :8010"
	@echo "make api      - run the Rails API on :3001 (needs the model service)"

verify:
	bash scripts/verify.sh

train eval:
	cd model_service && uv run python scripts/train.py

model-service:
	cd model_service && set -a && . ../.env && set +a && \
		uv run uvicorn service.main:app --port 8010

api:
	cd api && set -a && . ../.env && set +a && \
		MODEL_SERVICE_URL=http://127.0.0.1:8010 bin/rails server -p 3001
