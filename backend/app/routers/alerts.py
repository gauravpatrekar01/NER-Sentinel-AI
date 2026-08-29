from fastapi import APIRouter, HTTPException
from typing import List
from app.database import load_alerts, save_alerts
from app.models.models import Alert
from app.services.alert_service import clear_all_alerts

router = APIRouter(prefix="/alerts", tags=["alerts"])

@router.get("", response_model=List[Alert])
def get_alerts():
    return load_alerts()

@router.post("/read/{alert_id}")
def read_alert(alert_id: str):
    alerts = load_alerts()
    alert = next((a for a in alerts if a.alert_id == alert_id), None)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    alert.read = True
    save_alerts(alerts)
    return {"status": "success"}

@router.post("/clear")
def clear_alerts():
    clear_all_alerts()
    return {"status": "success"}
