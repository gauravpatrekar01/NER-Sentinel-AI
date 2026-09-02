from fastapi import APIRouter
from app.database import reset_database
from app.services.risk_service import recalculate_all_roads_risk
from app.services.app_state import set_emergency_mode
from app.services.alert_engine import clear_all_alerts
from app.services.graph_engine import invalidate_graph_cache

router = APIRouter(prefix="/reset", tags=["reset"])

@router.post("")
def trigger_reset():
    reset_database()
    clear_all_alerts()
    set_emergency_mode(False)
    invalidate_graph_cache()
    recalculate_all_roads_risk()
    return {"status": "success", "message": "Demo state successfully reset to initial baseline values."}