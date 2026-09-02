import time
import uuid
from typing import List, Dict, Any
from app.database import (
    load_incidents, save_incidents, load_roads, save_roads,
    load_vehicles, save_vehicles, load_deliveries, save_deliveries,
)
from app.models.models import Incident
from app.services.risk_service import recalculate_all_roads_risk
from app.services.decision_engine import run_decision_pipeline
from app.services.alert_engine import generate_alert
from app.services.geofence_service import check_geofence


INCIDENT_TYPE_SEVERITY = {
    "landslide": ("Landslide", "CRITICAL", True),
    "flood": ("Flood", "HIGH", True),
    "road damage": ("Road Damage", "MEDIUM", False),
    "bridge issue": ("Bridge Issue", "CRITICAL", True),
    "traffic blockage": ("Traffic Blockage", "HIGH", False),
}


def classify_incident(incident_type: str, severity: str) -> Dict[str, Any]:
    """Classify incident type and determine if road should be blocked."""
    type_lower = incident_type.lower()
    should_block = severity in ("HIGH", "CRITICAL") or type_lower in ("landslide", "bridge issue")
    if type_lower == "landslide":
        should_block = True
    return {
        "type": incident_type,
        "severity": severity,
        "should_block_road": should_block,
        "classification": f"{incident_type}/{severity}",
    }


def identify_affected_road(road_id: str, lat: float, lon: float, roads_dict: Dict) -> str:
    """Identify affected road - use provided road_id or geofence nearest road."""
    if road_id in roads_dict:
        return road_id
    # Find nearest road by checking geofence around path points
    min_dist = float("inf")
    nearest = road_id
    for rid, road in roads_dict.items():
        if road.path:
            for pt in road.path:
                gf = check_geofence(lat, lon, pt[0], pt[1], 5.0)
                if gf["distance_km"] < min_dist:
                    min_dist = gf["distance_km"]
                    nearest = rid
    return nearest


def register_incident_and_cascade(
    road_id: str,
    lat: float,
    lon: float,
    incident_type: str,
    severity: str,
    description: str,
    photo_url: str = None,
    optimize_immediately: bool = True,
) -> Dict[str, Any]:
    """
    Full incident intelligence chain:
    INCIDENT -> CLASSIFY -> SEVERITY -> GEO -> AFFECTED ROAD ->
    UPDATE STATUS -> RISK -> GRAPH -> VEHICLES -> ROUTES -> ETA -> ALERT
    """
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}

    # GEO + AFFECTED ROAD
    affected_road_id = identify_affected_road(road_id, lat, lon, roads_dict)

    # CLASSIFY + SEVERITY
    classification = classify_incident(incident_type, severity)

    # CREATE INCIDENT
    incidents = load_incidents()
    inc_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
    new_incident = Incident(
        incident_id=inc_id,
        road_id=affected_road_id,
        lat=lat,
        lon=lon,
        type=incident_type,
        severity=severity,
        description=description,
        photo_url=photo_url,
        timestamp=time.time(),
        active=True,
    )
    incidents.append(new_incident)
    save_incidents(incidents)

    # UPDATE ROAD STATUS
    road_blocked = False
    if affected_road_id in roads_dict and classification["should_block_road"]:
        roads_dict[affected_road_id].status = "BLOCKED"
        road_blocked = True
        save_roads(list(roads_dict.values()))

    # RECALCULATE RISK + GRAPH (via risk_service)
    recalculate_all_roads_risk()

    # Identify affected vehicles/deliveries before pipeline
    vehicles = load_vehicles()
    deliveries = load_deliveries()
    affected_vehicles = []
    affected_deliveries = []

    if road_blocked:
        for veh in vehicles:
            if veh.status == "COMPLETED":
                continue
            if affected_road_id in veh.current_route_id.split(";"):
                affected_vehicles.append(veh)

        affected_veh_ids = [v.vehicle_id for v in affected_vehicles]
        for deliv in deliveries:
            if deliv.vehicle_id in affected_veh_ids and deliv.status != "DELIVERED":
                affected_deliveries.append(deliv)

        generate_alert(
            alert_type="ROAD_BLOCKED",
            message=f"Road {affected_road_id} ({roads_dict[affected_road_id].name}) is BLOCKED due to {incident_type}. "
                    f"{len(affected_vehicles)} vehicles and {len(affected_deliveries)} deliveries affected.",
            severity="CRITICAL",
            road_id=affected_road_id,
            recommended_action="Recalculate route immediately",
        )

    # FULL DECISION PIPELINE: routes, ETA, alerts
    pipeline_result = {}
    if optimize_immediately:
        pipeline_result = run_decision_pipeline(
            trigger="incident",
            incident_road_id=affected_road_id,
        )

    return {
        "incident_id": inc_id,
        "classification": classification,
        "affected_road_id": affected_road_id,
        "road_blocked": road_blocked,
        "affected_vehicles_count": len(affected_vehicles),
        "affected_deliveries_count": len(affected_deliveries),
        "pipeline": pipeline_result,
    }
