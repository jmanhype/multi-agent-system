"""
Trading Orchestrator - Main 5-minute trading loop.

Integrates: DexAdapter -> FeatureExtractor -> RSIEMAStrategy -> RiskManager -> Execute -> Log
Paper mode works with zero API keys.
"""

import asyncio
import hashlib
import json
import logging
import os
import sqlite3
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any

import pandas as pd

from lib.data.dex_adapter import DexAdapter
from lib.features.extractor import FeatureExtractor
from lib.trading.strategies.rsi_ema import RSIEMAStrategy, Signal
from lib.risk.manager import RiskManager

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class TradeRecord:
    """Immutable trade record with SHA256 proof."""
    trade_id: str
    timestamp: str
    symbol: str
    side: str
    action: str  # 'open' or 'close'
    price: float
    size_usd: float
    mode: str  # 'paper' or 'live'
    signal_confidence: float = 0.0
    signal_reason: str = ""
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    pnl_usd: Optional[float] = None
    pnl_pct: Optional[float] = None
    exit_reason: str = ""
    risk_score: float = 0.0
    proof: str = ""  # SHA256 of record

    def compute_proof(self) -> str:
        """Compute SHA256 proof over all fields except proof."""
        d = asdict(self)
        d.pop("proof", None)
        canonical = json.dumps(d, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Trade Logger ────────────────────────────────────────────────────

class TradeLogger:
    """Append-only JSONL trade log + SQLite metrics."""

    def __init__(
        self,
        log_path: str = "logs/trades.jsonl",
        db_path: str = "db/metrics.db",
    ):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Ensure trades table exists."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS trades (
                trade_id TEXT PRIMARY KEY,
                timestamp TEXT,
                symbol TEXT,
                side TEXT,
                action TEXT,
                price REAL,
                size_usd REAL,
                mode TEXT,
                signal_confidence REAL,
                pnl REAL,
                pnl_pct REAL,
                exit_reason TEXT,
                risk_score REAL,
                proof TEXT
            )
        """)
        conn.commit()
        conn.close()

    def log(self, record: TradeRecord):
        """Append record to JSONL and SQLite."""
        record.proof = record.compute_proof()

        # JSONL
        with open(self.log_path, "a") as f:
            f.write(json.dumps(record.to_dict()) + "\n")

        # SQLite
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """INSERT OR REPLACE INTO trades
                   (trade_id, timestamp, symbol, side, action, price, size_usd,
                    mode, signal_confidence, pnl, pnl_pct, exit_reason, risk_score, proof)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.trade_id, record.timestamp, record.symbol,
                    record.side, record.action, record.price, record.size_usd,
                    record.mode, record.signal_confidence,
                    record.pnl_usd, record.pnl_pct, record.exit_reason,
                    record.risk_score, record.proof,
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to write trade to SQLite: {e}")


# ── Exchange Connector ──────────────────────────────────────────────

class ExchangeConnector:
    """Execute orders (paper or live via CCXT)."""

    def __init__(self, mode: str = "paper"):
        self.mode = mode
        self._exchange = None

    def _get_exchange(self):
        """Lazy-init CCXT exchange for live mode."""
        if self._exchange is None:
            import ccxt
            self._exchange = ccxt.binance({
                "apiKey": os.environ.get("BINANCE_API_KEY", ""),
                "secret": os.environ.get("BINANCE_SECRET", ""),
                "enableRateLimit": True,
            })
        return self._exchange

    def simulate_order(
        self,
        symbol: str,
        side: str,
        size_usd: float,
        price: float,
    ) -> Dict[str, Any]:
        """Paper trade - returns simulated fill."""
        return {
            "id": f"paper_{int(time.time()*1000)}",
            "symbol": symbol,
            "side": side,
            "type": "market",
            "price": price,
            "amount": size_usd / price if price > 0 else 0,
            "cost": size_usd,
            "filled": size_usd / price if price > 0 else 0,
            "status": "closed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    async def place_market_order(
        self,
        symbol: str,
        side: str,
        amount: float,
        retries: int = 3,
    ) -> Dict[str, Any]:
        """Live market order via CCXT with retries."""
        exchange = self._get_exchange()
        last_error = None

        for attempt in range(1, retries + 1):
            try:
                order = exchange.create_market_order(symbol, side, amount)
                logger.info(f"Order filled: {order['id']} {side} {amount} {symbol}")
                return order
            except Exception as e:
                last_error = e
                logger.warning(f"Order attempt {attempt}/{retries} failed: {e}")
                if attempt < retries:
                    await asyncio.sleep(2 ** attempt)

        raise RuntimeError(f"Order failed after {retries} attempts: {last_error}")


