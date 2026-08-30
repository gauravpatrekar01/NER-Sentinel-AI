from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database_sqlalchemy import Road, Vehicle, Delivery, RoadStatus, DeliveryStatus, DeliveryPriority
from app.services.data_service import DataService
from app.services.road_risk_service import RoadRiskService
from app.services.delivery_risk_service_new import DeliveryRiskService
from app.services.route_service_new import RouteService
from app.services.eta_service_new import ETAService
import json
import logging
import copy

logger = logging.getLogger(__name__)

class SimulationService:
    """Service for running what-if scenarios and simulations"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
        self.road_risk_service = RoadRiskService(db)
        self.delivery_risk_service = DeliveryRiskService(db)
        self.route_service = RouteService(db)
        self.eta_service = ETAService(db)
    
    def run_scenario(self, scenario: str, rainfall_mm: float = None) -> Dict[str, Any]:
        """
        Run a simulation scenario comparing baseline vs optimized outcomes.
        
        Scenarios:
        - NORMAL: Normal operations
        - HEAVY_RAIN: Heavy rainfall conditions
        - FLOOD: Flooding conditions
        - LANDSLIDE: Landslide incident
        - MULTIPLE_ROAD_CLOSURES: Multiple roads blocked
        """
        logger.info(f"Running simulation scenario: {scenario}")
        
        # Get current state as baseline
        baseline_state = self._capture_current_state()
        
        # Apply scenario conditions
        scenario_state = self._apply_scenario_conditions(scenario, rainfall_mm, baseline_state)
        
        # Run baseline simulation (without optimization)
        baseline_results = self._run_baseline_simulation(scenario_state)
        
        # Run optimized simulation (with NER-Sentinel optimization)
        optimized_results = self._run_optimized_simulation(scenario_state)
        
        # Calculate comparison metrics
        comparison = self._compare_results(baseline_results, optimized_results)
        
        logger.info(f"Simulation complete. Baseline delayed: {baseline_results['delayed_count']}, Optimized delayed: {optimized_results['delayed_count']}")
        
        return {
            "scenario": scenario,
            "baseline": baseline_results,
            "optimized": optimized_results,
            "comparison": comparison
        }
    
    def _capture_current_state(self) -> Dict[str, Any]:
        """Capture the current state of the system"""
        roads = self.data_service.get_all_roads()
        vehicles = self.data_service.get_all_vehicles()
        deliveries = self.data_service.get_all_deliveries()
        
        return {
            "roads": [
                {
                    "road_id": r.road_id,
                    "current_status": r.current_status.value,
                    "risk_score": r.risk_score,
                    "distance_km": r.distance_km
                }
                for r in roads
            ],
            "vehicles": [
                {
                    "vehicle_id": v.vehicle_id,
                    "current_road_id": v.current_road_id,
                    "status": v.status.value,
                    "speed_kmh": v.speed_kmh
                }
                for v in vehicles
            ],
            "deliveries": [
                {
                    "delivery_id": d.delivery_id,
                    "vehicle_id": d.vehicle_id,
                    "priority": d.priority.value,
                    "cargo_type": d.cargo_type,
                    "status": d.status.value,
                    "current_route": d.current_route,
                    "risk_score": d.risk_score
                }
                for d in deliveries
            ]
        }
    
    def _apply_scenario_conditions(self, scenario: str, rainfall_mm: float, state: Dict[str, Any]) -> Dict[str, Any]:
        """Apply scenario conditions to a copy of the state"""
        scenario_state = copy.deepcopy(state)
        
        # Set rainfall if provided
        if rainfall_mm is None:
            rainfall_mm = 142.0  # Default heavy rain
        
        # Apply scenario-specific conditions
        blocked_roads = []
        
        if scenario == "LANDSLIDE":
            blocked_roads = ["R-204"]  # Primary corridor blocked
        elif scenario == "FLOOD":
            blocked_roads = ["R-218", "R-303"]  # Silchar approaches blocked
        elif scenario == "HEAVY_RAIN":
            blocked_roads = ["R-204"] if rainfall_mm > 150 else []
        elif scenario == "MULTIPLE_ROAD_CLOSURES":
            blocked_roads = ["R-204", "R-218", "R-303"]
        
        # Apply blockages to scenario state
        for road in scenario_state["roads"]:
            if road["road_id"] in blocked_roads:
                road["current_status"] = "BLOCKED"
                road["risk_score"] = 100.0
        
        scenario_state["blocked_roads"] = blocked_roads
        scenario_state["rainfall_mm"] = rainfall_mm
        
        return scenario_state
    
    def _run_baseline_simulation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run simulation without NER-Sentinel optimization"""
        blocked_roads = state.get("blocked_roads", [])
        
        delayed_count = 0
        total_delay_minutes = 0
        critical_affected = 0
        on_time_count = 0
        
        for delivery in state["deliveries"]:
            if delivery["status"] == "DELIVERED":
                on_time_count += 1
                continue
            
            try:
                route_segments = json.loads(delivery["current_route"]) if isinstance(delivery["current_route"], str) else delivery["current_route"]
            except:
                route_segments = []
            
            # Check if route is blocked
            is_blocked = any(road_id in blocked_roads for road_id in route_segments)
            
            if is_blocked:
                delayed_count += 1
                # Baseline: vehicles get stuck, significant delay
                delay = 240 + (30 * len(route_segments))  # 4 hours + 30 min per segment
                total_delay_minutes += delay
                
                if delivery["priority"] == "CRITICAL":
                    critical_affected += 1
            else:
                # Weather impact even if not blocked
                if state.get("rainfall_mm", 0) > 100:
                    delayed_count += 1
                    total_delay_minutes += 90  # 1.5 hours weather delay
                else:
                    on_time_count += 1
        
        total_deliveries = len(state["deliveries"])
        avg_delay = total_delay_minutes / delayed_count if delayed_count > 0 else 0
        on_time_pct = (on_time_count / total_deliveries * 100) if total_deliveries > 0 else 0
        
        return {
            "delayed_count": delayed_count,
            "average_delay_minutes": round(avg_delay, 1),
            "critical_affected": critical_affected,
            "on_time_percentage": round(on_time_pct, 1),
            "total_deliveries": total_deliveries
        }
    
    def _run_optimized_simulation(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Run simulation with NER-Sentinel optimization"""
        blocked_roads = state.get("blocked_roads", [])
        
        delayed_count = 0
        total_delay_minutes = 0
        critical_affected = 0
        on_time_count = 0
        routes_optimized = 0
        
        for delivery in state["deliveries"]:
            if delivery["status"] == "DELIVERED":
                on_time_count += 1
                continue
            
            try:
                route_segments = json.loads(delivery["current_route"]) if isinstance(delivery["current_route"], str) else delivery["current_route"]
            except:
                route_segments = []
            
            # Check if route is blocked
            is_blocked = any(road_id in blocked_roads for road_id in route_segments)
            
            if is_blocked:
                # Try to find alternate route
                has_alternate = self._has_alternate_route(route_segments, blocked_roads)
                
                if has_alternate:
                    # Successfully rerouted - smaller delay due to longer but passable route
                    delayed_count += 1
                    delay = 105  # ~1.75 hours for alternate route
                    total_delay_minutes += delay
                    routes_optimized += 1
                    
                    if delivery["priority"] == "CRITICAL":
                        # Critical deliveries might still be affected but less so
                        if delay > 60:
                            critical_affected += 1
                else:
                    # No alternate - stuck like baseline
                    delayed_count += 1
                    delay = 240 + (30 * len(route_segments))
                    total_delay_minutes += delay
                    
                    if delivery["priority"] == "CRITICAL":
                        critical_affected += 1
            else:
                # Weather impact with optimized flow management
                if state.get("rainfall_mm", 0) > 100:
                    delayed_count += 1
                    total_delay_minutes += 45  # Optimized weather response: 45 min vs 90 min
                else:
                    on_time_count += 1
        
        total_deliveries = len(state["deliveries"])
        avg_delay = total_delay_minutes / delayed_count if delayed_count > 0 else 0
        on_time_pct = (on_time_count / total_deliveries * 100) if total_deliveries > 0 else 0
        
        return {
            "delayed_count": delayed_count,
            "average_delay_minutes": round(avg_delay, 1),
            "critical_affected": critical_affected,
            "on_time_percentage": round(on_time_pct, 1),
            "total_deliveries": total_deliveries,
            "routes_optimized": routes_optimized
        }
    
    def _has_alternate_route(self, current_route: List[str], blocked_roads: List[str]) -> bool:
        """Check if an alternate route exists"""
        # Simplified logic: if not all possible routes are blocked, alternate exists
        # In real implementation, this would use the route service
        total_roads = ["R-204", "R-207", "R-211", "R-218", "R-301", "R-302", "R-303"]
        available_roads = [r for r in total_roads if r not in blocked_roads]
        return len(available_roads) >= 3  # Need at least some connectivity
    
    def _compare_results(self, baseline: Dict[str, Any], optimized: Dict[str, Any]) -> Dict[str, Any]:
        """Compare baseline and optimized results"""
        delayed_reduction = baseline["delayed_count"] - optimized["delayed_count"]
        delay_reduction_minutes = baseline["average_delay_minutes"] - optimized["average_delay_minutes"]
        critical_saved = baseline["critical_affected"] - optimized["critical_affected"]
        on_time_improvement = optimized["on_time_percentage"] - baseline["on_time_percentage"]
        
        improvement_percentage = 0
        if baseline["delayed_count"] > 0:
            improvement_percentage = (delayed_reduction / baseline["delayed_count"]) * 100
        
        return {
            "delayed_reduced": delayed_reduction,
            "delay_reduction_percentage": round(improvement_percentage, 1),
            "average_delay_reduction_minutes": round(delay_reduction_minutes, 1),
            "critical_deliveries_saved": critical_saved,
            "on_time_improvement_percentage": round(on_time_improvement, 1),
            "routes_optimized": optimized.get("routes_optimized", 0)
        }
    
    def run_landslide_demo(self) -> Dict[str, Any]:
        """Run the specific landslide demo scenario"""
        return self.run_scenario("LANDSLIDE", rainfall_mm=142.0)
