import json, os, random
from typing import List, Dict

SCHEMA = {
    "id": str,
    "universe": list,
    "timeframes": list,
    "regime": dict,
    "entry": dict,
    "exit": dict,
    "risk": dict,
    "execution": dict
}

class ReflectivePromptEvolver:
    def __init__(self, enabled: bool, iterations: int = 2, batch_worst_k: int = 12):
        self.enabled = enabled
        self.iterations = iterations
        self.k = batch_worst_k

    def evolve(self, prompt: str, eval_rows: List[Dict]) -> str:
        if not self.enabled or not eval_rows: return prompt
        # Toy GEPA: inspect worst-K by total_return and adjust thresholds slightly outward.
        worst = sorted(eval_rows, key=lambda r: r['kpis'].get('total_return',0))[: self.k]
        # Synthesize delta: encourage more conservative RSI thresholds if many losers
        if worst:
            return prompt + "\nHeuristic: widen RSI gaps by 2 and prefer slower EMA." 
        return prompt


def _rand_choice(xs): return xs[random.randrange(len(xs))]

def _emplace(d: Dict, p: str, val):
    crt = d
    parts = p.split('.')
    for k in parts[:-1]: crt = crt.setdefault(k, {})
    crt[parts[-1]] = val


def generate_candidates(out_dir: str, seed_prompt: str, max_candidates: int = 10, seed: int = 42,
                        gepa_cfg: Dict | None = None, prior_evals: List[Dict] | None = None):
    random.seed(seed)
    os.makedirs(out_dir, exist_ok=True)
    evolver = ReflectivePromptEvolver(**gepa_cfg) if gepa_cfg else ReflectivePromptEvolver(False)
    prompt = seed_prompt
    prompt = evolver.evolve(prompt, prior_evals or [])

    for i in range(max_candidates):
        dsl = {
            "id": f"ema_rsi_{i}",
            "universe": ["BTC/USDT"],
            "timeframes": ["5m"],
            "regime": {"type":"ema_cross","fast": _rand_choice([12,20,24]), "slow": _rand_choice([50,60,72]), "direction":"up"},
            "entry": {"type":"rsi","op":"below","threshold": _rand_choice([28,30,32])},
            "exit": {"type":"rsi","op":"above","threshold": _rand_choice([68,70,72])},
            "risk": {"tp": _rand_choice([0.08,0.10,0.12]), "sl": _rand_choice([0.10,0.12,0.15]), "max_orders":1, "atr_cap_pct":0.03},
            "execution": {"order_type":"market","fees":{"maker_bps":1.0,"taker_bps":4.0},
                           "slippage":{"model":"impact","k":1.2},"latency_ms":250,
                           "lot":{"min_qty":0.0001,"tick":0.10}}
        }
        with open(os.path.join(out_dir, f"{dsl['id']}.json"),"w") as f:
            json.dump(dsl, f)