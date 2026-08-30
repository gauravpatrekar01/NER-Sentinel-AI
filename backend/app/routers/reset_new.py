from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db
from app.services.reset_service import ResetService

router = APIRouter(prefix="/reset", tags=["reset"])

@router.post("")
def reset_demo(db: Session = Depends(get_db)):
    reset_service = ResetService(db)
    result = reset_service.reset_demo()
    return result

@router.get("/status")
def get_reset_status(db: Session = Depends(get_db)):
    reset_service = ResetService(db)
    return reset_service.get_reset_status()

@router.post("/roads")
def reset_roads(db: Session = Depends(get_db)):
    reset_service = ResetService(db)
    return reset_service.reset_road_conditions()

@router.post("/incidents")
def reset_incidents(db: Session = Depends(get_db)):
    reset_service = ResetService(db)
    return reset_service.reset_incidents()

@router.post("/alerts")
def reset_alerts(db: Session = Depends(get_db)):
    reset_service = ResetService(db)
    return reset_service.reset_alerts()
