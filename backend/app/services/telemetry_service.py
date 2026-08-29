import time
from typing import List, Dict
from app.models.models import Vehicle, Road

def interpolate_position(path: List[List[float]], progress: float) -> List[float]:
    if not path:
        return [0.0, 0.0]
    if len(path) == 1:
        return path[0]
        
    # Scale progress [0.0, 1.0] to segment index space
    idx_float = progress * (len(path) - 1)
    idx = int(idx_float)
    frac = idx_float - idx
    
    if idx >= len(path) - 1:
        return path[-1]
        
    p1 = path[idx]
    p2 = path[idx + 1]
    
    lat = p1[0] + frac * (p2[0] - p1[0])
    lon = p1[1] + frac * (p2[1] - p1[1])
    return [lat, lon]

def update_vehicle_positions(vehicles: List[Vehicle], roads_dict: Dict[str, Road]) -> List[Vehicle]:
    current_time = time.time()
    
    for veh in vehicles:
        if veh.status == "COMPLETED" or veh.status == "BLOCKED" or veh.speed_kmh <= 0:
            veh.last_updated = current_time
            continue
            
        # Get path points for vehicle's current route
        route_segments = veh.current_route_id.split(";")
        full_path = []
        total_length = 0.0
        
        for rid in route_segments:
            road = roads_dict.get(rid)
            if road:
                total_length += road.length_km
                if road.path:
                    if full_path and full_path[-1] == road.path[0]:
                        full_path.extend(road.path[1:])
                    else:
                        full_path.extend(road.path)
                        
        if total_length <= 0 or not full_path:
            veh.last_updated = current_time
            continue
            
        # Time delta in hours
        time_delta = 0.0
        if veh.last_updated > 0:
            time_delta = (current_time - veh.last_updated) / 3600.0
            
        # For demo purposes, speed up time slightly (1 hour of travel takes 1 minute in real life)
        # Time multiplication factor: 60.0
        time_multiplier = 60.0
        elapsed_hours = time_delta * time_multiplier
        
        # Calculate new progress
        distance_moved = veh.speed_kmh * elapsed_hours
        progress_inc = distance_moved / total_length
        veh.progress = (veh.progress + progress_inc) % 1.0  # Loop progress
        
        # Interpolate coordinate
        lat, lon = interpolate_position(full_path, veh.progress)
        veh.current_lat = round(lat, 5)
        veh.current_lon = round(lon, 5)
        
        veh.last_updated = current_time
        
    return vehicles
