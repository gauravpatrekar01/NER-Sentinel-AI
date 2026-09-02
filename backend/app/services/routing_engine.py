"""
A* dynamic route optimization on the weighted road graph.
"""

from __future__ import annotations

import heapq
import math
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from app.models.models import Road
from app.services.graph_engine import (
    PREDEFINED_ROUTES,
    JUNCTIONS,
    ROAD_TOPOLOGY,
    build_road_graph,
    calculate_edge_cost,
    compute_risk_score,
    junction_for_location,
    map_status_to_frontend,
)
from app.services.app_state import is_emergency_mode


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    )
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _heuristic(node: str, goal: str) -> float:
    n1 = JUNCTIONS.get(node, {})
    n2 = JUNCTIONS.get(goal, {})
    if not n1 or not n2:
        return 0.0
    dist = _haversine_km(n1["lat"], n1["lon"], n2["lat"], n2["lon"])
    return dist * 2.0  # optimistic cost per km


def astar_find_path(
    graph: nx.DiGraph,
    start: str,
    goal: str,
    blocked_roads: Optional[List[str]] = None,
    emergency_mode: bool = False,
    priority: str = "NORMAL",
) -> Optional[List[str]]:
    """A* path finding returning list of road_ids."""
    blocked = set(blocked_roads or [])
    if start not in graph or goal not in graph:
        return None

    open_set: List[Tuple[float, float, str, List[str]]] = [(0.0, 0.0, start, [])]
    visited: Dict[str, float] = {}

    while open_set:
        f_score, g_score, current, path = heapq.heappop(open_set)
        if current in visited and visited[current] <= g_score:
            continue
        visited[current] = g_score

        if current == goal:
            return path

        for neighbor in graph.successors(current):
            edge = graph[current][neighbor]
            road_id = edge.get("road_id")
            if road_id in blocked:
                continue
            road: Road = edge.get("road")
            if not road:
                continue
            edge_cost = calculate_edge_cost(road, emergency_mode, priority)
            if math.isinf(edge_cost):
                continue
            new_g = g_score + edge_cost
            h = _heuristic(neighbor, goal)
            new_path = path + [road_id]
            heapq.heappush(open_set, (new_g + h, new_g, neighbor, new_path))

    return None


def calculate_route_cost(
    road_ids: List[str],
    roads_dict: Dict[str, Road],
    emergency_mode: bool = False,
    priority: str = "NORMAL",
) -> Dict[str, Any]:
    """Calculate total cost metrics for a sequence of road segments."""
    total_distance = 0.0
    total_time_hours = 0.0
    total_cost = 0.0
    max_risk = 0.0
    sum_risk = 0.0
    is_blocked = False
    blocked_road_name = ""
    full_path: List[List[float]] = []

    for rid in road_ids:
        road = roads_dict.get(rid)
        if not road:
            continue
        total_distance += road.length_km
        edge_cost = calculate_edge_cost(road, emergency_mode, priority)
        if math.isinf(edge_cost):
            is_blocked = True
            blocked_road_name = road.name

        risk = compute_risk_score(road)
        max_risk = max(max_risk, risk)
        sum_risk += risk

        base_speed = 60.0 if rid in ("R-204", "R-301") else 40.0
        speed_factor = max(0.3, 1.0 - risk / 100.0 * 0.6)
        total_time_hours += road.length_km / (base_speed * speed_factor)
        total_cost += edge_cost if not math.isinf(edge_cost) else 999999.0

        if road.path:
            if full_path and full_path[-1] == road.path[0]:
                full_path.extend(road.path[1:])
            else:
                full_path.extend(road.path)

    avg_risk = sum_risk / len(road_ids) if road_ids else 0.0
    if is_blocked:
        total_cost = 999999.0

    risk_level = "LOW"
    if max_risk >= 81:
        risk_level = "CRITICAL"
    elif max_risk >= 61:
        risk_level = "HIGH"
    elif max_risk >= 31:
        risk_level = "MODERATE"

    return {
        "total_distance_km": round(total_distance, 1),
        "travel_time_hours": round(total_time_hours, 2),
        "eta_minutes": round(total_time_hours * 60, 1),
        "max_risk_prob": round(max_risk / 100.0, 2),
        "avg_risk_prob": round(avg_risk / 100.0, 2),
        "risk_score": round(max_risk, 1),
        "risk_level": risk_level,
        "total_cost": round(total_cost, 2),
        "is_blocked": is_blocked,
        "blocked_road_name": blocked_road_name,
        "path": full_path,
    }


