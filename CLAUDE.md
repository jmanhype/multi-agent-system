# Operating Guide (Claude Code)

## Principles
- **LLM offline only** (research lane). Live loop is deterministic.
- **Black-box separation**: .claude/ = control plane; lib/ = implementation.
- **Append-only evidence**: logs/*.jsonl; db/metrics.db.
- **PR gate**: promotion to `artifacts/winner.json` only via PR.

## Daily Ops (TL;DR)
- 06:00 research-loop.md → new candidates; deterministic eval; proof → logs/runs.jsonl
- If winner beats `config/benchmarks.json`, merge PR (updates `artifacts/winner.json`).
- crypto-trader.md runs each 5m (paper or live). Live requires PIN via `hooks/guard_approve.sh`.

## Safety
- `hooks/circuit_breaker.sh` flips to paper on risk/latency errors.
- `hooks/kill_switch.sh` hard stops.