#!/usr/bin/env bash
set -euo pipefail

# Post-trade journaling hook
TRADE_JSON="${1}"
JOURNAL="logs/trades.jsonl"
METRICS_DB="db/metrics.db"

echo "Post-trade processing..."

# Append to journal
echo "$TRADE_JSON" >> "$JOURNAL"

# Extract fields
TIMESTAMP=$(echo "$TRADE_JSON" | jq -r '.timestamp')
SYMBOL=$(echo "$TRADE_JSON" | jq -r '.symbol')
SIDE=$(echo "$TRADE_JSON" | jq -r '.side')
PRICE=$(echo "$TRADE_JSON" | jq -r '.price')
AMOUNT=$(echo "$TRADE_JSON" | jq -r '.amount')
PNL=$(echo "$TRADE_JSON" | jq -r '.pnl // 0')

# Update database
sqlite3 "$METRICS_DB" << EOF
INSERT INTO trades (timestamp, symbol, side, price, amount, pnl)
VALUES ('$TIMESTAMP', '$SYMBOL', '$SIDE', $PRICE, $AMOUNT, $PNL);
EOF

# Check circuit breaker conditions
./.claude/hooks/circuit_breaker.sh || true

echo "✅ Trade journaled: $SYMBOL $SIDE @ $PRICE"
exit 0