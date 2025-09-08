#!/usr/bin/env bash
set -euo pipefail

# Pre-trade validation hook
# Runs before each trade execution

echo "🔍 Pre-trade validation started at $(date)"

# Configuration
CONFIG="${1:-config/settings.local.json}"
SYMBOL="${2:-BTC/USDT}"
SIDE="${3:-buy}"
SIZE="${4:-62.50}"

# Check if circuit breaker is active
if [[ -f .circuit_breaker_triggered ]]; then
    echo "❌ Circuit breaker is active - trade rejected"
    exit 1
fi

# Check if database exists
if [[ ! -f "db/metrics.db" ]]; then
    echo "⚠️  Database not found, initializing..."
    python scripts/init_db.py
fi

# Check daily loss limit
DAILY_LOSS=$(python -c "
import sqlite3, json
try:
    conn = sqlite3.connect('db/metrics.db')
    cursor = conn.cursor()
    cursor.execute('SELECT SUM(pnl) FROM trades WHERE date(timestamp) = date(\"now\")')
    result = cursor.fetchone()
    pnl = result[0] if result[0] else 0
    conn.close()
    print(pnl)
except Exception as e:
    print(0)
")

MAX_LOSS=$(jq -r '.risk.max_daily_loss_usd' "$CONFIG" 2>/dev/null || echo "100")

# Check if we have bc available for floating point comparison
if command -v bc >/dev/null 2>&1; then
    LOSS_EXCEEDED=$(echo "$DAILY_LOSS < -$MAX_LOSS" | bc -l 2>/dev/null || echo "0")
else
    # Fallback to Python for comparison
    LOSS_EXCEEDED=$(python -c "print(1 if $DAILY_LOSS < -$MAX_LOSS else 0)")
fi

if [[ "$LOSS_EXCEEDED" == "1" ]]; then
    echo "❌ Daily loss limit exceeded: $DAILY_LOSS (max: -$MAX_LOSS)"
    # Trigger circuit breaker
    echo '{"timestamp":"'$(date -Iseconds)'","reason":"Daily loss limit exceeded","triggered_by":"pre_trade_hook"}' > .circuit_breaker_triggered
    exit 1
fi

# Check consecutive losses
CONSECUTIVE_LOSSES=$(python -c "
import sqlite3
try:
    conn = sqlite3.connect('db/metrics.db')
    cursor = conn.cursor()
    cursor.execute('SELECT pnl FROM trades WHERE pnl != 0 ORDER BY timestamp DESC LIMIT 10')
    trades = cursor.fetchall()
    conn.close()
    
    consecutive = 0
    for (pnl,) in trades:
        if pnl < 0:
            consecutive += 1
        else:
            break
    print(consecutive)
except:
    print(0)
")

MAX_CONSECUTIVE=$(jq -r '.risk.max_consecutive_losses' "$CONFIG" 2>/dev/null || echo "5")

if [[ "$CONSECUTIVE_LOSSES" -ge "$MAX_CONSECUTIVE" ]]; then
    echo "❌ Too many consecutive losses: $CONSECUTIVE_LOSSES (max: $MAX_CONSECUTIVE)"
    echo '{"timestamp":"'$(date -Iseconds)'","reason":"Max consecutive losses exceeded","triggered_by":"pre_trade_hook"}' > .circuit_breaker_triggered
    exit 1
fi

# Check market hours (avoid low liquidity periods)
HOUR=$(date -u +"%H")
if [[ "$HOUR" -ge 3 && "$HOUR" -lt 7 ]]; then
    echo "⚠️  Trading during low liquidity hours (3-7 UTC) - extra caution"
fi

# Validate position size
MAX_SIZE=$(jq -r '.trading.position_size_usd' "$CONFIG" 2>/dev/null || echo "62.50")
if command -v bc >/dev/null 2>&1; then
    SIZE_EXCEEDED=$(echo "$SIZE > $MAX_SIZE * 2" | bc -l 2>/dev/null || echo "0")
else
    SIZE_EXCEEDED=$(python -c "print(1 if $SIZE > $MAX_SIZE * 2 else 0)")
fi

if [[ "$SIZE_EXCEEDED" == "1" ]]; then
    echo "❌ Position size $SIZE exceeds maximum allowed: $(echo "$MAX_SIZE * 2" | bc -l 2>/dev/null || python -c "print($MAX_SIZE * 2)")"
    exit 1
fi

echo "✅ Position size validated: $SIZE USD"

# Log pre-trade check
mkdir -p logs
echo '{"timestamp":"'$(date -Iseconds)'","type":"pre_trade_check","symbol":"'$SYMBOL'","side":"'$SIDE'","size":'$SIZE',"status":"approved"}' >> logs/trade_hooks.jsonl

echo "✅ Pre-trade validation completed successfully"
exit 0