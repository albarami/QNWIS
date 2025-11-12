.PHONY: validate-http validate-inproc case-studies compare-baseline

BASE_URL ?= http://localhost:8000
RESULTS_DIR ?= validation/results
CASES_DIR ?= validation/cases

validate-http:
	python scripts/validation/run_validation.py --mode http --base-url $(BASE_URL) --cases $(CASES_DIR) --outdir $(RESULTS_DIR)

validate-inproc:
	python scripts/validation/run_validation.py --mode inproc --cases $(CASES_DIR) --outdir $(RESULTS_DIR)

case-studies:
	python scripts/validation/render_case_studies.py

compare-baseline:
	python scripts/validation/compare_baseline.py
