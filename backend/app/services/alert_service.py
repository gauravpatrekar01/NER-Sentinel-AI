"""Backward-compatible alert service - delegates to alert_engine."""

from app.services.alert_engine import generate_alert, clear_all_alerts, evaluate_alerts

__all__ = ["generate_alert", "clear_all_alerts", "evaluate_alerts"]
