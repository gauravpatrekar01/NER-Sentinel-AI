from fastapi import APIRouter, HTTPException
from typing import List
from app.database import load_deliveries
from app.models.models import Delivery

router = APIRouter(prefix="/deliveries", tags=["deliveries"])

@router.get("", response_model=List[Delivery])
def get_deliveries():
    return load_deliveries()

@router.get("/{delivery_id}", response_model=Delivery)
def get_delivery(delivery_id: str):
    deliveries = load_deliveries()
    delivery = next((d for d in deliveries if d.delivery_id == delivery_id), None)
    if not delivery:
        raise HTTPException(status_code=404, detail="Delivery not found")
    return delivery
