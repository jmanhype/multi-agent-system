#!/usr/bin/env bash
set -euo pipefail
pkill -f crypto-trader || true
echo "All trader processes terminated."