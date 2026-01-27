#!/usr/bin/env python
"""
Paper Trading Bot
Executes the AI-generated strategy with simulated trades (no real money)

Usage:
    python paper_trader.py                    # Run once
    python paper_trader.py --loop             # Run continuously (every 5 min)
    python paper_trader.py --loop --interval 60   # Custom interval (seconds)
"""

import json
import time
import logging
import argparse
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List
import pandas as pd

from lib.data.dex_adapter import dex_adapter

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class Position:
    """Represents an open position"""
    symbol: str
    side: str  # 'long' or 'short'
    entry_price: float
    entry_time: datetime
    size_usd: float
    stop_loss_pct: float = 5.0
    take_profit_pct: float = 10.0

    @property
    def stop_loss_price(self) -> float:
        if self.side == 'long':
            return self.entry_price * (1 - self.stop_loss_pct / 100)
        return self.entry_price * (1 + self.stop_loss_pct / 100)

    @property
    def take_profit_price(self) -> float:
        if self.side == 'long':
            return self.entry_price * (1 + self.take_profit_pct / 100)
        return self.entry_price * (1 - self.take_profit_pct / 100)


@dataclass
class Trade:
    """Represents a completed trade"""
    symbol: str
    side: str
    entry_price: float
    exit_price: float
    entry_time: datetime
    exit_time: datetime
    size_usd: float
    pnl_usd: float
    pnl_pct: float
    exit_reason: str  # 'signal', 'stop_loss', 'take_profit'


@dataclass
class PaperAccount:
    """Simulated trading account"""
    initial_balance: float = 1000.0
    balance: float = 1000.0
    position: Optional[Position] = None
    trades: List[Trade] = field(default_factory=list)
    position_size_pct: float = 10.0  # Use 10% of balance per trade

    @property
    def equity(self) -> float:
        return self.balance

    @property
    def total_pnl(self) -> float:
        return self.balance - self.initial_balance

    @property
    def total_pnl_pct(self) -> float:
        return (self.total_pnl / self.initial_balance) * 100

    @property
    def win_rate(self) -> float:
        if not self.trades:
            return 0.0
        wins = sum(1 for t in self.trades if t.pnl_usd > 0)
        return wins / len(self.trades) * 100

    def summary(self) -> dict:
        return {
            "balance": round(self.balance, 2),
            "initial_balance": self.initial_balance,
            "total_pnl_usd": round(self.total_pnl, 2),
            "total_pnl_pct": round(self.total_pnl_pct, 2),
            "total_trades": len(self.trades),
            "win_rate": round(self.win_rate, 1),
            "has_position": self.position is not None
        }


