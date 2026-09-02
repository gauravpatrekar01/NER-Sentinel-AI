"""
Centralized risk engine with weighted formula, explainability, and DBSCAN clustering.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

import numpy as np
from sklearn.cluster import DBSCAN

from app.models.models import Incident, Road, WeatherObservation
from app.services.graph_engine import (
    compute_accessibility_score,
    compute_risk_score,
    map_status_to_frontend,
)


def classify_risk_level(risk_score: float, is_blocked: bool = False) -> str:
    if is_blocked or risk_score >= 100:
        return "BLOCKED"
    if risk_score >= 81:
        return "CRITICAL"
    if risk_score >= 61:
        return "HIGH"
    if risk_score >= 31:
        return "MODERATE"
    return "LOW"


def _weather_component(road: Road, weather: Optional[WeatherObservation]) -> float:
    rainfall = road.rainfall_mm
    if weather:
        rainfall = max(rainfall, weather.rainfall_mm)
    rainfall_risk = min(100.0, rainfall * 0.5)
    visibility_penalty = 0.0
    if weather and weather.visibility_km < 3.0:
        visibility_penalty = (3.0 - weather.visibility_km) * 15.0
    flood_component = road.flood_risk * 0.4
    return max(0.0, min(100.0, rainfall_risk * 0.6 + flood_component + visibility_penalty))


def _incident_component(road: Road) -> float:
    severity_map = {"None": 0, "LOW": 20, "MEDIUM": 45, "HIGH": 70, "CRITICAL": 95}
    sev = severity_map.get(road.field_incident_severity or "None", 0)
    return max(sev, road.disruption_probability * 100.0)


def _road_condition_component(road: Road) -> float:
    return max(0.0, min(100.0, (10.0 - road.road_condition) * 10.0))


def _traffic_component(road: Road) -> float:
    return max(0.0, min(100.0, road.traffic_level))


def _historical_component(road: Road) -> float:
    hist = min(100.0, road.historical_incidents * 12.0)
    terrain = road.terrain_risk * 0.5
    landslide = road.landslide_history * 0.5
    return max(0.0, min(100.0, (hist + terrain + landslide) / 3.0))


def calculate_road_risk(
    road: Road,
    weather: Optional[WeatherObservation] = None,
    use_ml: bool = True,
) -> Dict[str, Any]:
    """
    Centralized weighted risk calculation with explainability.
    Risk = 0.30*Weather + 0.25*Incident + 0.20*RoadCondition + 0.15*Traffic + 0.10*Historical
    """
    weather_risk = _weather_component(road, weather)
    incident_risk = _incident_component(road)
    condition_risk = _road_condition_component(road)
    traffic_risk = _traffic_component(road)
    historical_risk = _historical_component(road)

    weighted_score = (
        0.30 * weather_risk
        + 0.25 * incident_risk
        + 0.20 * condition_risk
        + 0.15 * traffic_risk
        + 0.10 * historical_risk
    )

    ml_probability = None
    ml_factors: List[Dict[str, Any]] = []
    if use_ml:
        from app.ml.predictor import predict_road_risk

        severity_map = {"None": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        sev_val = severity_map.get(road.field_incident_severity or "None", 0)
        effective_rainfall = road.rainfall_mm
        if weather:
            effective_rainfall = max(effective_rainfall, weather.rainfall_mm)

        ml_result = predict_road_risk(
            rainfall=effective_rainfall,
            terrain_risk=road.terrain_risk,
            historical_incidents=road.historical_incidents,
            road_condition=road.road_condition,
            traffic=road.traffic_level,
            flood_risk=road.flood_risk,
            landslide_history=road.landslide_history,
            field_incident_severity=sev_val,
        )
        ml_probability = ml_result["disruption_probability"]
        ml_factors = ml_result.get("factors", [])
        # Blend rule-based and ML (60% rules, 40% ML)
        ml_score = ml_probability * 100.0
        weighted_score = 0.6 * weighted_score + 0.4 * ml_score

    is_blocked = road.status == "BLOCKED"
    if is_blocked:
        weighted_score = 100.0

    risk_score = round(max(0.0, min(100.0, weighted_score)), 1)
    risk_level = classify_risk_level(risk_score, is_blocked)
    accessibility = 0.0 if is_blocked else compute_accessibility_score(road)

    factors = [
        {"factor": "Weather", "impact": round(0.30 * weather_risk)},
        {"factor": "Incident", "impact": round(0.25 * incident_risk)},
        {"factor": "Road Condition", "impact": round(0.20 * condition_risk)},
        {"factor": "Traffic", "impact": round(0.15 * traffic_risk)},
        {"factor": "Historical Risk", "impact": round(0.10 * historical_risk)},
    ]
    factors = sorted(factors, key=lambda x: x["impact"], reverse=True)
    factors = [f for f in factors if f["impact"] > 0][:5]

    explanation_parts = []
    if weather_risk > 50:
        explanation_parts.append("rainfall and weather conditions elevated")
    if incident_risk > 40:
        explanation_parts.append("active incidents on corridor")
    if condition_risk > 40:
        explanation_parts.append("road condition is poor")
    if not explanation_parts:
        explanation_parts.append("conditions within normal operating range")
    explanation = f"Risk score {risk_score}% because {', '.join(explanation_parts)}."

    return {
        "road_id": road.road_id,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "accessibility_score": round(accessibility, 1),
        "disruption_probability": round(risk_score / 100.0, 2),
        "factors": factors,
        "ml_factors": ml_factors,
        "ml_probability": ml_probability,
        "status": map_status_to_frontend("BLOCKED" if is_blocked else risk_level),
        "explanation": explanation,
        "components": {
            "weather": round(weather_risk, 1),
            "incident": round(incident_risk, 1),
            "road_condition": round(condition_risk, 1),
            "traffic": round(traffic_risk, 1),
            "historical": round(historical_risk, 1),
        },
    }


def cluster_incidents_dbscan(
    incidents: List[Incident],
    eps_km: float = 15.0,
    min_samples: int = 2,
) -> Dict[str, Any]:
    """
    DBSCAN spatial clustering of incident coordinates.
    Identifies high-risk corridors (clusters), not predictive risk alone.
    """
    active = [i for i in incidents if i.active]
    if len(active) < min_samples:
        return {
            "clusters": [],
            "noise_points": [{"incident_id": i.incident_id, "lat": i.lat, "lon": i.lon} for i in active],
            "high_risk_corridors": [],
            "message": "Insufficient incidents for clustering",
        }

    coords = np.array([[i.lat, i.lon] for i in active])
    # Convert eps from km to approximate degrees (1 deg ~ 111 km)
    eps_deg = eps_km / 111.0

    clustering = DBSCAN(eps=eps_deg, min_samples=min_samples, metric="euclidean")
    labels = clustering.fit_predict(coords)

    clusters: Dict[int, List[Dict[str, Any]]] = {}
    noise = []
    for idx, label in enumerate(labels):
        inc = active[idx]
        point = {
            "incident_id": inc.incident_id,
            "road_id": inc.road_id,
            "lat": inc.lat,
            "lon": inc.lon,
            "type": inc.type,
            "severity": inc.severity,
        }
        if label == -1:
            noise.append(point)
        else:
            clusters.setdefault(label, []).append(point)

    cluster_results = []
    high_risk_corridors = []
    for label, points in clusters.items():
        center_lat = sum(p["lat"] for p in points) / len(points)
        center_lon = sum(p["lon"] for p in points) / len(points)
        road_ids = list({p["road_id"] for p in points})
        cluster_info = {
            "cluster_id": int(label),
            "incident_count": len(points),
            "center_lat": round(center_lat, 4),
            "center_lon": round(center_lon, 4),
            "road_ids": road_ids,
            "incidents": points,
        }
        cluster_results.append(cluster_info)
        if len(points) >= min_samples:
            high_risk_corridors.append({
                "corridor_roads": road_ids,
                "incident_density": len(points),
                "center": [round(center_lat, 4), round(center_lon, 4)],
            })

    return {
        "clusters": cluster_results,
        "noise_points": noise,
        "high_risk_corridors": high_risk_corridors,
        "total_active_incidents": len(active),
    }


def recalculate_all_risks(
    roads: List[Road],
    weather: Optional[WeatherObservation] = None,
) -> List[Road]:
    """Apply centralized risk to all roads and update model fields."""
    for road in roads:
        result = calculate_road_risk(road, weather)
        road.accessibility_score = result["accessibility_score"]
        road.disruption_probability = result["disruption_probability"]
        road.risk_level = result["risk_level"]

        if road.status == "BLOCKED":
            road.accessibility_score = 0.0
            road.disruption_probability = 1.0
            road.risk_level = "BLOCKED"
        else:
            road.status = map_status_to_frontend(result["risk_level"])

    return roads
