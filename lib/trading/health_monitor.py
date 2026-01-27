"""
Health Monitor - System health, anomaly detection, and alerting.

Monitors trading orchestrator metrics, detects anomalies via z-score,
delegates circuit breaker logic to RiskManager, logs alerts to JSONL.
No psutil dependency - uses Python resource module for system metrics.
"""

import json
import logging
import os
import resource
import sqlite3
import time
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any

import numpy as np

from lib.risk.manager import RiskManager

logger = logging.getLogger(__name__)


# ── Data classes ────────────────────────────────────────────────────

@dataclass
class Alert:
    """System alert with severity and routing info."""
    alert_id: str
    timestamp: str
    severity: str  # 'INFO', 'WARNING', 'HIGH', 'CRITICAL'
    category: str  # 'system', 'trading', 'risk', 'anomaly'
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Metrics Collector ───────────────────────────────────────────────

class MetricsCollector:
    """Collect and store trading metrics in SQLite."""

    def __init__(self, db_path: str = "db/metrics.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS health_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                metric_name TEXT NOT NULL,
                metric_value REAL NOT NULL,
                metadata TEXT
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_ts
            ON health_metrics(timestamp)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_health_name
            ON health_metrics(metric_name)
        """)
        conn.commit()
        conn.close()

    def record(self, name: str, value: float, metadata: Optional[Dict] = None):
        """Record a single metric."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute(
            "INSERT INTO health_metrics (timestamp, metric_name, metric_value, metadata) VALUES (?, ?, ?, ?)",
            (
                datetime.now(timezone.utc).isoformat(),
                name,
                value,
                json.dumps(metadata) if metadata else None,
            ),
        )
        conn.commit()
        conn.close()

    def get_recent(self, name: str, minutes: int = 60) -> List[float]:
        """Get recent metric values within a time window."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT metric_value FROM health_metrics WHERE metric_name = ? AND timestamp >= ? ORDER BY timestamp",
            (name, cutoff),
        )
        values = [row[0] for row in cursor.fetchall()]
        conn.close()
        return values

    def get_latest(self, name: str) -> Optional[float]:
        """Get most recent value for a metric."""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.execute(
            "SELECT metric_value FROM health_metrics WHERE metric_name = ? ORDER BY timestamp DESC LIMIT 1",
            (name,),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_summary(self, name: str, minutes: int = 60) -> Dict[str, float]:
        """Get summary stats for a metric over a time window."""
        values = self.get_recent(name, minutes)
        if not values:
            return {"count": 0}
        arr = np.array(values)
        return {
            "count": len(arr),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "latest": float(arr[-1]),
        }

    def cleanup_old(self, days: int = 30):
        """Remove metrics older than N days."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("DELETE FROM health_metrics WHERE timestamp < ?", (cutoff,))
        conn.commit()
        conn.close()


# ── Circuit Breaker Monitor ─────────────────────────────────────────

class CircuitBreakerMonitor:
    """Delegates circuit breaker checks to RiskManager."""

    def __init__(self, risk_manager: RiskManager):
        self.risk_manager = risk_manager

    def check(self, metrics: Optional[Dict] = None) -> Dict[str, Any]:
        """Check circuit breaker status via RiskManager."""
        return self.risk_manager.check_circuit_breaker_conditions(metrics)

    def is_active(self) -> bool:
        """Check if circuit breaker file exists."""
        return os.path.exists(".circuit_breaker_triggered")

    def get_state(self) -> Optional[Dict]:
        """Read circuit breaker state from file."""
        if not self.is_active():
            return None
        try:
            with open(".circuit_breaker_triggered") as f:
                return json.load(f)
        except Exception:
            return {"active": True, "error": "could not read state"}


# ── Alert Manager ───────────────────────────────────────────────────

class AlertManager:
    """Route and log alerts by severity."""

    SEVERITY_ORDER = {"INFO": 0, "WARNING": 1, "HIGH": 2, "CRITICAL": 3}

    def __init__(
        self,
        log_path: str = "logs/alerts.jsonl",
        min_severity: str = "WARNING",
    ):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.min_severity = min_severity
        self.alert_history: List[Alert] = []
        self._alert_counter = 0

    def send(
        self,
        severity: str,
        category: str,
        message: str,
        details: Optional[Dict] = None,
    ) -> Optional[Alert]:
        """Create and route an alert if above minimum severity."""
        if self.SEVERITY_ORDER.get(severity, 0) < self.SEVERITY_ORDER.get(self.min_severity, 0):
            return None

        self._alert_counter += 1
        alert = Alert(
            alert_id=f"alert_{self._alert_counter}_{int(time.time())}",
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity=severity,
            category=category,
            message=message,
            details=details or {},
        )

        # Log to JSONL
        with open(self.log_path, "a") as f:
            f.write(json.dumps(alert.to_dict()) + "\n")

        # In-memory history (keep last 100)
        self.alert_history.append(alert)
        if len(self.alert_history) > 100:
            self.alert_history = self.alert_history[-100:]

        # Route by severity
        if severity == "CRITICAL":
            logger.critical(f"ALERT [{category}]: {message}")
        elif severity == "HIGH":
            logger.error(f"ALERT [{category}]: {message}")
        elif severity == "WARNING":
            logger.warning(f"ALERT [{category}]: {message}")
        else:
            logger.info(f"ALERT [{category}]: {message}")

        return alert

    def get_recent(self, minutes: int = 60, severity: Optional[str] = None) -> List[Alert]:
        """Get recent alerts, optionally filtered by severity."""
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()
        result = [a for a in self.alert_history if a.timestamp >= cutoff]
        if severity:
            result = [a for a in result if a.severity == severity]
        return result


