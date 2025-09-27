#!/bin/bash
# Pre-execution safety validation for DataAgent SQL operations
# Blocks DDL/DML and validates query safety before execution

set -euo pipefail

# Extract SQL query from tool arguments
QUERY="${1:-}"

if [ -z "$QUERY" ]; then
  echo "ERROR: No SQL query provided for validation"
  exit 1
fi

# Convert to uppercase for case-insensitive matching
QUERY_UPPER=$(echo "$QUERY" | tr '[:lower:]' '[:upper:]')

# Block DDL operations
DDL_KEYWORDS=("CREATE" "DROP" "ALTER" "TRUNCATE")
for keyword in "${DDL_KEYWORDS[@]}"; do
  if echo "$QUERY_UPPER" | grep -qw "$keyword"; then
    echo "BLOCKED: DDL operation detected ($keyword)"
    echo "Policy: DataAgent permits SELECT queries only"
    exit 1
  fi
done

# Block DML operations
DML_KEYWORDS=("INSERT" "UPDATE" "DELETE" "MERGE")
for keyword in "${DML_KEYWORDS[@]}"; do
  if echo "$QUERY_UPPER" | grep -qw "$keyword"; then
    echo "BLOCKED: DML operation detected ($keyword)"
    echo "Policy: DataAgent permits SELECT queries only"
    exit 1
  fi
done

# Block system table access
SYSTEM_PATTERNS=("PG_" "INFORMATION_SCHEMA" "MYSQL." "SYS.")
for pattern in "${SYSTEM_PATTERNS[@]}"; do
  if echo "$QUERY_UPPER" | grep -q "$pattern"; then
    echo "BLOCKED: System table access detected ($pattern)"
    echo "Policy: System metadata tables are restricted"
    exit 1
  fi
done

# Validate parameterized queries (enhanced injection detection)
if echo "$QUERY" | grep -Eq "'\s*;\s*.*(--|#|/\*)?"; then
  echo "WARNING: Potential SQL injection risk detected"
  echo "Policy: Use parameterized queries only"
  exit 1
fi

# Log validation success
echo "VALIDATED: SQL query passed safety checks"
exit 0