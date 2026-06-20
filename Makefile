.PHONY: demo test

PYTHON ?= python3

demo:
	mkdir -p data reports
	$(PYTHON) -m src.cli generate-scenarios --config configs/scenarios.yaml --out data/scenarios.jsonl
	$(PYTHON) -m src.cli run-baseline --supervisor configs/baseline_supervisor.yaml --scenarios data/scenarios.jsonl --out data/baseline_traces.jsonl
	$(PYTHON) -m src.cli verify --traces data/baseline_traces.jsonl --out reports/baseline
	$(PYTHON) -m src.cli repair --supervisor configs/baseline_supervisor.yaml --traces data/baseline_traces.jsonl --out data/candidates/
	$(PYTHON) -m src.cli evaluate-candidates --candidates data/candidates/ --scenarios data/scenarios.jsonl --out reports/latest

test:
	$(PYTHON) -m pytest

