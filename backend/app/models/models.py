from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class Road(BaseModel):
    road_id: str
    name: str
    length_km: float
    status: str  # OPEN, MODERATE, HIGH RISK, BLOCKED
    rainfall_mm: float
    terrain_risk: float  # 0 to 100
    historical_incidents: int
    road_condition: float  # 1 to 10 (10 is perfect, 1 is terrible)
    flood_risk: float  # 0 to 100
    landslide_history: float  # 0 to 100
    traffic_level: float  # 0 to 100
    field_incident_severity: Optional[str] = None  # None, LOW, MEDIUM, HIGH, CRITICAL
    accessibility_score: float = 100.0  # 0 to 100
    disruption_probability: float = 0.0  # 0.0 to 1.0
    risk_level: str = "LOW"  # LOW, MODERATE, HIGH, CRITICAL, BLOCKED
    path: List[List[float]] = []  # list of [lat, lon]

class Vehicle(BaseModel):
    vehicle_id: str
    cargo: str
    origin: str
    destination: str
    current_lat: float
    current_lon: float
    speed_kmh: float
    current_route_id: str
    original_route_id: str
    eta_str: str
    original_eta_str: str
    delivery_risk_pct: float
    progress: float  # 0.0 to 1.0 along the path
    status: str  # EN_ROUTE, DELAYED, BLOCKED, COMPLETED
    last_updated: float = 0.0  # epoch timestamp
    delay_reason: Optional[str] = ""

class Delivery(BaseModel):
    delivery_id: str
    cargo: str
    priority: str  # CRITICAL, HIGH, MEDIUM, NORMAL
    vehicle_id: str
    origin: str
    destination: str
    status: str  # PENDING, EN_ROUTE, DELAYED, DELIVERED
    weight_kg: float
    eta_str: str
    original_eta_str: str
    delay_reason: Optional[str] = ""
    delivery_risk_pct: float
    on_time_probability: float

class Incident(BaseModel):
    incident_id: str
    road_id: str
    lat: float
    lon: float
    type: str  # Landslide, Flood, Road Damage, Bridge Issue, Traffic Blockage, Other
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    description: str
    photo_url: Optional[str] = None
    timestamp: float
    active: bool = True

class WeatherObservation(BaseModel):
    rainfall_mm: float
    forecast: str  # Sunny, Moderate Rain, Heavy Rain, Storm
    visibility_km: float
    weather_risk_level: str  # LOW, MODERATE, HIGH, CRITICAL

class Route(BaseModel):
    route_id: str
    name: str
    path: List[List[float]]
    total_distance_km: float
    base_duration_hours: float
    current_duration_hours: float
    road_ids: List[str]

class Alert(BaseModel):
    alert_id: str
    type: str  # ROAD_BLOCKED, HIGH_DISRUPTION_RISK, VEHICLE_DELAY, CRITICAL_DELIVERY_DELAY, HIGH_RISK_CORRIDOR, ROUTE_UPDATED
    message: str
    timestamp: float
    severity: str  # INFO, WARNING, CRITICAL
    read: bool = False

class SimulationResult(BaseModel):
    scenario: str
    baseline_delayed_count: int
    baseline_avg_delay_hours: float
    baseline_critical_affected: int
    baseline_on_time_pct: float
    optimized_delayed_count: int
    optimized_avg_delay_hours: float
    optimized_critical_affected: int
    optimized_on_time_pct: float
