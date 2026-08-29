import time
import uuid
from typing import List
from app.database import load_alerts, save_alerts
from app.models.models import Alert

def generate_alert(alert_type: str, message: str, severity: str = "WARNING") -> Alert:
    alerts = load_alerts()
    
    new_alert = Alert(
        alert_id=f"AL-{uuid.uuid4().hex[:6].upper()}",
        type=alert_type,
        message=message,
        timestamp=time.time(),
        severity=severity,
        read=False
    )
    
    alerts.insert(0, new_alert)  # Add at the beginning (latest first)
    
    # Cap alerts
    if len(alerts) > 50:
        alerts = alerts[:50]
        
    save_alerts(alerts)
    return new_alert

def clear_all_alerts():
    save_alerts([])
