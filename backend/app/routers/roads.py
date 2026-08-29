from fastapi import APIRouter, HTTPException
from typing import List
from app.database import load_roads
from app.models.models import Road
from app.ml.predictor import predict_road_risk

router = APIRouter(prefix="/roads", tags=["roads"])

@router.get("", response_model=List[Road])
def get_roads():
    return load_roads()

@router.get("/{road_id}")
def get_road_by_id(road_id: str):
    roads = load_roads()
    road = next((r for r in roads if r.road_id == road_id), None)
    if not road:
        raise HTTPException(status_code=404, detail="Road segment not found")
        
    # Get ML prediction details to return factors for UI accessibility analysis panel
    # We map field incident severity to values 0-4
    severity_map = {"None": 0, "LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
    sev_val = severity_map.get(road.field_incident_severity or "None", 0)
    
    pred = predict_road_risk(
        rainfall=road.rainfall_mm,
        terrain_risk=road.terrain_risk,
        historical_incidents=road.historical_incidents,
        road_condition=road.road_condition,
        traffic=road.traffic_level,
        flood_risk=road.flood_risk,
        landslide_history=road.landslide_history,
        field_incident_severity=sev_val
    )
    
    # Merge ML output into response
    road_data = road.model_dump()
    road_data["factors"] = pred["factors"]
    road_data["disruption_probability"] = pred["disruption_probability"]
    road_data["accessibility_score"] = pred["accessibility_score"]
    road_data["risk_level"] = pred["risk_level"]
    
    # If blocked, enforce status
    if road.status == "BLOCKED":
        road_data["accessibility_score"] = 0
        road_data["disruption_probability"] = 1.0
        road_data["risk_level"] = "BLOCKED"
        
    return road_data