# ── Health Monitor ──────────────────────────────────────────────────

class HealthMonitor:
    """
    Orchestrates all health monitoring:
    - System resource metrics (via resource module, no psutil)
    - Trading performance metrics from orchestrator results
    - Z-score anomaly detection on metrics
    - Circuit breaker delegation to RiskManager
    - Alert routing
    """

    def __init__(
        self,
        risk_manager: Optional[RiskManager] = None,
        risk_config: Optional[Dict] = None,
        db_path: str = "db/metrics.db",
        alert_log: str = "logs/alerts.jsonl",
        z_score_threshold: float = 3.0,
    ):
        if risk_manager is None:
            if risk_config is None:
                risk_config = self._default_risk_config()
            risk_manager = RiskManager(risk_config)

        self.metrics = MetricsCollector(db_path)
        self.circuit_breaker = CircuitBreakerMonitor(risk_manager)
        self.alerts = AlertManager(log_path=alert_log)
        self.risk_manager = risk_manager
        self.z_score_threshold = z_score_threshold

        # Tracking
        self._iteration_results: List[Dict] = []

    @staticmethod
    def _default_risk_config() -> Dict:
        risk_path = Path("config/risk.json")
        if risk_path.exists():
            with open(risk_path) as f:
                cfg = json.load(f)
            return {
                "max_position_size": cfg.get("max_position_size", 62.50),
                "max_daily_loss": cfg.get("max_daily_loss_usd", 100),
                "max_drawdown": cfg.get("max_drawdown_percent", 5.0) / 100,
                "max_consecutive_losses": cfg.get("max_consecutive_losses", 3),
                "symbol_whitelist": cfg.get("symbol_whitelist", ["BTC/USDC"]),
            }
        return {"max_position_size": 62.50, "max_daily_loss": 100}

    # ── System metrics ──────────────────────────────────────────────

    def collect_system_metrics(self) -> Dict[str, float]:
        """Collect system metrics using Python resource module."""
        usage = resource.getrusage(resource.RUSAGE_SELF)
        metrics = {
            "memory_max_rss_mb": usage.ru_maxrss / (1024 * 1024) if os.name != "nt" else usage.ru_maxrss / 1024,
            "user_cpu_seconds": usage.ru_utime,
            "system_cpu_seconds": usage.ru_stime,
            "voluntary_context_switches": float(usage.ru_nvcsw),
            "involuntary_context_switches": float(usage.ru_nivcsw),
        }

        for name, value in metrics.items():
            self.metrics.record(f"system.{name}", value)

        return metrics

    # ── Trading metrics ─────────────────────────────────────────────

    def record_iteration(self, result: Dict[str, Any]):
        """Record a trading iteration result from orchestrator.

        Args:
            result: Dict returned by TradingOrchestrator.run_once()
        """
        self._iteration_results.append(result)
        if len(self._iteration_results) > 500:
            self._iteration_results = self._iteration_results[-500:]

        # Record key metrics
        if "elapsed_ms" in result:
            self.metrics.record("trading.latency_ms", result["elapsed_ms"])
        if "price" in result:
            self.metrics.record("trading.price", result["price"])
        if result.get("pnl_usd") is not None:
            self.metrics.record("trading.pnl_usd", result["pnl_usd"])
        if result.get("confidence") is not None:
            self.metrics.record("trading.signal_confidence", result["confidence"])

        status = result.get("status", "unknown")
        self.metrics.record("trading.status_ok", 1.0 if status == "ok" else 0.0)

        # Check for issues
        if status == "error":
            self.alerts.send("HIGH", "trading", f"Iteration error: {result.get('error', 'unknown')}", result)

        # Check latency
        latency = result.get("elapsed_ms", 0)
        if latency > 5000:
            self.alerts.send("WARNING", "trading", f"High latency: {latency}ms", {"latency_ms": latency})

    # ── Anomaly detection ───────────────────────────────────────────

    def detect_anomalies(self, metric_name: str = "trading.latency_ms", window_minutes: int = 60) -> Optional[Alert]:
        """Z-score anomaly detection on a metric.

        Returns Alert if anomaly detected, None otherwise.
        """
        values = self.metrics.get_recent(metric_name, window_minutes)
        if len(values) < 10:
            return None

        arr = np.array(values)
        mean = np.mean(arr)
        std = np.std(arr)

        if std < 1e-9:
            return None

        latest = arr[-1]
        z = abs(latest - mean) / std

        if z >= self.z_score_threshold:
            alert = self.alerts.send(
                "HIGH",
                "anomaly",
                f"Anomaly in {metric_name}: z-score={z:.2f} (value={latest:.2f}, mean={mean:.2f})",
                {"metric": metric_name, "z_score": z, "value": latest, "mean": mean, "std": std},
            )
            return alert
        return None

    # ── Health check ────────────────────────────────────────────────

    def check_health(self) -> Dict[str, Any]:
        """Run all health checks and return report.

        Returns:
            Dict with system, trading, circuit breaker, and alert status.
        """
        report: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": "healthy",
            "checks": {},
        }

        # 1. System metrics
        try:
            sys_metrics = self.collect_system_metrics()
            report["checks"]["system"] = {
                "status": "ok",
                "metrics": sys_metrics,
            }
        except Exception as e:
            report["checks"]["system"] = {"status": "error", "error": str(e)}

        # 2. Circuit breaker
        cb_active = self.circuit_breaker.is_active()
        cb_state = self.circuit_breaker.get_state()
        report["checks"]["circuit_breaker"] = {
            "active": cb_active,
            "state": cb_state,
        }
        if cb_active:
            report["overall_status"] = "degraded"

        # 3. Trading metrics
        latency_summary = self.metrics.get_summary("trading.latency_ms", 60)
        status_ok_summary = self.metrics.get_summary("trading.status_ok", 60)
        error_rate = 0.0
        if status_ok_summary.get("count", 0) > 0:
            error_rate = 1.0 - status_ok_summary.get("mean", 1.0)

        report["checks"]["trading"] = {
            "latency": latency_summary,
            "error_rate": error_rate,
            "total_iterations": len(self._iteration_results),
        }

        if error_rate > 0.1:
            report["overall_status"] = "degraded"
            self.alerts.send("HIGH", "trading", f"High error rate: {error_rate:.1%}")

        # 4. Risk status
        try:
            risk_status = self.risk_manager.get_risk_status()
            report["checks"]["risk"] = risk_status
        except Exception as e:
            report["checks"]["risk"] = {"status": "error", "error": str(e)}

        # 5. Anomaly detection
        anomaly_metrics = ["trading.latency_ms", "trading.price"]
        anomalies = []
        for m in anomaly_metrics:
            alert = self.detect_anomalies(m)
            if alert:
                anomalies.append(alert.to_dict())
        if anomalies:
            report["checks"]["anomalies"] = anomalies
            report["overall_status"] = "warning"

        # 6. Recent alerts
        recent_alerts = self.alerts.get_recent(minutes=60)
        critical_alerts = [a for a in recent_alerts if a.severity in ("CRITICAL", "HIGH")]
        report["checks"]["alerts"] = {
            "recent_count": len(recent_alerts),
            "critical_count": len(critical_alerts),
        }
        if critical_alerts:
            report["overall_status"] = "degraded"

        return report

    def generate_report(self) -> str:
        """Generate a human-readable health report."""
        health = self.check_health()
        lines = [
            f"=== Health Report ({health['timestamp']}) ===",
            f"Overall Status: {health['overall_status'].upper()}",
            "",
        ]

        # System
        sys_check = health["checks"].get("system", {})
        if sys_check.get("status") == "ok":
            m = sys_check.get("metrics", {})
            lines.append(f"System: RSS={m.get('memory_max_rss_mb', 0):.1f}MB CPU={m.get('user_cpu_seconds', 0):.1f}s")
        else:
            lines.append(f"System: ERROR - {sys_check.get('error', 'unknown')}")

        # Circuit breaker
        cb = health["checks"].get("circuit_breaker", {})
        lines.append(f"Circuit Breaker: {'ACTIVE' if cb.get('active') else 'OK'}")

        # Trading
        t = health["checks"].get("trading", {})
        lat = t.get("latency", {})
        lines.append(
            f"Trading: {t.get('total_iterations', 0)} iterations, "
            f"latency={lat.get('mean', 0):.0f}ms avg, "
            f"error_rate={t.get('error_rate', 0):.1%}"
        )

        # Risk
        risk = health["checks"].get("risk", {})
        lines.append(
            f"Risk: balance=${risk.get('current_balance', 0):.2f} "
            f"daily_pnl=${risk.get('daily_pnl', 0):.2f} "
            f"risk_score={risk.get('risk_score', 0):.1f}"
        )

        # Alerts
        a = health["checks"].get("alerts", {})
        lines.append(f"Alerts: {a.get('recent_count', 0)} recent, {a.get('critical_count', 0)} critical")

        return "\n".join(lines)
