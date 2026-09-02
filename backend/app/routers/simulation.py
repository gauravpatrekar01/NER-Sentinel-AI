from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from app.services.simulation_service import run_network_simulation
from app.models.models import SimulationResult
from app.database import load_weather, save_weather
from app.services.weather_integration import determine_weather_risk
from app.services.risk_service import recalculate_all_roads_risk
from app.services.gps_simulator import update_vehicle_positions
from app.services.incident_service import register_incident_and_cascade
from app.services.alert_engine import generate_alert

router = APIRouter(prefix="/simulation", tags=["simulation"])

class SimulationRequestSchema(BaseModel):
    scenario: str
    rainfall_mm: float

class EventSimulationSchema(BaseModel):
    event_type: str
    target_id: Optional[str] = None

@router.post("/run", response_model=SimulationResult)
def run_simulation(schema: SimulationRequestSchema):
    res_dict = run_network_simulation(schema.scenario, schema.rainfall_mm)
    return SimulationResult(**res_dict)

@router.post("/event")
def trigger_simulation_event(schema: EventSimulationSchema):
    event = schema.event_type.upper()
    
    if event in ["NORMAL", "HEAVY_RAIN", "EXTREME_RAIN"]:
        weather = load_weather()
        if event == "NORMAL":
            weather.rainfall_mm = 10.0
            weather.visibility_km = 8.0
            weather.forecast = "Clear"
        elif event == "HEAVY_RAIN":
            weather.rainfall_mm = 150.0
            weather.visibility_km = 2.0
            weather.forecast = "Heavy Rain"
        elif event == "EXTREME_RAIN":
            weather.rainfall_mm = 250.0
            weather.visibility_km = 0.5
            weather.forecast = "Extreme Rain Storm"
            
        weather.weather_risk_level = determine_weather_risk(weather.rainfall_mm, weather.visibility_km)
        save_weather(weather)
        
        # Recalculate
        recalculate_all_roads_risk()
        from app.services.decision_engine import run_decision_pipeline
        run_decision_pipeline(trigger=f"weather_{event}")
        
        if event != "NORMAL":
            generate_alert("WEATHER_ALERT", f"Weather changed to {weather.forecast}. Risk levels updated.", "WARNING")
            
    elif event == "FLOOD":
        # Create flood incident on a vulnerable road (R-218)
        register_incident_and_cascade(
            road_id="R-218",
            lat=25.1050,
            lon=92.4200,
            incident_type="Flood",
            severity="HIGH",
            description="Severe waterlogging and flooding reported on R-218.",
            optimize_immediately=True
        )
    elif event == "LANDSLIDE":
        register_incident_and_cascade(
            road_id="R-204",
            lat=25.9015,
            lon=91.8800,
            incident_type="Landslide",
            severity="CRITICAL",
            description="Monsoon triggered rockfall block at NH-6 Guwahati-Shillong corridor.",
            optimize_immediately=True
        )
    elif event == "EMERGENCY_MODE":
        from app.services.app_state import set_emergency_mode
        from app.services.decision_engine import run_decision_pipeline
        set_emergency_mode(True)
        generate_alert(
            "EMERGENCY_MODE",
            "Emergency Mode Activated: Prioritizing medical and food supplies with safety-first routing.",
            "CRITICAL",
        )
        run_decision_pipeline(trigger="emergency_mode", emergency_mode=True)
        
    return {"status": "success", "event": event}
