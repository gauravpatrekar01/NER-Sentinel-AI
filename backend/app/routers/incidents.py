from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.database import load_incidents
from app.models.models import Incident
from app.services.incident_service import register_incident_and_cascade

router = APIRouter(prefix="/incidents", tags=["incidents"])

class IncidentCreateSchema(BaseModel):
    road_id: str
    lat: float
    lon: float
    type: str
    severity: str
    description: str
    photo_url: Optional[str] = None
    optimize_immediately: Optional[bool] = True

@router.get("", response_model=List[Incident])
def get_incidents():
    return load_incidents()

@router.post("")
def create_incident(schema: IncidentCreateSchema):
    try:
        res = register_incident_and_cascade(
            road_id=schema.road_id,
            lat=schema.lat,
            lon=schema.lon,
            incident_type=schema.type,
            severity=schema.severity,
            description=schema.description,
            photo_url=schema.photo_url,
            optimize_immediately=schema.optimize_immediately
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error executing incident cascade: {str(e)}")