class PaperTrader:
    """
    Paper trading bot that executes the AI-generated strategy
    """

    def __init__(
        self,
        strategy_path: str = "config/best_strategy_ollama.json",
        initial_balance: float = 1000.0,
        position_size_pct: float = 10.0
    ):
        self.strategy_path = Path(strategy_path)
        self.strategy = self.load_strategy()
        self.account = PaperAccount(
            initial_balance=initial_balance,
            balance=initial_balance,
            position_size_pct=position_size_pct
        )
        self.state_file = Path("data/paper_trader_state.json")
        self.trades_log = Path("logs/paper_trades.jsonl")

        # Ensure directories exist
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.trades_log.parent.mkdir(parents=True, exist_ok=True)

        # Load previous state if exists
        self.load_state()

        logger.info(f"Paper Trader initialized")
        logger.info(f"Strategy: {self.strategy.get('strategy', {}).get('strategy_name', 'Unknown')}")
        logger.info(f"Balance: ${self.account.balance:.2f}")

    def load_strategy(self) -> dict:
        """Load the AI-generated strategy"""
        if not self.strategy_path.exists():
            raise FileNotFoundError(
                f"Strategy not found: {self.strategy_path}\n"
                "Run 'python gepa_optimizer_ollama.py' first to generate a strategy"
            )

        with open(self.strategy_path) as f:
            return json.load(f)

    def load_state(self):
        """Load previous trading state if exists"""
        if self.state_file.exists():
            try:
                with open(self.state_file) as f:
                    state = json.load(f)
                    self.account.balance = state.get('balance', self.account.initial_balance)
                    self.account.trades = []  # Trades are in the log file
                    if state.get('position'):
                        pos = state['position']
                        self.account.position = Position(
                            symbol=pos['symbol'],
                            side=pos['side'],
                            entry_price=pos['entry_price'],
                            entry_time=datetime.fromisoformat(pos['entry_time']),
                            size_usd=pos['size_usd'],
                            stop_loss_pct=pos.get('stop_loss_pct', 5.0),
                            take_profit_pct=pos.get('take_profit_pct', 10.0)
                        )
                    logger.info(f"Loaded previous state. Balance: ${self.account.balance:.2f}")
            except Exception as e:
                logger.warning(f"Could not load state: {e}")

    def save_state(self):
        """Save current trading state"""
        state = {
            'balance': self.account.balance,
            'initial_balance': self.account.initial_balance,
            'position': None,
            'last_update': datetime.now().isoformat()
        }

        if self.account.position:
            state['position'] = {
                'symbol': self.account.position.symbol,
                'side': self.account.position.side,
                'entry_price': self.account.position.entry_price,
                'entry_time': self.account.position.entry_time.isoformat(),
                'size_usd': self.account.position.size_usd,
                'stop_loss_pct': self.account.position.stop_loss_pct,
                'take_profit_pct': self.account.position.take_profit_pct
            }

        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)

    def log_trade(self, trade: Trade):
        """Append trade to log file"""
        with open(self.trades_log, 'a') as f:
            trade_dict = asdict(trade)
            trade_dict['entry_time'] = trade.entry_time.isoformat()
            trade_dict['exit_time'] = trade.exit_time.isoformat()
            f.write(json.dumps(trade_dict) + '\n')

    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate strategy indicators"""
        strategy = self.strategy.get('strategy', {})
        indicators = strategy.get('indicators', [])

        for indicator in indicators:
            ind_type = indicator.get('type', '').upper()
            length = indicator.get('length', 20)
            column = indicator.get('column', f'{ind_type.lower()}_{length}')

            if ind_type == 'SMA':
                df[column] = df['close'].rolling(window=length).mean()
            elif ind_type == 'EMA':
                df[column] = df['close'].ewm(span=length, adjust=False).mean()
            elif ind_type == 'RSI':
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=length).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=length).mean()
                rs = gain / loss
                df[column] = 100 - (100 / (1 + rs))

        # Add previous close for crossover detection
        df['prev_close'] = df['close'].shift(1)

        return df

    def check_signals(self, df: pd.DataFrame) -> Optional[str]:
        """
        Check for entry/exit signals based on strategy rules
        Returns: 'buy', 'sell', or None
        """
        strategy = self.strategy.get('strategy', {})
        entry_rules = strategy.get('entry_rules', [])

        if len(df) < 2:
            return None

        current = df.iloc[-1]
        previous = df.iloc[-2]

        # Check for MA crossover (simplified logic)
        if 'short_ma' in df.columns and 'long_ma' in df.columns:
            # Buy signal: short MA crosses above long MA
            if (previous['short_ma'] <= previous['long_ma'] and
                current['short_ma'] > current['long_ma']):
                return 'buy'

            # Sell signal: short MA crosses below long MA
            if (previous['short_ma'] >= previous['long_ma'] and
                current['short_ma'] < current['long_ma']):
                return 'sell'

        return None

    def check_exit_conditions(self, current_price: float) -> Optional[str]:
        """Check if position should be closed"""
        if not self.account.position:
            return None

        pos = self.account.position

        if pos.side == 'long':
            # Check stop loss
            if current_price <= pos.stop_loss_price:
                return 'stop_loss'
            # Check take profit
            if current_price >= pos.take_profit_price:
                return 'take_profit'
        else:
            # Short position (not implemented in current strategy)
            if current_price >= pos.stop_loss_price:
                return 'stop_loss'
            if current_price <= pos.take_profit_price:
                return 'take_profit'

        return None

    def open_position(self, side: str, price: float, symbol: str):
        """Open a new position"""
        size_usd = self.account.balance * (self.account.position_size_pct / 100)

        self.account.position = Position(
            symbol=symbol,
            side=side,
            entry_price=price,
            entry_time=datetime.now(),
            size_usd=size_usd,
            stop_loss_pct=5.0,
            take_profit_pct=10.0
        )

        logger.info(f"{'='*50}")
        logger.info(f"OPENED {side.upper()} POSITION")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"Entry Price: ${price:,.2f}")
        logger.info(f"Size: ${size_usd:.2f}")
        logger.info(f"Stop Loss: ${self.account.position.stop_loss_price:,.2f}")
        logger.info(f"Take Profit: ${self.account.position.take_profit_price:,.2f}")
        logger.info(f"{'='*50}")

        self.save_state()

    def close_position(self, price: float, reason: str):
        """Close current position"""
        if not self.account.position:
            return

        pos = self.account.position

        # Calculate PnL
        if pos.side == 'long':
            pnl_pct = ((price - pos.entry_price) / pos.entry_price) * 100
        else:
            pnl_pct = ((pos.entry_price - price) / pos.entry_price) * 100

        pnl_usd = pos.size_usd * (pnl_pct / 100)

        # Update balance
        self.account.balance += pnl_usd

        # Create trade record
        trade = Trade(
            symbol=pos.symbol,
            side=pos.side,
            entry_price=pos.entry_price,
            exit_price=price,
            entry_time=pos.entry_time,
            exit_time=datetime.now(),
            size_usd=pos.size_usd,
            pnl_usd=pnl_usd,
            pnl_pct=pnl_pct,
            exit_reason=reason
        )

        self.account.trades.append(trade)
        self.log_trade(trade)

        logger.info(f"{'='*50}")
        logger.info(f"CLOSED POSITION - {reason.upper()}")
        logger.info(f"Exit Price: ${price:,.2f}")
        logger.info(f"PnL: ${pnl_usd:+.2f} ({pnl_pct:+.2f}%)")
        logger.info(f"New Balance: ${self.account.balance:.2f}")
        logger.info(f"{'='*50}")

        self.account.position = None
        self.save_state()

    def run_once(self) -> dict:
        """Run one iteration of the trading loop"""
        symbol = self.strategy.get('symbol', 'BTC/USDC')
        timeframe = self.strategy.get('timeframe', '5m')

        logger.info(f"\n{'='*60}")
        logger.info(f"Paper Trader - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Symbol: {symbol} | Timeframe: {timeframe}")
        logger.info(f"{'='*60}")

        # Fetch latest data
        try:
            df = dex_adapter.get_candles(symbol, timeframe, limit=100)
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            return {"error": str(e)}

        # Calculate indicators
        df = self.calculate_indicators(df)

        current_price = df['close'].iloc[-1]
        logger.info(f"Current Price: ${current_price:,.2f}")

        # Check if we have a position
        if self.account.position:
            logger.info(f"Open Position: {self.account.position.side.upper()} @ ${self.account.position.entry_price:,.2f}")

            # Check exit conditions first
            exit_reason = self.check_exit_conditions(current_price)
            if exit_reason:
                self.close_position(current_price, exit_reason)
            else:
                # Check for signal-based exit
                signal = self.check_signals(df)
                if signal == 'sell' and self.account.position.side == 'long':
                    self.close_position(current_price, 'signal')

        else:
            logger.info("No open position")

            # Check for entry signals
            signal = self.check_signals(df)
            if signal == 'buy':
                self.open_position('long', current_price, symbol)
            elif signal == 'sell':
                # Could implement short selling here
                logger.info("Sell signal detected (shorting not implemented)")

        # Print account summary
        summary = self.account.summary()
        logger.info(f"\nAccount Summary:")
        logger.info(f"  Balance: ${summary['balance']:.2f}")
        logger.info(f"  Total PnL: ${summary['total_pnl_usd']:+.2f} ({summary['total_pnl_pct']:+.2f}%)")
        logger.info(f"  Trades: {summary['total_trades']} (Win Rate: {summary['win_rate']:.1f}%)")

        return summary

    def run_loop(self, interval_seconds: int = 300):
        """Run continuous trading loop"""
        logger.info(f"\nStarting paper trading loop (interval: {interval_seconds}s)")
        logger.info("Press Ctrl+C to stop\n")

        try:
            while True:
                self.run_once()
                logger.info(f"\nSleeping {interval_seconds}s until next check...")
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("\n\nStopping paper trader...")
            logger.info(f"Final Balance: ${self.account.balance:.2f}")
            logger.info(f"Total PnL: ${self.account.total_pnl:+.2f}")
            self.save_state()


def main():
    parser = argparse.ArgumentParser(description="Paper Trading Bot")
    parser.add_argument('--loop', action='store_true', help='Run continuously')
    parser.add_argument('--interval', type=int, default=300, help='Loop interval in seconds (default: 300)')
    parser.add_argument('--balance', type=float, default=1000, help='Initial balance (default: 1000)')
    parser.add_argument('--strategy', type=str, default='config/best_strategy_ollama.json', help='Strategy file path')
    parser.add_argument('--reset', action='store_true', help='Reset account state')
    parser.add_argument('--use-orchestrator', action='store_true',
                        help='Use the new TradingOrchestrator instead of legacy PaperTrader')
    parser.add_argument('--symbol', type=str, default='BTC/USDC', help='Trading symbol (orchestrator mode)')

    args = parser.parse_args()

    # Use new orchestrator if requested
    if args.use_orchestrator:
        import asyncio
        from lib.trading.orchestrator import TradingOrchestrator

        orchestrator = TradingOrchestrator(
            symbol=args.symbol,
            timeframe='5m',
            mode='paper',
        )

        if args.loop:
            asyncio.run(orchestrator.run_trading_loop(interval_seconds=args.interval))
        else:
            result = orchestrator.run_once()
            print(json.dumps(result, indent=2, default=str))
        return

    # Reset state if requested
    if args.reset:
        state_file = Path("data/paper_trader_state.json")
        if state_file.exists():
            state_file.unlink()
            logger.info("Account state reset")

    trader = PaperTrader(
        strategy_path=args.strategy,
        initial_balance=args.balance
    )

    if args.loop:
        trader.run_loop(interval_seconds=args.interval)
    else:
        trader.run_once()


if __name__ == "__main__":
    main()
