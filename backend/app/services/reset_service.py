from sqlalchemy.orm import Session
from typing import Dict, Any
from app.database_sqlalchemy import (
    SessionLocal, Alert, Simulation, Route, Incident, 
    WeatherObservation, Delivery, VehicleTelemetry, Vehicle, Road, RoadStatus
)
from app.services.data_service import DataService
from app.services.road_risk_service import RoadRiskService
from app.services.delivery_risk_service_new import DeliveryRiskService
from app.services.emergency_service import EmergencyService
from app.services.alert_service_new import AlertService
from app.seed import seed_database
import logging

logger = logging.getLogger(__name__)

class ResetService:
    """Service for resetting the system to initial state"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
        self.road_risk_service = RoadRiskService(db)
        self.delivery_risk_service = DeliveryRiskService(db)
        self.alert_service = AlertService(db)
    
    def reset_demo(self) -> Dict[str, Any]:
        """
        Reset the entire system to the initial seeded state.
        This restores roads, vehicles, deliveries, incidents, alerts, routes, 
        ETA, risk values, and emergency state.
        """
        logger.info("Starting system reset to initial state")
        
        try:
            # Step 1: Clear all dynamic data
            self._clear_dynamic_data()
            
            # Step 2: Reseed the database with initial data
            seed_success = seed_database()
            if not seed_success:
                raise Exception("Failed to seed database")
            
            # Step 3: Deactivate emergency mode
            EmergencyService.deactivate_emergency_mode()
            
            # Step 4: Recalculate initial risks
            self.road_risk_service.recalculate_all_roads_risk()
            self.delivery_risk_service.recalculate_all_deliveries_risk()
            
            # Step 5: Clear all alerts
            self.alert_service.clear_all_alerts()
            
            logger.info("System reset completed successfully")
            
            return {
                "status": "success",
                "message": "Demo state successfully reset to initial baseline values",
                "timestamp": None,
                "actions_performed": [
                    "Cleared dynamic data",
                    "Reseeded database",
                    "Deactivated emergency mode",
                    "Recalculated road risks",
                    "Recalculated delivery risks",
                    "Cleared alerts"
                ]
            }
            
        except Exception as e:
            logger.error(f"Error during system reset: {e}")
            return {
                "status": "error",
                "message": f"Reset failed: {str(e)}",
                "timestamp": None
            }
    
    def _clear_dynamic_data(self) -> None:
        """Clear all dynamic data while preserving schema"""
        db = SessionLocal()
        try:
            # Clear in order of dependencies
            db.query(Alert).delete()
            db.query(Simulation).delete()
            db.query(Route).delete()
            db.query(Incident).delete()
            db.query(WeatherObservation).delete()
            db.query(Delivery).delete()
            db.query(VehicleTelemetry).delete()
            db.query(Vehicle).delete()
            db.query(Road).delete()
            db.commit()
        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()
    
    def reset_road_conditions(self) -> Dict[str, Any]:
        """Reset only road conditions to initial state"""
        logger.info("Resetting road conditions")
        
        try:
            roads = self.data_service.get_all_roads()
            
            from app.database_sqlalchemy import RoadStatus
            
            for road in roads:
                self.data_service.update_road(
                    road.road_id,
                    current_status=RoadStatus.OPEN,
                    risk_score=0.0,
                    accessibility_score=100.0
                )
            
            # Recalculate risks based on baseline conditions
            self.road_risk_service.recalculate_all_roads_risk()
            
            return {
                "status": "success",
                "message": f"Reset {len(roads)} roads to initial conditions",
                "roads_reset": len(roads)
            }
            
        except Exception as e:
            logger.error(f"Error resetting road conditions: {e}")
            return {
                "status": "error",
                "message": f"Failed to reset road conditions: {str(e)}"
            }
    
    def reset_incidents(self) -> Dict[str, Any]:
        """Clear all incidents and recalculate impacts"""
        logger.info("Clearing all incidents")
        
        try:
            db = SessionLocal()
            try:
                db.query(Incident).delete()
                db.commit()
            except Exception as e:
                db.rollback()
                raise e
            finally:
                db.close()
            
            # Recalculate road risks without incidents
            self.road_risk_service.recalculate_all_roads_risk()
            
            return {
                "status": "success",
                "message": "All incidents cleared and road risks recalculated"
            }
            
        except Exception as e:
            logger.error(f"Error resetting incidents: {e}")
            return {
                "status": "error",
                "message": f"Failed to reset incidents: {str(e)}"
            }
    
    def reset_alerts(self) -> Dict[str, Any]:
        """Clear all alerts"""
        logger.info("Clearing all alerts")
        
        try:
            success = self.alert_service.clear_all_alerts()
            
            return {
                "status": "success" if success else "error",
                "message": "All alerts cleared" if success else "Failed to clear alerts"
            }
            
        except Exception as e:
            logger.error(f"Error resetting alerts: {e}")
            return {
                "status": "error",
                "message": f"Failed to reset alerts: {str(e)}"
            }
    
    def get_reset_status(self) -> Dict[str, Any]:
        """Get current reset status to understand system state"""
        db = SessionLocal()
        try:
            incident_count = db.query(Incident).count()
            alert_count = db.query(Alert).count()
            blocked_roads_count = db.query(Road).filter(
                Road.current_status == "BLOCKED"
            ).count()
            
            emergency_active = EmergencyService.is_emergency_active()
            
            # Determine if system is in baseline state
            is_baseline = (
                incident_count == 0 and
                alert_count == 0 and
                blocked_roads_count == 0 and
                not emergency_active
            )
            
            return {
                "is_baseline_state": is_baseline,
                "incident_count": incident_count,
                "alert_count": alert_count,
                "blocked_roads_count": blocked_roads_count,
                "emergency_mode_active": emergency_active,
                "system_health": "BASELINE" if is_baseline else "MODIFIED"
            }
            
        except Exception as e:
            logger.error(f"Error getting reset status: {e}")
            return {
                "is_baseline_state": False,
                "error": str(e)
            }
        finally:
            db.close()
