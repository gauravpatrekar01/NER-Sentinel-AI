from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db
from app.demo import run_landslide_demo, reset_demo

router = APIRouter(prefix="/demo", tags=["demo"])

@router.post("/landslide")
def trigger_landslide_demo(db: Session = Depends(get_db)):
    """Trigger the complete landslide demonstration scenario"""
    result = run_landslide_demo()
    return result

@router.post("/reset")
def trigger_demo_reset(db: Session = Depends(get_db)):
    """Reset the demo to initial state"""
    result = reset_demo()
    return result
