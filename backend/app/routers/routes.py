from fastapi import APIRouter
from app.services.route_service import get_optimized_routes

router = APIRouter(prefix="/routes", tags=["routes"])

@router.get("")
def get_routes(priority: str = "NORMAL", emergency: bool = False):
    return get_optimized_routes(priority=priority, emergency_mode=emergency)
