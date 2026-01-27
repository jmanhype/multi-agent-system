"""
Unit tests for HealthMonitor and supporting classes.
"""

import json
import os
import pytest
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

from lib.trading.health_monitor import (
    Alert,
    MetricsCollector,
    CircuitBreakerMonitor,
    AlertManager,
    HealthMonitor,
)
from lib.risk.manager import RiskManager


# ── Fixtures ────────────────────────────────────────────────────────

@pytest.fixture
def risk_config():
    return {
        "max_position_size": 62.50,
        "max_daily_loss": 100,
        "max_drawdown": 0.05,
        "max_consecutive_losses": 3,
        "symbol_whitelist": ["BTC/USDC", "ETH/USDC"],
    }


@pytest.fixture
def risk_manager(risk_config):
    return RiskManager(risk_config)


@pytest.fixture
def metrics_db(tmp_path):
    return MetricsCollector(db_path=str(tmp_path / "test_metrics.db"))


@pytest.fixture
def alert_manager(tmp_path):
    return AlertManager(log_path=str(tmp_path / "test_alerts.jsonl"))


@pytest.fixture
def health_monitor(tmp_path, risk_manager):
    return HealthMonitor(
        risk_manager=risk_manager,
        db_path=str(tmp_path / "test_metrics.db"),
        alert_log=str(tmp_path / "test_alerts.jsonl"),
    )


# ── Alert tests ─────────────────────────────────────────────────────

class TestAlert:
    def test_alert_creation(self):
        alert = Alert(
            alert_id="test_1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            severity="WARNING",
            category="trading",
            message="Test alert",
        )
        assert alert.severity == "WARNING"
        assert alert.acknowledged is False

    def test_alert_to_dict(self):
        alert = Alert(
            alert_id="test_1",
            timestamp="2024-01-01T00:00:00",
            severity="HIGH",
            category="system",
            message="High CPU",
            details={"cpu_pct": 95},
        )
        d = alert.to_dict()
        assert d["alert_id"] == "test_1"
        assert d["details"]["cpu_pct"] == 95


# ── MetricsCollector tests ──────────────────────────────────────────

class TestMetricsCollector:
    def test_record_and_get_latest(self, metrics_db):
        metrics_db.record("test_metric", 42.0)
        latest = metrics_db.get_latest("test_metric")
        assert latest == 42.0

    def test_record_multiple(self, metrics_db):
        for i in range(5):
            metrics_db.record("counter", float(i))
        values = metrics_db.get_recent("counter", minutes=60)
        assert len(values) == 5
        assert values[-1] == 4.0

    def test_get_summary(self, metrics_db):
        for v in [10.0, 20.0, 30.0, 40.0, 50.0]:
            metrics_db.record("latency", v)
        summary = metrics_db.get_summary("latency", minutes=60)
        assert summary["count"] == 5
        assert summary["mean"] == pytest.approx(30.0)
        assert summary["min"] == 10.0
        assert summary["max"] == 50.0

    def test_get_summary_empty(self, metrics_db):
        summary = metrics_db.get_summary("nonexistent", minutes=60)
        assert summary["count"] == 0

    def test_get_latest_nonexistent(self, metrics_db):
        assert metrics_db.get_latest("nonexistent") is None

    def test_cleanup_old(self, metrics_db):
        metrics_db.record("old_metric", 1.0)
        # cleanup_old with 0 days should remove everything
        metrics_db.cleanup_old(days=0)
        values = metrics_db.get_recent("old_metric", minutes=60)
        assert len(values) == 0


# ── CircuitBreakerMonitor tests ─────────────────────────────────────

class TestCircuitBreakerMonitor:
    def test_not_active_by_default(self, risk_manager):
        cb = CircuitBreakerMonitor(risk_manager)
        # Only active if .circuit_breaker_triggered file exists
        if os.path.exists(".circuit_breaker_triggered"):
            assert cb.is_active()
        else:
            assert not cb.is_active()

    def test_check_returns_dict(self, risk_manager):
        cb = CircuitBreakerMonitor(risk_manager)
        result = cb.check()
        assert "circuit_breaker_active" in result
        assert "triggers" in result

    def test_get_state_when_inactive(self, risk_manager):
        cb = CircuitBreakerMonitor(risk_manager)
        if not os.path.exists(".circuit_breaker_triggered"):
            assert cb.get_state() is None


# ── AlertManager tests ──────────────────────────────────────────────

