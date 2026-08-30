from sqlalchemy.orm import Session
from app.database_sqlalchemy import SessionLocal, IncidentType, IncidentSeverity
from app.services.incident_service_new import IncidentService
from app.services.road_risk_service import RoadRiskService
from app.services.delivery_risk_service_new import DeliveryRiskService
from app.services.impact_service import ImpactService
from app.services.route_service_new import RouteService
from app.services.eta_service_new import ETAService
from app.services.alert_service_new import AlertService
from app.services.emergency_service import EmergencyService
from app.services.simulation_service_new import SimulationService
from app.services.reset_service import ResetService
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_landslide_demo() -> dict:
    """
    Run the complete landslide demonstration scenario.
    
    This function orchestrates the entire workflow:
    1. Find R-204
    2. Create landslide incident
    3. Mark R-204 as blocked
    4. Recalculate road risk
    5. Find affected vehicles
    6. Find affected deliveries
    7. Calculate delivery risk
    8. Identify critical shipments
    9. Generate alternate routes
    10. Select recommended route
    11. Recalculate ETA
    12. Generate alerts
    13. Return complete structured result
    """
    db = SessionLocal()
    
    try:
        logger.info("=" * 80)
        logger.info("STARTING LANDSLIDE DEMO SCENARIO")
        logger.info("=" * 80)
        
        # Initialize services
        incident_service = IncidentService(db)
        road_risk_service = RoadRiskService(db)
        delivery_risk_service = DeliveryRiskService(db)
        impact_service = ImpactService(db)
        route_service = RouteService(db)
        eta_service = ETAService(db)
        alert_service = AlertService(db)
        emergency_service = EmergencyService()
        simulation_service = SimulationService(db)
        reset_service = ResetService(db)
        
        # Step 1: Find R-204
        logger.info("Step 1: Finding R-204 (Guwahati-Shillong Highway)")
        road_r204 = road_risk_service.data_service.get_road_by_id("R-204")
        if not road_r204:
            raise ValueError("R-204 not found in database")
        
        logger.info(f"Found R-204: {road_r204.name}, Status: {road_r204.current_status.value}")
        
        # Step 2: Create landslide incident
        logger.info("Step 2: Creating landslide incident on R-204")
        incident = incident_service.create_incident({
            "road_id": "R-204",
            "lat": 26.0400,
            "lng": 91.8900,
            "type": IncidentType.LANDSLIDE,
            "severity": IncidentSeverity.CRITICAL,
            "description": "Major landslide reported on NH-6 near Shillong. Road completely blocked.",
            "active": True
        })
        
        logger.info(f"Created incident: {incident.incident_id}")
        
        # Step 3: Process incident (this will block road, recalculate risk, etc.)
        logger.info("Step 3: Processing incident cascade")
        process_result = incident_service.process_incident(incident.incident_id, optimize_immediately=True)
        
        # Step 4: Verify R-204 is blocked
        logger.info("Step 4: Verifying R-204 status")
        updated_road = road_risk_service.data_service.get_road_by_id("R-204")
        logger.info(f"R-204 Status: {updated_road.current_status.value}, Risk Score: {updated_road.risk_score}")
        
        # Step 5: Calculate impact
        logger.info("Step 5: Calculating incident impact")
        impact = impact_service.calculate_incident_impact("R-204")
        logger.info(f"Affected vehicles: {len(impact['affected_vehicles'])}")
        logger.info(f"Affected deliveries: {len(impact['affected_deliveries'])}")
        logger.info(f"Critical deliveries: {len(impact['critical_deliveries'])}")
        
        # Step 6: Recalculate delivery risks
        logger.info("Step 6: Recalculating delivery risks")
        for delivery in impact['affected_deliveries']:
            try:
                risk_result = delivery_risk_service.calculate_delivery_risk(delivery['delivery_id'])
                logger.info(f"Delivery {delivery['delivery_id']} risk: {risk_result['risk_level']} ({risk_result['risk_score']}%)")
            except Exception as e:
                logger.error(f"Error calculating risk for delivery {delivery['delivery_id']}: {e}")
        
        # Step 7: Check for critical shipments
        logger.info("Step 7: Identifying critical shipments")
        critical_deliveries = [d for d in impact['affected_deliveries'] if d['priority'] == 'CRITICAL']
        logger.info(f"Critical shipments at risk: {len(critical_deliveries)}")
        for cd in critical_deliveries:
            logger.info(f"  - {cd['delivery_id']}: {cd['cargo_type']} to {cd['destination']}")
        
        # Step 8: Generate alternate routes (this is done in process_incident, but let's verify)
        logger.info("Step 8: Verifying alternate route generation")
        # Check if vehicle V-104 was rerouted
        vehicle_v104 = road_risk_service.data_service.get_vehicle_by_id("V-104")
        if vehicle_v104:
            logger.info(f"Vehicle V-104 current road: {vehicle_v104.current_road_id}")
        
        # Step 9: Recalculate ETA
        logger.info("Step 9: Recalculating ETAs")
        eta_updates = []
        for delivery in impact['affected_deliveries']:
            try:
                eta_result = eta_service.calculate_eta(delivery['delivery_id'])
                eta_updates.append(eta_result)
                logger.info(f"Delivery {delivery['delivery_id']} ETA: {eta_result['new_eta']} (delay: {eta_result['delay_minutes']}m)")
            except Exception as e:
                logger.error(f"Error calculating ETA for delivery {delivery['delivery_id']}: {e}")
        
        # Step 10: Check alerts
        logger.info("Step 10: Checking generated alerts")
        alerts = alert_service.get_all_alerts()
        logger.info(f"Total alerts generated: {len(alerts)}")
        for alert in alerts[:5]:  # Show first 5 alerts
            logger.info(f"  - {alert.type.value}: {alert.title}")
        
        # Step 11: Activate emergency mode
        logger.info("Step 11: Activating emergency mode")
        emergency_result = emergency_service.activate_emergency_mode()
        logger.info(f"Emergency mode: {emergency_result['status']}")
        
        # Step 12: Run simulation comparison
        logger.info("Step 12: Running simulation comparison")
        sim_result = simulation_service.run_landslide_demo()
        logger.info(f"Baseline delayed: {sim_result['baseline']['delayed_count']}")
        logger.info(f"Optimized delayed: {sim_result['optimized']['delayed_count']}")
        logger.info(f"Improvement: {sim_result['comparison']['delayed_reduction_percentage']}%")
        
        # Compile final result
        final_result = {
            "incident": {
                "incident_id": incident.incident_id,
                "type": incident.type.value,
                "severity": incident.severity.value,
                "road_id": incident.road_id
            },
            "road": {
                "road_id": updated_road.road_id,
                "name": updated_road.name,
                "status": updated_road.current_status.value,
                "risk_score": updated_road.risk_score,
                "accessibility_score": updated_road.accessibility_score
            },
            "impact": impact,
            "risk": {
                "affected_deliveries_count": len(impact['affected_deliveries']),
                "critical_deliveries_count": len(impact['critical_deliveries']),
                "average_risk_score": sum(d['risk_score'] for d in impact['affected_deliveries']) / len(impact['affected_deliveries']) if impact['affected_deliveries'] else 0
            },
            "routes": {
                "vehicles_rerouted": process_result.get('affected_vehicles_count', 0),
                "optimization_applied": True
            },
            "eta_updates": eta_updates,
            "alerts": [
                {
                    "alert_id": a.alert_id,
                    "type": a.type.value,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message
                }
                for a in alerts[:10]
            ],
            "emergency_mode": {
                "active": emergency_service.is_emergency_active(),
                "status": emergency_result['status']
            },
            "simulation": {
                "baseline": sim_result['baseline'],
                "optimized": sim_result['optimized'],
                "comparison": sim_result['comparison']
            }
        }
        
        logger.info("=" * 80)
        logger.info("LANDSLIDE DEMO COMPLETED SUCCESSFULLY")
        logger.info("=" * 80)
        
        return final_result
        
    except Exception as e:
        logger.error(f"Error in landslide demo: {e}")
        raise
    finally:
        db.close()

