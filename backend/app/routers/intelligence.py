from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from app.database import load_roads, load_vehicles, load_deliveries, load_incidents, load_weather, save_vehicles
from app.services.decision_engine import run_decision_pipeline
from app.services.graph_engine import detect_bottlenecks, calculate_district_connectivity, get_road_edge_attributes
from app.services.routing_engine import find_best_route, find_alternative_routes
from app.services.risk_engine import calculate_road_risk, cluster_incidents_dbscan
from app.services.app_state import is_emergency_mode, set_emergency_mode
from app.services.geofence_service import update_vehicle_location
from app.services.eta_engine import calculate_vehicle_eta

router = APIRouter(tags=["intelligence"])


class EmergencyRouteRequest(BaseModel):
    origin: str = "Guwahati"
    destination: str = "Silchar"
    priority: str = "CRITICAL"
    emergency_mode: bool = True


class VehicleLocationUpdate(BaseModel):
    lat: float
    lon: float


@router.get("/intelligence/state")
def get_intelligence_state():
    """Full system intelligence state from the decision pipeline."""
    result = run_decision_pipeline(trigger="api_query")
    weather = load_weather()
    roads = load_roads()
    incidents = load_incidents()
    return {
        "pipeline": result,
        "weather_mode": "SIMULATION",
        "weather": weather.model_dump(),
        "road_count": len(roads),
        "blocked_roads": [r.road_id for r in roads if r.status == "BLOCKED"],
        "active_incidents": len([i for i in incidents if i.active]),
        "emergency_mode": is_emergency_mode(),
    }


@router.get("/bottlenecks")
def get_bottlenecks(top_n: int = 5):
    roads = load_roads()
    return {"bottlenecks": detect_bottlenecks(roads, top_n=top_n)}


@router.get("/connectivity")
def get_connectivity():
    roads = load_roads()
    return {"districts": calculate_district_connectivity(roads)}


@router.post("/emergency/route")
def emergency_route(request: EmergencyRouteRequest):
    roads = load_roads()
    if request.emergency_mode:
        set_emergency_mode(True)
    route = find_best_route(
        origin=request.origin,
        destination=request.destination,
        roads=roads,
        priority=request.priority,
        emergency_mode=True,
    )
    if route.get("error"):
        raise HTTPException(status_code=404, detail=route["error"])
    return route


@router.post("/emergency/activate")
def activate_emergency():
    return set_emergency_mode(True)


@router.post("/emergency/deactivate")
def deactivate_emergency():
    return set_emergency_mode(False)


@router.get("/roads/{road_id}/risk")
def get_road_risk(road_id: str):
    roads = load_roads()
    road = next((r for r in roads if r.road_id == road_id), None)
    if not road:
        raise HTTPException(status_code=404, detail="Road not found")
    weather = load_weather()
    risk = calculate_road_risk(road, weather)
    edge = get_road_edge_attributes(road)
    return {**risk, "graph_edge": edge}


@router.post("/routes/calculate")
def calculate_route(
    origin: str = "Guwahati",
    destination: str = "Silchar",
    priority: str = "NORMAL",
    emergency: bool = False,
):
    roads = load_roads()
    return find_alternative_routes(origin, destination, roads, priority, emergency)


@router.get("/vehicles/{vehicle_id}/eta")
def get_vehicle_eta(vehicle_id: str):
    vehicles = load_vehicles()
    deliveries = load_deliveries()
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}

    vehicle = next((v for v in vehicles if v.vehicle_id == vehicle_id), None)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    delivery = next((d for d in deliveries if d.vehicle_id == vehicle_id), None)
    if not delivery:
        raise HTTPException(status_code=404, detail="No delivery linked to vehicle")

    return calculate_vehicle_eta(vehicle, delivery, roads_dict)


@router.post("/vehicles/{vehicle_id}/location")
def update_location(vehicle_id: str, body: VehicleLocationUpdate):
    vehicles = load_vehicles()
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}

    vehicle = next((v for v in vehicles if v.vehicle_id == vehicle_id), None)
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")

    result = update_vehicle_location(vehicle, body.lat, body.lon, roads_dict)
    save_vehicles(vehicles)
    return result
