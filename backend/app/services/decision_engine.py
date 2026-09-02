"""
Centralized Decision Engine orchestrating the full intelligence pipeline:
DATA -> RISK -> GRAPH -> ROUTING -> ETA -> ALERT -> DECISION
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from app.database import (
    load_roads,
    save_roads,
    load_vehicles,
    save_vehicles,
    load_deliveries,
    save_deliveries,
    load_incidents,
    load_weather,
    load_alerts,
)
from app.models.models import Road, Vehicle, Delivery, WeatherObservation
from app.services.app_state import is_emergency_mode
from app.services.graph_engine import invalidate_graph_cache, build_road_graph
from app.services.risk_engine import calculate_road_risk, cluster_incidents_dbscan, recalculate_all_risks
from app.services.routing_engine import find_best_route, calculate_route_cost
from app.services.geofence_service import calculate_route_deviation
from app.services.alert_engine import evaluate_alerts, generate_alert
from app.services.eta_engine import calculate_vehicle_eta
from app.services.delivery_risk_service import recalculate_delivery_risks
from app.ml.disruption_model import predict_disruption
from app.ml.delay_model import predict_delay


def run_decision_pipeline(
    trigger: str = "periodic",
    incident_road_id: Optional[str] = None,
    emergency_mode: Optional[bool] = None,
) -> Dict[str, Any]:
    """
    Execute the full decision pipeline and return system recommendations.
    """
    if emergency_mode is None:
        emergency_mode = is_emergency_mode()

    weather = load_weather()
    incidents = load_incidents()
    roads = load_roads()
    vehicles = load_vehicles()
    deliveries = load_deliveries()

    # 1. RISK ENGINE
    roads = recalculate_all_risks(roads, weather)
    save_roads(roads)
    roads_dict = {r.road_id: r for r in roads}

    # 2. GRAPH UPDATE
    invalidate_graph_cache()
    graph = build_road_graph(roads)

    # 3. DBSCAN incident clustering
    clusters = cluster_incidents_dbscan(incidents)

    decisions: List[Dict[str, Any]] = []
    rerouted_vehicles: List[str] = []
    route_deviations: List[Dict[str, Any]] = []

    # 4. Per-vehicle: ROUTING + ETA + GEOFENCE
    for veh in vehicles:
        if veh.status not in ("EN_ROUTE", "DELAYED", "BLOCKED"):
            continue

        deviation = calculate_route_deviation(veh, roads_dict)
        route_deviations.append(deviation)

        route_segments = veh.current_route_id.split(";")
        is_blocked = any(
            roads_dict.get(rid) and roads_dict[rid].status == "BLOCKED"
            for rid in route_segments
        )
        max_risk = max(
            (roads_dict[rid].disruption_probability * 100 for rid in route_segments if roads_dict.get(rid)),
            default=0,
        )

        should_reroute = is_blocked or (max_risk > 60 and not is_blocked)

        if should_reroute:
            alt = find_best_route(
                origin=veh.origin,
                destination=veh.destination,
                roads=roads,
                priority="CRITICAL" if "medicine" in veh.cargo.lower() or "oxygen" in veh.cargo.lower() else "NORMAL",
                emergency_mode=emergency_mode,
                blocked_roads=[rid for rid, r in roads_dict.items() if r.status == "BLOCKED"],
            )
            if alt.get("road_ids") and not alt.get("is_blocked"):
                new_route = ";".join(alt["road_ids"])
                if new_route != veh.current_route_id:
                    old_route = veh.current_route_id
                    veh.current_route_id = new_route
                    veh.progress = 0.0
                    rerouted_vehicles.append(veh.vehicle_id)
                    decisions.append({
                        "action": "REROUTE",
                        "vehicle_id": veh.vehicle_id,
                        "from_route": old_route,
                        "to_route": new_route,
                        "reason": alt.get("reason", "Lower risk alternate selected"),
                    })
                    generate_alert(
                        alert_type="ROUTE_UPDATED",
                        message=f"Vehicle {veh.vehicle_id} rerouted: {alt.get('reason', '')}",
                        severity="CRITICAL" if emergency_mode else "WARNING",
                        vehicle_id=veh.vehicle_id,
                        recommended_action="Follow updated route",
                    )

        if deviation.get("route_deviation"):
            decisions.append({
                "action": "ROUTE_DEVIATION",
                "vehicle_id": veh.vehicle_id,
                "distance_km": deviation["distance_from_route_km"],
            })

    save_vehicles(vehicles)

    # 5. ETA + delivery risk recalculation
    vehicles_dict = {v.vehicle_id: v for v in load_vehicles()}
    deliveries = load_deliveries()
    for delivery in deliveries:
        veh = vehicles_dict.get(delivery.vehicle_id)
        if not veh:
            continue
        eta_result = calculate_vehicle_eta(veh, delivery, roads_dict)
        delivery.eta_str = eta_result["eta_str"]
        delivery.delay_reason = eta_result.get("explanation", "")
        if eta_result.get("delay_minutes", 0) > 5:
            delivery.status = "DELAYED"
    recalculate_delivery_risks(deliveries, vehicles_dict, roads_dict)
    save_deliveries(deliveries)

    # 6. ML predictions (aggregate for corridor)
    r204 = roads_dict.get("R-204")
    ml_features = {
        "rainfall": weather.rainfall_mm,
        "traffic": r204.traffic_level if r204 else 50,
        "road_condition": r204.road_condition if r204 else 5,
        "road_risk": (r204.disruption_probability * 100) if r204 else 50,
        "historical_incidents": r204.historical_incidents if r204 else 2,
        "incident_count": len([i for i in incidents if i.active]),
        "terrain_risk": r204.terrain_risk if r204 else 50,
        "vehicle_speed": 40,
        "distance": 290,
        "historical_travel_time": 5.5,
    }
    disruption_pred = predict_disruption(ml_features)
    delay_pred = predict_delay(ml_features)
    ml_combined = {**disruption_pred, **delay_pred}

    # 7. ALERT ENGINE
    alerts = evaluate_alerts(
        roads=roads,
        vehicles=vehicles,
        deliveries=deliveries,
        ml_predictions=ml_combined,
        route_deviations=route_deviations,
        emergency_mode=emergency_mode,
    )

    # 8. DECISIONS summary
    if incident_road_id and roads_dict.get(incident_road_id):
        road = roads_dict[incident_road_id]
        if road.status == "BLOCKED":
            decisions.insert(0, {
                "action": "MARK_BLOCKED",
                "road_id": incident_road_id,
                "reason": f"{incident_road_id} marked BLOCKED due to incident",
            })

    if weather.rainfall_mm > 100:
        decisions.append({
            "action": "WEATHER_WARNING",
            "rainfall_mm": weather.rainfall_mm,
            "reason": "Heavy rainfall increasing corridor risk",
        })

    return {
        "trigger": trigger,
        "timestamp": time.time(),
        "decisions": decisions,
        "rerouted_vehicles": rerouted_vehicles,
        "incident_clusters": clusters,
        "ml_predictions": {
            "disruption": disruption_pred,
            "delay": delay_pred,
        },
        "alerts_generated": len(alerts),
        "emergency_mode": emergency_mode,
        "summary": _build_summary(decisions, rerouted_vehicles, weather, roads_dict),
    }


def _build_summary(
    decisions: List[Dict[str, Any]],
    rerouted: List[str],
    weather: WeatherObservation,
    roads_dict: Dict[str, Road],
) -> str:
    parts = []
    blocked = [rid for rid, r in roads_dict.items() if r.status == "BLOCKED"]
    if blocked:
        parts.append(f"Roads blocked: {', '.join(blocked)}")
    if rerouted:
        parts.append(f"Rerouted {len(rerouted)} vehicle(s)")
    if weather.rainfall_mm > 80:
        parts.append(f"Heavy rainfall ({weather.rainfall_mm}mm) affecting risk")
    if not parts:
        parts.append("Normal operations - no critical actions required")
    return "; ".join(parts)


def evaluate_vehicle_route(
    vehicle: Vehicle,
    roads_dict: Dict[str, Road],
    weather: WeatherObservation,
    emergency_mode: bool,
) -> Dict[str, Any]:
    """Evaluate a single vehicle for rerouting decision (used by GPS simulator)."""
    current_route = vehicle.current_route_id.split(";")
    blocked_roads = [rid for rid, r in roads_dict.items() if r.status == "BLOCKED"]

    current_metrics = calculate_route_cost(
        current_route, roads_dict, emergency_mode, "CRITICAL" if emergency_mode else "NORMAL"
    )

    alt = find_best_route(
        origin=vehicle.origin,
        destination=vehicle.destination,
        roads=list(roads_dict.values()),
        priority="CRITICAL" if emergency_mode else "NORMAL",
        emergency_mode=emergency_mode,
        blocked_roads=blocked_roads,
    )

    alt_route_ids = alt.get("road_ids", [])
    alt_metrics = calculate_route_cost(
        alt_route_ids, roads_dict, emergency_mode, "CRITICAL" if emergency_mode else "NORMAL"
    ) if alt_route_ids else current_metrics

    decision = "PROCEED"
    reasons: List[str] = []
    recommended_route = vehicle.current_route_id
    recommended_eta = current_metrics.get("eta_minutes", 0)
    recommended_risk = current_metrics.get("risk_score", 0)
    alert_required = False

    if current_metrics["is_blocked"]:
        decision = "REROUTE"
        reasons.append("Current route is BLOCKED by a critical incident.")
        alert_required = True
        if alt_route_ids:
            recommended_route = ";".join(alt_route_ids)
            recommended_eta = alt_metrics.get("eta_minutes", 0)
            recommended_risk = alt_metrics.get("risk_score", 0)
            reasons.append(alt.get("reason", "Alternative route selected via A* optimization"))
    elif current_metrics.get("risk_score", 0) > 60:
        if alt_metrics.get("risk_score", 100) < current_metrics.get("risk_score", 0) - 15 and not alt_metrics.get("is_blocked"):
            decision = "REROUTE"
            reasons.append(
                f"Current route risk ({current_metrics['risk_score']:.0f}%) exceeds threshold. "
                f"Alternative is safer ({alt_metrics['risk_score']:.0f}%)."
            )
            if emergency_mode:
                reasons.append("Emergency protocol demands lowest-risk corridor for critical supplies.")
            alert_required = True
            if alt_route_ids:
                recommended_route = ";".join(alt_route_ids)
                recommended_eta = alt_metrics.get("eta_minutes", 0)
                recommended_risk = alt_metrics.get("risk_score", 0)
        else:
            reasons.append("Current route is high risk, but alternative is also unsafe or blocked.")

    return {
        "decision": decision,
        "recommended_route": recommended_route,
        "current_route_risk": current_metrics.get("risk_score", 0),
        "recommended_route_risk": alt_metrics.get("risk_score", 0) if decision == "REROUTE" else current_metrics.get("risk_score", 0),
        "current_eta_mins": current_metrics.get("eta_minutes", 0),
        "recommended_eta_mins": recommended_eta,
        "reroute_required": decision == "REROUTE",
        "alert_required": alert_required,
        "reasons": reasons,
        "is_blocked": current_metrics["is_blocked"],
    }
