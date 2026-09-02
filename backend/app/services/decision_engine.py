import uuid
import time
from typing import Dict, Any, List
from app.models.models import Vehicle, Delivery, Road, WeatherObservation, Alert
from app.database import load_alerts, save_alerts

# Define the two primary corridors for the NER Prototype
CORRIDOR_1_NH6 = ["R-204", "R-207", "R-211", "R-218"] # Guwahati-Shillong-Silchar
CORRIDOR_2_NH27 = ["R-301", "R-302", "R-303"] # Guwahati-Nagaon-Haflong-Silchar

def get_corridor_risk_and_eta(route_ids: List[str], roads_dict: Dict[str, Road], speed_kmh: float, progress: float = 0.0) -> Dict[str, Any]:
    total_risk = 0.0
    total_distance = 0.0
    is_blocked = False
    
    # Simple risk max over the remaining segments
    max_risk = 0.0
    
    for rid in route_ids:
        road = roads_dict.get(rid)
        if road:
            total_distance += road.length_km
            max_risk = max(max_risk, road.disruption_probability)
            if road.status == "BLOCKED":
                is_blocked = True
                
    # ETA Calculation
    # Remaining distance = total distance * (1 - progress)
    remaining_distance = total_distance * (1.0 - progress)
    
    # Adjust effective speed based on risk
    # High risk (disruption_prob > 0.5) slows down vehicle
    effective_speed = speed_kmh * (1.0 - (max_risk * 0.4)) 
    if effective_speed < 10.0:
        effective_speed = 10.0 # Min speed
        
    eta_hours = remaining_distance / effective_speed if effective_speed > 0 else 999
    eta_mins = int(eta_hours * 60)
    
    return {
        "risk": round(max_risk * 100, 1),
        "is_blocked": is_blocked,
        "eta_mins": eta_mins,
        "total_distance": total_distance
    }

def generate_alert(alert_type: str, message: str, severity: str):
    alerts = load_alerts()
    new_alert = Alert(
        alert_id=f"ALT-{str(uuid.uuid4())[:8]}",
        type=alert_type,
        message=message,
        timestamp=time.time(),
        severity=severity,
        read=False
    )
    alerts.insert(0, new_alert)
    # Keep only last 50 alerts
    save_alerts(alerts[:50])
    return new_alert

def evaluate_vehicle_route(
    vehicle: Vehicle, 
    roads_dict: Dict[str, Road],
    weather: WeatherObservation,
    emergency_mode: bool
) -> Dict[str, Any]:
    
    current_route = vehicle.current_route_id.split(";")
    
    # Determine alternative route (Toggle between the two corridors for the demo)
    is_nh6 = all(r in current_route for r in CORRIDOR_1_NH6 if r in vehicle.current_route_id)
    if is_nh6:
        alt_route = CORRIDOR_2_NH27
    else:
        alt_route = CORRIDOR_1_NH6
        
    current_metrics = get_corridor_risk_and_eta(current_route, roads_dict, vehicle.speed_kmh, vehicle.progress)
    alt_metrics = get_corridor_risk_and_eta(alt_route, roads_dict, vehicle.speed_kmh, 0.0) # Progress 0 on new route
    
    decision = "PROCEED"
    reasons = []
    recommended_route = vehicle.current_route_id
    recommended_eta = current_metrics["eta_mins"]
    recommended_risk = current_metrics["risk"]
    alert_required = False
    
    # Decision Logic
    if current_metrics["is_blocked"]:
        decision = "REROUTE"
        reasons.append("Current route is BLOCKED by a critical incident.")
        alert_required = True
        recommended_route = ";".join(alt_route)
        recommended_eta = alt_metrics["eta_mins"]
        recommended_risk = alt_metrics["risk"]
    elif current_metrics["risk"] > 60.0:
        if alt_metrics["risk"] < current_metrics["risk"] - 20.0 and not alt_metrics["is_blocked"]:
            decision = "REROUTE"
            reasons.append(f"Current route risk ({current_metrics['risk']}%) exceeds threshold. Alternative is safer ({alt_metrics['risk']}%).")
            if emergency_mode:
                reasons.append("Emergency protocol demands lowest-risk corridor for critical supplies.")
            alert_required = True
            recommended_route = ";".join(alt_route)
            recommended_eta = alt_metrics["eta_mins"]
            recommended_risk = alt_metrics["risk"]
        else:
            reasons.append("Current route is high risk, but alternative is also unsafe or blocked.")
            
    # Generate Alerts if needed
    if alert_required:
        generate_alert(
            alert_type="ROUTE_UPDATED",
            message=f"Vehicle {vehicle.vehicle_id} rerouted to {recommended_route}. Reason: {reasons[0]}",
            severity="CRITICAL" if emergency_mode else "WARNING"
        )
        
    # Formatting ETA back to string (e.g. current hour + eta_mins)
    # For simplicity in demo, we'll just return the integer minutes for the UI to handle, or calculate a string
    current_time_str = "12:00" # Dummy baseline if we were calculating exact HH:MM, but we can just use relative
    
    return {
        "decision": decision,
        "recommended_route": recommended_route,
        "current_route_risk": current_metrics["risk"],
        "recommended_route_risk": alt_metrics["risk"] if decision == "REROUTE" else current_metrics["risk"],
        "current_eta_mins": current_metrics["eta_mins"],
        "recommended_eta_mins": recommended_eta,
        "reroute_required": decision == "REROUTE",
        "alert_required": alert_required,
        "reasons": reasons,
        "is_blocked": current_metrics["is_blocked"]
    }
