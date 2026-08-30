from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db
from app.services.emergency_service import EmergencyService
from app.services.data_service import DataService

router = APIRouter(prefix="/emergency", tags=["emergency"])

@router.post("/activate")
def activate_emergency_mode(db: Session = Depends(get_db)):
    emergency_service = EmergencyService(db)
    result = emergency_service.activate_emergency_mode()
    return result

@router.post("/deactivate")
def deactivate_emergency_mode(db: Session = Depends(get_db)):
    emergency_service = EmergencyService(db)
    result = emergency_service.deactivate_emergency_mode()
    return result

@router.get("/status")
def get_emergency_status(db: Session = Depends(get_db)):
    emergency_service = EmergencyService(db)
    return {
        "active": emergency_service.is_emergency_active(),
        "prioritization": emergency_service.get_emergency_prioritization()
    }

@router.get("/critical-deliveries")
def get_emergency_critical_deliveries(db: Session = Depends(get_db)):
    emergency_service = EmergencyService(db)
    deliveries = emergency_service.get_emergency_critical_deliveries()
    return {
        "critical_deliveries": deliveries,
        "count": len(deliveries)
    }

@router.get("/readiness")
def get_emergency_readiness(db: Session = Depends(get_db)):
    emergency_service = EmergencyService(db)
    return emergency_service.assess_emergency_readiness()

@router.post("/optimize")
def optimize_for_emergency(db: Session = Depends(get_db)):
    emergency_service = EmergencyService(db)
    return emergency_service.optimize_for_emergency()
