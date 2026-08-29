from fastapi import APIRouter
from app.database import reset_database
from app.services.risk_service import recalculate_all_roads_risk
from app.services.alert_service import clear_all_alerts

router = APIRouter(prefix="/reset", tags=["reset"])

@router.post("")
def trigger_reset():
    # 1. Reset database CSV files
    reset_database()
    
    # 2. Clear all active alerts
    clear_all_alerts()
    
    # 3. Recalculate initial risks
    recalculate_all_roads_risk()
    
    return {"status": "success", "message": "Demo state successfully reset to initial baseline values."}
