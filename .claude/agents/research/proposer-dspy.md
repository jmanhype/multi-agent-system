# DSPy Proposer (REQUIRED)
Goal: Generate K strategy DSL candidates into artifacts/candidates/.
- Uses config/prompts/proposer_seed.txt and fixed schema.
- GEPA (reflective prompt evolution) enabled when configured: batch worst-K, synthesize instruction deltas, re-run.
- Deterministic sampling via fixed seeds where supported.
Output: N JSON files.