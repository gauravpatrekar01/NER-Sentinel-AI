"""Application-wide runtime state (emergency mode, weather mode)."""

from enum import Enum
from typing import Dict, Any

class WeatherMode(str, Enum):
    LIVE = "LIVE"
    SIMULATION = "SIMULATION"
    FALLBACK = "FALLBACK"


_emergency_mode: bool = False
_weather_mode: WeatherMode = WeatherMode.FALLBACK
_route_deviation_threshold_km: float = 2.0


def is_emergency_mode() -> bool:
    return _emergency_mode


def set_emergency_mode(active: bool) -> Dict[str, Any]:
    global _emergency_mode
    _emergency_mode = active
    return {
        "status": "activated" if active else "deactivated",
        "emergency_mode": active,
        "message": (
            "Emergency mode activated. Critical deliveries receive safety-first routing."
            if active
            else "Emergency mode deactivated. Normal routing weights restored."
        ),
    }


def get_weather_mode() -> WeatherMode:
    return _weather_mode


def set_weather_mode(mode: WeatherMode) -> None:
    global _weather_mode
    _weather_mode = mode


def get_route_deviation_threshold_km() -> float:
    return _route_deviation_threshold_km


def set_route_deviation_threshold_km(km: float) -> None:
    global _route_deviation_threshold_km
    _route_deviation_threshold_km = max(0.1, km)
