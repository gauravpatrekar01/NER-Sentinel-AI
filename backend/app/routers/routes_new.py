from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db
from app.services.route_service_new import RouteService
from app.services.data_service import DataService
from pydantic import BaseModel

router = APIRouter(prefix="/routes", tags=["routes"])

class RouteOptimizeSchema(BaseModel):
    origin: str
    destination: str
    blocked_roads: list = []
    priority: str = "NORMAL"
    emergency_mode: bool = False

class DeliveryRouteOptimizeSchema(BaseModel):
    delivery_id: str
    blocked_roads: list = []

@router.post("/optimize")
def optimize_routes(schema: RouteOptimizeSchema, db: Session = Depends(get_db)):
    route_service = RouteService(db)
    try:
        result = route_service.find_alternative_routes(
            origin=schema.origin,
            destination=schema.destination,
            blocked_roads=schema.blocked_roads,
            priority=schema.priority,
            emergency_mode=schema.emergency_mode
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing routes: {str(e)}")

@router.post("/optimize/delivery")
def optimize_delivery_route(schema: DeliveryRouteOptimizeSchema, db: Session = Depends(get_db)):
    route_service = RouteService(db)
    try:
        result = route_service.optimize_route_for_delivery(
            delivery_id=schema.delivery_id,
            blocked_roads=schema.blocked_roads
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error optimizing delivery route: {str(e)}")

@router.get("/delivery/{delivery_id}")
def get_delivery_routes(delivery_id: str, db: Session = Depends(get_db)):
    data_service = DataService(db)
    routes = data_service.get_routes_by_delivery(delivery_id)
    
    return [
        {
            "route_id": r.route_id,
            "name": r.name,
            "distance_km": r.distance_km,
            "travel_time_minutes": r.travel_time_minutes,
            "is_alternative": r.is_alternative,
            "created_at": r.created_at.isoformat()
        }
        for r in routes
    ]
