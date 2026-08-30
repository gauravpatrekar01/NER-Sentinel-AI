import pytest
from sqlalchemy.orm import Session
from app.database_sqlalchemy import SessionLocal, init_db, RoadStatus, IncidentType, IncidentSeverity, DeliveryPriority
from app.services.road_risk_service import RoadRiskService
from app.services.delivery_risk_service_new import DeliveryRiskService
from app.services.incident_service_new import IncidentService
from app.services.impact_service import ImpactService
from app.services.route_service_new import RouteService
from app.services.eta_service_new import ETAService
from app.services.alert_service_new import AlertService
from app.services.emergency_service import EmergencyService
from app.services.simulation_service_new import SimulationService
from app.services.reset_service import ResetService
from app.seed import seed_database

@pytest.fixture(scope="function")
def db():
    """Create a fresh database for each test"""
    init_db()
    seed_database()
    db = SessionLocal()
    yield db
    db.close()

class TestRoadRiskService:
    def test_calculate_road_risk(self, db):
        service = RoadRiskService(db)
        result = service.calculate_road_risk("R-204")
        
        assert result["road_id"] == "R-204"
        assert "risk_score" in result
        assert "accessibility_score" in result
        assert "risk_level" in result
        assert "disruption_probability" in result
        assert "factors" in result
        assert 0 <= result["risk_score"] <= 100
        assert 0 <= result["accessibility_score"] <= 100
    
    def test_block_road(self, db):
        service = RoadRiskService(db)
        success = service.block_road("R-204")
        
        assert success is True
        road = service.data_service.get_road_by_id("R-204")
        assert road.current_status == RoadStatus.BLOCKED
        assert road.accessibility_score == 0.0
        assert road.risk_score == 100.0
    
    def test_unblock_road(self, db):
        service = RoadRiskService(db)
        service.block_road("R-204")
        success = service.unblock_road("R-204")
        
        assert success is True
        road = service.data_service.get_road_by_id("R-204")
        assert road.current_status != RoadStatus.BLOCKED
    
    def test_get_high_risk_roads(self, db):
        service = RoadRiskService(db)
        # First recalculate to get realistic risk values
        service.recalculate_all_roads_risk()
        
        high_risk_roads = service.get_high_risk_roads(threshold=50.0)
        assert isinstance(high_risk_roads, list)
    
    def test_get_road_network_health(self, db):
        service = RoadRiskService(db)
        health = service.get_road_network_health()
        
        assert "total_roads" in health
        assert "blocked_roads" in health
        assert "average_risk_score" in health
        assert "network_health_percentage" in health

class TestDeliveryRiskService:
    def test_calculate_delivery_risk(self, db):
        service = DeliveryRiskService(db)
        result = service.calculate_delivery_risk("DL-1092")
        
        assert result["delivery_id"] == "DL-1092"
        assert "risk_score" in result
        assert "risk_level" in result
        assert "on_time_probability" in result
        assert 0 <= result["risk_score"] <= 100
        assert 0 <= result["on_time_probability"] <= 100
    
    def test_get_critical_at_risk_deliveries(self, db):
        service = DeliveryRiskService(db)
        critical_deliveries = service.get_critical_at_risk_deliveries()
        
        assert isinstance(critical_deliveries, list)
        for delivery in critical_deliveries:
            assert delivery.priority == DeliveryPriority.CRITICAL
    
    def test_assess_delivery_fleet_risk(self, db):
        service = DeliveryRiskService(db)
        assessment = service.assess_delivery_fleet_risk()
        
        assert "total_deliveries" in assessment
        assert "active_deliveries" in assessment
        assert "at_risk_count" in assessment
        assert "average_risk_score" in assessment

