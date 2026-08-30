from fastapi import APIRouter, HTTPException, Depends
from typing import List
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db, Delivery
from app.services.data_service import DataService
from app.services.delivery_risk_service_new import DeliveryRiskService
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

class DeliveryResponse(BaseModel):
    delivery_id: str
    vehicle_id: str
    cargo_type: str
    priority: str
    origin: str
    destination: str
    status: str
    weight_kg: float
    eta: str
    original_eta: str
    risk_score: float
    on_time_probability: float
    delay_reason: str

@router.get("", response_model=List[DeliveryResponse])
def get_deliveries(db: Session = Depends(get_db)):
    data_service = DataService(db)
    deliveries = data_service.get_all_deliveries()
    return [
        DeliveryResponse(
            delivery_id=d.delivery_id,
            vehicle_id=d.vehicle_id,
            cargo_type=d.cargo_type,
            priority=d.priority.value,
            origin=d.origin,
            destination=d.destination,
            status=d.status.value,
            weight_kg=d.weight_kg,
            eta=d.eta.isoformat() if d.eta else None,
            original_eta=d.original_eta.isoformat() if d.original_eta else None,
            risk_score=d.risk_score,
            on_time_probability=d.on_time_probability,
            delay_reason=d.delay_reason or ""
        )
        for d in deliveries
    ]

@router.get("/{delivery_id}")
def get_delivery(delivery_id: str, db: Session = Depends(get_db)):
    data_service = DataService(db)
    delivery = data_service.get_delivery_by_id(delivery_id)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    
    return DeliveryResponse(
        delivery_id=delivery.delivery_id,
        vehicle_id=delivery.vehicle_id,
        cargo_type=delivery.cargo_type,
        priority=delivery.priority.value,
        origin=delivery.origin,
        destination=delivery.destination,
        status=delivery.status.value,
        weight_kg=delivery.weight_kg,
        eta=delivery.eta.isoformat() if delivery.eta else None,
        original_eta=delivery.original_eta.isoformat() if delivery.original_eta else None,
        risk_score=delivery.risk_score,
        on_time_probability=delivery.on_time_probability,
        delay_reason=delivery.delay_reason or ""
    )

@router.get("/{delivery_id}/risk")
def get_delivery_risk(delivery_id: str, db: Session = Depends(get_db)):
    delivery_risk_service = DeliveryRiskService(db)
    try:
        result = delivery_risk_service.calculate_delivery_risk(delivery_id)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.get("/critical/at-risk")
def get_critical_at_risk_deliveries(db: Session = Depends(get_db)):
    delivery_risk_service = DeliveryRiskService(db)
    critical_deliveries = delivery_risk_service.get_critical_at_risk_deliveries()
    return [
        {
            "delivery_id": d.delivery_id,
            "cargo_type": d.cargo_type,
            "priority": d.priority.value,
            "destination": d.destination,
            "risk_score": d.risk_score,
            "on_time_probability": d.on_time_probability,
            "eta": d.eta.isoformat() if d.eta else None
        }
        for d in critical_deliveries
    ]
