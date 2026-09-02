"""
GPS positioning and geofencing for route deviation detection.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from app.models.models import Road, Vehicle
from app.services.app_state import get_route_deviation_threshold_km


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_to_segment_distance_km(
    point: Tuple[float, float],
    seg_start: Tuple[float, float],
    seg_end: Tuple[float, float],
) -> float:
    """Minimum distance from point to line segment in km (equirectangular approx)."""
    lat, lon = point
    lat1, lon1 = seg_start
    lat2, lon2 = seg_end

    if lat1 == lat2 and lon1 == lon2:
        return haversine_km(lat, lon, lat1, lon1)

    # Project point onto segment
    dx = lon2 - lon1
    dy = lat2 - lat1
    t = max(0.0, min(1.0, ((lon - lon1) * dx + (lat - lat1) * dy) / (dx * dx + dy * dy + 1e-12)))
    proj_lat = lat1 + t * dy
    proj_lon = lon1 + t * dx
    return haversine_km(lat, lon, proj_lat, proj_lon)


def get_route_coordinates(route_id: str, roads_dict: Dict[str, Road]) -> List[List[float]]:
    coords: List[List[float]] = []
    for rid in route_id.split(";"):
        road = roads_dict.get(rid.strip())
        if road and road.path:
            if coords and coords[-1] == road.path[0]:
                coords.extend(road.path[1:])
            else:
                coords.extend(road.path)
    return coords


def distance_to_planned_route(
    lat: float,
    lon: float,
    route_coords: List[List[float]],
) -> float:
    """Minimum distance from vehicle position to planned route polyline (km)."""
    if not route_coords:
        return 0.0
    if len(route_coords) == 1:
        return haversine_km(lat, lon, route_coords[0][0], route_coords[0][1])

    min_dist = float("inf")
    for i in range(len(route_coords) - 1):
        d = point_to_segment_distance_km(
            (lat, lon),
            (route_coords[i][0], route_coords[i][1]),
            (route_coords[i + 1][0], route_coords[i + 1][1]),
        )
        min_dist = min(min_dist, d)
    return min_dist


def calculate_route_deviation(
    vehicle: Vehicle,
    roads_dict: Dict[str, Road],
    threshold_km: Optional[float] = None,
) -> Dict[str, Any]:
    """Check if vehicle has deviated from its planned route."""
    if threshold_km is None:
        threshold_km = get_route_deviation_threshold_km()

    planned_coords = get_route_coordinates(vehicle.current_route_id, roads_dict)
    distance_km = distance_to_planned_route(vehicle.current_lat, vehicle.current_lon, planned_coords)
    route_deviation = distance_km > threshold_km

    return {
        "vehicle_id": vehicle.vehicle_id,
        "distance_from_route_km": round(distance_km, 3),
        "threshold_km": threshold_km,
        "route_deviation": route_deviation,
        "current_lat": vehicle.current_lat,
        "current_lon": vehicle.current_lon,
        "planned_route": vehicle.current_route_id,
    }


def check_geofence(
    lat: float,
    lon: float,
    center_lat: float,
    center_lon: float,
    radius_km: float,
) -> Dict[str, Any]:
    """Check if a point is inside a circular geofence."""
    distance = haversine_km(lat, lon, center_lat, center_lon)
    return {
        "inside": distance <= radius_km,
        "distance_km": round(distance, 3),
        "radius_km": radius_km,
    }


def calculate_vehicle_position(
    vehicle: Vehicle,
    roads_dict: Dict[str, Road],
    progress: Optional[float] = None,
) -> Dict[str, Any]:
    """Calculate vehicle position along route at given progress."""
    from app.services.gps_simulator import interpolate_position

    prog = progress if progress is not None else vehicle.progress
    route_coords = get_route_coordinates(vehicle.current_route_id, roads_dict)
    pos = interpolate_position(route_coords, prog)

    current_road = None
    for rid in vehicle.current_route_id.split(";"):
        road = roads_dict.get(rid.strip())
        if road:
            current_road = rid.strip()

    return {
        "vehicle_id": vehicle.vehicle_id,
        "latitude": pos[0],
        "longitude": pos[1],
        "current_road": current_road,
        "progress": prog,
        "speed_kmh": vehicle.speed_kmh,
        "destination": vehicle.destination,
        "planned_route": vehicle.current_route_id,
    }


def update_vehicle_location(
    vehicle: Vehicle,
    lat: float,
    lon: float,
    roads_dict: Dict[str, Road],
) -> Dict[str, Any]:
    """Update vehicle GPS position and check deviation."""
    vehicle.current_lat = lat
    vehicle.current_lon = lon
    deviation = calculate_route_deviation(vehicle, roads_dict)
    return {
        "vehicle_id": vehicle.vehicle_id,
        "updated": True,
        "position": {"lat": lat, "lon": lon},
        "deviation": deviation,
    }
