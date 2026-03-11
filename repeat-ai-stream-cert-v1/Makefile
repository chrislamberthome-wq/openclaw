.PHONY: install test lint format check clean

install:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

test-cov:
	pytest tests/ -v --cov=verifier --cov-report=term-missing --cov-report=html

lint:
	ruff check verifier/ tests/ examples/

format:
	ruff format verifier/ tests/ examples/

check: lint
	ruff format --check verifier/ tests/ examples/

typecheck:
	mypy verifier/

validate-schemas:
	python -c "import json, jsonschema; \
	  [jsonschema.Draft7Validator(json.load(open(s))).check_schema(json.load(open(s))) \
	   for s in ['schemas/ai_inference_receipt.schema.json', \
	             'schemas/input_event_envelope.schema.json', \
	             'schemas/replay_verification_result.schema.json']]"
	@echo "All schemas are valid."

clean:
	rm -rf dist/ build/ *.egg-info .pytest_cache htmlcov .coverage
	find . -type d -name __pycache__ -exec rm -rf {} +

all: install check test
