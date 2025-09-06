#!/usr/bin/env bash
set -euo pipefail

# Circuit breaker for emergency trading halt
# Integrates with health monitoring system for comprehensive protection

CONFIG="${1:-config/settings.local.json}"
METRICS_DB="${2:-db/metrics.db}"
LOG_FILE="logs/circuit_breaker.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log_message() {
    echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

# Function to trigger circuit breaker
trigger_circuit_breaker() {
    local reason="$1"
    local value="$2"
    
    log_message "CIRCUIT BREAKER TRIGGERED: $reason - Value: $value"
    
    # Create trigger file with metadata
    cat > .circuit_breaker_triggered << EOF
{
    "timestamp": "$(date -Iseconds)",
    "reason": "$reason",
    "value": "$value",
    "triggered_by": "circuit_breaker.sh"
}
EOF
    
    # Stop trading processes
    log_message "Stopping trading processes..."
    pkill -f "trading.orchestrator" || true
    pkill -f "binanceus_trading" || true
    
    # Send alert via health monitoring system if available
    if [[ -x "scripts/health_check.py" ]]; then
        python3 scripts/health_check.py alerts 2>/dev/null || true
    fi
    
    exit 2
}

log_message "Running circuit breaker checks..."

# Check if metrics database exists
if [[ ! -f "$METRICS_DB" ]]; then
    log_message "WARNING: Metrics database not found at $METRICS_DB"
    # Initialize database if health monitor is available
    if [[ -x "lib/monitoring/health_monitor.py" ]]; then
        python3 -c "from lib.monitoring.health_monitor import MetricsCollector; MetricsCollector()"
        log_message "Initialized metrics database"
    else
        log_message "Skipping database checks - no metrics available"
        exit 0
    fi
fi

# Load configuration with defaults
if [[ -f "$CONFIG" ]]; then
    MAX_LOSS=$(jq -r '.max_daily_loss_usd // 5000' "$CONFIG")
    MAX_DD=$(jq -r '.max_drawdown_percent // 15' "$CONFIG")
    MAX_LATENCY=$(jq -r '.max_api_latency_ms // 2000' "$CONFIG")
    MAX_ERROR_RATE=$(jq -r '.max_error_rate // 0.1' "$CONFIG")
else
    # Default thresholds
    MAX_LOSS=5000
    MAX_DD=15
    MAX_LATENCY=2000
    MAX_ERROR_RATE=0.1
    log_message "WARNING: Config file not found, using default thresholds"
fi

# Check if tables exist and have data
TRADES_EXIST=$(sqlite3 "$METRICS_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='trades';" 2>/dev/null || echo "")
ACCOUNT_EXIST=$(sqlite3 "$METRICS_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='account_state';" 2>/dev/null || echo "")
METRICS_EXIST=$(sqlite3 "$METRICS_DB" "SELECT name FROM sqlite_master WHERE type='table' AND name='metrics';" 2>/dev/null || echo "")

# Check daily loss (if trades table exists)
if [[ -n "$TRADES_EXIST" ]]; then
    DAILY_LOSS=$(sqlite3 "$METRICS_DB" "SELECT COALESCE(SUM(pnl), 0) FROM trades WHERE date(timestamp) = date('now');" 2>/dev/null || echo "0")
    
    if (( $(echo "$DAILY_LOSS < -$MAX_LOSS" | bc -l) )); then
        trigger_circuit_breaker "Daily loss limit exceeded" "$DAILY_LOSS"
    fi
    
    log_message "Daily P&L check: $DAILY_LOSS (limit: -$MAX_LOSS)"
else
    log_message "No trades table found - skipping daily loss check"
fi

# Check drawdown (if account_state table exists)
if [[ -n "$ACCOUNT_EXIST" ]]; then
    DRAWDOWN=$(sqlite3 "$METRICS_DB" "SELECT COALESCE(MAX((peak_balance - current_balance) / peak_balance * 100), 0) FROM account_state;" 2>/dev/null || echo "0")
    
    if (( $(echo "$DRAWDOWN > $MAX_DD" | bc -l) )); then
        trigger_circuit_breaker "Max drawdown exceeded" "${DRAWDOWN}%"
    fi
    
    log_message "Drawdown check: ${DRAWDOWN}% (limit: ${MAX_DD}%)"
else
    log_message "No account_state table found - skipping drawdown check"
fi

# Check recent metrics from health monitoring system
if [[ -n "$METRICS_EXIST" ]]; then
    # Check API latency (last 5 minutes)
    RECENT_LATENCY=$(sqlite3 "$METRICS_DB" "
        SELECT COALESCE(AVG(value), 0) 
        FROM metrics 
        WHERE name = 'api_latency_ms' 
        AND datetime(timestamp) > datetime('now', '-5 minutes');
    " 2>/dev/null || echo "0")
    
    if (( $(echo "$RECENT_LATENCY > $MAX_LATENCY" | bc -l) )); then
        trigger_circuit_breaker "API latency too high" "${RECENT_LATENCY}ms"
    fi
    
    # Check error rate (last 5 minutes)
    RECENT_ERROR_RATE=$(sqlite3 "$METRICS_DB" "
        SELECT COALESCE(AVG(value), 0) 
        FROM metrics 
        WHERE name = 'error_rate' 
        AND datetime(timestamp) > datetime('now', '-5 minutes');
    " 2>/dev/null || echo "0")
    
    if (( $(echo "$RECENT_ERROR_RATE > $MAX_ERROR_RATE" | bc -l) )); then
        trigger_circuit_breaker "Error rate too high" "${RECENT_ERROR_RATE}"
    fi
    
    # Check memory usage
    MEMORY_USAGE=$(sqlite3 "$METRICS_DB" "
        SELECT COALESCE(MAX(value), 0) 
        FROM metrics 
        WHERE name = 'memory_usage_pct' 
        AND datetime(timestamp) > datetime('now', '-2 minutes');
    " 2>/dev/null || echo "0")
    
    if (( $(echo "$MEMORY_USAGE > 95" | bc -l) )); then
        trigger_circuit_breaker "Critical memory usage" "${MEMORY_USAGE}%"
    fi
    
    log_message "Health metrics check: Latency=${RECENT_LATENCY}ms, ErrorRate=${RECENT_ERROR_RATE}, Memory=${MEMORY_USAGE}%"
else
    log_message "No metrics table found - skipping health metrics check"
fi

# Check if system is already in emergency mode
if [[ -f ".circuit_breaker_triggered" ]]; then
    log_message "Circuit breaker already triggered - system in emergency mode"
    exit 2
fi

# Additional system health checks using health monitor if available
if [[ -x "scripts/health_check.py" ]]; then
    # Run health check and parse result
    HEALTH_STATUS=$(python3 scripts/health_check.py status 2>/dev/null | grep "Status:" | cut -d' ' -f2 || echo "UNKNOWN")
    
    if [[ "$HEALTH_STATUS" == "CRITICAL" ]]; then
        trigger_circuit_breaker "System health critical" "$HEALTH_STATUS"
    fi
    
    log_message "System health status: $HEALTH_STATUS"
fi

log_message "All circuit breaker checks passed ✓"
exit 0