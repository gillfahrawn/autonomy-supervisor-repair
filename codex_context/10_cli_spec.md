python -m src.cli generate-scenarios --config configs/scenarios.yaml --out data/scenarios.jsonl

python -m src.cli run-baseline --supervisor configs/baseline_supervisor.yaml --scenarios data/scenarios.jsonl --out data/baseline_traces.jsonl

python -m src.cli verify --traces data/baseline_traces.jsonl --out reports/baseline

python -m src.cli repair --supervisor configs/baseline_supervisor.yaml --traces data/baseline_traces.jsonl --out data/candidates/

python -m src.cli evaluate-candidates --candidates data/candidates/ --scenarios data/scenarios.jsonl --out reports/latest