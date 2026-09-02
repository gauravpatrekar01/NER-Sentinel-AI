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
        
    # 6. Route Optimization & ETA Recalculation via Decision Engine
    # By calling the GPS simulator update function, it will automatically
    # evaluate the new risks and reroute any vehicles using the Decision Engine.
    from app.services.gps_simulator import update_vehicle_positions
    if optimize_immediately:
        update_vehicle_positions()
        
    return {
        "incident_id": inc_id,
        "affected_vehicles_count": len(affected_vehicles),
        "affected_deliveries_count": len(affected_deliveries)
    }
