from sqlalchemy import create_engine, Column, String, Float, Integer, Boolean, DateTime, Text, ForeignKey, Enum as SQLEnum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import enum

DATABASE_URL = "sqlite:///./ner_sentinel.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class RoadStatus(str, enum.Enum):
    OPEN = "OPEN"
    MODERATE = "MODERATE"
    HIGH_RISK = "HIGH_RISK"
    BLOCKED = "BLOCKED"

class VehicleStatus(str, enum.Enum):
    IDLE = "IDLE"
    IN_TRANSIT = "IN_TRANSIT"
    DELAYED = "DELAYED"
    REROUTING = "REROUTING"
    EMERGENCY = "EMERGENCY"

class DeliveryPriority(str, enum.Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    NORMAL = "NORMAL"

class DeliveryStatus(str, enum.Enum):
    PENDING = "PENDING"
    EN_ROUTE = "EN_ROUTE"
    DELAYED = "DELAYED"
    DELIVERED = "DELIVERED"

class IncidentType(str, enum.Enum):
    LANDSLIDE = "LANDSLIDE"
    FLOOD = "FLOOD"
    ROAD_DAMAGE = "ROAD_DAMAGE"
    BRIDGE_ISSUE = "BRIDGE_ISSUE"
    TRAFFIC_BLOCKAGE = "TRAFFIC_BLOCKAGE"
    OTHER = "OTHER"

class IncidentSeverity(str, enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class WeatherCondition(str, enum.Enum):
    NORMAL = "NORMAL"
    LIGHT_RAIN = "LIGHT_RAIN"
    HEAVY_RAIN = "HEAVY_RAIN"
    STORM = "STORM"
    FLOOD_RISK = "FLOOD_RISK"

class AlertType(str, enum.Enum):
    ROAD_BLOCKED = "ROAD_BLOCKED"
    HIGH_ROAD_RISK = "HIGH_ROAD_RISK"
    DELIVERY_AT_RISK = "DELIVERY_AT_RISK"
    VEHICLE_DELAY = "VEHICLE_DELAY"
    ROUTE_CHANGED = "ROUTE_CHANGED"
    CRITICAL_DELIVERY = "CRITICAL_DELIVERY"
    EMERGENCY_MODE = "EMERGENCY_MODE"

class AlertSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"

class Road(Base):
    __tablename__ = "roads"
    
    id = Column(Integer, primary_key=True, index=True)
    road_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    geometry = Column(Text)  # GeoJSON or WKT
    distance_km = Column(Float, nullable=False)
    road_condition = Column(Float)  # 1 to 10
    terrain_risk = Column(Float)  # 0 to 100
    flood_risk = Column(Float)  # 0 to 100
    landslide_history = Column(Float)  # 0 to 100
    traffic_level = Column(Float)  # 0 to 100
    current_status = Column(SQLEnum(RoadStatus), default=RoadStatus.OPEN)
    risk_score = Column(Float, default=0.0)
    accessibility_score = Column(Float, default=100.0)
    
    # Relationships
    vehicles = relationship("Vehicle", back_populates="current_road")
    incidents = relationship("Incident", back_populates="road")

class Vehicle(Base):
    __tablename__ = "vehicles"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String, unique=True, index=True, nullable=False)
    vehicle_type = Column(String)
    capacity = Column(Float)
    current_lat = Column(Float)
    current_lng = Column(Float)
    current_road_id = Column(String, ForeignKey("roads.road_id"))
    current_route_id = Column(String)  # Store route as semicolon-separated road IDs
    original_route_id = Column(String)  # Store original route for comparison
    speed_kmh = Column(Float)
    status = Column(SQLEnum(VehicleStatus), default=VehicleStatus.IDLE)
    
    # Relationships
    current_road = relationship("Road", back_populates="vehicles")
    telemetry = relationship("VehicleTelemetry", back_populates="vehicle")
    deliveries = relationship("Delivery", back_populates="vehicle")

class VehicleTelemetry(Base):
    __tablename__ = "vehicle_telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    vehicle_id = Column(String, ForeignKey("vehicles.vehicle_id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    lat = Column(Float)
    lng = Column(Float)
    speed_kmh = Column(Float)
    heading = Column(Float)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="telemetry")

