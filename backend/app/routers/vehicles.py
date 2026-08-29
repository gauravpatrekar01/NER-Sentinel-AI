from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.database import load_vehicles, save_vehicles, load_roads
from app.models.models import Vehicle
from app.services.telemetry_service import update_vehicle_positions

router = APIRouter(prefix="/vehicles", tags=["vehicles"])

@router.get("", response_model=List[Vehicle])
def get_vehicles():
    vehicles = load_vehicles()
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    
    # Update telemetry position before returning
    updated_vehicles = update_vehicle_positions(vehicles, roads_dict)
    save_vehicles(updated_vehicles)
    return updated_vehicles

@router.get("/{vehicle_id}", response_model=Vehicle)
def get_vehicle(vehicle_id: str):
    vehicles = load_vehicles()
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    
    updated_vehicles = update_vehicle_positions(vehicles, roads_dict)
    save_vehicles(updated_vehicles)
    
    vehicle = next((v for v in updated_vehicles if v.vehicle_id == vehicle_id), None)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle

@router.get("/{vehicle_id}/telemetry")
def get_vehicle_telemetry(vehicle_id: str):
    vehicles = load_vehicles()
    vehicle = next((v for v in vehicles if v.vehicle_id == vehicle_id), None)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
        
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    
    # Construct complete coordinate path of the route
    route_segments = vehicle.current_route_id.split(";")
    full_path = []
    
    for rid in route_segments:
        road = roads_dict.get(rid)
        if road and road.path:
            if full_path and full_path[-1] == road.path[0]:
                full_path.extend(road.path[1:])
            else:
                full_path.extend(road.path)
                
    return {
        "vehicle_id": vehicle_id,
        "current_route_id": vehicle.current_route_id,
        "path": full_path
    }
