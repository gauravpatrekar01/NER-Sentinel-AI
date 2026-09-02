import asyncio
import time
from typing import Dict, List
from app.database import load_vehicles, save_vehicles, load_roads, load_deliveries, save_deliveries
from app.models.models import Vehicle, Road, Delivery
from app.services.decision_engine import evaluate_vehicle_route
from app.services.delivery_risk_service import recalculate_delivery_risks
from app.database import load_weather

# We need a background task that constantly advances vehicles along their routes
async def run_gps_simulation(interval_seconds: int = 5):
    """
    Background task to simulate vehicle movement along their current routes.
    Runs every `interval_seconds`.
    """
    print("Starting GPS Simulator Background Task...")
    while True:
        try:
            update_vehicle_positions()
        except Exception as e:
            print(f"Error in GPS simulation loop: {e}")
            
        await asyncio.sleep(interval_seconds)

def get_route_coordinates(route_id: str, roads_dict: Dict[str, Road]) -> List[List[float]]:
    coords = []
    for rid in route_id.split(";"):
        road = roads_dict.get(rid)
        if road and road.path:
            coords.extend(road.path)
    return coords

def interpolate_position(coords: List[List[float]], progress: float) -> List[float]:
    """
    Given a list of [lat, lon] coordinates and a progress (0.0 to 1.0),
    interpolate the exact current position.
    """
    if not coords:
        return [0.0, 0.0]
    if progress <= 0.0:
        return coords[0]
    if progress >= 1.0:
        return coords[-1]
        
    # Find the segment
    total_segments = len(coords) - 1
    exact_idx = progress * total_segments
    lower_idx = int(exact_idx)
    upper_idx = min(lower_idx + 1, total_segments)
    
    # Remainder is the interpolation factor between lower and upper
    factor = exact_idx - lower_idx
    
    lat1, lon1 = coords[lower_idx]
    lat2, lon2 = coords[upper_idx]
    
    lat = lat1 + (lat2 - lat1) * factor
    lon = lon1 + (lon2 - lon1) * factor
    
    return [lat, lon]

def update_vehicle_positions():
    vehicles = load_vehicles()
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    weather = load_weather()
    
    # TODO: Read emergency mode from state if available, assuming false for now unless overridden
    is_emergency_mode = False 
    
    updated = False
    
    for veh in vehicles:
        if veh.status == "EN_ROUTE":
            # 1. Evaluate Decision Engine for rerouting
            decision_data = evaluate_vehicle_route(veh, roads_dict, weather, is_emergency_mode)
            
            if decision_data["reroute_required"]:
                veh.current_route_id = decision_data["recommended_route"]
                veh.delivery_risk_pct = decision_data["recommended_route_risk"]
                # Reset progress for new route (simplification for demo)
                veh.progress = 0.0
                
            # 2. Move Vehicle
            # Assuming speed_kmh, convert to rough progress increment
            # A 100km route at 50kmh takes 2 hours.
            # So in 5 seconds (interval), it travels (50 / 3600) * 5 = 0.069 km
            # Progress increment = 0.069 / 100 = 0.00069
            
            route_coords = get_route_coordinates(veh.current_route_id, roads_dict)
            total_distance = sum(roads_dict[rid].length_km for rid in veh.current_route_id.split(";") if rid in roads_dict)
            
            if total_distance > 0:
                distance_moved = (veh.speed_kmh / 3600.0) * 5.0 # 5 seconds
                progress_inc = distance_moved / total_distance
                
                # Slower progress if high risk
                if decision_data["current_route_risk"] > 50.0:
                    progress_inc *= 0.5
                if decision_data["is_blocked"] and not decision_data["reroute_required"]:
                    progress_inc = 0.0 # Stuck!
                    veh.status = "BLOCKED"
                    
                veh.progress = min(1.0, veh.progress + progress_inc)
                
                if veh.progress >= 1.0:
                    veh.status = "COMPLETED"
                    veh.progress = 1.0
                    
                # 3. Update Lat/Lon visually
                new_pos = interpolate_position(route_coords, veh.progress)
                veh.current_lat = new_pos[0]
                veh.current_lon = new_pos[1]
                
            # Formatting ETA back to string (Current Hour + ETA mins)
            # Just store the raw string for the UI to display
            # We'll attach the reasoning string so the UI can read it
            veh.delay_reason = " | ".join(decision_data["reasons"]) if decision_data["reasons"] else ""
            
            updated = True
            
    if updated:
        save_vehicles(vehicles)
        
        # Also recalculate deliveries ETAs and risks based on updated vehicles
        deliveries = load_deliveries()
        vehicles_dict = {v.vehicle_id: v for v in vehicles}
        recalculate_delivery_risks(deliveries, vehicles_dict, roads_dict)
        save_deliveries(deliveries)
