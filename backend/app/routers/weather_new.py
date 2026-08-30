from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from app.database_sqlalchemy import get_db, WeatherObservation, WeatherCondition
from app.services.data_service import DataService
from app.services.road_risk_service import RoadRiskService
from app.services.delivery_risk_service_new import DeliveryRiskService
from pydantic import BaseModel

router = APIRouter(prefix="/weather", tags=["weather"])

class WeatherUpdateSchema(BaseModel):
    location: str
    rainfall_mm: float
    visibility_km: float
    temperature: float
    weather_condition: str
    forecast_risk: float

class WeatherResponse(BaseModel):
    location: str
    rainfall_mm: float
    visibility_km: float
    temperature: float
    weather_condition: str
    forecast_risk: float
    timestamp: str

@router.get("", response_model=WeatherResponse)
def get_weather(db: Session = Depends(get_db)):
    data_service = DataService(db)
    weather = data_service.get_latest_weather()
    if not weather:
        raise HTTPException(status_code=404, detail="No weather data found")
    
    return WeatherResponse(
        location=weather.location,
        rainfall_mm=weather.rainfall_mm,
        visibility_km=weather.visibility_km,
        temperature=weather.temperature,
        weather_condition=weather.weather_condition.value,
        forecast_risk=weather.forecast_risk,
        timestamp=weather.timestamp.isoformat()
    )

@router.post("/simulate")
def simulate_weather(schema: WeatherUpdateSchema, db: Session = Depends(get_db)):
    data_service = DataService(db)
    
    try:
        weather_condition = WeatherCondition(schema.weather_condition)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid weather condition")
    
    # Update or create weather observation
    weather_data = {
        "location": schema.location,
        "rainfall_mm": schema.rainfall_mm,
        "visibility_km": schema.visibility_km,
        "temperature": schema.temperature,
        "weather_condition": weather_condition,
        "forecast_risk": schema.forecast_risk
    }
    
    existing_weather = data_service.get_latest_weather()
    if existing_weather:
        weather = data_service.update_weather(**weather_data)
    else:
        weather = data_service.create_weather_observation(weather_data)
    
    # Cascade: Recalculate road risks
    road_risk_service = RoadRiskService(db)
    road_risk_service.recalculate_all_roads_risk()
    
    # Cascade: Recalculate delivery risks
    delivery_risk_service = DeliveryRiskService(db)
    delivery_risk_service.recalculate_all_deliveries_risk()
    
    return WeatherResponse(
        location=weather.location,
        rainfall_mm=weather.rainfall_mm,
        visibility_km=weather.visibility_km,
        temperature=weather.temperature,
        weather_condition=weather.weather_condition.value,
        forecast_risk=weather.forecast_risk,
        timestamp=weather.timestamp.isoformat()
    )
