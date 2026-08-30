from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db, Road
from app.services.road_risk_service import RoadRiskService
from app.services.data_service import DataService
from pydantic import BaseModel

router = APIRouter(prefix="/roads", tags=["roads"])

class RoadResponse(BaseModel):
    road_id: str
    name: str
    distance_km: float
    road_condition: float
    terrain_risk: float
    flood_risk: float
    landslide_history: float
    traffic_level: float
    current_status: str
    risk_score: float
    accessibility_score: float
    geometry: str = None

@router.get("", response_model=List[RoadResponse])
def get_roads(db: Session = Depends(get_db)):
    data_service = DataService(db)
    roads = data_service.get_all_roads()
    return [
        RoadResponse(
            road_id=r.road_id,
            name=r.name,
            distance_km=r.distance_km,
            road_condition=r.road_condition,
            terrain_risk=r.terrain_risk,
            flood_risk=r.flood_risk,
            landslide_history=r.landslide_history,
            traffic_level=r.traffic_level,
            current_status=r.current_status.value,
            risk_score=r.risk_score,
            accessibility_score=r.accessibility_score,
            geometry=r.geometry
        )
        for r in roads
    ]

@router.get("/{road_id}")
def get_road_by_id(road_id: str, db: Session = Depends(get_db)):
    road_risk_service = RoadRiskService(db)
    try:
        result = road_risk_service.calculate_road_risk(road_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/{road_id}/risk")
def get_road_risk(road_id: str, db: Session = Depends(get_db)):
    road_risk_service = RoadRiskService(db)
    try:
        result = road_risk_service.calculate_road_risk(road_id)
        return {
            "road_id": result["road_id"],
            "risk_score": result["risk_score"],
            "accessibility_score": result["accessibility_score"],
            "risk_level": result["risk_level"],
            "disruption_probability": result["disruption_probability"],
            "factors": result["factors"]
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/network/health")
def get_network_health(db: Session = Depends(get_db)):
    road_risk_service = RoadRiskService(db)
    return road_risk_service.get_road_network_health()