class Delivery(Base):
    __tablename__ = "deliveries"
    
    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(String, unique=True, index=True, nullable=False)
    vehicle_id = Column(String, ForeignKey("vehicles.vehicle_id"), nullable=False)
    cargo_type = Column(String)
    priority = Column(SQLEnum(DeliveryPriority), default=DeliveryPriority.NORMAL)
    origin = Column(String)
    destination = Column(String)
    current_route = Column(Text)  # JSON array of road IDs
    distance_remaining = Column(Float)
    eta = Column(DateTime)
    risk_score = Column(Float, default=0.0)
    status = Column(SQLEnum(DeliveryStatus), default=DeliveryStatus.PENDING)
    weight_kg = Column(Float)
    original_eta = Column(DateTime)
    delay_reason = Column(Text)
    on_time_probability = Column(Float, default=100.0)
    
    # Relationships
    vehicle = relationship("Vehicle", back_populates="deliveries")
    route = relationship("Route", back_populates="delivery", uselist=False)

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    incident_id = Column(String, unique=True, index=True, nullable=False)
    road_id = Column(String, ForeignKey("roads.road_id"), nullable=False)
    lat = Column(Float)
    lng = Column(Float)
    type = Column(SQLEnum(IncidentType), nullable=False)
    severity = Column(SQLEnum(IncidentSeverity), nullable=False)
    description = Column(Text)
    photo_url = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)
    
    # Relationships
    road = relationship("Road", back_populates="incidents")

class WeatherObservation(Base):
    __tablename__ = "weather_observations"
    
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String)
    rainfall_mm = Column(Float)
    visibility_km = Column(Float)
    temperature = Column(Float)
    weather_condition = Column(SQLEnum(WeatherCondition), default=WeatherCondition.NORMAL)
    forecast_risk = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)

class Route(Base):
    __tablename__ = "routes"
    
    id = Column(Integer, primary_key=True, index=True)
    route_id = Column(String, unique=True, index=True, nullable=False)
    delivery_id = Column(String, ForeignKey("deliveries.delivery_id"), nullable=False)
    name = Column(String)
    path = Column(Text)  # JSON array of coordinates
    distance_km = Column(Float)
    travel_time_minutes = Column(Float)
    road_ids = Column(Text)  # JSON array of road IDs
    is_alternative = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    delivery = relationship("Delivery", back_populates="route")

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(String, unique=True, index=True, nullable=False)
    type = Column(SQLEnum(AlertType), nullable=False)
    severity = Column(SQLEnum(AlertSeverity), default=AlertSeverity.INFO)
    title = Column(String)
    message = Column(Text)
    road_id = Column(String)
    delivery_id = Column(String)
    vehicle_id = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    read = Column(Boolean, default=False)

class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(String, unique=True, index=True, nullable=False)
    scenario = Column(String)
    baseline_data = Column(Text)  # JSON
    optimized_data = Column(Text)  # JSON
    timestamp = Column(DateTime, default=datetime.utcnow)

class District(Base):
    __tablename__ = "districts"
    
    id = Column(Integer, primary_key=True, index=True)
    district_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    state = Column(String)
    headquarters = Column(String)
    population = Column(Integer)
    area_sq_km = Column(Float)
    risk_level = Column(String)

class Depot(Base):
    __tablename__ = "depots"
    
    id = Column(Integer, primary_key=True, index=True)
    depot_id = Column(String, unique=True, index=True, nullable=False)
    name = Column(String)
    location = Column(String)
    lat = Column(Float)
    lng = Column(Float)
    district_id = Column(String, ForeignKey("districts.district_id"))
    capacity = Column(Float)
    depot_type = Column(String)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
