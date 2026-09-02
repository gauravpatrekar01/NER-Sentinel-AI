"""Backward-compatible ETA service - delegates to eta_engine."""

from app.services.eta_engine import calculate_eta_and_delay, calculate_vehicle_eta

__all__ = ["calculate_eta_and_delay", "calculate_vehicle_eta"]