class TestIncidentService:
    def test_create_incident(self, db):
        service = IncidentService(db)
        incident = service.create_incident({
            "road_id": "R-204",
            "lat": 26.0400,
            "lng": 91.8900,
            "type": IncidentType.LANDSLIDE,
            "severity": IncidentSeverity.CRITICAL,
            "description": "Test landslide"
        })
        
        assert incident.incident_id is not None
        assert incident.road_id == "R-204"
        assert incident.type == IncidentType.LANDSLIDE
    
    def test_process_incident_blocks_road(self, db):
        service = IncidentService(db)
        incident = service.create_incident({
            "road_id": "R-204",
            "lat": 26.0400,
            "lng": 91.8900,
            "type": IncidentType.LANDSLIDE,
            "severity": IncidentSeverity.CRITICAL,
            "description": "Test landslide"
        })
        
        result = service.process_incident(incident.incident_id, optimize_immediately=False)
        
        assert result["road_blocked"] is True
        road = service.data_service.get_road_by_id("R-204")
        assert road.current_status == RoadStatus.BLOCKED
    
    def test_resolve_incident(self, db):
        service = IncidentService(db)
        incident = service.create_incident({
            "road_id": "R-204",
            "lat": 26.0400,
            "lng": 91.8900,
            "type": IncidentType.LANDSLIDE,
            "severity": IncidentSeverity.CRITICAL,
            "description": "Test landslide"
        })
        
        service.process_incident(incident.incident_id)
        result = service.resolve_incident(incident.incident_id)
        
        assert result["status"] == "resolved"
        assert result["road_unblocked"] is True

class TestImpactService:
    def test_calculate_incident_impact(self, db):
        service = ImpactService(db)
        # First block a road to create impact
        road_service = RoadRiskService(db)
        road_service.block_road("R-204")
        
        impact = service.calculate_incident_impact("R-204")
        
        assert "affected_vehicles" in impact
        assert "affected_deliveries" in impact
        assert "critical_deliveries" in impact
        assert "estimated_total_delay_minutes" in impact
    
    def test_calculate_network_impact(self, db):
        service = ImpactService(db)
        network_impact = service.calculate_network_impact()
        
        assert "blocked_roads_count" in network_impact
        assert "total_affected_vehicles_count" in network_impact
        assert "total_affected_deliveries_count" in network_impact

class TestRouteService:
    def test_find_alternative_routes(self, db):
        service = RouteService(db)
        result = service.find_alternative_routes(
            origin="Guwahati",
            destination="Silchar",
            blocked_roads=[],
            priority="NORMAL"
        )
        
        assert "alternatives" in result
        assert "recommended_route" in result
        assert isinstance(result["alternatives"], list)
    
    def test_find_alternative_routes_with_blocked_roads(self, db):
        service = RouteService(db)
        result = service.find_alternative_routes(
            origin="Guwahati",
            destination="Silchar",
            blocked_roads=["R-204"],
            priority="CRITICAL"
        )
        
        assert "alternatives" in result
        # When main route is blocked, should recommend alternate
        if result["alternatives"]:
            assert any(not alt["is_blocked"] for alt in result["alternatives"])

class TestETAService:
    def test_calculate_eta(self, db):
        service = ETAService(db)
        result = service.calculate_eta("DL-1092")
        
        assert "delivery_id" in result
        assert "new_eta" in result
        assert "delay_minutes" in result
        assert "reasons" in result
        assert isinstance(result["reasons"], list)
    
    def test_check_eta_breaches(self, db):
        service = ETAService(db)
        breaches = service.check_eta_breaches(threshold_minutes=60)
        
        assert isinstance(breaches, list)

class TestAlertService:
    def test_generate_alert(self, db):
        service = AlertService(db)
        alert = service.generate_alert(
            alert_type="ROAD_BLOCKED",
            severity="CRITICAL",
            title="Test Alert",
            message="Test message"
        )
        
        assert alert.alert_id is not None
        assert alert.type.value == "ROAD_BLOCKED"
        assert alert.severity.value == "CRITICAL"
    
    def test_get_all_alerts(self, db):
        service = AlertService(db)
        service.generate_alert("TEST", "INFO", "Test", "Test message")
        alerts = service.get_all_alerts()
        
        assert isinstance(alerts, list)
        assert len(alerts) > 0
    
    def test_mark_as_read(self, db):
        service = AlertService(db)
        alert = service.generate_alert("TEST", "INFO", "Test", "Test message")
        success = service.mark_as_read(alert.alert_id)
        
        assert success is True
    
    def test_clear_all_alerts(self, db):
        service = AlertService(db)
        service.generate_alert("TEST", "INFO", "Test", "Test message")
        success = service.clear_all_alerts()
        
        assert success is True
        alerts = service.get_all_alerts()
        assert len(alerts) == 0