# ── Open Position Tracker ───────────────────────────────────────────

@dataclass
class OpenPosition:
    """Tracks a single open position."""
    position_id: str
    symbol: str
    side: str
    entry_price: float
    size_usd: float
    entry_time: str
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_confidence: float = 0.0
    signal_reason: str = ""


# ── Trading Orchestrator ────────────────────────────────────────────

class TradingOrchestrator:
    """
    Main trading loop orchestrator.

    5-minute cycle:
        1. Fetch latest OHLCV data via DexAdapter
        2. Extract features via FeatureExtractor
        3. Generate signal via RSIEMAStrategy
        4. Validate risk via RiskManager
        5. Execute trade (paper or live)
        6. Log everything
    """

    def __init__(
        self,
        symbol: str = "BTC/USDC",
        timeframe: str = "5m",
        mode: str = "paper",
        risk_config: Optional[Dict] = None,
        strategy: Optional[RSIEMAStrategy] = None,
    ):
        self.symbol = symbol
        self.timeframe = timeframe
        self.mode = mode

        # Load risk config
        if risk_config is None:
            risk_config = self._load_risk_config()
        self.risk_manager = RiskManager(risk_config)

        # Strategy
        self.strategy = strategy or RSIEMAStrategy.from_winner_config()

        # Components
        self.adapter = DexAdapter(sandbox=False)
        self.extractor = FeatureExtractor()
        self.connector = ExchangeConnector(mode=mode)
        self.trade_logger = TradeLogger()

        # State
        self.position: Optional[OpenPosition] = None
        self.iteration_count = 0
        self.running = False
        self._load_state()

        logger.info(
            f"TradingOrchestrator initialized: {symbol} {timeframe} mode={mode} "
            f"strategy={self.strategy}"
        )

    @staticmethod
    def _load_risk_config() -> Dict:
        """Load risk config from file or return defaults."""
        risk_path = Path("config/risk.json")
        if risk_path.exists():
            with open(risk_path) as f:
                cfg = json.load(f)
            return {
                "max_position_size": cfg.get("max_position_size", 62.50),
                "max_daily_loss": cfg.get("max_daily_loss_usd", 100),
                "max_drawdown": cfg.get("max_drawdown_percent", 5.0) / 100,
                "max_consecutive_losses": cfg.get("max_consecutive_losses", 3),
                "bankroll_percentage": cfg.get("per_trade_risk_percent", 2.0) / 100,
                "max_leverage": cfg.get("max_leverage", 3.0),
                "symbol_whitelist": cfg.get("symbol_whitelist", ["BTC/USDC", "ETH/USDC"]),
            }
        return {
            "max_position_size": 62.50,
            "max_daily_loss": 100,
            "max_drawdown": 0.05,
            "max_consecutive_losses": 3,
            "symbol_whitelist": ["BTC/USDC", "ETH/USDC"],
        }

    def _state_path(self) -> Path:
        return Path("data/orchestrator_state.json")

    def _load_state(self):
        """Load orchestrator state from disk."""
        sp = self._state_path()
        if sp.exists():
            try:
                with open(sp) as f:
                    state = json.load(f)
                if state.get("position"):
                    p = state["position"]
                    self.position = OpenPosition(**p)
                self.iteration_count = state.get("iteration_count", 0)
                logger.info(f"Loaded state: iteration={self.iteration_count}, position={'yes' if self.position else 'no'}")
            except Exception as e:
                logger.warning(f"Failed to load state: {e}")

    def _save_state(self):
        """Persist orchestrator state."""
        sp = self._state_path()
        sp.parent.mkdir(parents=True, exist_ok=True)
        state = {
            "iteration_count": self.iteration_count,
            "position": asdict(self.position) if self.position else None,
            "last_update": datetime.now(timezone.utc).isoformat(),
            "mode": self.mode,
            "symbol": self.symbol,
        }
        with open(sp, "w") as f:
            json.dump(state, f, indent=2)

    # ── Single iteration ────────────────────────────────────────────

    def run_once(self) -> Dict[str, Any]:
        """Execute one trading iteration.

        Returns:
            Dict with iteration result summary.
        """
        self.iteration_count += 1
        start = time.time()
        result: Dict[str, Any] = {
            "iteration": self.iteration_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "symbol": self.symbol,
            "mode": self.mode,
        }

        try:
            # 1. Fetch data
            df = self.adapter.get_candles(self.symbol, self.timeframe, limit=200)
            if df.empty or len(df) < 60:
                result["status"] = "insufficient_data"
                result["candles"] = len(df)
                self._save_state()
                return result
            result["candles"] = len(df)

            current_price = float(df["close"].iloc[-1])
            result["price"] = current_price

            # 2. Extract features
            features = self.extractor.extract(df, self.symbol, self.timeframe)
            quality = features.get("metadata", {}).get("data_quality_score", 0)
            result["data_quality"] = quality

            if quality < 0.7:
                result["status"] = "low_quality_data"
                self._save_state()
                return result

            # 3. Generate signal
            signal = self.strategy.generate_signal(features, self.symbol)
            result["signal"] = signal.action
            result["confidence"] = signal.confidence

            # 4. Act on signal
            if self.position is not None:
                # Check exit conditions
                result.update(self._handle_exit(signal, current_price))
            else:
                # Check entry conditions
                result.update(self._handle_entry(signal, current_price, features))

            result["status"] = "ok"

        except Exception as e:
            logger.error(f"Iteration {self.iteration_count} failed: {e}")
            result["status"] = "error"
            result["error"] = str(e)

        result["elapsed_ms"] = round((time.time() - start) * 1000, 1)
        self._save_state()
        return result

    def _handle_entry(
        self,
        signal: Signal,
        price: float,
        features: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Handle potential entry."""
        info: Dict[str, Any] = {"trade_action": "none"}

        if signal.action != "entry_long" or signal.confidence < 0.5:
            return info

        # Risk validation
        volatility = features.get("features", {}).get("volatility", {}).get("realized_vol", 0.15)
        atr_val = features.get("features", {}).get("volatility", {}).get("atr_14", price * 0.02)

        sizing = self.risk_manager.calculate_position_size(
            price=price, atr=atr_val, symbol=self.symbol,
            market_data={"volatility": volatility},
        )
        size_usd = sizing.get("recommended_size", 0)

        if size_usd <= 0:
            info["trade_action"] = "risk_rejected_sizing"
            return info

        risk_result = self.risk_manager.validate_trade(
            {"symbol": self.symbol, "size": size_usd, "side": "long"},
            {"volatility": volatility},
        )

        if not risk_result.get("approved", False):
            info["trade_action"] = "risk_rejected"
            info["risk_recommendation"] = risk_result.get("recommendation", "")
            return info

        adjusted_size = risk_result.get("adjusted_size", size_usd)

        # Execute
        if self.mode == "paper":
            fill = self.connector.simulate_order(self.symbol, "buy", adjusted_size, price)
        else:
            # Live mode would use async; for sync context, run in event loop
            loop = asyncio.new_event_loop()
            try:
                amount = adjusted_size / price
                fill = loop.run_until_complete(
                    self.connector.place_market_order(self.symbol, "buy", amount)
                )
            finally:
                loop.close()

        # Record position
        position_id = f"pos_{int(time.time()*1000)}"
        self.position = OpenPosition(
            position_id=position_id,
            symbol=self.symbol,
            side="long",
            entry_price=price,
            size_usd=adjusted_size,
            entry_time=datetime.now(timezone.utc).isoformat(),
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            signal_confidence=signal.confidence,
            signal_reason=signal.reason,
        )

        # Log trade
        record = TradeRecord(
            trade_id=f"t_{position_id}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=self.symbol,
            side="long",
            action="open",
            price=price,
            size_usd=adjusted_size,
            mode=self.mode,
            signal_confidence=signal.confidence,
            signal_reason=signal.reason,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            risk_score=risk_result.get("risk_score", 0),
        )
        self.trade_logger.log(record)

        info["trade_action"] = "opened_long"
        info["size_usd"] = adjusted_size
        info["stop_loss"] = signal.stop_loss
        info["take_profit"] = signal.take_profit
        logger.info(
            f"OPENED LONG {self.symbol} @ {price:.2f} size=${adjusted_size:.2f} "
            f"SL={signal.stop_loss} TP={signal.take_profit}"
        )
        return info

    def _handle_exit(self, signal: Signal, price: float) -> Dict[str, Any]:
        """Handle exit logic for open position."""
        info: Dict[str, Any] = {"trade_action": "holding"}
        pos = self.position

        exit_reason = ""

        # Check stop loss / take profit
        if pos.stop_loss and price <= pos.stop_loss:
            exit_reason = "stop_loss"
        elif pos.take_profit and price >= pos.take_profit:
            exit_reason = "take_profit"
        elif signal.action == "exit" and signal.confidence >= 0.5:
            exit_reason = f"signal: {signal.reason}"

        if not exit_reason:
            return info

        # Calculate PnL
        if pos.side == "long":
            pnl_pct = (price - pos.entry_price) / pos.entry_price
        else:
            pnl_pct = (pos.entry_price - price) / pos.entry_price
        pnl_usd = pos.size_usd * pnl_pct

        # Execute close
        if self.mode == "paper":
            self.connector.simulate_order(self.symbol, "sell", pos.size_usd, price)
        else:
            loop = asyncio.new_event_loop()
            try:
                amount = pos.size_usd / price
                loop.run_until_complete(
                    self.connector.place_market_order(self.symbol, "sell", amount)
                )
            finally:
                loop.close()

        # Update risk manager
        self.risk_manager.update_pnl(pnl_usd)

        # Log trade
        record = TradeRecord(
            trade_id=f"t_close_{pos.position_id}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            symbol=self.symbol,
            side=pos.side,
            action="close",
            price=price,
            size_usd=pos.size_usd,
            mode=self.mode,
            signal_confidence=signal.confidence,
            signal_reason=signal.reason,
            stop_loss=pos.stop_loss,
            take_profit=pos.take_profit,
            pnl_usd=round(pnl_usd, 4),
            pnl_pct=round(pnl_pct * 100, 4),
            exit_reason=exit_reason,
        )
        self.trade_logger.log(record)

        logger.info(
            f"CLOSED {pos.side.upper()} {self.symbol} @ {price:.2f} "
            f"PnL=${pnl_usd:+.2f} ({pnl_pct:+.2%}) reason={exit_reason}"
        )

        self.position = None
        info["trade_action"] = "closed"
        info["exit_reason"] = exit_reason
        info["pnl_usd"] = round(pnl_usd, 4)
        info["pnl_pct"] = round(pnl_pct * 100, 4)
        return info

    # ── Continuous loop ─────────────────────────────────────────────

    async def run_trading_loop(
        self,
        interval_seconds: int = 300,
        max_iterations: Optional[int] = None,
    ):
        """Run the trading loop continuously.

        Args:
            interval_seconds: Sleep between iterations (default 5 min).
            max_iterations: Stop after N iterations (None = forever).
        """
        self.running = True
        logger.info(
            f"Starting trading loop: {self.symbol} {self.timeframe} "
            f"mode={self.mode} interval={interval_seconds}s"
        )

        iteration = 0
        try:
            while self.running:
                result = self.run_once()
                logger.info(
                    f"[{result.get('iteration')}] status={result.get('status')} "
                    f"price={result.get('price', 'N/A')} signal={result.get('signal', 'N/A')} "
                    f"action={result.get('trade_action', 'N/A')} "
                    f"elapsed={result.get('elapsed_ms', 0)}ms"
                )

                iteration += 1
                if max_iterations and iteration >= max_iterations:
                    logger.info(f"Reached max iterations ({max_iterations})")
                    break

                await asyncio.sleep(interval_seconds)

        except KeyboardInterrupt:
            logger.info("Trading loop stopped by user")
        finally:
            self.running = False
            self._save_state()
            logger.info("Trading loop ended")

    def stop(self):
        """Signal the loop to stop."""
        self.running = False

    def get_status(self) -> Dict[str, Any]:
        """Return current orchestrator status."""
        risk_status = self.risk_manager.get_risk_status()
        return {
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "mode": self.mode,
            "running": self.running,
            "iteration_count": self.iteration_count,
            "position": asdict(self.position) if self.position else None,
            "strategy": str(self.strategy),
            "risk": risk_status,
        }
