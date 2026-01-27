#!/usr/bin/env python
"""
Unified CLI entry point for the trading system.

Commands:
    trade    - Run paper/live trading loop
    research - Run strategy evolution pipeline
    health   - Show system health status
    verify   - Run audit log verification
    download - Download historical market data
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path


def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


# ── Trade command ───────────────────────────────────────────────────

def cmd_trade(args):
    """Run the trading orchestrator loop."""
    from lib.trading.orchestrator import TradingOrchestrator
    from lib.trading.health_monitor import HealthMonitor

    orchestrator = TradingOrchestrator(
        symbol=args.symbol,
        timeframe=args.timeframe,
        mode=args.mode,
    )

    if args.once:
        result = orchestrator.run_once()
        print(json.dumps(result, indent=2, default=str))
        return

    # Continuous loop with health monitoring
    monitor = HealthMonitor(risk_manager=orchestrator.risk_manager)

    async def _loop():
        orchestrator.running = True
        iteration = 0
        try:
            while orchestrator.running:
                result = orchestrator.run_once()
                monitor.record_iteration(result)

                iteration += 1
                if args.max_iterations and iteration >= args.max_iterations:
                    break

                await asyncio.sleep(args.interval)
        except KeyboardInterrupt:
            pass
        finally:
            orchestrator.stop()
            print("\n" + monitor.generate_report())

    asyncio.run(_loop())


# ── Research command ────────────────────────────────────────────────

def cmd_research(args):
    """Run the strategy research/evolution pipeline."""
    from lib.data.download import DataDownloader
    from lib.research.orchestrator import ResearchOrchestrator

    downloader = DataDownloader()
    print(f"Downloading {args.symbol} {args.timeframe} data ({args.days} days)...")
    data = downloader.download_with_cache(args.symbol, args.timeframe, args.days)

    if data.empty or len(data) < 100:
        print(f"Insufficient data: {len(data)} candles (need >= 100)")
        sys.exit(1)

    print(f"Data: {len(data)} candles from {data['timestamp'].min()} to {data['timestamp'].max()}")

    orchestrator = ResearchOrchestrator()
    winner = orchestrator.run_pipeline(
        data=data,
        generations=args.generations,
        population_size=args.population,
        test_split=args.test_split,
    )

    if winner:
        print(f"\nWinner: {winner.candidate_id}")
        print(f"Fitness: {winner.fitness:.4f}")
        print(f"Params: {json.dumps(winner.params, indent=2)}")
        print(f"Metrics: {json.dumps(winner.metrics, indent=2, default=str)}")
        print("Saved to: artifacts/winner.json")
    else:
        print("\nNo candidate met all benchmark requirements.")


# ── Health command ──────────────────────────────────────────────────

def cmd_health(args):
    """Show system health status."""
    from lib.trading.health_monitor import HealthMonitor

    monitor = HealthMonitor()
    if args.json:
        report = monitor.check_health()
        print(json.dumps(report, indent=2, default=str))
    else:
        print(monitor.generate_report())


# ── Verify command ──────────────────────────────────────────────────

def cmd_verify(args):
    """Run audit verification on all log files."""
    from lib.audit.verify import AuditVerifier

    verifier = AuditVerifier()
    results = verifier.verify_all()

    if args.json:
        print(json.dumps(results, indent=2))
        return

    print(f"Audit Verification Report ({results['timestamp']})")
    print(f"Overall: {'PASS' if results['overall_valid'] else 'FAIL'}")
    print(f"Files checked: {results['files_checked']}")
    print()

    for name, r in results["results"].items():
        status = "PASS" if r["is_valid"] else "FAIL"
        print(f"  {name:25s} {status:4s}  entries={r['total_entries']}  invalid={r['invalid_entries']}")
        for err in r.get("errors", [])[:3]:
            print(f"    -> {err}")

    sys.exit(0 if results["overall_valid"] else 1)


# ── Download command ────────────────────────────────────────────────

def cmd_download(args):
    """Download historical market data."""
    from lib.data.download import DataDownloader

    downloader = DataDownloader()

    if args.all:
        results = downloader.download_all(timeframe=args.timeframe, days=args.days)
        for sym, df in results.items():
            print(f"  {sym}: {len(df)} candles")
    else:
        df = downloader.download_with_cache(args.symbol, args.timeframe, args.days)
        print(f"{args.symbol}: {len(df)} candles")
        if not df.empty:
            print(f"  From: {df['timestamp'].min()}")
            print(f"  To:   {df['timestamp'].max()}")
            print(f"  Cache: data/cache/{args.symbol.replace('/', '_')}_{args.timeframe}.parquet")


# ── Main parser ─────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Trading System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug logging")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # trade
    p_trade = subparsers.add_parser("trade", help="Run trading loop")
    p_trade.add_argument("--mode", choices=["paper", "live"], default="paper")
    p_trade.add_argument("--symbol", default="BTC/USDC")
    p_trade.add_argument("--timeframe", default="5m")
    p_trade.add_argument("--interval", type=int, default=300, help="Loop interval seconds")
    p_trade.add_argument("--once", action="store_true", help="Run one iteration and exit")
    p_trade.add_argument("--max-iterations", type=int, default=None)
    p_trade.set_defaults(func=cmd_trade)

    # research
    p_research = subparsers.add_parser("research", help="Run strategy evolution")
    p_research.add_argument("--symbol", default="BTC/USDC")
    p_research.add_argument("--timeframe", default="5m")
    p_research.add_argument("--days", type=int, default=30)
    p_research.add_argument("--generations", type=int, default=10)
    p_research.add_argument("--population", type=int, default=20)
    p_research.add_argument("--test-split", type=float, default=0.3)
    p_research.set_defaults(func=cmd_research)

    # health
    p_health = subparsers.add_parser("health", help="Show health status")
    p_health.add_argument("--json", action="store_true", help="Output as JSON")
    p_health.set_defaults(func=cmd_health)

    # verify
    p_verify = subparsers.add_parser("verify", help="Audit log verification")
    p_verify.add_argument("--json", action="store_true", help="Output as JSON")
    p_verify.set_defaults(func=cmd_verify)

    # download
    p_download = subparsers.add_parser("download", help="Download market data")
    p_download.add_argument("--symbol", default="BTC/USDC")
    p_download.add_argument("--timeframe", default="5m")
    p_download.add_argument("--days", type=int, default=7)
    p_download.add_argument("--all", action="store_true", help="Download all whitelisted symbols")
    p_download.set_defaults(func=cmd_download)

    args = parser.parse_args()
    setup_logging(args.verbose)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
