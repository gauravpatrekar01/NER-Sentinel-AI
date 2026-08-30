from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database_sqlalchemy import Road, RoadStatus
from app.services.data_service import DataService
from app.ml.predictor import predict_road_risk
import logging

logger = logging.getLogger(__name__)

class RoadRiskService:
    """Service for calculating and managing road risk scores"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
    
    def calculate_road_risk(self, road_id: str) -> Dict[str, Any]:
        """
        Calculate risk score for a specific road based on current conditions.
        
        Returns:
            Dict with road_id, risk_score, accessibility_score, risk_level, 
            disruption_probability, and factors
        """
        road = self.data_service.get_road_by_id(road_id)
        if not road:
            raise ValueError(f"Road {road_id} not found")
        
        # Get current weather
        weather = self.data_service.get_latest_weather()
        rainfall = weather.rainfall_mm if weather else road.terrain_risk
        
        # Get active incidents for this road
        incidents = self.data_service.get_incidents_by_road(road_id, active_only=True)
        
        # Calculate field incident severity (0-4 scale)
        severity_map = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
        field_incident_severity = 0
        if incidents:
            field_incident_severity = max(
                [severity_map.get(inc.severity.value, 0) for inc in incidents]
            )
        
        # Run ML prediction
        prediction = predict_road_risk(
            rainfall=rainfall,
            terrain_risk=road.terrain_risk,
            historical_incidents=0,  # This would need to be added to Road model
            road_condition=road.road_condition,
            traffic=road.traffic_level,
            flood_risk=road.flood_risk,
            landslide_history=road.landslide_history,
            field_incident_severity=field_incident_severity
        )
        
        # Update road with new risk values
        self.data_service.update_road(
            road_id,
            risk_score=prediction["disruption_probability"] * 100,
            accessibility_score=prediction["accessibility_score"]
        )
        
        # Determine road status based on risk level
        if road.current_status == RoadStatus.BLOCKED:
            risk_level = "BLOCKED"
        else:
            risk_level = prediction["risk_level"]
            # Update status based on risk level
            if risk_level == "CRITICAL":
                self.data_service.update_road(road_id, current_status=RoadStatus.HIGH_RISK)
            elif risk_level == "HIGH":
                self.data_service.update_road(road_id, current_status=RoadStatus.HIGH_RISK)
            elif risk_level == "MODERATE":
                self.data_service.update_road(road_id, current_status=RoadStatus.MODERATE)
            else:
                self.data_service.update_road(road_id, current_status=RoadStatus.OPEN)
        
        logger.info(f"Calculated risk for road {road_id}: {prediction['risk_level']} ({prediction['disruption_probability']})")
        
        return {
            "road_id": road_id,
            "risk_score": round(prediction["disruption_probability"] * 100, 1),
            "accessibility_score": prediction["accessibility_score"],
            "risk_level": risk_level,
            "disruption_probability": prediction["disruption_probability"],
            "factors": prediction["factors"]
        }
    
    def recalculate_all_roads_risk(self) -> List[Dict[str, Any]]:
        """Recalculate risk scores for all roads in the system"""
        roads = self.data_service.get_all_roads()
        results = []
        
        for road in roads:
            try:
                result = self.calculate_road_risk(road.road_id)
                results.append(result)
            except Exception as e:
                logger.error(f"Error calculating risk for road {road.road_id}: {e}")
        
        return results
    
    def block_road(self, road_id: str) -> bool:
        """Mark a road as blocked"""
        road = self.data_service.get_road_by_id(road_id)
        if not road:
            return False
        
        self.data_service.update_road(
            road_id,
            current_status=RoadStatus.BLOCKED,
            accessibility_score=0.0,
            risk_score=100.0
        )
        
        # Commit the changes
        self.data_service.commit()
        
        logger.info(f"Road {road_id} marked as BLOCKED")
        return True
    
    def unblock_road(self, road_id: str) -> bool:
        """Unblock a road and recalculate its risk"""
        road = self.data_service.get_road_by_id(road_id)
        if not road:
            return False
        
        # Recalculate risk will determine the appropriate status
        self.calculate_road_risk(road_id)
        
        logger.info(f"Road {road_id} unblocked and risk recalculated")
        return True
    
    def get_high_risk_roads(self, threshold: float = 70.0) -> List[Road]:
        """Get roads with risk score above threshold"""
        roads = self.data_service.get_all_roads()
        return [r for r in roads if r.risk_score >= threshold]
    
    def get_road_network_health(self) -> Dict[str, Any]:
        """Get overall health metrics for the road network"""
        roads = self.data_service.get_all_roads()
        
        total_roads = len(roads)
        blocked_roads = len([r for r in roads if r.current_status == RoadStatus.BLOCKED])
        high_risk_roads = len([r for r in roads if r.current_status == RoadStatus.HIGH_RISK])
        
        avg_risk_score = sum(r.risk_score for r in roads) / total_roads if total_roads > 0 else 0
        avg_accessibility = sum(r.accessibility_score for r in roads) / total_roads if total_roads > 0 else 0
        
        return {
            "total_roads": total_roads,
            "blocked_roads": blocked_roads,
            "high_risk_roads": high_risk_roads,
            "accessible_roads": total_roads - blocked_roads,
            "average_risk_score": round(avg_risk_score, 1),
            "average_accessibility_score": round(avg_accessibility, 1),
            "network_health_percentage": round(avg_accessibility, 1)
        }