def find_best_route(
    origin: str,
    destination: str,
    roads: List[Road],
    priority: str = "NORMAL",
    emergency_mode: Optional[bool] = None,
    blocked_roads: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Find optimal route using A* between named locations."""
    if emergency_mode is None:
        emergency_mode = is_emergency_mode()

    roads_dict = {r.road_id: r for r in roads}
    graph = build_road_graph(roads)
    start = junction_for_location(origin)
    goal = junction_for_location(destination)

    road_ids: Optional[List[str]] = None
    reason = ""

    if start and goal:
        road_ids = astar_find_path(graph, start, goal, blocked_roads, emergency_mode, priority)
        if road_ids:
            reason = "A* selected lowest dynamic-cost path balancing distance, time, and risk"

    if not road_ids:
        # Fallback to predefined routes
        best_cfg = None
        best_cost = float("inf")
        for cfg in PREDEFINED_ROUTES:
            metrics = calculate_route_cost(cfg["road_ids"], roads_dict, emergency_mode, priority)
            if metrics["total_cost"] < best_cost:
                best_cost = metrics["total_cost"]
                best_cfg = cfg
                reason = "Selected from predefined corridors by lowest weighted cost"
        if best_cfg:
            road_ids = best_cfg["road_ids"]

    if not road_ids:
        return {"error": "No route found", "route_id": None}

    metrics = calculate_route_cost(road_ids, roads_dict, emergency_mode, priority)
    route_id = f"ALT-{hash(tuple(road_ids)) % 100:02d}"

    return {
        "route_id": route_id,
        "road_ids": road_ids,
        "road_segments": road_ids,
        "distance_km": metrics["total_distance_km"],
        "eta_minutes": metrics["eta_minutes"],
        "risk_score": metrics["risk_score"],
        "risk_level": metrics["risk_level"],
        "total_cost": metrics["total_cost"],
        "reason": reason,
        "path": metrics["path"],
        "is_blocked": metrics["is_blocked"],
    }


def find_alternative_routes(
    origin: str,
    destination: str,
    roads: List[Road],
    priority: str = "NORMAL",
    emergency_mode: Optional[bool] = None,
    blocked_roads: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Compare A* result with predefined corridor alternatives."""
    if emergency_mode is None:
        emergency_mode = is_emergency_mode()

    roads_dict = {r.road_id: r for r in roads}
    alternatives = []
    seen_paths = set()

    # A* optimal
    best = find_best_route(origin, destination, roads, priority, emergency_mode, blocked_roads)
    if best.get("road_ids"):
        key = tuple(best["road_ids"])
        seen_paths.add(key)
        alternatives.append({
            "route_id": best["route_id"],
            "name": f"Optimized Route ({'Emergency' if emergency_mode else 'Standard'})",
            "road_ids": best["road_ids"],
            "total_distance_km": best["distance_km"],
            "travel_time_hours": round(best["eta_minutes"] / 60.0, 2),
            "max_risk_prob": best["risk_score"] / 100.0,
            "avg_risk_prob": best["risk_score"] / 100.0,
            "risk_score": best["risk_score"],
            "risk_level": best["risk_level"],
            "is_blocked": best["is_blocked"],
            "blocked_road_name": "",
            "cost_score": best["total_cost"],
            "path": best["path"],
            "reason": best["reason"],
        })

    for cfg in PREDEFINED_ROUTES:
        key = tuple(cfg["road_ids"])
        if key in seen_paths:
            continue
        metrics = calculate_route_cost(cfg["road_ids"], roads_dict, emergency_mode, priority)
        alternatives.append({
            "route_id": cfg["route_id"],
            "name": cfg["name"],
            "road_ids": cfg["road_ids"],
            "total_distance_km": metrics["total_distance_km"],
            "travel_time_hours": metrics["travel_time_hours"],
            "max_risk_prob": metrics["max_risk_prob"],
            "avg_risk_prob": metrics["avg_risk_prob"],
            "risk_score": metrics["risk_score"],
            "risk_level": metrics["risk_level"],
            "is_blocked": metrics["is_blocked"],
            "blocked_road_name": metrics["blocked_road_name"],
            "cost_score": metrics["total_cost"],
            "path": metrics["path"],
            "reason": "Predefined corridor route",
        })
        seen_paths.add(key)

    alternatives.sort(key=lambda x: x["cost_score"])
    recommended = next((a for a in alternatives if not a["is_blocked"]), alternatives[0] if alternatives else None)

    return {
        "recommended_route_id": recommended["route_id"] if recommended else None,
        "recommended_route": recommended,
        "routes": alternatives,
        "alternatives": alternatives,
        "all_blocked": all(a["is_blocked"] for a in alternatives) if alternatives else True,
    }


def get_optimized_routes_compat(
    priority: str = "NORMAL",
    emergency_mode: bool = False,
    roads: Optional[List[Road]] = None,
) -> Dict[str, Any]:
    """Backward-compatible wrapper matching existing route_service API."""
    from app.database import load_roads

    if roads is None:
        roads = load_roads()

    result = find_alternative_routes(
        origin="Guwahati",
        destination="Silchar",
        roads=roads,
        priority=priority,
        emergency_mode=emergency_mode,
    )
    return {
        "recommended_route_id": result["recommended_route_id"],
        "routes": result["routes"],
        "all_blocked": result["all_blocked"],
    }