def reset_demo() -> dict:
    """Reset the demo to initial state"""
    db = SessionLocal()
    try:
        reset_service = ResetService(db)
        result = reset_service.reset_demo()
        logger.info("Demo reset completed")
        return result
    finally:
        db.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "reset":
        print("Resetting demo...")
        reset_demo()
    else:
        print("Running landslide demo...")
        result = run_landslide_demo()
        print("\n" + "=" * 80)
        print("DEMO SUMMARY")
        print("=" * 80)
        print(f"Incident: {result['incident']['incident_id']} - {result['incident']['type']}")
        print(f"Road Status: {result['road']['status']} (Risk: {result['road']['risk_score']}%)")
        print(f"Affected Vehicles: {result['impact']['affected_vehicles_count']}")
        print(f"Affected Deliveries: {result['impact']['affected_deliveries_count']}")
        print(f"Critical Deliveries: {result['impact']['critical_deliveries_count']}")
        print(f"Estimated Delay: {result['impact']['estimated_total_delay_str']}")
        print(f"Emergency Mode: {result['emergency_mode']['active']}")
        print(f"Baseline Delayed: {result['simulation']['baseline']['delayed_count']}")
        print(f"Optimized Delayed: {result['simulation']['optimized']['delayed_count']}")
        print(f"Improvement: {result['simulation']['comparison']['delayed_reduction_percentage']}%")
