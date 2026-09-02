import os
import requests
from typing import Dict, Any
from app.database import load_weather, save_weather
from app.models.models import WeatherObservation

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
# Defaulting to Shillong coordinates as a central representative point for NER logistics corridor
DEFAULT_LAT = 25.5788
DEFAULT_LON = 91.8833

def fetch_real_weather() -> Dict[str, Any]:
    """
    Fetches real weather from OpenWeather if API key exists.
    Otherwise, returns None to allow simulated fallback.
    """
    if not OPENWEATHER_API_KEY:
        return None
        
    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?lat={DEFAULT_LAT}&lon={DEFAULT_LON}&appid={OPENWEATHER_API_KEY}&units=metric"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        
        # OpenWeather returns rain in last 1h or 3h. Default to 0 if not raining.
        rainfall = 0.0
        if "rain" in data:
            rainfall = data["rain"].get("1h", data["rain"].get("3h", 0.0))
            
        visibility_km = data.get("visibility", 10000) / 1000.0
        forecast_desc = data["weather"][0]["main"] if "weather" in data else "Clear"
        
        return {
            "rainfall_mm": rainfall,
            "visibility_km": visibility_km,
            "forecast": forecast_desc
        }
    except Exception as e:
        print(f"Error fetching real weather: {e}")
        return None

def determine_weather_risk(rainfall_mm: float, visibility_km: float) -> str:
    if rainfall_mm > 100 or visibility_km < 1.0:
        return "CRITICAL"
    if rainfall_mm > 50 or visibility_km < 3.0:
        return "HIGH"
    if rainfall_mm > 10 or visibility_km < 5.0:
        return "MODERATE"
    return "LOW"

def update_weather_dynamically():
    """
    Called by periodic tasks or endpoints to update the weather.
    Uses real data if available, otherwise maintains current state or falls back.
    """
    current_weather = load_weather()
    
    real_data = fetch_real_weather()
    if real_data:
        new_weather = WeatherObservation(
            rainfall_mm=real_data["rainfall_mm"],
            forecast=real_data["forecast"],
            visibility_km=real_data["visibility_km"],
            weather_risk_level=determine_weather_risk(real_data["rainfall_mm"], real_data["visibility_km"])
        )
        save_weather(new_weather)
        return new_weather
        
    return current_weather
