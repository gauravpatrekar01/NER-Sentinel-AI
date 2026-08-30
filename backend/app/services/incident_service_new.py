from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database_sqlalchemy import Incident, IncidentType, IncidentSeverity, RoadStatus
from app.services.data_service import DataService
from app.services.road_risk_service import RoadRiskService
from app.services.delivery_risk_service_new import DeliveryRiskService
from app.services.impact_service import ImpactService
from app.services.route_service_new import RouteService
from app.services.eta_service_new import ETAService
from app.services.alert_service_new import AlertService
import uuid
import logging

logger = logging.getLogger(__name__)

class IncidentService:
    """Service for managing incidents and their cascading effects"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
        self.road_risk_service = RoadRiskService(db)
        self.delivery_risk_service = DeliveryRiskService(db)
        self.impact_service = ImpactService(db)
        self.route_service = RouteService(db)
        self.eta_service = ETAService(db)
        self.alert_service = AlertService(db)
    
    def create_incident(self, incident_data: Dict[str, Any]) -> Incident:
        """Create a new incident and trigger the cascade workflow"""
        incident_id = f"INC-{uuid.uuid4().hex[:6].upper()}"
        incident_data["incident_id"] = incident_id
        
        incident = self.data_service.create_incident(incident_data)
        logger.info(f"Created incident {incident_id} on road {incident_data['road_id']}")
        
        return incident
    
    def process_incident(self, incident_id: str, optimize_immediately: bool = True) -> Dict[str, Any]:
        """
        Process an incident through the complete cascade:
        1. Update road status if needed
        2. Recalculate road risk
        3. Calculate impact
        4. Identify affected vehicles and deliveries
        5. Calculate delivery risks
        6. Generate alternate routes if requested
        7. Recalculate ETA
        8. Generate alerts
        """
        incident = self.data_service.get_incident_by_id(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        logger.info(f"Processing incident {incident_id} - Type: {incident.type}, Severity: {incident.severity}")
        
        # Step 1: Check if incident should block the road
        should_block = (
            incident.type == IncidentType.LANDSLIDE or
            incident.severity == IncidentSeverity.CRITICAL or
            (incident.type == IncidentType.FLOOD and incident.severity == IncidentSeverity.HIGH)
        )
        
        if should_block:
            self.road_risk_service.block_road(incident.road_id)
            logger.info(f"Incident blocked road {incident.road_id}")
        
        # Step 2: Recalculate road risk
        self.road_risk_service.calculate_road_risk(incident.road_id)
        
        # Step 3: Calculate impact
        impact = self.impact_service.calculate_incident_impact(incident.road_id)
        
        # Step 4: Identify affected vehicles and deliveries
        affected_vehicles = impact.get("affected_vehicles", [])
        affected_deliveries = impact.get("affected_deliveries", [])
        critical_deliveries = impact.get("critical_deliveries", [])
        
        logger.info(f"Impact: {len(affected_vehicles)} vehicles, {len(affected_deliveries)} deliveries affected")
        
        # Step 5: Generate road blocked alert
        if should_block:
            self.alert_service.generate_alert(
                alert_type="ROAD_BLOCKED",
                severity="CRITICAL",
                title=f"Road {incident.road_id} Blocked",
                message=f"Road {incident.road_id} is blocked due to {incident.type.value}. {len(affected_vehicles)} vehicles and {len(affected_deliveries)} deliveries affected.",
                road_id=incident.road_id
            )
        
        # Step 6: Route optimization and ETA recalculation
        eta_updates = []
        
        if optimize_immediately and affected_vehicles:
            for vehicle_data in affected_vehicles:
                # Get vehicle ID from dict or object
                vehicle_id = vehicle_data.get("vehicle_id") if isinstance(vehicle_data, dict) else vehicle_data.vehicle_id
                
                # Get the actual vehicle object
                vehicle = self.data_service.get_vehicle_by_id(vehicle_id)
                if not vehicle:
                    continue
                    
                # Get deliveries for this vehicle
                vehicle_deliveries = self.data_service.get_deliveries_by_vehicle(vehicle_id)
                
                if vehicle_deliveries:
                    primary_delivery = vehicle_deliveries[0]
                    
                    # Try to find alternate routes
                    try:
                        import json
                        current_route = json.loads(primary_delivery.current_route) if isinstance(primary_delivery.current_route, str) else primary_delivery.current_route
                        origin = current_route[0] if current_route else None
                        destination = current_route[-1] if current_route else None
                        
                        if origin and destination:
                            # Get alternative routes
                            alt_routes = self.route_service.find_alternative_routes(
                                origin=origin,
                                destination=destination,
                                blocked_roads=[incident.road_id]
                            )
                            
                            if alt_routes.get("recommended_route"):
                                # Update vehicle route
                                new_route_id = alt_routes["recommended_route"]
                                new_route_segments = alt_routes["alternatives"][0]["road_ids"]
                                
                                self.data_service.update_vehicle(
                                    vehicle.vehicle_id,
                                    current_road_id=new_route_segments[0] if new_route_segments else None
                                )
                                
                                # Update delivery route
                                self.data_service.update_delivery(
                                    primary_delivery.delivery_id,
                                    current_route=json.dumps(new_route_segments)
                                )
                                
                                # Generate route changed alert
                                self.alert_service.generate_alert(
                                    alert_type="ROUTE_CHANGED",
                                    severity="WARNING",
                                    title=f"Vehicle {vehicle_id} Rerouted",
                                    message=f"Vehicle {vehicle_id} rerouted via {new_route_id} to bypass {incident.road_id}.",
                                    vehicle_id=vehicle_id,
                                    delivery_id=primary_delivery.delivery_id
                                )
                                
                                logger.info(f"Vehicle {vehicle.vehicle_id} rerouted to {new_route_id}")
                            else:
                                # No alternative route available
                                self.data_service.update_vehicle(vehicle_id, status="BLOCKED")
                                self.alert_service.generate_alert(
                                    alert_type="VEHICLE_DELAY",
                                    severity="CRITICAL",
                                    title=f"Vehicle {vehicle_id} Blocked",
                                    message=f"Vehicle {vehicle_id} is blocked. No alternative routes available.",
                                    vehicle_id=vehicle_id
                                )
                    except Exception as e:
                        logger.error(f"Error finding alternate routes for vehicle {vehicle_id}: {e}")
                    
                    # Step 7: Recalculate ETA
                    for delivery in vehicle_deliveries:
                        try:
                            eta_result = self.eta_service.calculate_eta(
                                delivery_id=delivery.delivery_id
                            )
                            eta_updates.append(eta_result)
                            
                            # Check for critical delivery delays
                            if delivery.priority.value == "CRITICAL" and eta_result.get("delay_minutes", 0) > 30:
                                self.alert_service.generate_alert(
                                    alert_type="CRITICAL_DELIVERY",
                                    severity="CRITICAL",
                                    title=f"Critical Delivery {delivery.delivery_id} Delayed",
                                    message=f"CRITICAL cargo {delivery.cargo_type} is delayed by {eta_result.get('delay_minutes', 0)} minutes. ETA: {eta_result.get('new_eta')}.",
                                    delivery_id=delivery.delivery_id,
                                    vehicle_id=vehicle_id
                                )
                        except Exception as e:
                            logger.error(f"Error calculating ETA for delivery {delivery.delivery_id}: {e}")
        
        # Step 8: Recalculate delivery risks
        for delivery_data in affected_deliveries:
            # Get delivery ID from dict or object
            delivery_id = delivery_data.get("delivery_id") if isinstance(delivery_data, dict) else delivery_data.delivery_id
            try:
                self.delivery_risk_service.calculate_delivery_risk(delivery_id)
            except Exception as e:
                logger.error(f"Error calculating risk for delivery {delivery_id}: {e}")
            try:
                self.delivery_risk_service.calculate_delivery_risk(delivery.delivery_id)
            except Exception as e:
                logger.error(f"Error calculating risk for delivery {delivery.delivery_id}: {e}")
        
        return {
            "incident_id": incident_id,
            "road_blocked": should_block,
            "affected_vehicles_count": len(affected_vehicles),
            "affected_deliveries_count": len(affected_deliveries),
            "critical_deliveries_count": len(critical_deliveries),
            "impact": impact,
            "eta_updates": eta_updates
        }
    
    def resolve_incident(self, incident_id: str) -> Dict[str, Any]:
        """Resolve an incident and restore normal operations"""
        incident = self.data_service.get_incident_by_id(incident_id)
        if not incident:
            raise ValueError(f"Incident {incident_id} not found")
        
        # Mark incident as inactive
        self.data_service.update_incident(incident_id, active=False)
        
        # Check if road can be unblocked (no other active blocking incidents)
        active_incidents = self.data_service.get_incidents_by_road(incident.road_id, active_only=True)
        blocking_incidents = [inc for inc in active_incidents if 
                              inc.type == IncidentType.LANDSLIDE or 
                              inc.severity == IncidentSeverity.CRITICAL]
        
        if not blocking_incidents:
            self.road_risk_service.unblock_road(incident.road_id)
            logger.info(f"Road {incident.road_id} unblocked after resolving incident {incident_id}")
        
        # Recalculate risks
        self.road_risk_service.calculate_road_risk(incident.road_id)
        
        return {
            "incident_id": incident_id,
            "status": "resolved",
            "road_unblocked": len(blocking_incidents) == 0
        }
    
    def get_active_incidents(self) -> List[Incident]:
        """Get all currently active incidents"""
        return self.data_service.get_all_incidents(active_only=True)
