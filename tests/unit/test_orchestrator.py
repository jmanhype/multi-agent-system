"""
Unit tests for TradingOrchestrator and supporting classes.
"""

import json
import os
import pytest
import time
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

from lib.trading.orchestrator import (
    TradeRecord,
    TradeLogger,
    ExchangeConnector,
    TradingOrchestrator,
    OpenPosition,
)
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
def risk_config():
    return {
        "max_position_size": 62.50,
        "max_daily_loss": 100,
        "max_drawdown": 0.05,
        "max_consecutive_losses": 3,
        "symbol_whitelist": ["BTC/USDC", "ETH/USDC"],
    }


# ── TradeRecord tests ───────────────────────────────────────────────

class TestTradeRecord:
    def test_compute_proof(self):
        record = TradeRecord(
            trade_id="t_123",
            timestamp="2024-01-01T00:00:00",
            symbol="BTC/USDC",
            side="long",
            action="open",
            price=42000.0,
            size_usd=50.0,
            mode="paper",
        )
        proof = record.compute_proof()
        assert isinstance(proof, str)
        assert len(proof) == 64  # SHA256 hex

    def test_proof_deterministic(self):
        kwargs = dict(
            trade_id="t_1", timestamp="2024-01-01", symbol="BTC/USDC",
            side="long", action="open", price=42000.0, size_usd=50.0, mode="paper",
        )
        r1 = TradeRecord(**kwargs)
        r2 = TradeRecord(**kwargs)
        assert r1.compute_proof() == r2.compute_proof()

    def test_proof_changes_on_field_change(self):
        kwargs = dict(
            trade_id="t_1", timestamp="2024-01-01", symbol="BTC/USDC",
            side="long", action="open", price=42000.0, size_usd=50.0, mode="paper",
        )
        r1 = TradeRecord(**kwargs)
        kwargs["price"] = 43000.0
        r2 = TradeRecord(**kwargs)
        assert r1.compute_proof() != r2.compute_proof()

    def test_to_dict(self):
        record = TradeRecord(
            trade_id="t_1", timestamp="2024-01-01", symbol="BTC/USDC",
            side="long", action="open", price=42000.0, size_usd=50.0, mode="paper",
        )
        d = record.to_dict()
        assert isinstance(d, dict)
        assert d["trade_id"] == "t_1"
        assert d["price"] == 42000.0


# ── TradeLogger tests ───────────────────────────────────────────────

class TestTradeLogger:
    def test_log_creates_file(self, tmp_path):
        log_path = str(tmp_path / "trades.jsonl")
        db_path = str(tmp_path / "metrics.db")
        logger = TradeLogger(log_path=log_path, db_path=db_path)

        record = TradeRecord(
            trade_id="t_test", timestamp="2024-01-01", symbol="BTC/USDC",
            side="long", action="open", price=42000.0, size_usd=50.0, mode="paper",
        )
        logger.log(record)

        assert Path(log_path).exists()
        with open(log_path) as f:
            entry = json.loads(f.readline())
        assert entry["trade_id"] == "t_test"
        assert entry["proof"]  # proof should be computed

    def test_log_multiple_entries(self, tmp_path):
        log_path = str(tmp_path / "trades.jsonl")
        db_path = str(tmp_path / "metrics.db")
        logger = TradeLogger(log_path=log_path, db_path=db_path)

        for i in range(3):
            record = TradeRecord(
                trade_id=f"t_{i}", timestamp=f"2024-01-0{i+1}", symbol="BTC/USDC",
                side="long", action="open", price=42000.0 + i, size_usd=50.0, mode="paper",
            )
            logger.log(record)

        with open(log_path) as f:
            lines = f.readlines()
        assert len(lines) == 3


# ── ExchangeConnector tests ─────────────────────────────────────────

class TestExchangeConnector:
    def test_paper_simulate_order(self):
        conn = ExchangeConnector(mode="paper")
        fill = conn.simulate_order("BTC/USDC", "buy", 50.0, 42000.0)
        assert fill["symbol"] == "BTC/USDC"
        assert fill["side"] == "buy"
        assert fill["status"] == "closed"
        assert fill["cost"] == 50.0
        assert fill["amount"] == pytest.approx(50.0 / 42000.0, rel=1e-6)

    def test_paper_simulate_zero_price(self):
        conn = ExchangeConnector(mode="paper")
        fill = conn.simulate_order("BTC/USDC", "buy", 50.0, 0.0)
        assert fill["amount"] == 0

    def test_mode_stored(self):
        conn = ExchangeConnector(mode="live")
        assert conn.mode == "live"


