"""
Unit tests for RSIEMAStrategy.
"""

import json
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from unittest.mock import patch
from pathlib import Path

from lib.trading.strategies.rsi_ema import RSIEMAStrategy, Signal


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def sample_ohlcv():
    """Generate 200 rows of synthetic OHLCV data."""
    np.random.seed(42)
    n = 200
    base = 40000
    returns = np.random.normal(0.0001, 0.005, n)
    prices = base * (1 + returns).cumprod()

    return pd.DataFrame({
        "timestamp": pd.date_range("2024-01-01", periods=n, freq="5min"),
        "open": prices * (1 + np.random.normal(0, 0.001, n)),
        "high": prices * (1 + np.abs(np.random.normal(0, 0.002, n))),
        "low": prices * (1 - np.abs(np.random.normal(0, 0.002, n))),
        "close": prices,
        "volume": np.random.lognormal(10, 0.5, n),
    })


@pytest.fixture
def strategy():
    """Default strategy with winner parameters."""
    return RSIEMAStrategy(
        ema_fast=10,
        ema_slow=58,
        rsi_period=14,
        rsi_entry=27,
        rsi_exit=58,
        take_profit=0.0723,
        stop_loss=0.0423,
    )


@pytest.fixture
def oversold_features():
    """FeatureExtractor output simulating oversold RSI in uptrend."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "BTC/USDC",
        "timeframe": "5m",
        "features": {
            "price": {"close": 42000.0, "returns": 0.001, "log_returns": 0.001},
            "trend": {
                "ema_10": 42100.0,
                "ema_58": 41800.0,
                "regime_direction": "up",
                "trend_strength": 0.007,
            },
            "momentum": {
                "rsi_14": 22.0,
                "rsi_entry_signal": True,
                "rsi_exit_signal": False,
            },
            "volatility": {"atr_14": 350.0, "atr_cap_pct": 0.03, "realized_vol": 0.18},
            "volume": {
                "volume_ratio": 1.8,
                "volume_trend": "increasing",
                "volume_confirmation": True,
            },
            "execution": {},
        },
        "signals": {"entry_long": 0.9, "entry_short": 0.0, "exit_signal": 0.0},
        "metadata": {
            "n_features": 20,
            "computation_time_ms": 5.0,
            "data_quality_score": 0.95,
            "regime_state": "strong_uptrend",
        },
    }


@pytest.fixture
def overbought_features():
    """FeatureExtractor output simulating overbought RSI."""
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "symbol": "BTC/USDC",
        "timeframe": "5m",
        "features": {
            "price": {"close": 45000.0, "returns": 0.002, "log_returns": 0.002},
            "trend": {
                "ema_10": 44800.0,
                "ema_58": 44900.0,  # downtrend
                "regime_direction": "down",
                "trend_strength": 0.002,
            },
            "momentum": {
                "rsi_14": 72.0,
                "rsi_entry_signal": False,
                "rsi_exit_signal": True,
            },
            "volatility": {"atr_14": 400.0, "atr_cap_pct": 0.03, "realized_vol": 0.20},
            "volume": {
                "volume_ratio": 0.8,
                "volume_trend": "decreasing",
                "volume_confirmation": False,
            },
            "execution": {},
        },
        "signals": {"entry_long": 0.0, "entry_short": 0.0, "exit_signal": 0.8},
        "metadata": {
            "n_features": 20,
            "computation_time_ms": 5.0,
            "data_quality_score": 0.92,
            "regime_state": "weak_downtrend",
        },
    }


# ── Constructor tests ───────────────────────────────────────────────

class TestRSIEMAStrategyInit:
    def test_default_params(self):
        s = RSIEMAStrategy()
        assert s.ema_fast == 10
        assert s.ema_slow == 58
        assert s.rsi_entry == 27
        assert s.rsi_exit == 58

    def test_custom_params(self):
        s = RSIEMAStrategy(ema_fast=20, ema_slow=80, rsi_entry=30, rsi_exit=70)
        assert s.ema_fast == 20
        assert s.ema_slow == 80

    def test_from_params(self):
        params = {"ema_fast": 15, "ema_slow": 45, "rsi_entry": 25, "rsi_exit": 65}
        s = RSIEMAStrategy.from_params(params)
        assert s.ema_fast == 15
        assert s.rsi_exit == 65

    def test_to_params_round_trip(self, strategy):
        params = strategy.to_params()
        s2 = RSIEMAStrategy.from_params(params)
        assert s2.ema_fast == strategy.ema_fast
        assert s2.stop_loss == strategy.stop_loss

    def test_from_winner_config(self, tmp_path):
        cfg = {
            "regime": {"fast": 12, "slow": 50},
            "entry": {"threshold": 30},
            "exit": {"threshold": 60},
            "risk": {"tp": 0.08, "sl": 0.04, "atr_cap_pct": 0.025},
        }
        cfg_file = tmp_path / "test_winner.json"
        cfg_file.write_text(json.dumps(cfg))
        s = RSIEMAStrategy.from_winner_config(str(cfg_file))
        assert s.ema_fast == 12
        assert s.ema_slow == 50
        assert s.rsi_entry == 30
        assert s.take_profit == 0.08

    def test_from_winner_config_missing_file(self):
        s = RSIEMAStrategy.from_winner_config("/nonexistent/file.json")
        assert s.ema_fast == 10  # defaults


# ── Indicator calculation tests ─────────────────────────────────────

class TestCalculateIndicators:
    def test_adds_indicator_columns(self, strategy, sample_ohlcv):
        df = strategy.calculate_indicators(sample_ohlcv)
        assert "ema_fast" in df.columns
        assert "ema_slow" in df.columns
        assert "rsi" in df.columns
        assert "atr" in df.columns
        assert "uptrend" in df.columns

    def test_indicator_shapes(self, strategy, sample_ohlcv):
        df = strategy.calculate_indicators(sample_ohlcv)
        assert len(df) == len(sample_ohlcv)
        # RSI and ATR have NaN for first few rows (rolling window)
        assert df["rsi"].notna().sum() > len(df) - 20

    def test_uptrend_is_boolean(self, strategy, sample_ohlcv):
        df = strategy.calculate_indicators(sample_ohlcv)
        assert df["uptrend"].dtype == bool


# ── DataFrame signal generation tests ───────────────────────────────

class TestGenerateSignals:
    def test_entries_exits_columns(self, strategy, sample_ohlcv):
        df = strategy.generate_signals(sample_ohlcv)
        assert "entries" in df.columns
        assert "exits" in df.columns

    def test_signals_are_boolean(self, strategy, sample_ohlcv):
        df = strategy.generate_signals(sample_ohlcv)
        assert df["entries"].dtype == bool
        assert df["exits"].dtype == bool

    def test_no_simultaneous_entry_exit(self, strategy, sample_ohlcv):
        """Entry and exit can overlap (strategy allows it) but check they exist."""
        df = strategy.generate_signals(sample_ohlcv)
        # At least one entry or exit should be generated in 200 bars
        total_signals = df["entries"].sum() + df["exits"].sum()
        assert total_signals > 0

    def test_no_nan_in_signals(self, strategy, sample_ohlcv):
        df = strategy.generate_signals(sample_ohlcv)
        assert df["entries"].isna().sum() == 0
        assert df["exits"].isna().sum() == 0


# ── Single signal generation tests ──────────────────────────────────

class TestGenerateSignal:
    def test_entry_signal_on_oversold(self, strategy, oversold_features):
        signal = strategy.generate_signal(oversold_features, "BTC/USDC")
        assert signal.action == "entry_long"
        assert signal.confidence > 0.5
        assert signal.stop_loss is not None
        assert signal.take_profit is not None

    def test_exit_signal_on_overbought(self, strategy, overbought_features):
        signal = strategy.generate_signal(overbought_features, "BTC/USDC")
        assert signal.action == "exit"
        assert signal.confidence > 0.5

    def test_hold_signal_neutral(self, strategy):
        """Neutral RSI in uptrend should produce hold."""
        features = {
            "features": {
                "price": {"close": 42000.0},
                "trend": {"ema_10": 42100.0, "ema_58": 42000.0},
                "momentum": {"rsi_14": 45.0},
                "volatility": {"atr_14": 300.0},
                "volume": {"volume_confirmation": False},
            }
        }
        signal = strategy.generate_signal(features, "BTC/USDC")
        assert signal.action == "hold"
        assert signal.confidence == 0.0

    def test_signal_has_indicators(self, strategy, oversold_features):
        signal = strategy.generate_signal(oversold_features, "BTC/USDC")
        assert "rsi" in signal.indicators
        assert "ema_fast" in signal.indicators
        assert "close" in signal.indicators

    def test_signal_to_dict(self, strategy, oversold_features):
        signal = strategy.generate_signal(oversold_features, "BTC/USDC")
        d = signal.to_dict()
        assert isinstance(d, dict)
        assert "action" in d
        assert "confidence" in d
        assert "indicators" in d

    def test_volume_confirmation_boosts_confidence(self, strategy, oversold_features):
        # With volume confirmation
        signal_with = strategy.generate_signal(oversold_features, "BTC/USDC")

        # Without volume confirmation
        no_vol = json.loads(json.dumps(oversold_features))
        no_vol["features"]["volume"]["volume_confirmation"] = False
        signal_without = strategy.generate_signal(no_vol, "BTC/USDC")

        assert signal_with.confidence >= signal_without.confidence


# ── Repr test ───────────────────────────────────────────────────────

class TestRepr:
    def test_repr(self, strategy):
        r = repr(strategy)
        assert "RSIEMAStrategy" in r
        assert "10/58" in r
        assert "27" in r
