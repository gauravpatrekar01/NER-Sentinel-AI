"""
Hybrid rule + ML alert engine.
Combines deterministic thresholds with ML prediction outputs.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional

from app.database import load_alerts, save_alerts
from app.models.models import Alert, Road, Vehicle, Delivery


def _make_alert(
    alert_type: str,
    severity: str,
    title: str,
    message: str,
    road_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    recommended_action: str = "",
) -> Alert:
    full_message = message
    if recommended_action:
        full_message = f"{message} | Action: {recommended_action}"

    return Alert(
        alert_id=f"AL-{uuid.uuid4().hex[:6].upper()}",
        type=alert_type,
        message=full_message,
        timestamp=time.time(),
        severity=severity,
        read=False,
    )


def persist_alert(alert: Alert) -> Alert:
    alerts = load_alerts()
    alerts.insert(0, alert)
    save_alerts(alerts[:50])
    return alert


def generate_alert(
    alert_type: str,
    message: str,
    severity: str = "WARNING",
    title: Optional[str] = None,
    road_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    recommended_action: str = "",
) -> Alert:
    """Backward-compatible alert generation."""
    alert = _make_alert(
        alert_type=alert_type,
        severity=severity,
        title=title or alert_type.replace("_", " ").title(),
        message=message,
        road_id=road_id,
        vehicle_id=vehicle_id,
        recommended_action=recommended_action,
    )
    return persist_alert(alert)


def evaluate_alerts(
    roads: List[Road],
    vehicles: Optional[List[Vehicle]] = None,
    deliveries: Optional[List[Delivery]] = None,
    ml_predictions: Optional[Dict[str, Any]] = None,
    route_deviations: Optional[List[Dict[str, Any]]] = None,
    emergency_mode: bool = False,
) -> List[Alert]:
    """
    Rule + ML hybrid alert evaluation.
    Rules:
    - risk > 80 -> CRITICAL
    - road BLOCKED -> ROAD_BLOCKED
    - predicted_delay > 30 min -> DELAY
    - route deviation -> ROUTE_DEVIATION
    - emergency route affected -> EMERGENCY_ROUTE
    """
    generated: List[Alert] = []
    roads_dict = {r.road_id: r for r in roads}

    for road in roads:
        risk_pct = road.disruption_probability * 100.0
        if road.status == "BLOCKED":
            alert = _make_alert(
                alert_type="ROAD_BLOCKED",
                severity="CRITICAL",
                title=f"Route {road.road_id} Blocked",
                message=f"{road.name} is BLOCKED and impassable.",
                road_id=road.road_id,
                recommended_action="Recalculate route immediately",
            )
            generated.append(persist_alert(alert))
        elif risk_pct > 80:
            alert = _make_alert(
                alert_type="HIGH_DISRUPTION_RISK",
                severity="CRITICAL",
                title=f"Critical Risk on {road.road_id}",
                message=f"Road risk exceeded 80% ({risk_pct:.0f}%). {road.name} requires caution.",
                road_id=road.road_id,
                recommended_action="Consider alternate corridor",
            )
            generated.append(persist_alert(alert))
        elif risk_pct > 60:
            alert = _make_alert(
                alert_type="HIGH_RISK_CORRIDOR",
                severity="WARNING",
                title=f"Elevated Risk on {road.road_id}",
                message=f"Road risk at {risk_pct:.0f}% on {road.name}.",
                road_id=road.road_id,
                recommended_action="Monitor conditions closely",
            )
            generated.append(persist_alert(alert))

    if ml_predictions:
        prob = ml_predictions.get("probability", 0)
        if prob > 0.7:
            alert = _make_alert(
                alert_type="HIGH_DISRUPTION_RISK",
                severity="CRITICAL" if prob > 0.85 else "WARNING",
                title="ML Disruption Prediction",
                message=f"ML predicts {prob * 100:.0f}% disruption probability ({ml_predictions.get('risk_level', 'HIGH')}).",
                recommended_action="Prepare contingency routing",
            )
            generated.append(persist_alert(alert))

        delay_min = ml_predictions.get("predicted_delay_minutes", 0)
        if delay_min > 30:
            alert = _make_alert(
                alert_type="VEHICLE_DELAY",
                severity="WARNING" if delay_min < 60 else "CRITICAL",
                title="Predicted Delivery Delay",
                message=f"Predicted delay of {delay_min} minutes (probability {ml_predictions.get('delay_probability', 0) * 100:.0f}%).",
                recommended_action="Notify stakeholders and reroute if possible",
            )
            generated.append(persist_alert(alert))

    if route_deviations:
        for dev in route_deviations:
            if dev.get("route_deviation"):
                alert = _make_alert(
                    alert_type="ROUTE_DEVIATION",
                    severity="WARNING",
                    title=f"Vehicle {dev['vehicle_id']} Off Route",
                    message=f"Vehicle deviated {dev['distance_from_route_km']:.1f}km from planned route (threshold {dev['threshold_km']}km).",
                    vehicle_id=dev["vehicle_id"],
                    recommended_action="Verify driver status and recalculate route",
                )
                generated.append(persist_alert(alert))

    if emergency_mode and vehicles:
        emergency_cargo = ("medicine", "medical", "oxygen", "food", "water", "essential")
        for veh in vehicles:
            if veh.status not in ("EN_ROUTE", "DELAYED"):
                continue
            route_segments = veh.current_route_id.split(";")
            blocked_on_route = [rid for rid in route_segments if roads_dict.get(rid) and roads_dict[rid].status == "BLOCKED"]
            is_emergency_cargo = any(k in veh.cargo.lower() for k in emergency_cargo)
            if blocked_on_route and is_emergency_cargo:
                alert = _make_alert(
                    alert_type="EMERGENCY_ROUTE",
                    severity="CRITICAL",
                    title=f"Emergency Route Affected: {veh.vehicle_id}",
                    message=f"Emergency cargo vehicle blocked by {blocked_on_route[0]}. Cargo: {veh.cargo}.",
                    vehicle_id=veh.vehicle_id,
                    road_id=blocked_on_route[0],
                    recommended_action="Immediate reroute via safest available corridor",
                )
                generated.append(persist_alert(alert))

    if deliveries:
        for d in deliveries:
            if d.priority == "CRITICAL" and d.delivery_risk_pct > 80:
                alert = _make_alert(
                    alert_type="CRITICAL_DELIVERY_DELAY",
                    severity="CRITICAL",
                    title=f"Critical Delivery at Risk: {d.delivery_id}",
                    message=f"{d.cargo} delivery risk at {d.delivery_risk_pct}%.",
                    vehicle_id=d.vehicle_id,
                    recommended_action="Escalate to emergency routing protocol",
                )
                generated.append(persist_alert(alert))

    return generated


def clear_all_alerts() -> None:
    save_alerts([])
