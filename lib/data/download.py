"""
Data Downloader - Paginated historical data fetch with parquet caching.

Uses DexAdapter for Binance public endpoints (no API key needed).
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from lib.data.dex_adapter import DexAdapter

logger = logging.getLogger(__name__)

# Timeframe to milliseconds mapping
_TF_MS = {
    "1m": 60_000,
    "5m": 300_000,
    "15m": 900_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}


class DataDownloader:
    """Download and cache historical OHLCV data via DexAdapter."""

    def __init__(
        self,
        adapter: Optional[DexAdapter] = None,
        cache_dir: str = "data/cache",
    ):
        self.adapter = adapter or DexAdapter(sandbox=False)
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def download(
        self,
        symbol: str = "BTC/USDC",
        timeframe: str = "5m",
        days: int = 30,
    ) -> pd.DataFrame:
        """Download historical candles with pagination (max 1000 per request).

        Args:
            symbol: Trading pair
            timeframe: Candle interval
            days: Number of days of history

        Returns:
            DataFrame with columns [timestamp, open, high, low, close, volume]
        """
        tf_ms = _TF_MS.get(timeframe, 300_000)
        candles_needed = int(days * 86_400_000 / tf_ms)
        since = datetime.utcnow() - timedelta(days=days)

        frames: List[pd.DataFrame] = []
        fetched = 0
        current_since = since

        while fetched < candles_needed:
            batch_limit = min(1000, candles_needed - fetched)
            logger.info(
                f"Fetching {symbol} {timeframe} batch: {fetched}/{candles_needed} "
                f"since {current_since.isoformat()}"
            )

            df_batch = self.adapter.get_candles(
                symbol=symbol,
                timeframe=timeframe,
                limit=batch_limit,
                since=current_since,
            )

            if df_batch.empty:
                logger.warning("Empty batch returned, stopping pagination")
                break

            frames.append(df_batch)
            fetched += len(df_batch)

            # Advance the cursor past the last candle
            last_ts = df_batch["timestamp"].iloc[-1]
            if isinstance(last_ts, pd.Timestamp):
                current_since = last_ts.to_pydatetime() + timedelta(milliseconds=tf_ms)
            else:
                current_since = last_ts + timedelta(milliseconds=tf_ms)

            # Stop if we got fewer candles than requested (end of available data)
            if len(df_batch) < batch_limit:
                break

        if not frames:
            logger.warning(f"No data fetched for {symbol} {timeframe}")
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        result = pd.concat(frames, ignore_index=True)
        result = result.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
        logger.info(f"Downloaded {len(result)} candles for {symbol} {timeframe}")
        return result

    def _cache_path(self, symbol: str, timeframe: str) -> Path:
        """Generate cache file path."""
        safe_name = symbol.replace("/", "_")
        return self.cache_dir / f"{safe_name}_{timeframe}.parquet"

    def download_with_cache(
        self,
        symbol: str = "BTC/USDC",
        timeframe: str = "5m",
        days: int = 30,
    ) -> pd.DataFrame:
        """Download with parquet cache; only fetches new data since last cache.

        Returns:
            Complete DataFrame from cache + new data.
        """
        cache_file = self._cache_path(symbol, timeframe)
        cached_df = pd.DataFrame()

        if cache_file.exists():
            try:
                cached_df = pd.read_parquet(cache_file)
                logger.info(f"Loaded {len(cached_df)} cached candles for {symbol}")
            except Exception as e:
                logger.warning(f"Cache read failed: {e}, re-downloading")
                cached_df = pd.DataFrame()

        if not cached_df.empty:
            # Only fetch data newer than cache
            last_ts = cached_df["timestamp"].max()
            if isinstance(last_ts, pd.Timestamp):
                last_dt = last_ts.to_pydatetime()
            else:
                last_dt = last_ts

            target_start = datetime.utcnow() - timedelta(days=days)
            if last_dt > target_start:
                # Cache covers requested range partly; fetch only the gap
                gap_hours = (datetime.utcnow() - last_dt).total_seconds() / 3600
                gap_days = max(1, gap_hours / 24)
                new_df = self.download(symbol, timeframe, days=gap_days)

                if not new_df.empty:
                    combined = pd.concat([cached_df, new_df], ignore_index=True)
                    combined = combined.drop_duplicates(subset=["timestamp"]).sort_values("timestamp").reset_index(drop=True)
                else:
                    combined = cached_df
            else:
                # Cache is too old, re-download everything
                combined = self.download(symbol, timeframe, days)
        else:
            combined = self.download(symbol, timeframe, days)

        # Save to cache
        if not combined.empty:
            combined.to_parquet(cache_file, index=False)
            logger.info(f"Cached {len(combined)} candles to {cache_file}")

        return combined

    def download_all(
        self,
        symbols: Optional[List[str]] = None,
        timeframe: str = "5m",
        days: int = 30,
    ) -> Dict[str, pd.DataFrame]:
        """Batch download for all whitelisted symbols.

        Args:
            symbols: List of symbols, defaults to risk.json whitelist.
            timeframe: Candle interval.
            days: Days of history.

        Returns:
            Dict mapping symbol -> DataFrame
        """
        if symbols is None:
            symbols = self._load_whitelist()

        results: Dict[str, pd.DataFrame] = {}
        for sym in symbols:
            try:
                results[sym] = self.download_with_cache(sym, timeframe, days)
            except Exception as e:
                logger.error(f"Failed to download {sym}: {e}")

        logger.info(f"Downloaded data for {len(results)}/{len(symbols)} symbols")
        return results

    @staticmethod
    def _load_whitelist() -> List[str]:
        """Load symbol whitelist from config/risk.json."""
        risk_path = Path("config/risk.json")
        if risk_path.exists():
            with open(risk_path) as f:
                cfg = json.load(f)
            return cfg.get("symbol_whitelist", ["BTC/USDC", "ETH/USDC"])
        return ["BTC/USDC", "ETH/USDC"]