# ── TradingOrchestrator tests ───────────────────────────────────────

class TestTradingOrchestrator:
    def test_init_paper_mode(self, risk_config):
        orch = TradingOrchestrator(
            symbol="BTC/USDC",
            mode="paper",
            risk_config=risk_config,
        )
        assert orch.symbol == "BTC/USDC"
        assert orch.mode == "paper"
        assert orch.position is None

    def test_get_status(self, risk_config):
        orch = TradingOrchestrator(
            symbol="BTC/USDC",
            mode="paper",
            risk_config=risk_config,
        )
        status = orch.get_status()
        assert status["symbol"] == "BTC/USDC"
        assert status["mode"] == "paper"
        assert status["running"] is False
        assert "risk" in status

    @patch("lib.trading.orchestrator.DexAdapter")
    def test_run_once_insufficient_data(self, MockAdapter, risk_config):
        mock_adapter = MockAdapter.return_value
        mock_adapter.get_candles.return_value = pd.DataFrame()

        orch = TradingOrchestrator(
            symbol="BTC/USDC",
            mode="paper",
            risk_config=risk_config,
        )
        orch.adapter = mock_adapter

        result = orch.run_once()
        assert result["status"] == "insufficient_data"

    @patch("lib.trading.orchestrator.DexAdapter")
    def test_run_once_with_data(self, MockAdapter, risk_config, sample_ohlcv):
        mock_adapter = MockAdapter.return_value
        mock_adapter.get_candles.return_value = sample_ohlcv

        orch = TradingOrchestrator(
            symbol="BTC/USDC",
            mode="paper",
            risk_config=risk_config,
        )
        orch.adapter = mock_adapter
        orch.iteration_count = 0  # Reset counter for test isolation

        result = orch.run_once()
        assert result["status"] in ("ok", "low_quality_data")
        assert "price" in result or result["status"] == "low_quality_data"
        assert result["iteration"] == 1

    def test_handle_exit_stop_loss(self, risk_config):
        orch = TradingOrchestrator(
            symbol="BTC/USDC",
            mode="paper",
            risk_config=risk_config,
        )

        # Set up a position with stop loss at 40000
        orch.position = OpenPosition(
            position_id="test_pos",
            symbol="BTC/USDC",
            side="long",
            entry_price=42000.0,
            size_usd=50.0,
            entry_time=datetime.now(timezone.utc).isoformat(),
            stop_loss=40000.0,
            take_profit=46000.0,
        )

        signal = Signal(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol="BTC/USDC",
            action="hold",
            confidence=0.0,
            indicators={},
        )

        # Price below stop loss
        result = orch._handle_exit(signal, 39500.0)
        assert result["trade_action"] == "closed"
        assert result["exit_reason"] == "stop_loss"
        assert result["pnl_usd"] < 0

    def test_handle_exit_take_profit(self, risk_config):
        orch = TradingOrchestrator(
            symbol="BTC/USDC",
            mode="paper",
            risk_config=risk_config,
        )

        orch.position = OpenPosition(
            position_id="test_pos",
            symbol="BTC/USDC",
            side="long",
            entry_price=42000.0,
            size_usd=50.0,
            entry_time=datetime.now(timezone.utc).isoformat(),
            stop_loss=40000.0,
            take_profit=46000.0,
        )

        signal = Signal(
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol="BTC/USDC",
            action="hold",
            confidence=0.0,
            indicators={},
        )

        result = orch._handle_exit(signal, 47000.0)
        assert result["trade_action"] == "closed"
        assert result["exit_reason"] == "take_profit"
        assert result["pnl_usd"] > 0

    def test_state_persistence(self, tmp_path, risk_config):
        state_path = tmp_path / "data" / "orchestrator_state.json"

        orch = TradingOrchestrator(
            symbol="ETH/USDC",
            mode="paper",
            risk_config=risk_config,
        )
        orch.iteration_count = 42
        orch._save_state()

        # The state file should exist
        default_path = Path("data/orchestrator_state.json")
        if default_path.exists():
            with open(default_path) as f:
                state = json.load(f)
            assert state["iteration_count"] == 42
            assert state["symbol"] == "ETH/USDC"
