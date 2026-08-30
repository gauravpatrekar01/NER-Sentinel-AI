from sqlalchemy.orm import Session
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta
from app.database_sqlalchemy import Delivery, Vehicle, Road, RoadStatus
from app.services.data_service import DataService
import json
import logging

logger = logging.getLogger(__name__)

class ETAService:
    """Service for calculating and managing Estimated Time of Arrival"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
    
    def calculate_eta(self, delivery_id: str) -> Dict[str, Any]:
        """
        Calculate ETA for a specific delivery based on current conditions.
        
        Returns:
            Dict with original_eta, new_eta, delay_minutes, and reasons
        """
        delivery = self.data_service.get_delivery_by_id(delivery_id)
        if not delivery:
            raise ValueError(f"Delivery {delivery_id} not found")
        
        vehicle = self.data_service.get_vehicle_by_id(delivery.vehicle_id)
        if not vehicle:
            raise ValueError(f"Vehicle {delivery.vehicle_id} not found")
        
        original_eta = delivery.original_eta
        if not original_eta:
            original_eta = datetime.now() + timedelta(hours=2)  # Default fallback
        
        # Get route segments
        try:
            route_segments = json.loads(delivery.current_route) if isinstance(delivery.current_route, str) else delivery.current_route
        except:
            route_segments = []
        
        # Calculate total distance and check for blocked roads
        total_distance = 0.0
        blocked_segments = []
        risk_factors = []
        
        for road_id in route_segments:
            road = self.data_service.get_road_by_id(road_id)
            if road:
                total_distance += road.distance_km
                if road.current_status == RoadStatus.BLOCKED:
                    blocked_segments.append(road.name)
                if road.risk_score > 50:
                    risk_factors.append(f"High risk on {road.name}")
        
        # Calculate remaining distance based on vehicle progress
        # For simplicity, assume progress is stored elsewhere or calculate from current position
        remaining_distance = total_distance  # Full route for now
        
        # Calculate effective speed
        base_speed = vehicle.speed_kmh if vehicle.speed_kmh > 0 else 40.0
        
        # Apply speed reduction factors
        speed_multiplier = 1.0
        
        if blocked_segments:
            speed_multiplier = 0.1  # Severely impacted
        elif risk_factors:
            speed_multiplier = 0.7  # Moderately impacted
        
        # Weather impact (would get from weather service)
        weather = self.data_service.get_latest_weather()
        if weather and weather.rainfall_mm > 100:
            speed_multiplier *= 0.8
        
        actual_speed = base_speed * speed_multiplier
        
        # Calculate travel time
        travel_time_hours = remaining_distance / actual_speed if actual_speed > 0 else 999
        new_eta = datetime.now() + timedelta(hours=travel_time_hours)
        
        # Calculate delay
        delay_minutes = int((new_eta - original_eta).total_seconds() / 60)
        
        # Determine reasons for delay
        reasons = []
        if blocked_segments:
            reasons.append(f"Blocked roads: {', '.join(blocked_segments)}")
        if risk_factors:
            reasons.extend(risk_factors)
        if weather and weather.rainfall_mm > 100:
            reasons.append("Heavy rainfall")
        if vehicle.current_route_id != vehicle.current_road_id:  # Route changed
            reasons.append("Route changed to alternate path")
        
        if not reasons:
            reasons.append("Normal operations")
        
        # Update delivery with new ETA
        self.data_service.update_delivery(
            delivery_id,
            eta=new_eta,
            delay_reason="; ".join(reasons) if reasons else ""
        )
        
        logger.info(f"ETA calculated for delivery {delivery_id}: {new_eta.strftime('%H:%M')} (delay: {delay_minutes}m)")
        
        return {
            "delivery_id": delivery_id,
            "original_eta": original_eta.strftime("%H:%M") if original_eta else None,
            "new_eta": new_eta.strftime("%H:%M"),
            "delay_minutes": delay_minutes,
            "reasons": reasons,
            "actual_speed_kmh": round(actual_speed, 1),
            "remaining_distance_km": round(remaining_distance, 1)
        }
    
    def calculate_batch_eta(self, delivery_ids: list = None) -> Dict[str, Any]:
        """Calculate ETA for multiple deliveries"""
        if delivery_ids is None:
            # Calculate for all active deliveries
            from app.database_sqlalchemy import DeliveryStatus
            deliveries = self.data_service.get_deliveries_by_status(DeliveryStatus.EN_ROUTE)
            delivery_ids = [d.delivery_id for d in deliveries]
        
        results = []
        for delivery_id in delivery_ids:
            try:
                result = self.calculate_eta(delivery_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error calculating ETA for delivery {delivery_id}: {e}")
        
        return {
            "total_calculated": len(results),
            "results": results
        }
    
    def get_eta_forecast(self, delivery_id: str, hours_ahead: int = 24) -> Dict[str, Any]:
        """Get ETA forecast considering predicted conditions"""
        delivery = self.data_service.get_delivery_by_id(delivery_id)
        if not delivery:
            raise ValueError(f"Delivery {delivery_id} not found")
        
        # Simple forecast: current ETA with confidence intervals
        current_eta = self.calculate_eta(delivery_id)
        
        # Calculate optimistic and pessimistic scenarios
        optimistic_delay = max(0, current_eta["delay_minutes"] - 30)
        pessimistic_delay = current_eta["delay_minutes"] + 60
        
        base_time = datetime.now()
        optimistic_eta = base_time + timedelta(minutes=optimistic_delay)
        pessimistic_eta = base_time + timedelta(minutes=pessimistic_delay)
        
        return {
            "delivery_id": delivery_id,
            "current_eta": current_eta["new_eta"],
            "optimistic_eta": optimistic_eta.strftime("%H:%M"),
            "pessimistic_eta": pessimistic_eta.strftime("%H:%M"),
            "confidence": "HIGH" if current_eta["delay_minutes"] < 60 else "MEDIUM"
        }
    
    def check_eta_breaches(self, threshold_minutes: int = 60) -> list:
        """Check for deliveries that will breach ETA threshold"""
        from app.database_sqlalchemy import DeliveryStatus
        
        active_deliveries = self.data_service.get_deliveries_by_status(DeliveryStatus.EN_ROUTE)
        breaches = []
        
        for delivery in active_deliveries:
            try:
                eta_result = self.calculate_eta(delivery.delivery_id)
                if eta_result["delay_minutes"] > threshold_minutes:
                    breaches.append({
                        "delivery_id": delivery.delivery_id,
                        "cargo_type": delivery.cargo_type,
                        "priority": delivery.priority.value,
                        "delay_minutes": eta_result["delay_minutes"],
                        "new_eta": eta_result["new_eta"]
                    })
            except Exception as e:
                logger.error(f"Error checking ETA breach for delivery {delivery.delivery_id}: {e}")
        
        return breaches
