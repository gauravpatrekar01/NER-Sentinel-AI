from typing import Dict, Any
from app.services.routing_engine import get_optimized_routes_compat


def get_optimized_routes(priority: str = "NORMAL", emergency_mode: bool = False) -> Dict[str, Any]:
    """Backward-compatible route optimization using A* routing engine."""
    return get_optimized_routes_compat(priority=priority, emergency_mode=emergency_mode)
