from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from app.database_sqlalchemy import Road, RoadStatus
from app.services.data_service import DataService
import json
import logging

logger = logging.getLogger(__name__)

class RoutingProvider:
    """Abstract base class for routing providers"""
    
    def calculate_route(self, origin: str, destination: str, **kwargs) -> Dict[str, Any]:
        """Calculate a route between origin and destination"""
        raise NotImplementedError

class DemoRoutingProvider(RoutingProvider):
    """Deterministic routing provider for demo purposes"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
    
    def calculate_route(self, origin: str, destination: str, **kwargs) -> Dict[str, Any]:
        """Calculate a route using predefined demo routes"""
        # Demo routes for the Northeast India corridor
        demo_routes = {
            ("Guwahati", "Silchar"): {
                "primary": {
                    "route_id": "RT-NH6",
                    "name": "NH-6 Primary Corridor (via Shillong)",
                    "road_ids": ["R-204", "R-207", "R-211", "R-218"],
                    "distance_km": 290.0,
                    "base_time_hours": 5.8
                },
                "alternate": {
                    "route_id": "RT-NH27-54",
                    "name": "NH-27/NH-54 Alternate Corridor (via Haflong)",
                    "road_ids": ["R-301", "R-302", "R-303"],
                    "distance_km": 370.0,
                    "base_time_hours": 7.4
                }
            },
            ("Guwahati", "Shillong"): {
                "primary": {
                    "route_id": "RT-GHY-SHL",
                    "name": "Guwahati-Shillong Direct",
                    "road_ids": ["R-204"],
                    "distance_km": 100.0,
                    "base_time_hours": 1.7
                }
            },
            ("Shillong", "Silchar"): {
                "primary": {
                    "route_id": "RT-SHL-SIL",
                    "name": "Shillong-Silchar via Jowai",
                    "road_ids": ["R-207", "R-211", "R-218"],
                    "distance_km": 190.0,
                    "base_time_hours": 4.5
                }
            }
        }
        
        # Try to find matching route
        key = (origin, destination)
        if key in demo_routes:
            return demo_routes[key]
        
        # Return default route if not found
        return {
            "primary": {
                "route_id": "RT-DEFAULT",
                "name": "Default Route",
                "road_ids": [],
                "distance_km": 0.0,
                "base_time_hours": 0.0
            }
        }

class RouteService:
    """Service for route optimization and management"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
        self.routing_provider = DemoRoutingProvider(db)
    
    def find_alternative_routes(
        self, 
        origin: str, 
        destination: str, 
        blocked_roads: List[str] = None,
        priority: str = "NORMAL",
        emergency_mode: bool = False
    ) -> Dict[str, Any]:
        """
        Find alternative routes considering current road conditions.
        
        Returns:
            Dict with alternatives list and recommended_route
        """
        if blocked_roads is None:
            blocked_roads = []
        
        # Get available routes from routing provider
        route_options = self.routing_provider.calculate_route(origin, destination)
        
        alternatives = []
        
        # Process each route option
        for route_type, route_data in route_options.items():
            scored_route = self._score_route(
                route_data, 
                blocked_roads, 
                priority, 
                emergency_mode
            )
            if scored_route:
                alternatives.append(scored_route)
        
        # Sort by score (lower is better)
        alternatives.sort(key=lambda x: x["score"])
        
        # Select recommended route
        recommended_route = None
        if alternatives and not all(alt["is_blocked"] for alt in alternatives):
            recommended_route = next((alt for alt in alternatives if not alt["is_blocked"]), alternatives[0])
            recommended_route = recommended_route["route_id"] if recommended_route else None
        
        logger.info(f"Found {len(alternatives)} route alternatives from {origin} to {destination}. Recommended: {recommended_route}")
        
        return {
            "alternatives": alternatives,
            "recommended_route": recommended_route,
            "all_blocked": all(alt["is_blocked"] for alt in alternatives) if alternatives else True
        }
    
    def _score_route(
        self, 
        route_data: Dict[str, Any], 
        blocked_roads: List[str],
        priority: str,
        emergency_mode: bool
    ) -> Optional[Dict[str, Any]]:
        """Score a route based on multiple factors"""
        road_ids = route_data["road_ids"]
        
        # Check if route is blocked
        is_blocked = any(road_id in blocked_roads for road_id in road_ids)
        if is_blocked:
            return {
                **route_data,
                "is_blocked": True,
                "risk_score": 100.0,
                "travel_time_minutes": 9999,
                "score": 999999.0
            }
        
        # Get road details
        roads = []
        total_distance = 0.0
        total_time = 0.0
        max_risk = 0.0
        avg_risk = 0.0
        
        for road_id in road_ids:
            road = self.data_service.get_road_by_id(road_id)
            if road:
                roads.append(road)
                total_distance += road.distance_km
                
                # Calculate segment time based on road conditions
                base_speed = 50.0  # default km/h
                if road_id in ["R-204", "R-301"]:
                    base_speed = 60.0
                elif road_id in ["R-218", "R-302", "R-303"]:
                    base_speed = 35.0
                
                # Apply speed reduction based on risk
                speed_factor = 1.0
                if road.current_status == RoadStatus.HIGH_RISK:
                    speed_factor = 0.6
                elif road.current_status == RoadStatus.MODERATE:
                    speed_factor = 0.8
                
                actual_speed = base_speed * speed_factor
                segment_time = road.distance_km / actual_speed
                total_time += segment_time
                
                max_risk = max(max_risk, road.risk_score)
                avg_risk += road.risk_score
        
        if roads:
            avg_risk = avg_risk / len(roads)
        
        travel_time_minutes = total_time * 60
        
        # Calculate optimization score
        # Score = travel_time * (1 + risk_multiplier * max_risk)
        # Critical and High priority deliveries are more risk-averse
        risk_multiplier = 1.5
        if priority == "CRITICAL":
            risk_multiplier = 10.0
        elif priority == "HIGH":
            risk_multiplier = 5.0
        
        if emergency_mode:
            risk_multiplier *= 2.0
        
        cost_score = travel_time_minutes * (1.0 + risk_multiplier * (max_risk / 100.0))
        
        return {
            **route_data,
            "is_blocked": False,
            "risk_score": round(max_risk, 1),
            "travel_time_minutes": round(travel_time_minutes, 1),
            "score": round(cost_score, 1)
        }
    
    def optimize_route_for_delivery(self, delivery_id: str, blocked_roads: List[str] = None) -> Dict[str, Any]:
        """Optimize route for a specific delivery"""
        delivery = self.data_service.get_delivery_by_id(delivery_id)
        if not delivery:
            raise ValueError(f"Delivery {delivery_id} not found")
        
        try:
            current_route = json.loads(delivery.current_route) if isinstance(delivery.current_route, str) else delivery.current_route
        except:
            current_route = []
        
        if not current_route:
            return {"error": "No current route found for delivery"}
        
        origin = current_route[0]
        destination = current_route[-1]
        
        return self.find_alternative_routes(
            origin=origin,
            destination=destination,
            blocked_roads=blocked_roads or [],
            priority=delivery.priority.value,
            emergency_mode=False
        )
    
    def create_route_record(self, delivery_id: str, route_data: Dict[str, Any]) -> str:
        """Create a route record in the database"""
        route_id = f"RT-{delivery_id}-{route_data['route_id']}"
        
        route_record = {
            "route_id": route_id,
            "delivery_id": delivery_id,
            "name": route_data["name"],
            "path": json.dumps([]),  # Would be populated by actual routing service
            "distance_km": route_data["distance_km"],
            "travel_time_minutes": route_data["travel_time_minutes"],
            "road_ids": json.dumps(route_data["road_ids"]),
            "is_alternative": True
        }
        
        self.data_service.create_route(route_record)
        return route_id
