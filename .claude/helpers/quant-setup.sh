#!/usr/bin/env bash
set -euo pipefail

# Quant system setup helper
echo "🚀 Setting up Quant LLM Research+Execution System"

# Create directory structure
echo "Creating directories..."
mkdir -p data/{historical,models,strategies}
mkdir -p artifacts
mkdir -p logs
mkdir -p db
mkdir -p .claude/secrets

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

# Setup environment
if [ ! -f .env ]; then
    echo "Creating .env from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env with your API keys"
fi

# Setup PIN
if [ ! -f .claude/secrets/pin.hash ]; then
    echo "Setting up trading PIN..."
    read -sp "Enter your trading PIN: " pin
    echo
    echo -n "$pin" | sha256sum | cut -d' ' -f1 > .claude/secrets/pin.hash
    echo "✅ PIN configured"
fi

# Load pretrained model if available
if [ -f data/models/big_optimize_1016.pkl ]; then
    echo "Loading pretrained strategies..."
    python scripts/load_pretrained.py
fi

# Initialize database
echo "Initializing metrics database..."
sqlite3 db/metrics.db << EOF
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    timestamp DATETIME,
    symbol TEXT,
    side TEXT,
    price REAL,
    amount REAL,
    pnl REAL
);

CREATE TABLE IF NOT EXISTS account_state (
    timestamp DATETIME PRIMARY KEY,
    current_balance REAL,
    peak_balance REAL,
    daily_pnl REAL,
    total_pnl REAL
);
EOF

# Set permissions
chmod +x .claude/hooks/*.sh
chmod +x scripts/*.py

echo "✅ Quant system setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API keys"
echo "2. Run research: python -m lib.research.orchestrate"
echo "3. Start paper trading: python -m lib.trading.orchestrator --mode paper"