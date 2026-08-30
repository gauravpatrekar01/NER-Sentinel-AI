from sqlalchemy.orm import Session
from typing import Dict, Any, List
from app.database_sqlalchemy import Alert, AlertType, AlertSeverity
from app.services.data_service import DataService
import uuid
import logging

logger = logging.getLogger(__name__)

class AlertService:
    """Service for generating and managing alerts"""
    
    def __init__(self, db: Session):
        self.data_service = DataService(db)
    
    def generate_alert(
        self, 
        alert_type: str, 
        severity: str = "WARNING",
        title: str = None,
        message: str = "",
        road_id: str = None,
        delivery_id: str = None,
        vehicle_id: str = None
    ) -> Alert:
        """Generate a new alert"""
        alert_id = f"AL-{uuid.uuid4().hex[:6].upper()}"
        
        # Map string types to enums
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            alert_type_enum = AlertType.OTHER
        
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            severity_enum = AlertSeverity.WARNING
        
        alert_data = {
            "alert_id": alert_id,
            "type": alert_type_enum,
            "severity": severity_enum,
            "title": title or f"{alert_type.replace('_', ' ').title()}",
            "message": message,
            "road_id": road_id,
            "delivery_id": delivery_id,
            "vehicle_id": vehicle_id
        }
        
        alert = self.data_service.create_alert(alert_data)
        logger.info(f"Generated alert {alert_id}: {alert_type} - {message[:50]}...")
        
        return alert
    
    def get_all_alerts(self, unread_only: bool = False, limit: int = 50) -> List[Alert]:
        """Get alerts, optionally filtering by unread status"""
        alerts = self.data_service.get_all_alerts(unread_only=unread_only)
        return alerts[:limit]
    
    def get_alerts_by_type(self, alert_type: str) -> List[Alert]:
        """Get alerts of a specific type"""
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            return []
        
        all_alerts = self.data_service.get_all_alerts()
        return [a for a in all_alerts if a.type == alert_type_enum]
    
    def get_alerts_by_severity(self, severity: str) -> List[Alert]:
        """Get alerts of a specific severity"""
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            return []
        
        all_alerts = self.data_service.get_all_alerts()
        return [a for a in all_alerts if a.severity == severity_enum]
    
    def mark_as_read(self, alert_id: str) -> bool:
        """Mark an alert as read"""
        alert = self.data_service.mark_alert_read(alert_id)
        return alert is not None
    
    def mark_all_as_read(self) -> int:
        """Mark all alerts as read"""
        unread_alerts = self.data_service.get_all_alerts(unread_only=True)
        count = 0
        for alert in unread_alerts:
            if self.mark_as_read(alert.alert_id):
                count += 1
        return count
    
    def clear_all_alerts(self) -> bool:
        """Clear all alerts from the system"""
        return self.data_service.clear_all_alerts()
    
    def get_critical_alerts(self) -> List[Alert]:
        """Get all critical alerts"""
        return self.get_alerts_by_severity("CRITICAL")
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get a summary of current alerts"""
        all_alerts = self.data_service.get_all_alerts()
        
        unread_count = len([a for a in all_alerts if not a.read])
        critical_count = len([a for a in all_alerts if a.severity == AlertSeverity.CRITICAL])
        warning_count = len([a for a in all_alerts if a.severity == AlertSeverity.WARNING])
        
        # Count by type
        type_counts = {}
        for alert in all_alerts:
            type_name = alert.type.value
            type_counts[type_name] = type_counts.get(type_name, 0) + 1
        
        return {
            "total_alerts": len(all_alerts),
            "unread_alerts": unread_count,
            "critical_alerts": critical_count,
            "warning_alerts": warning_count,
            "info_alerts": len(all_alerts) - critical_count - warning_count,
            "alerts_by_type": type_counts,
            "recent_alerts": [
                {
                    "alert_id": a.alert_id,
                    "type": a.type.value,
                    "severity": a.severity.value,
                    "title": a.title,
                    "message": a.message,
                    "timestamp": a.timestamp.isoformat()
                }
                for a in all_alerts[:5]
            ]
        }
    
    def generate_system_alert(self, message: str, severity: str = "INFO") -> Alert:
        """Generate a system-level alert"""
        return self.generate_alert(
            alert_type="OTHER",
            severity=severity,
            title="System Notification",
            message=message
        )
