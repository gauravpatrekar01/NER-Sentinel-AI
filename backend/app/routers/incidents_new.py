from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db, Incident, IncidentType, IncidentSeverity
from app.services.incident_service_new import IncidentService
from app.services.data_service import DataService
from pydantic import BaseModel

router = APIRouter(prefix="/incidents", tags=["incidents"])

class IncidentCreateSchema(BaseModel):
    road_id: str
    lat: float
    lng: float
    type: str
    severity: str
    description: str
    photo_url: str = None
    optimize_immediately: bool = True

class IncidentResponse(BaseModel):
    incident_id: str
    road_id: str
    lat: float
    lng: float
    type: str
    severity: str
    description: str
    photo_url: str
    timestamp: str
    active: bool

@router.get("", response_model=List[IncidentResponse])
def get_incidents(active_only: bool = False, db: Session = Depends(get_db)):
    data_service = DataService(db)
    incidents = data_service.get_all_incidents(active_only=active_only)
    return [
        IncidentResponse(
            incident_id=i.incident_id,
            road_id=i.road_id,
            lat=i.lat,
            lng=i.lng,
            type=i.type.value,
            severity=i.severity.value,
            description=i.description,
            photo_url=i.photo_url,
            timestamp=i.timestamp.isoformat(),
            active=i.active
        )
        for i in incidents
    ]

@router.post("")
def create_incident(schema: IncidentCreateSchema, db: Session = Depends(get_db)):
    incident_service = IncidentService(db)
    
    try:
        incident_type = IncidentType(schema.type)
        incident_severity = IncidentSeverity(schema.severity)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid incident type or severity: {e}")
    
    incident_data = {
        "road_id": schema.road_id,
        "lat": schema.lat,
        "lng": schema.lng,
        "type": incident_type,
        "severity": incident_severity,
        "description": schema.description,
        "photo_url": schema.photo_url,
        "active": True
    }
    
    try:
        incident = incident_service.create_incident(incident_data)
        result = incident_service.process_incident(incident.incident_id, schema.optimize_immediately)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing incident: {str(e)}")

@router.post("/{incident_id}/process")
def process_incident(incident_id: str, optimize_immediately: bool = True, db: Session = Depends(get_db)):
    incident_service = IncidentService(db)
    try:
        result = incident_service.process_incident(incident_id, optimize_immediately)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing incident: {str(e)}")

@router.post("/{incident_id}/resolve")
def resolve_incident(incident_id: str, db: Session = Depends(get_db)):
    incident_service = IncidentService(db)
    try:
        result = incident_service.resolve_incident(incident_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error resolving incident: {str(e)}")
