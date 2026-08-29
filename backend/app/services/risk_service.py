from typing import List
from app.database import load_roads, save_roads, load_weather, load_incidents
from app.ml.predictor import predict_road_risk
from app.models.models import Road

def recalculate_all_roads_risk() -> List[Road]:
    roads = load_roads()
    weather = load_weather()
    incidents = load_incidents()
    
    # Map active incidents to roads
    # If a road has multiple active incidents, we take the highest severity
    severity_map = {"None": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    road_incidents = {}
    road_blocked = {}
    
    for inc in incidents:
        if inc.active:
            # If the incident type is Landslide or severity is CRITICAL, mark as blocked
            if inc.type.lower() == "landslide" or inc.severity == "CRITICAL" or inc.type.lower() == "flood" and inc.severity == "HIGH":
                road_blocked[inc.road_id] = True
            
            sev_val = severity_map.get(inc.severity, 0)
            if inc.road_id not in road_incidents or sev_val > road_incidents[inc.road_id]["val"]:
                road_incidents[inc.road_id] = {
                    "val": sev_val,
                    "severity": inc.severity
                }
                
    for road in roads:
        # Get active incident severity
        incident_info = road_incidents.get(road.road_id, {"val": 0, "severity": "None"})
        road.field_incident_severity = incident_info["severity"] if incident_info["severity"] != "None" else None
        
        # Weather influence: road rainfall is baseline road rainfall + current regional weather rainfall
        # (This links weather changes directly to the road risk engine!)
        effective_rainfall = max(road.rainfall_mm, weather.rainfall_mm)
        
        # Run ML prediction
        prediction = predict_road_risk(
            rainfall=effective_rainfall,
            terrain_risk=road.terrain_risk,
            historical_incidents=road.historical_incidents,
            road_condition=road.road_condition,
            traffic=road.traffic_level,
            flood_risk=road.flood_risk,
            landslide_history=road.landslide_history,
            field_incident_severity=incident_info["val"]
        )
        
        # Apply ML values
        road.accessibility_score = prediction["accessibility_score"]
        road.disruption_probability = prediction["disruption_probability"]
        road.risk_level = prediction["risk_level"]
        
        # Apply blockage override if active block exists
        if road_blocked.get(road.road_id, False) or road.status == "BLOCKED":
            road.status = "BLOCKED"
            road.accessibility_score = 0
            road.disruption_probability = 1.0
            road.risk_level = "BLOCKED"
        else:
            # If there was a block but now cleared, reset to prediction state
            if road.status == "BLOCKED":
                road.status = "OPEN"  # cleared
            
            # Map risk level back to status if it's open
            if road.risk_level == "CRITICAL":
                road.status = "HIGH RISK"
            elif road.risk_level == "HIGH":
                road.status = "HIGH RISK"
            elif road.risk_level == "MODERATE":
                road.status = "MODERATE"
            else:
                road.status = "OPEN"
                
    save_roads(roads)
    return roads
