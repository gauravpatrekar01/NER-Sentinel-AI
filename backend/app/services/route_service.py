from typing import List, Dict, Any
from app.database import load_roads
from app.models.models import Road

# Define our 3 distinct routes between Guwahati and Silchar
ROUTES_CONFIG = [
    {
        "route_id": "RT-NH6",
        "name": "NH-6 Primary Corridor (via Shillong)",
        "road_ids": ["R-204", "R-207", "R-211", "R-218"]
    },
    {
        "route_id": "RT-NH27-54",
        "name": "NH-27/NH-54 Alternate Corridor (via Haflong)",
        "road_ids": ["R-301", "R-302", "R-303"]
    },
    {
        "route_id": "RT-MOUNTAIN",
        "name": "NH-2 Alternate Hill Bypass (Hybrid)",
        "road_ids": ["R-301", "R-302", "R-218"]
    }
]

def calculate_route_details(route_cfg: Dict[str, Any], roads_dict: Dict[str, Road], priority: str = "NORMAL", emergency_mode: bool = False) -> Dict[str, Any]:
    road_ids = route_cfg["road_ids"]
    
    total_distance = 0.0
    total_time = 0.0
    max_risk = 0.0
    sum_risk = 0.0
    is_blocked = False
    blocked_road_name = ""
    
    # Coordinates list for the entire route
    full_path = []
    
    for rid in road_ids:
        road = roads_dict.get(rid)
        if not road:
            continue
            
        total_distance += road.length_km
        
        # Base speed limits
        base_speed = 50.0  # default
        if rid in ["R-204", "R-301"]:
            base_speed = 60.0  # flatter roads
        elif rid in ["R-218", "R-302", "R-303"]:
            base_speed = 35.0  # steep/hilly terrain
            
        # Speed reduction factor based on risk and conditions
        speed_factor = 1.0
        if road.status == "BLOCKED":
            is_blocked = True
            blocked_road_name = road.name
            speed_factor = 0.0001  # extremely slow / blocked
        elif road.risk_level == "CRITICAL":
            speed_factor = 0.4
        elif road.risk_level == "HIGH":
            speed_factor = 0.6
        elif road.risk_level == "MODERATE":
            speed_factor = 0.8
            
        actual_speed = base_speed * speed_factor
        segment_time = road.length_km / actual_speed
        
        total_time += segment_time
        max_risk = max(max_risk, road.disruption_probability)
        sum_risk += road.disruption_probability
        
        # Append path points
        if road.path:
            # Avoid repeating joint points
            if full_path and full_path[-1] == road.path[0]:
                full_path.extend(road.path[1:])
            else:
                full_path.extend(road.path)
                
    avg_risk = sum_risk / len(road_ids) if road_ids else 0.0
    
    # Calculate optimization cost score
    # Score = travel_time * (1 + risk_multiplier * max_risk)
    # Critical and High priority deliveries are much more risk-averse
    risk_multiplier = 1.5
    if priority == "CRITICAL":
        risk_multiplier = 10.0
    elif priority == "HIGH":
        risk_multiplier = 5.0
        
    if emergency_mode:
        risk_multiplier *= 2.0  # double down on safety in emergency mode
        
    cost_score = total_time * (1.0 + risk_multiplier * max_risk)
    if is_blocked:
        cost_score = 999999.0  # infinite cost
        
    return {
        "route_id": route_cfg["route_id"],
        "name": route_cfg["name"],
        "road_ids": road_ids,
        "total_distance_km": round(total_distance, 1),
        "travel_time_hours": round(total_time, 2),
        "max_risk_prob": round(max_risk, 2),
        "avg_risk_prob": round(avg_risk, 2),
        "is_blocked": is_blocked,
        "blocked_road_name": blocked_road_name,
        "cost_score": cost_score,
        "path": full_path
    }

def get_optimized_routes(priority: str = "NORMAL", emergency_mode: bool = False) -> Dict[str, Any]:
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    
    evaluated_routes = []
    for route_cfg in ROUTES_CONFIG:
        details = calculate_route_details(route_cfg, roads_dict, priority, emergency_mode)
        evaluated_routes.append(details)
        
    # Sort by cost score to find recommended
    sorted_routes = sorted(evaluated_routes, key=lambda x: x["cost_score"])
    
    recommended = sorted_routes[0]
    
    # Check if all routes are blocked
    all_blocked = all(r["is_blocked"] for r in sorted_routes)
    
    return {
        "recommended_route_id": recommended["route_id"] if not all_blocked else None,
        "routes": evaluated_routes,
        "all_blocked": all_blocked
    }
