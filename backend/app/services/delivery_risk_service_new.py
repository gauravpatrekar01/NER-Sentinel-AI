from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database_sqlalchemy import Delivery, Vehicle, Road, DeliveryStatus, DeliveryPriority
from app.services.data_service import DataService
import logging

logger = logging.getLogger(__name__)

class DeliveryRiskService:
    """Service for calculating and managing delivery risk scores"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
    
    def calculate_delivery_risk(self, delivery_id: str) -> Dict[str, Any]:
        """
        Calculate risk score for a specific delivery based on current conditions.
        
        Returns:
            Dict with delivery_id, risk_score, risk_level, on_time_probability
        """
        delivery = self.data_service.get_delivery_by_id(delivery_id)
        if not delivery:
            raise ValueError(f"Delivery {delivery_id} not found")
        
        vehicle = self.data_service.get_vehicle_by_id(delivery.vehicle_id)
        if not vehicle:
            raise ValueError(f"Vehicle {delivery.vehicle_id} not found")
        
        # Get route segments
        try:
            import json
            route_segments = json.loads(delivery.current_route) if isinstance(delivery.current_route, str) else delivery.current_route
        except:
            route_segments = []
        
        # Calculate max road risk along the route
        max_road_risk = 0.0
        is_route_blocked = False
        
        for road_id in route_segments:
            road = self.data_service.get_road_by_id(road_id)
            if road:
                max_road_risk = max(max_road_risk, road.risk_score / 100.0)  # Convert to 0-1 scale
                if road.current_status.value == "BLOCKED":
                    is_route_blocked = True
        
        # Calculate delivery risk percentage
        if is_route_blocked:
            risk_pct = 91.0
        else:
            # Normal scaling: map 0.0-1.0 probability to 10% - 90% risk range
            risk_pct = 10.0 + (max_road_risk * 80.0)
        
        # Apply priority weighting
        priority_multiplier = {
            DeliveryPriority.CRITICAL: 1.2,
            DeliveryPriority.HIGH: 1.1,
            DeliveryPriority.MEDIUM: 1.0,
            DeliveryPriority.NORMAL: 0.9
        }
        
        risk_pct *= priority_multiplier.get(delivery.priority, 1.0)
        risk_pct = min(risk_pct, 100.0)  # Cap at 100%
        
        # Determine risk level
        if risk_pct >= 80:
            risk_level = "CRITICAL"
        elif risk_pct >= 60:
            risk_level = "HIGH"
        elif risk_pct >= 40:
            risk_level = "MODERATE"
        else:
            risk_level = "LOW"
        
        # On-time probability is inverse of risk
        on_time_prob = 100.0 - risk_pct
        
        # Update delivery with new risk values
        self.data_service.update_delivery(
            delivery_id,
            risk_score=round(risk_pct, 1),
            on_time_probability=round(on_time_prob, 1)
        )
        
        # Update status if high risk
        if risk_level == "CRITICAL" and delivery.status == DeliveryStatus.EN_ROUTE:
            self.data_service.update_delivery(delivery_id, status=DeliveryStatus.DELAYED)
        
        logger.info(f"Calculated risk for delivery {delivery_id}: {risk_level} ({risk_pct}%)")
        
        return {
            "delivery_id": delivery_id,
            "risk_score": round(risk_pct, 1),
            "risk_level": risk_level,
            "on_time_probability": round(on_time_prob, 1),
            "route_blocked": is_route_blocked,
            "max_road_risk": round(max_road_risk, 2)
        }
    
    def recalculate_all_deliveries_risk(self) -> List[Dict[str, Any]]:
        """Recalculate risk scores for all active deliveries"""
        deliveries = self.data_service.get_deliveries_by_status(DeliveryStatus.EN_ROUTE)
        results = []
        
        for delivery in deliveries:
            try:
                result = self.calculate_delivery_risk(delivery.delivery_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error calculating risk for delivery {delivery.delivery_id}: {e}")
        
        return results
    
    def get_at_risk_deliveries(self, threshold: float = 60.0) -> List[Delivery]:
        """Get deliveries with risk score above threshold"""
        deliveries = self.data_service.get_all_deliveries()
        return [d for d in deliveries if d.risk_score >= threshold and d.status != DeliveryStatus.DELIVERED]
    
    def get_critical_at_risk_deliveries(self) -> List[Delivery]:
        """Get critical priority deliveries that are at risk"""
        critical_deliveries = self.data_service.get_critical_deliveries()
        return [d for d in critical_deliveries if d.risk_score >= 50.0 and d.status != DeliveryStatus.DELIVERED]
    
    def assess_delivery_fleet_risk(self) -> Dict[str, Any]:
        """Get overall risk assessment for the entire delivery fleet"""
        all_deliveries = self.data_service.get_all_deliveries()
        active_deliveries = [d for d in all_deliveries if d.status != DeliveryStatus.DELIVERED]
        
        if not active_deliveries:
            return {
                "total_deliveries": 0,
                "active_deliveries": 0,
                "at_risk_count": 0,
                "critical_at_risk_count": 0,
                "average_risk_score": 0.0,
                "average_on_time_probability": 100.0
            }
        
        at_risk_deliveries = [d for d in active_deliveries if d.risk_score >= 60.0]
        critical_at_risk = [d for d in at_risk_deliveries if d.priority == DeliveryPriority.CRITICAL]
        
        avg_risk = sum(d.risk_score for d in active_deliveries) / len(active_deliveries)
        avg_on_time = sum(d.on_time_probability for d in active_deliveries) / len(active_deliveries)
        
        return {
            "total_deliveries": len(all_deliveries),
            "active_deliveries": len(active_deliveries),
            "at_risk_count": len(at_risk_deliveries),
            "critical_at_risk_count": len(critical_at_risk),
            "average_risk_score": round(avg_risk, 1),
            "average_on_time_probability": round(avg_on_time, 1)
        }
