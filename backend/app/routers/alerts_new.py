from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db, Alert
from app.services.alert_service_new import AlertService
from app.services.data_service import DataService
from pydantic import BaseModel

router = APIRouter(prefix="/alerts", tags=["alerts"])

class AlertResponse(BaseModel):
    alert_id: str
    type: str
    severity: str
    title: str
    message: str
    road_id: str
    delivery_id: str
    vehicle_id: str
    timestamp: str
    read: bool

@router.get("", response_model=List[AlertResponse])
def get_alerts(unread_only: bool = False, db: Session = Depends(get_db)):
    data_service = DataService(db)
    alerts = data_service.get_all_alerts(unread_only=unread_only)
    return [
        AlertResponse(
            alert_id=a.alert_id,
            type=a.type.value,
            severity=a.severity.value,
            title=a.title,
            message=a.message,
            road_id=a.road_id,
            delivery_id=a.delivery_id,
            vehicle_id=a.vehicle_id,
            timestamp=a.timestamp.isoformat(),
            read=a.read
        )
        for a in alerts
    ]

@router.get("/summary")
def get_alert_summary(db: Session = Depends(get_db)):
    alert_service = AlertService(db)
    return alert_service.get_alert_summary()

@router.get("/critical")
def get_critical_alerts(db: Session = Depends(get_db)):
    alert_service = AlertService(db)
    alerts = alert_service.get_critical_alerts()
    return [
        AlertResponse(
            alert_id=a.alert_id,
            type=a.type.value,
            severity=a.severity.value,
            title=a.title,
            message=a.message,
            road_id=a.road_id,
            delivery_id=a.delivery_id,
            vehicle_id=a.vehicle_id,
            timestamp=a.timestamp.isoformat(),
            read=a.read
        )
        for a in alerts
    ]

@router.post("/{alert_id}/read")
def mark_alert_as_read(alert_id: str, db: Session = Depends(get_db)):
    alert_service = AlertService(db)
    success = alert_service.mark_as_read(alert_id)
    if not success:
        raise HTTPException(status_code=404, detail="Alert not found")
    return {"status": "success", "message": "Alert marked as read"}

@router.post("/read-all")
def mark_all_as_read(db: Session = Depends(get_db)):
    alert_service = AlertService(db)
    count = alert_service.mark_all_as_read()
    return {"status": "success", "marked_count": count}

@router.delete("/clear")
def clear_all_alerts(db: Session = Depends(get_db)):
    alert_service = AlertService(db)
    success = alert_service.clear_all_alerts()
    if not success:
        raise HTTPException(status_code=500, detail="Failed to clear alerts")
    return {"status": "success", "message": "All alerts cleared"}
