from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db, Vehicle
from app.services.data_service import DataService
from pydantic import BaseModel

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

class VehicleResponse(BaseModel):
    vehicle_id: str
    vehicle_type: str
    capacity: float
    current_lat: float
    current_lng: float
    current_road_id: str
    speed_kmh: float
    status: str

class VehicleTelemetryResponse(BaseModel):
    vehicle_id: str
    timestamp: str
    lat: float
    lng: float
    speed_kmh: float
    heading: float

@router.get("", response_model=List[VehicleResponse])
def get_vehicles(db: Session = Depends(get_db)):
    data_service = DataService(db)
    vehicles = data_service.get_all_vehicles()
    return [
        VehicleResponse(
            vehicle_id=v.vehicle_id,
            vehicle_type=v.vehicle_type,
            capacity=v.capacity,
            current_lat=v.current_lat,
            current_lng=v.current_lng,
            current_road_id=v.current_road_id,
            speed_kmh=v.speed_kmh,
            status=v.status.value
        )
        for v in vehicles
    ]

@router.get("/{vehicle_id}")
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    data_service = DataService(db)
    vehicle = data_service.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    return VehicleResponse(
        vehicle_id=vehicle.vehicle_id,
        vehicle_type=vehicle.vehicle_type,
        capacity=vehicle.capacity,
        current_lat=vehicle.current_lat,
        current_lng=vehicle.current_lng,
        current_road_id=vehicle.current_road_id,
        speed_kmh=vehicle.speed_kmh,
        status=vehicle.status.value
    )

@router.get("/{vehicle_id}/telemetry")
def get_vehicle_telemetry(vehicle_id: str, db: Session = Depends(get_db)):
    data_service = DataService(db)
    telemetry_list = data_service.get_vehicle_telemetry(vehicle_id, limit=10)
    
    return [
        VehicleTelemetryResponse(
            vehicle_id=t.vehicle_id,
            timestamp=t.timestamp.isoformat(),
            lat=t.lat,
            lng=t.lng,
            speed_kmh=t.speed_kmh,
            heading=t.heading
        )
        for t in telemetry_list
    ]

@router.post("/{vehicle_id}/telemetry")
def add_vehicle_telemetry(vehicle_id: str, lat: float, lng: float, speed_kmh: float, heading: float = 0.0, db: Session = Depends(get_db)):
    data_service = DataService(db)
    vehicle = data_service.get_vehicle_by_id(vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    
    telemetry = data_service.add_vehicle_telemetry(vehicle_id, lat, lng, speed_kmh, heading)
    
    # Update vehicle current position
    data_service.update_vehicle(vehicle_id, current_lat=lat, current_lng=lng)
    
    return {"status": "success", "telemetry_id": telemetry.id}
