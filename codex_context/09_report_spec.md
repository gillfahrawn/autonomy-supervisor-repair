The tool must generate:

reports/latest/index.md
reports/latest/summary.json
reports/latest/before_after.csv
reports/latest/best_patch.yaml
reports/latest/failure_examples/
reports/latest/trace_plots/

The report must include:
- baseline failure rate
- candidate patch rankings
- before/after violation counts
- top 5 counterexample traces
- best patch diff
- invariant check result
- limitations section