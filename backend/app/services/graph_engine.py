"""
Dynamic weighted road graph built from CSV road data.
Supports edge costs, bottleneck detection, and district connectivity.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

import networkx as nx

from app.models.models import Road

# Junction nodes for the NER corridor network
JUNCTIONS: Dict[str, Dict[str, Any]] = {
    "J-GUW": {"name": "Guwahati", "lat": 26.1445, "lon": 91.7362, "district": "Kamrup Metropolitan"},
    "J-SHL": {"name": "Shillong", "lat": 25.5788, "lon": 91.8833, "district": "East Khasi Hills"},
    "J-JOW": {"name": "Jowai", "lat": 25.4484, "lon": 92.2032, "district": "West Jaintia Hills"},
    "J-KHL": {"name": "Khliehriat", "lat": 25.3578, "lon": 92.3689, "district": "East Jaintia Hills"},
    "J-SIL": {"name": "Silchar", "lat": 24.8333, "lon": 92.7789, "district": "Cachar"},
    "J-NAG": {"name": "Nagaon", "lat": 26.3500, "lon": 92.6800, "district": "Nagaon"},
    "J-HAF": {"name": "Haflong", "lat": 25.1700, "lon": 93.0300, "district": "Dima Hasao"},
}

# Road segment topology: road_id -> (source_junction, dest_junction)
ROAD_TOPOLOGY: Dict[str, Tuple[str, str]] = {
    "R-204": ("J-GUW", "J-SHL"),
    "R-207": ("J-SHL", "J-JOW"),
    "R-211": ("J-JOW", "J-KHL"),
    "R-218": ("J-KHL", "J-SIL"),
    "R-301": ("J-GUW", "J-NAG"),
    "R-302": ("J-NAG", "J-HAF"),
    "R-303": ("J-HAF", "J-SIL"),
}

ROAD_DISTRICT: Dict[str, str] = {
    "R-204": "East Khasi Hills",
    "R-207": "East Khasi Hills",
    "R-211": "West Jaintia Hills",
    "R-218": "Cachar",
    "R-301": "Nagaon",
    "R-302": "Dima Hasao",
    "R-303": "Cachar",
}

# Predefined multi-segment routes (backward compatible with route_service)
PREDEFINED_ROUTES = [
    {"route_id": "RT-NH6", "name": "NH-6 Primary Corridor (via Shillong)", "road_ids": ["R-204", "R-207", "R-211", "R-218"]},
    {"route_id": "RT-NH27-54", "name": "NH-27/NH-54 Alternate Corridor (via Haflong)", "road_ids": ["R-301", "R-302", "R-303"]},
    {"route_id": "RT-MOUNTAIN", "name": "NH-2 Alternate Hill Bypass (Hybrid)", "road_ids": ["R-301", "R-302", "R-218"]},
]

_graph_cache: Optional[nx.DiGraph] = None
_roads_snapshot: Optional[Dict[str, Road]] = None


def _road_damage_score(road: Road) -> float:
    """Road damage risk from condition (1=terrible, 10=perfect)."""
    return max(0.0, min(100.0, (10.0 - road.road_condition) * 10.0))


def _weather_risk_for_road(road: Road) -> float:
    rainfall_risk = min(100.0, road.rainfall_mm * 0.5)
    return max(0.0, min(100.0, (rainfall_risk + road.flood_risk) / 2.0))


def _incident_risk_for_road(road: Road) -> float:
    severity_map = {"None": 0, "LOW": 25, "MEDIUM": 50, "HIGH": 75, "CRITICAL": 100}
    base = severity_map.get(road.field_incident_severity or "None", 0)
    return max(base, road.disruption_probability * 100.0)


def _historical_risk_for_road(road: Road) -> float:
    hist = min(100.0, road.historical_incidents * 12.0)
    return max(0.0, min(100.0, (hist + road.landslide_history) / 2.0))


def compute_accessibility_score(road: Road) -> float:
    """Accessibility = 100 - weather - traffic - incident - road damage."""
    weather = _weather_risk_for_road(road)
    traffic = road.traffic_level
    incident = _incident_risk_for_road(road)
    damage = _road_damage_score(road)
    score = 100.0 - weather * 0.25 - traffic * 0.25 - incident * 0.30 - damage * 0.20
    return round(max(0.0, min(100.0, score)), 1)


def compute_risk_score(road: Road) -> float:
    """Composite risk score 0-100 from road attributes."""
    weather = _weather_risk_for_road(road)
    incident = _incident_risk_for_road(road)
    condition = _road_damage_score(road)
    traffic = road.traffic_level
    historical = _historical_risk_for_road(road)
    terrain = road.terrain_risk

    score = (
        0.30 * weather
        + 0.25 * incident
        + 0.20 * condition
        + 0.15 * traffic
        + 0.10 * historical
        + 0.05 * terrain
    )
    if road.status == "BLOCKED":
        return 100.0
    return round(max(0.0, min(100.0, score)), 1)


def classify_road_status(risk_score: float, is_blocked: bool, emergency: bool = False) -> str:
    if is_blocked:
        return "BLOCKED"
    if emergency and risk_score >= 61:
        return "HIGH_RISK"
    if risk_score >= 81:
        return "HIGH_RISK"
    if risk_score >= 61:
        return "HIGH_RISK"
    if risk_score >= 31:
        return "CAUTION"
    return "OPEN"


def map_status_to_frontend(status: str) -> str:
    """Map internal status to existing frontend-compatible values."""
    mapping = {
        "OPEN": "OPEN",
        "LOW": "OPEN",
        "CAUTION": "MODERATE",
        "RESTRICTED": "MODERATE",
        "MODERATE": "MODERATE",
        "HIGH": "HIGH RISK",
        "HIGH_RISK": "HIGH RISK",
        "CRITICAL": "HIGH RISK",
        "BLOCKED": "BLOCKED",
        "EMERGENCY": "HIGH RISK",
    }
    return mapping.get(status, status)


def calculate_edge_cost(
    road: Road,
    emergency_mode: bool = False,
    priority: str = "NORMAL",
) -> float:
    """
    Dynamic edge cost:
    Distance + Time + Risk + Traffic + Fuel
    BLOCKED roads -> infinity
    """
    if road.status == "BLOCKED":
        return float("inf")

    distance_cost = road.length_km * 1.0

    base_speed = 60.0 if road.road_id in ("R-204", "R-301") else 40.0
    risk_score = compute_risk_score(road)
    speed_factor = max(0.3, 1.0 - (risk_score / 100.0) * 0.6)
    travel_hours = road.length_km / (base_speed * speed_factor)
    time_cost = travel_hours * 60.0  # minutes

    risk_cost = risk_score * 2.0
    traffic_cost = road.traffic_level * 0.5
    fuel_cost = road.length_km * 0.15

    risk_weight = 1.5
    if priority == "CRITICAL":
        risk_weight = 10.0
    elif priority == "HIGH":
        risk_weight = 5.0
    if emergency_mode:
        risk_weight *= 2.5

    total = distance_cost + time_cost + risk_cost * risk_weight + traffic_cost + fuel_cost
    return round(total, 2)


def build_road_graph(roads: List[Road], force_rebuild: bool = False) -> nx.DiGraph:
    """Build or return cached directed graph with dynamic edge attributes."""
    global _graph_cache, _roads_snapshot

    roads_dict = {r.road_id: r for r in roads}
    if not force_rebuild and _graph_cache is not None and _roads_snapshot == roads_dict:
        return _graph_cache

    g = nx.DiGraph()
    for jid, meta in JUNCTIONS.items():
        g.add_node(jid, **meta)

    for road_id, (src, dst) in ROAD_TOPOLOGY.items():
        road = roads_dict.get(road_id)
        if not road:
            continue
        risk = compute_risk_score(road)
        acc = compute_accessibility_score(road)
        internal_status = classify_road_status(risk, road.status == "BLOCKED")
        g.add_edge(
            src,
            dst,
            road_id=road_id,
            distance=road.length_km,
            travel_time=road.length_km / max(30.0, 60.0 - risk_score_to_speed_penalty(risk)),
            traffic=road.traffic_level,
            road_condition=road.road_condition,
            weather_risk=_weather_risk_for_road(road),
            incident_risk=_incident_risk_for_road(road),
            historical_risk=_historical_risk_for_road(road),
            terrain_risk=road.terrain_risk,
            accessibility_score=acc,
            risk_score=risk,
            status=internal_status,
            dynamic_cost=calculate_edge_cost(road),
            road=road,
        )

    _graph_cache = g
    _roads_snapshot = roads_dict
    return g


def risk_score_to_speed_penalty(risk_score: float) -> float:
    return min(40.0, risk_score * 0.35)


def invalidate_graph_cache() -> None:
    global _graph_cache, _roads_snapshot
    _graph_cache = None
    _roads_snapshot = None


def get_road_edge_attributes(road: Road) -> Dict[str, Any]:
    """Full edge attribute dict for a single road segment."""
    risk = compute_risk_score(road)
    status = classify_road_status(risk, road.status == "BLOCKED")
    src, dst = ROAD_TOPOLOGY.get(road.road_id, ("", ""))
    return {
        "road_id": road.road_id,
        "source": src,
        "destination": dst,
        "distance": road.length_km,
        "travel_time": road.length_km / max(30.0, 60.0 - risk_score_to_speed_penalty(risk)),
        "traffic": road.traffic_level,
        "road_condition": road.road_condition,
        "weather_risk": round(_weather_risk_for_road(road), 1),
        "incident_risk": round(_incident_risk_for_road(road), 1),
        "historical_risk": round(_historical_risk_for_road(road), 1),
        "terrain_risk": road.terrain_risk,
        "accessibility_score": compute_accessibility_score(road),
        "risk_score": risk,
        "status": status,
        "dynamic_cost": calculate_edge_cost(road),
    }


def detect_bottlenecks(roads: List[Road], top_n: int = 5) -> List[Dict[str, Any]]:
    """Betweenness centrality + traffic + incident frequency -> bottleneck score."""
    g = build_road_graph(roads)
    if g.number_of_edges() == 0:
        return []

    centrality = nx.betweenness_centrality(g, weight="dynamic_cost")
    results = []

    for u, v, data in g.edges(data=True):
        road = data.get("road")
        if not road:
            continue
        bc = centrality.get(u, 0.0) + centrality.get(v, 0.0)
        bc_norm = min(100.0, bc * 200.0)
        traffic_factor = road.traffic_level * 0.3
        delay_factor = (100.0 - compute_accessibility_score(road)) * 0.2
        incident_factor = road.historical_incidents * 5.0
        bottleneck_score = round(min(100.0, bc_norm + traffic_factor + delay_factor + incident_factor), 1)

        classification = "LOW"
        if bottleneck_score >= 81:
            classification = "CRITICAL"
        elif bottleneck_score >= 61:
            classification = "HIGH"
        elif bottleneck_score >= 31:
            classification = "MODERATE"

        results.append({
            "road_id": road.road_id,
            "name": road.name,
            "bottleneck_score": bottleneck_score,
            "classification": classification,
            "betweenness": round(bc, 4),
            "traffic_level": road.traffic_level,
            "incident_count": road.historical_incidents,
        })

    results.sort(key=lambda x: x["bottleneck_score"], reverse=True)
    return results[:top_n]


def calculate_district_connectivity(roads: List[Road]) -> List[Dict[str, Any]]:
    """District-level connectivity analysis."""
    g = build_road_graph(roads)
    districts: Dict[str, Dict[str, Any]] = {}

    for road in roads:
        district = ROAD_DISTRICT.get(road.road_id, "Unknown")
        if district not in districts:
            districts[district] = {
                "district": district,
                "roads": [],
                "blocked": 0,
                "accessible_connections": 0,
                "total_connections": 0,
            }
        districts[district]["roads"].append(road.road_id)
        if road.status == "BLOCKED":
            districts[district]["blocked"] += 1

    for district, info in districts.items():
        district_roads = set(info["roads"])
        total_conn = 0
        accessible = 0
        for road_id in district_roads:
            if road_id not in ROAD_TOPOLOGY:
                continue
            src, dst = ROAD_TOPOLOGY[road_id]
            total_conn += 2  # in + out potential
            road = next((r for r in roads if r.road_id == road_id), None)
            if road and road.status != "BLOCKED":
                accessible += 2

        # Shortest path availability between key junctions in district roads
        district_junctions = set()
        for rid in district_roads:
            if rid in ROAD_TOPOLOGY:
                district_junctions.update(ROAD_TOPOLOGY[rid])

        sp_count = 0
        sp_ok = 0
        junction_list = list(district_junctions)
        for i, j1 in enumerate(junction_list):
            for j2 in junction_list[i + 1 :]:
                sp_count += 1
                try:
                    if nx.has_path(g, j1, j2):
                        sp_ok += 1
                except nx.NetworkXError:
                    pass

        blocked_connections = info["blocked"]
        degree_score = (accessible / max(1, total_conn)) * 50.0
        path_score = (sp_ok / max(1, sp_count)) * 50.0 if sp_count else 50.0
        connectivity_score = round(max(0.0, min(100.0, degree_score + path_score - blocked_connections * 10)), 1)

        info["accessible_connections"] = accessible
        info["total_connections"] = total_conn
        info["blocked_connections"] = blocked_connections
        info["connectivity_score"] = connectivity_score
        info["shortest_paths_available"] = sp_ok
        info["shortest_paths_total"] = sp_count

    return list(districts.values())


def junction_for_location(name: str) -> Optional[str]:
    """Map location name to junction ID."""
    name_lower = name.lower()
    for jid, meta in JUNCTIONS.items():
        if meta["name"].lower() in name_lower or name_lower in meta["name"].lower():
            return jid
    location_aliases = {
        "guwahati": "J-GUW",
        "shillong": "J-SHL",
        "jowai": "J-JOW",
        "khliehriat": "J-KHL",
        "silchar": "J-SIL",
        "nagaon": "J-NAG",
        "haflong": "J-HAF",
    }
    for alias, jid in location_aliases.items():
        if alias in name_lower:
            return jid
    return None


def resolve_vehicle_junctions(origin: str, destination: str) -> Tuple[Optional[str], Optional[str]]:
    return junction_for_location(origin), junction_for_location(destination)
