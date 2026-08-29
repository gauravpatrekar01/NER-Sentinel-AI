from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.database import load_weather, save_weather, load_vehicles, load_roads, load_deliveries, save_deliveries
from app.models.models import WeatherObservation
from app.services.risk_service import recalculate_all_roads_risk
from app.services.delivery_risk_service import recalculate_delivery_risks

router = APIRouter(prefix="/weather", tags=["weather"])

class WeatherUpdateSchema(BaseModel):
    rainfall_mm: float
    forecast: str
    visibility_km: float
    weather_risk_level: str

@router.get("", response_model=WeatherObservation)
def get_weather():
    return load_weather()

@router.post("", response_model=WeatherObservation)
def update_weather(schema: WeatherUpdateSchema):
    # Update weather observation
    new_weather = WeatherObservation(
        rainfall_mm=schema.rainfall_mm,
        forecast=schema.forecast,
        visibility_km=schema.visibility_km,
        weather_risk_level=schema.weather_risk_level
    )
    save_weather(new_weather)
    
    # Cascade: Road Risk update
    recalculate_all_roads_risk()
    
    # Reload models
    roads = load_roads()
    roads_dict = {r.road_id: r for r in roads}
    vehicles = load_vehicles()
    vehicles_dict = {v.vehicle_id: v for v in vehicles}
    deliveries = load_deliveries()
    
    # Cascade: Delivery Risk update
    recalculate_delivery_risks(deliveries, vehicles_dict, roads_dict)
    save_deliveries(deliveries)
    
    return new_weather