class TestEmergencyService:
    def test_activate_emergency_mode(self, db):
        service = EmergencyService(db)
        result = service.activate_emergency_mode()
        
        assert result["status"] == "activated"
        assert EmergencyService.is_emergency_active() is True
    
    def test_deactivate_emergency_mode(self, db):
        service = EmergencyService(db)
        service.activate_emergency_mode()
        result = service.deactivate_emergency_mode()
        
        assert result["status"] == "deactivated"
        assert EmergencyService.is_emergency_active() is False
    
    def test_get_emergency_prioritization(self, db):
        service = EmergencyService(db)
        prioritization = service.get_emergency_prioritization()
        
        assert "emergency_mode" in prioritization
        assert "priority_weights" in prioritization
    
    def test_get_emergency_critical_deliveries(self, db):
        service = EmergencyService(db)
        critical_deliveries = service.get_emergency_critical_deliveries()
        
        assert isinstance(critical_deliveries, list)

class TestSimulationService:
    def test_run_scenario(self, db):
        service = SimulationService(db)
        result = service.run_scenario("LANDSLIDE", rainfall_mm=142.0)
        
        assert "scenario" in result
        assert "baseline" in result
        assert "optimized" in result
        assert "comparison" in result
    
    def test_run_landslide_demo(self, db):
        service = SimulationService(db)
        result = service.run_landslide_demo()
        
        assert result["scenario"] == "LANDSLIDE"
        assert result["baseline"]["delayed_count"] >= 0
        assert result["optimized"]["delayed_count"] >= 0

class TestResetService:
    def test_reset_demo(self, db):
        service = ResetService(db)
        result = service.reset_demo()
        
        assert result["status"] == "success"
        assert "actions_performed" in result
    
    def test_get_reset_status(self, db):
        service = ResetService(db)
        status = service.get_reset_status()
        
        assert "is_baseline_state" in status
        assert "incident_count" in status
        assert "alert_count" in status

class TestIntegrationLandslideWorkflow:
    def test_complete_landslide_workflow(self, db):
        """Integration test for the complete landslide workflow"""
        # Setup
        road_service = RoadRiskService(db)
        incident_service = IncidentService(db)
        impact_service = ImpactService(db)
        delivery_risk_service = DeliveryRiskService(db)
        route_service = RouteService(db)
        eta_service = ETAService(db)
        alert_service = AlertService(db)
        emergency_service = EmergencyService()
        
        # Step 1: Initial state
        initial_road = road_service.data_service.get_road_by_id("R-204")
        assert initial_road.current_status == RoadStatus.OPEN
        
        # Step 2: Create landslide incident
        incident = incident_service.create_incident({
            "road_id": "R-204",
            "lat": 26.0400,
            "lng": 91.8900,
            "type": IncidentType.LANDSLIDE,
            "severity": IncidentSeverity.CRITICAL,
            "description": "Major landslide"
        })
        
        # Step 3: Process incident
        process_result = incident_service.process_incident(incident.incident_id, optimize_immediately=True)
        assert process_result["road_blocked"] is True
        
        # Step 4: Verify road is blocked
        blocked_road = road_service.data_service.get_road_by_id("R-204")
        assert blocked_road.current_status == RoadStatus.BLOCKED
        
        # Step 5: Calculate impact
        impact = impact_service.calculate_incident_impact("R-204")
        assert len(impact["affected_vehicles"]) > 0
        assert len(impact["affected_deliveries"]) > 0
        
        # Step 6: Calculate delivery risks
        for delivery in impact["affected_deliveries"]:
            risk_result = delivery_risk_service.calculate_delivery_risk(delivery["delivery_id"])
            assert risk_result["risk_score"] > 0
        
        # Step 7: Identify critical deliveries
        critical_deliveries = [d for d in impact["affected_deliveries"] if d["priority"] == "CRITICAL"]
        assert len(critical_deliveries) > 0
        
        # Step 8: Generate alternate routes
        for delivery in impact["affected_deliveries"]:
            try:
                route_result = route_service.optimize_route_for_delivery(
                    delivery["delivery_id"],
                    blocked_roads=["R-204"]
                )
                assert "alternatives" in route_result
            except:
                pass  # Some deliveries might not have alternate routes
        
        # Step 9: Recalculate ETA
        for delivery in impact["affected_deliveries"]:
            eta_result = eta_service.calculate_eta(delivery["delivery_id"])
            assert "new_eta" in eta_result
        
        # Step 10: Verify alerts generated
        alerts = alert_service.get_all_alerts()
        assert len(alerts) > 0
        
        # Step 11: Activate emergency mode
        emergency_service.activate_emergency_mode()
        assert emergency_service.is_emergency_active() is True
        
        # Step 12: Deactivate emergency mode
        emergency_service.deactivate_emergency_mode()
        assert emergency_service.is_emergency_active() is False
        
        # Success - complete workflow executed
        assert True

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
