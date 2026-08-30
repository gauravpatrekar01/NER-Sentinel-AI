from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database_sqlalchemy import Delivery, DeliveryPriority
from app.services.data_service import DataService
from app.services.route_service_new import RouteService
from app.services.alert_service_new import AlertService
import logging

logger = logging.getLogger(__name__)

class EmergencyService:
    """Service for managing emergency mode and prioritization"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
        self.route_service = RouteService(db)
        self.alert_service = AlertService(db)
    
    # Simple in-memory emergency state (in production, this would be in database)
    _emergency_active = False
    
    @classmethod
    def is_emergency_active(cls) -> bool:
        """Check if emergency mode is currently active"""
        return cls._emergency_active
    
    @classmethod
    def activate_emergency_mode(cls) -> Dict[str, Any]:
        """Activate emergency mode for enhanced prioritization"""
        cls._emergency_active = True
        logger.warning("EMERGENCY MODE ACTIVATED")
        
        return {
            "status": "activated",
            "message": "Emergency mode activated. Critical deliveries will receive highest priority.",
            "timestamp": None  # Would use actual timestamp
        }
    
    @classmethod
    def deactivate_emergency_mode(cls) -> Dict[str, Any]:
        """Deactivate emergency mode and return to normal operations"""
        cls._emergency_active = False
        logger.info("Emergency mode deactivated. Returning to normal operations.")
        
        return {
            "status": "deactivated",
            "message": "Emergency mode deactivated. Normal priority levels restored.",
            "timestamp": None
        }
    
    def get_emergency_prioritization(self) -> Dict[str, Any]:
        """Get current prioritization rules based on emergency state"""
        if self._emergency_active:
            return {
                "emergency_mode": True,
                "priority_weights": {
                    "CRITICAL": 10.0,
                    "HIGH": 8.0,
                    "MEDIUM": 6.0,
                    "NORMAL": 4.0
                },
                "cargo_priorities": [
                    "Medicines",
                    "Emergency Supplies",
                    "Food",
                    "Water",
                    "Medical Oxygen"
                ],
                "routing_preferences": "SAFETY_OVER_SPEED"
            }
        else:
            return {
                "emergency_mode": False,
                "priority_weights": {
                    "CRITICAL": 5.0,
                    "HIGH": 3.0,
                    "MEDIUM": 2.0,
                    "NORMAL": 1.0
                },
                "cargo_priorities": [
                    "Medicines",
                    "Medical Oxygen"
                ],
                "routing_preferences": "BALANCED"
            }
    
    def optimize_for_emergency(self) -> Dict[str, Any]:
        """Re-optimize all active routes with emergency prioritization"""
        if not self._emergency_active:
            return {"error": "Emergency mode is not active"}
        
        from app.database_sqlalchemy import DeliveryStatus
        
        active_deliveries = self.data_service.get_deliveries_by_status(DeliveryStatus.EN_ROUTE)
        optimized_count = 0
        
        for delivery in active_deliveries:
            # Focus on critical and high priority deliveries
            if delivery.priority in [DeliveryPriority.CRITICAL, DeliveryPriority.HIGH]:
                try:
                    # Re-optimize route with emergency mode
                    route_result = self.route_service.optimize_route_for_delivery(
                        delivery.delivery_id,
                        emergency_mode=True
                    )
                    
                    if route_result.get("recommended_route"):
                        optimized_count += 1
                        logger.info(f"Emergency re-optimized route for delivery {delivery.delivery_id}")
                except Exception as e:
                    logger.error(f"Error emergency optimizing delivery {delivery.delivery_id}: {e}")
        
        # Generate emergency alert
        self.alert_service.generate_alert(
            alert_type="EMERGENCY_MODE",
            severity="CRITICAL",
            title="Emergency Route Optimization Complete",
            message=f"Re-optimized {optimized_count} critical/high priority delivery routes for emergency conditions."
        )
        
        return {
            "status": "complete",
            "optimized_deliveries": optimized_count,
            "total_active": len(active_deliveries)
        }
    
    def get_emergency_critical_deliveries(self) -> List[Dict[str, Any]]:
        """Get deliveries that should be prioritized during emergency"""
        emergency_cargo_types = [
            "Medicines", "Essential Medicines", "Medical Oxygen", 
            "Emergency Supplies", "Food", "Water", "Drinking Water"
        ]
        
        from app.database_sqlalchemy import DeliveryStatus
        
        active_deliveries = self.data_service.get_deliveries_by_status(DeliveryStatus.EN_ROUTE)
        emergency_deliveries = []
        
        for delivery in active_deliveries:
            # Include if priority is CRITICAL or cargo type matches emergency types
            if (delivery.priority == DeliveryPriority.CRITICAL or 
                any(cargo in delivery.cargo_type for cargo in emergency_cargo_types)):
                emergency_deliveries.append({
                    "delivery_id": delivery.delivery_id,
                    "cargo_type": delivery.cargo_type,
                    "priority": delivery.priority.value,
                    "destination": delivery.destination,
                    "current_eta": delivery.eta.isoformat() if delivery.eta else None,
                    "risk_score": delivery.risk_score,
                    "vehicle_id": delivery.vehicle_id
                })
        
        # Sort by priority and risk
        priority_order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "NORMAL": 3}
        emergency_deliveries.sort(key=lambda x: (priority_order.get(x["priority"], 4), -x["risk_score"]))
        
        return emergency_deliveries
    
    def assess_emergency_readiness(self) -> Dict[str, Any]:
        """Assess system readiness for emergency operations"""
        from app.database_sqlalchemy import RoadStatus
        
        roads = self.data_service.get_all_roads()
        blocked_roads = [r for r in roads if r.current_status == RoadStatus.BLOCKED]
        
        active_deliveries = self.data_service.get_deliveries_by_status(DeliveryStatus.EN_ROUTE)
        critical_deliveries = [d for d in active_deliveries if d.priority == DeliveryPriority.CRITICAL]
        
        # Calculate network health
        accessible_roads = len(roads) - len(blocked_roads)
        network_health = (accessible_roads / len(roads) * 100) if roads else 0
        
        readiness_level = "HIGH"
        if network_health < 50:
            readiness_level = "LOW"
        elif network_health < 75:
            readiness_level = "MEDIUM"
        
        return {
            "readiness_level": readiness_level,
            "network_health_percentage": round(network_health, 1),
            "total_roads": len(roads),
            "blocked_roads": len(blocked_roads),
            "accessible_roads": accessible_roads,
            "active_deliveries": len(active_deliveries),
            "critical_deliveries": len(critical_deliveries),
            "emergency_mode_active": self._emergency_active,
            "recommendations": self._get_emergency_recommendations(readiness_level, len(blocked_roads))
        }
    
    def _get_emergency_recommendations(self, readiness_level: str, blocked_roads_count: int) -> List[str]:
        """Get recommendations based on current readiness"""
        recommendations = []
        
        if readiness_level == "LOW":
            recommendations.append("Activate emergency mode immediately")
            recommendations.append("Prioritize critical deliveries for alternative routing")
            recommendations.append("Alert authorities about severe network disruption")
        elif readiness_level == "MEDIUM":
            recommendations.append("Monitor critical delivery routes closely")
            recommendations.append("Prepare contingency plans for key corridors")
        else:
            recommendations.append("Maintain standard operations with increased monitoring")
        
        if blocked_roads_count > 0:
            recommendations.append(f"Address {blocked_roads_count} blocked road(s) urgently")
        
        return recommendations