class TestAlertManager:
    def test_send_above_min_severity(self, alert_manager):
        alert = alert_manager.send("WARNING", "trading", "Test warning")
        assert alert is not None
        assert alert.severity == "WARNING"

    def test_send_below_min_severity(self, alert_manager):
        alert = alert_manager.send("INFO", "trading", "Test info")
        assert alert is None  # Default min_severity is WARNING

    def test_send_critical(self, alert_manager):
        alert = alert_manager.send("CRITICAL", "risk", "Circuit breaker!")
        assert alert is not None
        assert alert.severity == "CRITICAL"

    def test_alert_logged_to_file(self, tmp_path):
        log_path = str(tmp_path / "alerts.jsonl")
        mgr = AlertManager(log_path=log_path, min_severity="INFO")
        mgr.send("INFO", "test", "hello")

        with open(log_path) as f:
            entry = json.loads(f.readline())
        assert entry["message"] == "hello"

    def test_get_recent(self, alert_manager):
        alert_manager.send("WARNING", "test", "msg1")
        alert_manager.send("HIGH", "test", "msg2")
        recent = alert_manager.get_recent(minutes=60)
        assert len(recent) == 2

    def test_get_recent_filtered(self, alert_manager):
        alert_manager.send("WARNING", "test", "warn")
        alert_manager.send("HIGH", "test", "high")
        recent = alert_manager.get_recent(minutes=60, severity="HIGH")
        assert len(recent) == 1
        assert recent[0].severity == "HIGH"

    def test_history_capped_at_100(self):
        mgr = AlertManager(log_path="/dev/null", min_severity="INFO")
        for i in range(120):
            mgr.send("INFO", "test", f"msg_{i}")
        assert len(mgr.alert_history) == 100


# ── HealthMonitor tests ─────────────────────────────────────────────

class TestHealthMonitor:
    def test_collect_system_metrics(self, health_monitor):
        metrics = health_monitor.collect_system_metrics()
        assert "memory_max_rss_mb" in metrics
        assert "user_cpu_seconds" in metrics
        assert metrics["user_cpu_seconds"] >= 0

    def test_record_iteration(self, health_monitor):
        result = {
            "iteration": 1,
            "status": "ok",
            "elapsed_ms": 150.0,
            "price": 42000.0,
            "signal": "hold",
            "confidence": 0.3,
        }
        health_monitor.record_iteration(result)
        assert len(health_monitor._iteration_results) == 1

        latest_latency = health_monitor.metrics.get_latest("trading.latency_ms")
        assert latest_latency == 150.0

    def test_record_iteration_error(self, health_monitor):
        result = {"iteration": 1, "status": "error", "error": "test error"}
        health_monitor.record_iteration(result)
        # Should trigger an alert
        recent = health_monitor.alerts.get_recent(minutes=1)
        assert len(recent) >= 1

    def test_detect_anomalies_insufficient_data(self, health_monitor):
        alert = health_monitor.detect_anomalies("trading.latency_ms")
        assert alert is None  # Not enough data

    def test_detect_anomalies_with_outlier(self, health_monitor):
        # Record normal values
        for _ in range(20):
            health_monitor.metrics.record("test.metric", 100.0)
        # Record outlier
        health_monitor.metrics.record("test.metric", 10000.0)

        alert = health_monitor.detect_anomalies("test.metric")
        assert alert is not None
        assert alert.severity == "HIGH"
        assert "anomaly" in alert.category

    def test_check_health(self, health_monitor):
        report = health_monitor.check_health()
        assert "timestamp" in report
        assert "overall_status" in report
        assert "checks" in report
        assert report["overall_status"] in ("healthy", "warning", "degraded")

    def test_check_health_includes_all_sections(self, health_monitor):
        report = health_monitor.check_health()
        checks = report["checks"]
        assert "system" in checks
        assert "circuit_breaker" in checks
        assert "trading" in checks
        assert "risk" in checks
        assert "alerts" in checks

    def test_generate_report(self, health_monitor):
        text = health_monitor.generate_report()
        assert "Health Report" in text
        assert "Overall Status" in text
        assert "System" in text
        assert "Circuit Breaker" in text
        assert "Trading" in text

    def test_iteration_history_capped(self, health_monitor):
        for i in range(600):
            health_monitor.record_iteration({"iteration": i, "status": "ok"})
        assert len(health_monitor._iteration_results) == 500

    def test_high_latency_alert(self, health_monitor):
        result = {"iteration": 1, "status": "ok", "elapsed_ms": 8000.0}
        health_monitor.record_iteration(result)
        recent = health_monitor.alerts.get_recent(minutes=1, severity="WARNING")
        assert len(recent) >= 1
