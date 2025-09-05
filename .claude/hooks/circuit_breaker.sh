#!/usr/bin/env bash
set -euo pipefail
# Flip mode to paper in settings.local.json
jq '.mode = "paper"' config/settings.local.json > config/settings.local.json.tmp && mv config/settings.local.json.tmp config/settings.local.json
echo "Circuit breaker engaged: mode=paper"