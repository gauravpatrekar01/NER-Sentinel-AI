import time
import uuid
from typing import List, Dict, Any
from app.database import (
    load_incidents, save_incidents, load_roads, save_roads, 
    load_vehicles, save_vehicles, load_deliveries, save_deliveries
)
from app.models.models import Incident, Road, Vehicle, Delivery
from app.services.risk_service import recalculate_all_roads_risk
from app.services.route_service import get_optimized_routes
from app.services.eta_service import calculate_eta_and_delay
from app.services.delivery_risk_service import recalculate_delivery_risks
from app.services.alert_service import generate_alert

def register_incident_and_cascade(
    road_id: str,
    lat: float,
    lon: float,
    incident_type: str,
    severity: str,
    description: str,
    photo_url: str = None,
    optimize_immediately: bool = True
) -> Dict[str, Any]:
    
    # 1. Save the Incident
    incidents = load_incidents()
    inc_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
    new_incident = Incident(
        incident_id=inc_id,
        road_id=road_id,
        lat=lat,
        lon=lon,
        type=incident_type,
        severity=severity,
        description=description,
        photo_url=photo_url,
        timestamp=time.time(),
        active=True
    )
    incidents.append(new_incident)
    save_incidents(incidents)
    
    # 2. Block the road segment if severity is HIGH/CRITICAL or landslide
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    
    road_blocked = False
    if road_id in roads_dict:
        road = roads_dict[road_id]
        if incident_type.lower() == "landslide" or severity in ["HIGH", "CRITICAL"]:
            road.status = "BLOCKED"
            road_blocked = True
            save_roads(roads)
            
    # 3. Recalculate all roads risk (updates ML scores and applies blockage overrides)
    recalculate_all_roads_risk()
    
    # Reload updated roads and other models
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    vehicles = load_vehicles()
    deliveries = load_deliveries()
    
    affected_vehicles: List[Vehicle] = []
    affected_deliveries: List[Delivery] = []
    
    # 4. Identify affected vehicles
    if road_blocked:
        for veh in vehicles:
            if veh.status == "COMPLETED":
                continue
            route_segments = veh.current_route_id.split(";")
            if road_id in route_segments:
                affected_vehicles.append(veh)
                
    affected_veh_ids = [v.vehicle_id for v in affected_vehicles]
    
    # 5. Identify affected deliveries
    for deliv in deliveries:
        if deliv.vehicle_id in affected_veh_ids and deliv.status != "DELIVERED":
            affected_deliveries.append(deliv)
            
    # Generate block alert
    if road_blocked:
        block_msg = f"Road {road_id} ({roads_dict[road_id].name}) is BLOCKED due to a {incident_type}."
        generate_alert(
            alert_type="ROAD_BLOCKED",
            message=f"{block_msg} {len(affected_vehicles)} vehicles and {len(affected_deliveries)} deliveries affected.",
            severity="CRITICAL"
        )
        
    # 6. Route Optimization & ETA Recalculation
    vehicles_dict = {v.vehicle_id: v for v in vehicles}
    deliveries_dict = {d.delivery_id: d for d in deliveries}
    
    for veh in affected_vehicles:
        # Find matching delivery for this vehicle
        veh_deliveries = [d for d in deliveries if d.vehicle_id == veh.vehicle_id]
        primary_priority = veh_deliveries[0].priority if veh_deliveries else "NORMAL"
        
        if optimize_immediately:
            # Run Route Optimizer
            opt_result = get_optimized_routes(priority=primary_priority)
            
            # Update vehicle route
            # Get paths and segments of recommended route
            rec_route_id = opt_result["recommended_route_id"]
            if rec_route_id:
                # Find the route details in result list
                rec_route_details = next((r for r in opt_result["routes"] if r["route_id"] == rec_route_id), None)
                if rec_route_details:
                    new_segments = rec_route_details["road_ids"]
                    veh.current_route_id = ";".join(new_segments)
                    
                    # Project vehicle coordinates to the start or a segment along the new route
                    # Since V-104 starts at Guwahati, reset progress or coordinate to first point
                    if veh.vehicle_id == "V-104":
                        veh.progress = 0.05
                        veh.current_lat = 26.1445
                        veh.current_lon = 91.7362
                        
                    # Generate Route Updated Alert
                    route_name_display = "Haflong Bypass" if rec_route_id == "RT-NH27-54" else rec_route_details["name"]
                    generate_alert(
                        alert_type="ROUTE_UPDATED",
                        message=f"Vehicle {veh.vehicle_id} rerouted via {route_name_display} to bypass {road_id}.",
                        severity="WARNING"
                    )
            else:
                veh.status = "BLOCKED"
                generate_alert(
                    alert_type="VEHICLE_DELAY",
                    message=f"Vehicle {veh.vehicle_id} is blocked. No alternative routes available.",
                    severity="CRITICAL"
                )
        else:
            # Baseline - vehicle does not reroute, becomes delayed/blocked
            veh.status = "BLOCKED"
            
        # Update ETA and Delay for each delivery of this vehicle
        for deliv in veh_deliveries:
            # We need the path length of the current assigned route
            if optimize_immediately and rec_route_id and rec_route_details:
                path_len = rec_route_details["total_distance_km"]
            else:
                # Use current route segments sum
                path_len = sum(roads_dict[rid].length_km for rid in veh.current_route_id.split(";") if rid in roads_dict)
                
            new_eta, delay_val, delay_reason = calculate_eta_and_delay(veh, deliv, roads_dict, path_len)
            
            deliv.eta_str = new_eta
            deliv.delay_reason = delay_reason
            if "stuck" in delay_reason.lower() or "blocked" in delay_reason.lower():
                deliv.status = "DELAYED"
                
            # If critical delivery is delayed, generate a warning
            if deliv.priority == "CRITICAL" and delay_val != "On Time":
                generate_alert(
                    alert_type="CRITICAL_DELIVERY_DELAY",
                    message=f"CRITICAL cargo {deliv.delivery_id} ({deliv.cargo}) is delayed by {delay_val}. ETA: {new_eta}.",
                    severity="CRITICAL"
                )
                
    # 7. Recalculate Delivery Risks
    recalculate_delivery_risks(deliveries, vehicles_dict, roads_dict)
    
    # Save back to files
    save_vehicles(vehicles)
    save_deliveries(deliveries)
    
    return {
        "incident_id": inc_id,
        "affected_vehicles_count": len(affected_vehicles),
        "affected_deliveries_count": len(affected_deliveries)
    }
