#!/bin/bash
# Post-execution audit logging for DataAgent operations
# Appends Merkle-chained audit entries to append-only log

set -euo pipefail

# Audit log location
AUDIT_LOG=".taskmaster/logs/data_agent_audit.jsonl"
mkdir -p "$(dirname "$AUDIT_LOG")"
touch "$AUDIT_LOG"

# Extract execution context
REQUEST_ID="${1:-unknown}"
STATUS="${2:-unknown}"
EXECUTION_TIME="${3:-0}"

# Get previous Merkle hash (or genesis)
if [ -s "$AUDIT_LOG" ]; then
  PREV_HASH=$(tail -1 "$AUDIT_LOG" | jq -r '.merkle_hash // "genesis"')
else
  PREV_HASH="genesis"
fi

# Generate current entry payload
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
PAYLOAD=$(jq -n \
  --arg ts "$TIMESTAMP" \
  --arg req_id "$REQUEST_ID" \
  --arg status "$STATUS" \
  --arg exec_time "$EXECUTION_TIME" \
  --arg prev_hash "$PREV_HASH" \
  '{
    timestamp: $ts,
    request_id: $req_id,
    status: $status,
    execution_time_ms: ($exec_time | tonumber),
    prev_merkle_hash: $prev_hash
  }')

# Compute Merkle hash (SHA256 of payload + prev_hash)
CURRENT_HASH=$(echo "$PAYLOAD" | sha256sum | awk '{print $1}')

# Append entry with Merkle hash
AUDIT_ENTRY=$(echo "$PAYLOAD" | jq --arg hash "$CURRENT_HASH" '. + {merkle_hash: $hash}')
echo "$AUDIT_ENTRY" >> "$AUDIT_LOG"

echo "AUDIT: Entry logged with Merkle hash $CURRENT_HASH"
exit 0