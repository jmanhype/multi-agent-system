"""
Research Orchestrator - Evolutionary strategy optimization pipeline.

Generates RSI-EMA strategy candidates, backtests them, and promotes
winners that beat config/benchmarks.json thresholds.

Uses Ollama (free) for LLM-guided proposals when available,
falls back to deterministic parameter variations.
"""

import copy
import hashlib
import json
import logging
import os
import random
import time
import uuid
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple

import numpy as np
import pandas as pd

from lib.trading.strategies.rsi_ema import RSIEMAStrategy
from lib.research.backtester_vbt import run_backtest as vbt_run_backtest

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class StrategyCandidate:
    """A strategy candidate with its backtest results."""
    candidate_id: str
    generation: int
    params: Dict[str, Any]
    metrics: Dict[str, float] = field(default_factory=dict)
    fitness: float = 0.0
    parent_id: Optional[str] = None
    mutation_type: str = "seed"
    timestamp: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Strategy Proposer ───────────────────────────────────────────────

class StrategyProposer:
    """Generate strategy candidates via Ollama or deterministic variations."""

    # Parameter ranges for RSI-EMA strategy
    PARAM_RANGES = {
        "ema_fast": (5, 30),
        "ema_slow": (30, 100),
        "rsi_period": (7, 21),
        "rsi_entry": (15, 40),
        "rsi_exit": (50, 80),
        "take_profit": (0.03, 0.15),
        "stop_loss": (0.02, 0.08),
        "atr_cap_pct": (0.01, 0.05),
    }

    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self._ollama_available = None

    def _check_ollama(self) -> bool:
        """Check if Ollama is available."""
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.ollama_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3) as resp:
                self._ollama_available = resp.status == 200
        except Exception:
            self._ollama_available = False
        logger.info(f"Ollama available: {self._ollama_available}")
        return self._ollama_available

    def generate_candidates(
        self,
        n: int = 20,
        base_params: Optional[Dict] = None,
    ) -> List[StrategyCandidate]:
        """Generate N strategy candidates.

        Tries Ollama first, falls back to deterministic generation.
        """
        if base_params is None:
            base_params = RSIEMAStrategy.from_winner_config().to_params()

        candidates = []

        # First candidate is always the base (current winner)
        candidates.append(StrategyCandidate(
            candidate_id=f"seed_{uuid.uuid4().hex[:8]}",
            generation=0,
            params=dict(base_params),
            mutation_type="seed",
            timestamp=datetime.now(timezone.utc).isoformat(),
        ))

        # Try Ollama for creative proposals
        if self._check_ollama():
            ollama_candidates = self._propose_via_ollama(base_params, n=min(5, n - 1))
            candidates.extend(ollama_candidates)

        # Fill remaining with deterministic variations
        remaining = n - len(candidates)
        if remaining > 0:
            deterministic = self._generate_deterministic(base_params, n=remaining)
            candidates.extend(deterministic)

        return candidates[:n]

    def _propose_via_ollama(
        self,
        base_params: Dict,
        n: int = 5,
    ) -> List[StrategyCandidate]:
        """Ask Ollama to suggest parameter variations."""
        candidates = []
        try:
            import urllib.request

            prompt = (
                f"You are a quantitative trading researcher. Given this RSI-EMA strategy:\n"
                f"{json.dumps(base_params, indent=2)}\n\n"
                f"Suggest {n} parameter variations that might improve Sharpe ratio.\n"
                f"Return ONLY a JSON array of parameter dicts. Each dict must have keys: "
                f"ema_fast, ema_slow, rsi_period, rsi_entry, rsi_exit, take_profit, stop_loss, atr_cap_pct.\n"
                f"Keep ema_fast < ema_slow. Keep rsi_entry < rsi_exit.\n"
                f"Respond with JSON only, no explanation."
            )

            payload = json.dumps({
                "model": "llama3.2",
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": 0.8},
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.ollama_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=60) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                response_text = result.get("response", "")

            # Parse JSON from response
            # Try to find JSON array in the response
            start = response_text.find("[")
            end = response_text.rfind("]") + 1
            if start >= 0 and end > start:
                param_list = json.loads(response_text[start:end])
                for i, params in enumerate(param_list[:n]):
                    # Validate and clamp parameters
                    params = self._clamp_params(params)
                    if params.get("ema_fast", 10) < params.get("ema_slow", 58):
                        candidates.append(StrategyCandidate(
                            candidate_id=f"ollama_{uuid.uuid4().hex[:8]}",
                            generation=0,
                            params=params,
                            mutation_type="ollama_proposal",
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        ))

            logger.info(f"Ollama proposed {len(candidates)} candidates")

        except Exception as e:
            logger.warning(f"Ollama proposal failed: {e}")

        return candidates

    def _generate_deterministic(
        self,
        base_params: Dict,
        n: int = 15,
    ) -> List[StrategyCandidate]:
        """Generate deterministic parameter variations."""
        candidates = []
        rng = random.Random(42)

        for i in range(n):
            params = dict(base_params)
            mutation_type = rng.choice(["jitter", "grid", "random"])

            if mutation_type == "jitter":
                # Small random perturbations around base
                for key, (lo, hi) in self.PARAM_RANGES.items():
                    if key in params:
                        val = params[key]
                        spread = (hi - lo) * 0.15
                        params[key] = self._clamp_value(
                            val + rng.gauss(0, spread), lo, hi
                        )

            elif mutation_type == "grid":
                # Systematic grid exploration
                grid_key = list(self.PARAM_RANGES.keys())[i % len(self.PARAM_RANGES)]
                lo, hi = self.PARAM_RANGES[grid_key]
                step = (hi - lo) / (n + 1)
                params[grid_key] = lo + step * (i + 1)

            else:  # random
                # Fully random within ranges
                for key, (lo, hi) in self.PARAM_RANGES.items():
                    if isinstance(base_params.get(key), int):
                        params[key] = rng.randint(int(lo), int(hi))
                    else:
                        params[key] = rng.uniform(lo, hi)

            # Enforce constraints
            params = self._clamp_params(params)

            # Ensure ema_fast < ema_slow and rsi_entry < rsi_exit
            if params.get("ema_fast", 10) >= params.get("ema_slow", 58):
                params["ema_fast"] = max(5, params["ema_slow"] - 10)
            if params.get("rsi_entry", 27) >= params.get("rsi_exit", 58):
                params["rsi_entry"] = max(15, params["rsi_exit"] - 15)

            # Round integer params
            for key in ("ema_fast", "ema_slow", "rsi_period"):
                if key in params:
                    params[key] = int(round(params[key]))

            candidates.append(StrategyCandidate(
                candidate_id=f"det_{uuid.uuid4().hex[:8]}",
                generation=0,
                params=params,
                mutation_type=mutation_type,
                timestamp=datetime.now(timezone.utc).isoformat(),
            ))

        return candidates

    def _clamp_params(self, params: Dict) -> Dict:
        """Clamp parameters to valid ranges."""
        clamped = dict(params)
        for key, (lo, hi) in self.PARAM_RANGES.items():
            if key in clamped:
                clamped[key] = self._clamp_value(clamped[key], lo, hi)
        return clamped

    @staticmethod
    def _clamp_value(val: float, lo: float, hi: float) -> float:
        return max(lo, min(hi, val))


# ── Performance Analyzer ───────────────────────────────────────────

class PerformanceAnalyzer:
    """Multi-criteria scoring for strategy candidates."""

    # Weighted scoring: sharpe*0.3 + win_rate*0.2 + pf*0.2 - dd*0.3
    WEIGHTS = {
        "sharpe_ratio": 0.3,
        "win_rate": 0.2,
        "profit_factor": 0.2,
        "max_drawdown": -0.3,  # Negative weight (penalty)
    }

    def score(self, metrics: Dict[str, float]) -> float:
        """Compute fitness score from backtest metrics."""
        sharpe = metrics.get("sharpe_ratio", 0)
        win_rate = metrics.get("win_rate", 0)
        pf = metrics.get("profit_factor", 0)
        dd = abs(metrics.get("max_drawdown", 0))

        # Normalize components to ~[0, 1] range
        sharpe_norm = min(sharpe / 5.0, 1.0) if sharpe > 0 else 0
        win_rate_norm = win_rate  # Already 0-1
        pf_norm = min(pf / 3.0, 1.0) if pf > 0 else 0
        dd_norm = min(dd / 0.5, 1.0)  # Drawdown as fraction

        fitness = (
            self.WEIGHTS["sharpe_ratio"] * sharpe_norm
            + self.WEIGHTS["win_rate"] * win_rate_norm
            + self.WEIGHTS["profit_factor"] * pf_norm
            + self.WEIGHTS["max_drawdown"] * dd_norm  # Already negative weight
        )

        return round(fitness, 6)

    def rank(self, candidates: List[StrategyCandidate]) -> List[StrategyCandidate]:
        """Rank candidates by fitness (highest first)."""
        return sorted(candidates, key=lambda c: c.fitness, reverse=True)

    def meets_benchmarks(self, metrics: Dict[str, float], benchmarks: Dict) -> Tuple[bool, List[str]]:
        """Check if metrics meet benchmark thresholds.

        Returns:
            (passed, list of failing criteria)
        """
        targets = benchmarks.get("target_metrics", {})
        failures = []

        checks = {
            "min_sharpe": ("sharpe_ratio", ">="),
            "min_win_rate": ("win_rate", ">="),
            "min_profit_factor": ("profit_factor", ">="),
            "max_drawdown": ("max_drawdown", "<="),
            "min_total_return": ("total_return", ">="),
            "min_sortino": ("sortino", ">="),
        }

        for target_key, (metric_key, op) in checks.items():
            threshold = targets.get(target_key)
            if threshold is None:
                continue

            value = metrics.get(metric_key, 0)
            if op == ">=" and value < threshold:
                failures.append(f"{metric_key}={value:.4f} < {threshold}")
            elif op == "<=" and abs(value) > threshold:
                failures.append(f"{metric_key}={abs(value):.4f} > {threshold}")

        return (len(failures) == 0, failures)


# ── Backtest Coordinator ────────────────────────────────────────────

class BacktestCoordinator:
    """Run backtests for strategy candidates using existing infrastructure."""

    def __init__(self):
        pass

    def run(
        self,
        candidate: StrategyCandidate,
        data: pd.DataFrame,
        initial_cash: float = 10000,
    ) -> Dict[str, float]:
        """Backtest a single candidate.

        Args:
            candidate: Strategy candidate with params.
            data: OHLCV DataFrame.
            initial_cash: Starting capital.

        Returns:
            Backtest metrics dict.
        """
        strategy = RSIEMAStrategy.from_params(candidate.params)
        df_signals = strategy.generate_signals(data)

        try:
            results = vbt_run_backtest(
                df_signals,
                position_size=0.25,
                initial_cash=initial_cash,
            )
        except Exception as e:
            logger.error(f"Backtest failed for {candidate.candidate_id}: {e}")
            results = {
                "total_return": 0,
                "sharpe_ratio": 0,
                "max_drawdown": 0,
                "win_rate": 0,
                "profit_factor": 0,
                "trades": 0,
                "sortino": 0,
            }

        return results

    def run_batch(
        self,
        candidates: List[StrategyCandidate],
        data: pd.DataFrame,
        initial_cash: float = 10000,
    ) -> List[StrategyCandidate]:
        """Backtest all candidates and attach metrics.

        Returns:
            Candidates with metrics and fitness populated.
        """
        analyzer = PerformanceAnalyzer()

        for i, cand in enumerate(candidates):
            logger.info(f"Backtesting {i+1}/{len(candidates)}: {cand.candidate_id}")
            metrics = self.run(cand, data, initial_cash)
            cand.metrics = metrics
            cand.fitness = analyzer.score(metrics)

        return candidates


# ── Research Orchestrator ───────────────────────────────────────────

class ResearchOrchestrator:
    """
    Evolutionary strategy optimization pipeline.

    1. Generate initial population of RSI-EMA parameter variations
    2. Backtest each candidate
    3. Evolve: tournament selection + crossover + mutation
    4. Out-of-sample validation of winner
    5. Promote to artifacts/winner.json if benchmarks are met
    """

    def __init__(
        self,
        db_path: str = "db/grid_results.db",
        log_path: str = "logs/runs.jsonl",
        benchmarks_path: str = "config/benchmarks.json",
    ):
        self.proposer = StrategyProposer()
        self.coordinator = BacktestCoordinator()
        self.analyzer = PerformanceAnalyzer()

        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.benchmarks = self._load_benchmarks(benchmarks_path)
        self.session_id = f"research_{uuid.uuid4().hex[:8]}"

        # Try to use DatabaseManager if available
        self._db = None
        try:
            from lib.storage.db_manager import DatabaseManager
            self._db = DatabaseManager(db_path)
        except Exception as e:
            logger.warning(f"DatabaseManager not available: {e}")

    @staticmethod
    def _load_benchmarks(path: str) -> Dict:
        p = Path(path)
        if p.exists():
            with open(p) as f:
                return json.load(f)
        return {
            "target_metrics": {
                "min_sharpe": 2.0,
                "min_win_rate": 0.55,
                "min_profit_factor": 1.8,
                "max_drawdown": 0.30,
            }
        }

    # ── Population generation ───────────────────────────────────────

    def generate_initial_population(self, size: int = 20) -> List[StrategyCandidate]:
        """Generate initial population of strategy candidates."""
        logger.info(f"Generating initial population of {size} candidates")
        return self.proposer.generate_candidates(n=size)

    # ── Evolution ───────────────────────────────────────────────────

    def run_evolution(
        self,
        data: pd.DataFrame,
        generations: int = 10,
        population_size: int = 20,
        elite_count: int = 3,
        mutation_rate: float = 0.3,
    ) -> List[StrategyCandidate]:
        """Run evolutionary optimization.

        Args:
            data: OHLCV DataFrame for backtesting (in-sample).
            generations: Number of evolution generations.
            population_size: Candidates per generation.
            elite_count: Top N candidates carried forward unchanged.
            mutation_rate: Probability of mutation per parameter.

        Returns:
            Final population sorted by fitness.
        """
        logger.info(
            f"Starting evolution: {generations} generations, "
            f"pop_size={population_size}, elite={elite_count}"
        )

        # Initial population
        population = self.generate_initial_population(population_size)

        # Backtest initial population
        population = self.coordinator.run_batch(population, data)
        population = self.analyzer.rank(population)

        self._log_generation(0, population)

        for gen in range(1, generations + 1):
            logger.info(f"Generation {gen}/{generations}")

            new_population: List[StrategyCandidate] = []

            # Elitism: carry forward top candidates unchanged
            elites = population[:elite_count]
            for elite in elites:
                elite_copy = StrategyCandidate(
                    candidate_id=f"elite_{uuid.uuid4().hex[:8]}",
                    generation=gen,
                    params=dict(elite.params),
                    parent_id=elite.candidate_id,
                    mutation_type="elite",
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                new_population.append(elite_copy)

            # Fill rest with crossover + mutation
            while len(new_population) < population_size:
                # Tournament selection (pick best of 3 random)
                parent_a = self._tournament_select(population, k=3)
                parent_b = self._tournament_select(population, k=3)

                # Crossover
                child_params = self._crossover(parent_a.params, parent_b.params)

                # Mutation
                mut_type = "crossover"
                if random.random() < mutation_rate:
                    child_params = self._mutate(child_params)
                    mut_type = "crossover+mutate"

                child = StrategyCandidate(
                    candidate_id=f"gen{gen}_{uuid.uuid4().hex[:8]}",
                    generation=gen,
                    params=child_params,
                    parent_id=parent_a.candidate_id,
                    mutation_type=mut_type,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                )
                new_population.append(child)

            # Backtest new generation
            population = self.coordinator.run_batch(new_population, data)
            population = self.analyzer.rank(population)

            self._log_generation(gen, population)

            # Report
            best = population[0]
            logger.info(
                f"Gen {gen} best: fitness={best.fitness:.4f} "
                f"sharpe={best.metrics.get('sharpe_ratio', 0):.2f} "
                f"wr={best.metrics.get('win_rate', 0):.2%} "
                f"pf={best.metrics.get('profit_factor', 0):.2f}"
            )

        return population

    def _tournament_select(
        self,
        population: List[StrategyCandidate],
        k: int = 3,
    ) -> StrategyCandidate:
        """Select best candidate from k random tournament participants."""
        participants = random.sample(population, min(k, len(population)))
        return max(participants, key=lambda c: c.fitness)

    def _crossover(self, params_a: Dict, params_b: Dict) -> Dict:
        """Uniform crossover between two parent parameter sets."""
        child = {}
        for key in params_a:
            if key in params_b:
                child[key] = random.choice([params_a[key], params_b[key]])
            else:
                child[key] = params_a[key]

        # Enforce constraints
        child = self.proposer._clamp_params(child)
        if child.get("ema_fast", 10) >= child.get("ema_slow", 58):
            child["ema_fast"] = max(5, child["ema_slow"] - 10)
        if child.get("rsi_entry", 27) >= child.get("rsi_exit", 58):
            child["rsi_entry"] = max(15, child["rsi_exit"] - 15)

        for key in ("ema_fast", "ema_slow", "rsi_period"):
            if key in child:
                child[key] = int(round(child[key]))

        return child

    def _mutate(self, params: Dict) -> Dict:
        """Apply gaussian mutation to parameters."""
        mutated = dict(params)
        # Mutate 1-3 random parameters
        keys_to_mutate = random.sample(
            list(self.proposer.PARAM_RANGES.keys()),
            k=min(3, len(self.proposer.PARAM_RANGES)),
        )

        for key in keys_to_mutate:
            if key in mutated:
                lo, hi = self.proposer.PARAM_RANGES[key]
                spread = (hi - lo) * 0.2
                mutated[key] = max(lo, min(hi, mutated[key] + random.gauss(0, spread)))

        for key in ("ema_fast", "ema_slow", "rsi_period"):
            if key in mutated:
                mutated[key] = int(round(mutated[key]))

        return mutated

    # ── Winner selection ────────────────────────────────────────────

    def select_winner(
        self,
        candidates: List[StrategyCandidate],
        test_data: pd.DataFrame,
    ) -> Optional[StrategyCandidate]:
        """Validate top candidates on out-of-sample data.

        Returns:
            Best candidate that passes benchmarks, or None.
        """
        logger.info(f"Validating top candidates on out-of-sample data ({len(test_data)} rows)")

        # Re-backtest top 5 on out-of-sample data
        top_n = candidates[:5]
        validated = self.coordinator.run_batch(top_n, test_data)
        validated = self.analyzer.rank(validated)

        for cand in validated:
            passed, failures = self.analyzer.meets_benchmarks(cand.metrics, self.benchmarks)
            if passed:
                logger.info(f"Winner found: {cand.candidate_id} fitness={cand.fitness:.4f}")
                return cand
            else:
                logger.info(
                    f"Candidate {cand.candidate_id} failed benchmarks: "
                    + ", ".join(failures)
                )

        logger.warning("No candidate passed all benchmarks")
        return None

    # ── Promotion ───────────────────────────────────────────────────

    def promote_winner(self, winner: StrategyCandidate) -> str:
        """Save winner to artifacts/winner.json and log to runs.jsonl.

        Returns:
            Path to winner file.
        """
        output_dir = Path("artifacts")
        output_dir.mkdir(parents=True, exist_ok=True)
        winner_path = output_dir / "winner.json"

        winner_data = {
            "id": winner.candidate_id,
            "promoted_at": datetime.now(timezone.utc).isoformat(),
            "session_id": self.session_id,
            "generation": winner.generation,
            "params": winner.params,
            "metrics": winner.metrics,
            "fitness": winner.fitness,
            "mutation_type": winner.mutation_type,
            "parent_id": winner.parent_id,
        }

        with open(winner_path, "w") as f:
            json.dump(winner_data, f, indent=2)

        # Log to runs.jsonl
        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "winner_promoted",
            "session_id": self.session_id,
            "winner": winner_data,
        }
        with open(self.log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        # Save to database if available
        if self._db:
            try:
                self._db.save_evolution_step(
                    session_id=self.session_id,
                    generation=winner.generation,
                    strategy_config=winner.params,
                    fitness=winner.fitness,
                    parent=winner.parent_id,
                    mutation=winner.mutation_type,
                    metrics=winner.metrics,
                )
            except Exception as e:
                logger.warning(f"Failed to save to database: {e}")

        logger.info(f"Winner promoted to {winner_path}")
        return str(winner_path)

    # ── Logging ─────────────────────────────────────────────────────

    def _log_generation(self, generation: int, population: List[StrategyCandidate]):
        """Log generation results to JSONL."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": "generation_complete",
            "session_id": self.session_id,
            "generation": generation,
            "population_size": len(population),
            "best_fitness": population[0].fitness if population else 0,
            "best_metrics": population[0].metrics if population else {},
            "fitness_distribution": {
                "mean": float(np.mean([c.fitness for c in population])),
                "std": float(np.std([c.fitness for c in population])),
                "min": float(min(c.fitness for c in population)),
                "max": float(max(c.fitness for c in population)),
            },
        }

        with open(self.log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")

        # Save to database
        if self._db:
            for cand in population[:5]:  # Save top 5
                try:
                    self._db.save_evolution_step(
                        session_id=self.session_id,
                        generation=generation,
                        strategy_config=cand.params,
                        fitness=cand.fitness,
                        parent=cand.parent_id,
                        mutation=cand.mutation_type,
                        metrics=cand.metrics,
                    )
                except Exception:
                    pass

    # ── Full pipeline ───────────────────────────────────────────────

    def run_pipeline(
        self,
        data: pd.DataFrame,
        generations: int = 10,
        population_size: int = 20,
        test_split: float = 0.3,
    ) -> Optional[StrategyCandidate]:
        """Run the complete research pipeline.

        Args:
            data: Full OHLCV DataFrame.
            generations: Evolution generations.
            population_size: Candidates per generation.
            test_split: Fraction of data for out-of-sample validation.

        Returns:
            Promoted winner or None.
        """
        logger.info(
            f"Starting research pipeline: {len(data)} rows, "
            f"{generations} generations, pop={population_size}"
        )

        # Split data
        split_idx = int(len(data) * (1 - test_split))
        train_data = data.iloc[:split_idx].copy()
        test_data = data.iloc[split_idx:].copy()

        logger.info(f"Train: {len(train_data)} rows, Test: {len(test_data)} rows")

        # Evolution on training data
        final_population = self.run_evolution(
            train_data,
            generations=generations,
            population_size=population_size,
        )

        # Validate on test data
        winner = self.select_winner(final_population, test_data)

        if winner:
            self.promote_winner(winner)
            return winner

        logger.warning("Pipeline completed without a qualifying winner")
        return None
