from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database_sqlalchemy import Road, Vehicle, Delivery, DeliveryPriority, RoadStatus
from app.services.data_service import DataService
import json
import logging

logger = logging.getLogger(__name__)

class ImpactService:
    """Service for calculating the impact of incidents on the logistics network"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
    
    def calculate_incident_impact(self, road_id: str) -> Dict[str, Any]:
        """
        Calculate the impact of an incident on a specific road.
        
        Returns:
            Dict with affected vehicles, deliveries, critical deliveries, and estimated delay
        """
        road = self.data_service.get_road_by_id(road_id)
        if not road:
            raise ValueError(f"Road {road_id} not found")
        
        # Get vehicles currently on this road
        affected_vehicles = self.data_service.get_vehicles_on_road(road_id)
        
        # Get deliveries for affected vehicles
        affected_deliveries = []
        critical_deliveries = []
        
        for vehicle in affected_vehicles:
            vehicle_deliveries = self.data_service.get_deliveries_by_vehicle(vehicle.vehicle_id)
            for delivery in vehicle_deliveries:
                if delivery.status.value != "DELIVERED":
                    affected_deliveries.append(delivery)
                    if delivery.priority == DeliveryPriority.CRITICAL:
                        critical_deliveries.append(delivery)
        
        # Also check vehicles whose route includes this road
        all_vehicles = self.data_service.get_all_vehicles()
        for vehicle in all_vehicles:
            if vehicle.status.value == "COMPLETED":
                continue
                
            if vehicle.vehicle_id in [v.vehicle_id for v in affected_vehicles]:
                continue  # Already counted
            
            # Check if vehicle's route includes this road
            vehicle_deliveries = self.data_service.get_deliveries_by_vehicle(vehicle.vehicle_id)
            for delivery in vehicle_deliveries:
                if delivery.status.value == "DELIVERED":
                    continue
                    
                try:
                    route_segments = json.loads(delivery.current_route) if isinstance(delivery.current_route, str) else delivery.current_route
                    if road_id in route_segments:
                        if vehicle not in affected_vehicles:
                            affected_vehicles.append(vehicle)
                        if delivery not in affected_deliveries:
                            affected_deliveries.append(delivery)
                        if delivery.priority == DeliveryPriority.CRITICAL and delivery not in critical_deliveries:
                            critical_deliveries.append(delivery)
                except:
                    continue
        
        # Calculate estimated total delay
        # Base delay calculation: 4 hours for blocked road + additional time per affected delivery
        base_delay_minutes = 240  # 4 hours
        additional_delay_per_delivery = 15  # 15 minutes per delivery
        estimated_total_delay = base_delay_minutes + (len(affected_deliveries) * additional_delay_per_delivery)
        
        # Convert to hours and minutes
        delay_hours = estimated_total_delay // 60
        delay_minutes = estimated_total_delay % 60
        delay_str = f"{delay_hours}h {delay_minutes}m" if delay_hours > 0 else f"{delay_minutes}m"
        
        logger.info(f"Impact for road {road_id}: {len(affected_vehicles)} vehicles, {len(affected_deliveries)} deliveries, {len(critical_deliveries)} critical")
        
        return {
            "road_id": road_id,
            "affected_vehicles": [
                {
                    "vehicle_id": v.vehicle_id,
                    "vehicle_type": v.vehicle_type,
                    "current_lat": v.current_lat,
                    "current_lng": v.current_lng,
                    "status": v.status.value
                }
                for v in affected_vehicles
            ],
            "affected_deliveries": [
                {
                    "delivery_id": d.delivery_id,
                    "cargo_type": d.cargo_type,
                    "priority": d.priority.value,
                    "destination": d.destination,
                    "current_eta": d.eta.isoformat() if d.eta else None,
                    "risk_score": d.risk_score
                }
                for d in affected_deliveries
            ],
            "critical_deliveries": [
                {
                    "delivery_id": d.delivery_id,
                    "cargo_type": d.cargo_type,
                    "destination": d.destination,
                    "current_eta": d.eta.isoformat() if d.eta else None,
                    "risk_score": d.risk_score
                }
                for d in critical_deliveries
            ],
            "estimated_total_delay_minutes": estimated_total_delay,
            "estimated_total_delay_str": delay_str
        }
    
    def calculate_network_impact(self) -> Dict[str, Any]:
        """
        Calculate the overall impact of all currently blocked roads on the network.
        
        Returns:
            Dict with network-wide impact statistics
        """
        blocked_roads = self.data_service.get_blocked_roads()
        
        total_affected_vehicles = []
        total_affected_deliveries = []
        total_critical_deliveries = []
        total_estimated_delay = 0
        
        for road in blocked_roads:
            impact = self.calculate_incident_impact(road.road_id)
            
            # Accumulate unique vehicles and deliveries
            for vehicle in impact["affected_vehicles"]:
                if vehicle["vehicle_id"] not in [v["vehicle_id"] for v in total_affected_vehicles]:
                    total_affected_vehicles.append(vehicle)
            
            for delivery in impact["affected_deliveries"]:
                if delivery["delivery_id"] not in [d["delivery_id"] for d in total_affected_deliveries]:
                    total_affected_deliveries.append(delivery)
            
            for delivery in impact["critical_deliveries"]:
                if delivery["delivery_id"] not in [d["delivery_id"] for d in total_critical_deliveries]:
                    total_critical_deliveries.append(delivery)
            
            total_estimated_delay += impact["estimated_total_delay_minutes"]
        
        # Convert total delay to readable format
        delay_hours = total_estimated_delay // 60
        delay_minutes = total_estimated_delay % 60
        delay_str = f"{delay_hours}h {delay_minutes}m" if delay_hours > 0 else f"{delay_minutes}m"
        
        return {
            "blocked_roads_count": len(blocked_roads),
            "blocked_road_ids": [r.road_id for r in blocked_roads],
            "total_affected_vehicles_count": len(total_affected_vehicles),
            "total_affected_deliveries_count": len(total_affected_deliveries),
            "total_critical_deliveries_count": len(total_critical_deliveries),
            "total_estimated_delay_minutes": total_estimated_delay,
            "total_estimated_delay_str": delay_str,
            "network_operational_percentage": round(
                (1 - len(total_affected_deliveries) / max(len(self.data_service.get_all_deliveries()), 1)) * 100, 1
            )
        }
    
    def get_most_critical_deliveries(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get the most critical deliveries currently at risk"""
        at_risk_deliveries = []
        
        all_deliveries = self.data_service.get_all_deliveries()
        for delivery in all_deliveries:
            if delivery.status.value != "DELIVERED" and delivery.risk_score >= 50.0:
                at_risk_deliveries.append({
                    "delivery_id": delivery.delivery_id,
                    "cargo_type": delivery.cargo_type,
                    "priority": delivery.priority.value,
                    "destination": delivery.destination,
                    "risk_score": delivery.risk_score,
                    "on_time_probability": delivery.on_time_probability,
                    "current_eta": delivery.eta.isoformat() if delivery.eta else None
                })
        
        # Sort by risk score (descending) and priority
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "NORMAL": 3}
        at_risk_deliveries.sort(key=lambda x: (priority_order.get(x["priority"], 4), -x["risk_score"]))
        
        return at_risk_deliveries[:limit]
