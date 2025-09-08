# Strategy Finder (deterministic evaluator)
1) Load dataset snapshot (registry), derive dataset_sha.
2) Read candidates/*.json ∪ fallback grid.
3) For each: compile → backtest (vectorbtpro if available; fallback engine otherwise).
4) Select winner via fixed tie-breakers.
5) Append proof bundle → logs/runs.jsonl.
6) If KPIs ≥ benchmarks → open PR to update artifacts/winner.json.