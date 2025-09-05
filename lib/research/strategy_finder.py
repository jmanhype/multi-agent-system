import json, hashlib, glob
import pandas as pd
from .strategy_compiler import compile_strategy
from .backtester_vbt import run_backtest

FIXED_TIEBREAK = [
    ("total_return", True),
    ("sortino", True),
    ("trades", True)
]

def _sha_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()

def _sha_file(path: str) -> str:
    with open(path,'rb') as f: return _sha_bytes(f.read())

def _select_winner(results):
    def key(x):
        return tuple((x[k] if asc else -x[k]) for k, asc in [(m, True) for m,_ in FIXED_TIEBREAK])
    return max(results, key=lambda r: (r['kpis']['total_return'], r['kpis']['sortino'], r['kpis']['trades']))

def run_research(snapshot_path: str, candidates: list[dict]) -> dict:
    # Load snapshot (pickle DataFrame with OHLCV columns)
    df = pd.read_pickle(snapshot_path)
    dataset_sha = _sha_file(snapshot_path)

    results = []
    for dsl in candidates:
        fn = compile_strategy(dsl)
        df2 = fn(df)
        kpis = run_backtest(df2)
        results.append({"id": dsl.get("id","anon"), "dsl": dsl, "kpis": kpis})

    winner = _select_winner(results)

    # Append proof bundle
    bundle = {
        "dataset_sha": dataset_sha,
        "results_sha": _sha_bytes(json.dumps(results, sort_keys=True).encode()),
        "winner": winner["id"],
        "kpis": winner["kpis"]
    }
    with open("logs/runs.jsonl","a") as f: f.write(json.dumps(bundle)+"\n")

    # (PR creation is out-of-scope for this stub.)
    return bundle