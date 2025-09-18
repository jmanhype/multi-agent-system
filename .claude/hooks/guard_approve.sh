#!/usr/bin/env bash
set -euo pipefail
PIN_FILE=".guard_pin"
read -p "Enter live-trade PIN: " pin
if [[ ! -f "$PIN_FILE" ]] || [[ "$pin" != "$(cat $PIN_FILE)" ]]; then
  echo "DENIED" >&2; exit 1
fi
echo "APPROVED"