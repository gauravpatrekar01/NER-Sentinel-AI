from typing import List
from app.database import load_roads, save_roads, load_weather, load_incidents
from app.models.models import Road
from app.services.risk_engine import calculate_road_risk, recalculate_all_risks
from app.services.graph_engine import invalidate_graph_cache


def recalculate_all_roads_risk() -> List[Road]:
    roads = load_roads()
    weather = load_weather()
    incidents = load_incidents()

    severity_map = {"None": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    road_incidents = {}
    road_blocked = {}

    for inc in incidents:
        if inc.active:
            if (
                inc.type.lower() == "landslide"
                or inc.severity == "CRITICAL"
                or (inc.type.lower() == "flood" and inc.severity == "HIGH")
            ):
                road_blocked[inc.road_id] = True

            sev_val = severity_map.get(inc.severity, 0)
            if inc.road_id not in road_incidents or sev_val > road_incidents[inc.road_id]["val"]:
                road_incidents[inc.road_id] = {"val": sev_val, "severity": inc.severity}

    for road in roads:
        incident_info = road_incidents.get(road.road_id, {"val": 0, "severity": "None"})
        road.field_incident_severity = incident_info["severity"] if incident_info["severity"] != "None" else None

        result = calculate_road_risk(road, weather)
        road.accessibility_score = result["accessibility_score"]
        road.disruption_probability = result["disruption_probability"]
        road.risk_level = result["risk_level"]

        if road_blocked.get(road.road_id, False):
            road.status = "BLOCKED"
            road.accessibility_score = 0
            road.disruption_probability = 1.0
            road.risk_level = "BLOCKED"
        elif road.status != "BLOCKED":
            road.status = result["status"]

    invalidate_graph_cache()
    save_roads(roads)
    return roads
