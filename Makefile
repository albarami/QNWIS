.PHONY: validate-http validate-inproc case-studies compare-baseline install dev test lint type audit lock verify

BASE_URL ?= http://localhost:8000
RESULTS_DIR ?= validation/results
CASES_DIR ?= validation/cases

# Validation targets
validate-http:
	python scripts/validation/run_validation.py --mode http --base-url $(BASE_URL) --cases $(CASES_DIR) --outdir $(RESULTS_DIR)

validate-inproc:
	python scripts/validation/run_validation.py --mode inproc --cases $(CASES_DIR) --outdir $(RESULTS_DIR)

case-studies:
	python scripts/validation/render_case_studies.py

compare-baseline:
	python scripts/validation/compare_baseline.py

# Dependency management
install:
	pip install -e .

dev:
	pip install -e ".[dev]"

lock:
	python scripts/generate_requirements_txt.py

verify:
	python scripts/verify_runtime_dependencies.py

# Testing
test:
	pytest -v --cov=src

# Code quality
lint:
	ruff check .
	flake8
	black --check .
	isort --check-only .

type:
	mypy src

# Security
audit:
	bandit -r src
	safety check || true
	pip-audit -r requirements.txt || true
