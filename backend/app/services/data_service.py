from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from app.database_sqlalchemy import (
    Road, Vehicle, VehicleTelemetry, Delivery, Incident, 
    WeatherObservation, Route, Alert, District, Depot,
    get_db
)
import json

class DataService:
    """Central data access service for all database operations"""
    
    def __init__(self, db: Session):
        self.db = db
    
    # Road operations
    def get_all_roads(self) -> List[Road]:
        return self.db.query(Road).all()
    
    def get_road_by_id(self, road_id: str) -> Optional[Road]:
        return self.db.query(Road).filter(Road.road_id == road_id).first()
    
    def update_road(self, road_id: str, **kwargs) -> Optional[Road]:
        road = self.get_road_by_id(road_id)
        if road:
            for key, value in kwargs.items():
                if hasattr(road, key):
                    setattr(road, key, value)
            self.db.commit()
            self.db.refresh(road)
        return road
    
    def get_blocked_roads(self) -> List[Road]:
        from app.database_sqlalchemy import RoadStatus
        return self.db.query(Road).filter(Road.current_status == RoadStatus.BLOCKED).all()
    
    # Vehicle operations
    def get_all_vehicles(self) -> List[Vehicle]:
        return self.db.query(Vehicle).all()
    
    def get_vehicle_by_id(self, vehicle_id: str) -> Optional[Vehicle]:
        return self.db.query(Vehicle).filter(Vehicle.vehicle_id == vehicle_id).first()
    
    def update_vehicle(self, vehicle_id: str, **kwargs) -> Optional[Vehicle]:
        vehicle = self.get_vehicle_by_id(vehicle_id)
        if vehicle:
            for key, value in kwargs.items():
                if hasattr(vehicle, key):
                    setattr(vehicle, key, value)
            self.db.commit()
            self.db.refresh(vehicle)
        return vehicle
    
    def get_vehicles_on_road(self, road_id: str) -> List[Vehicle]:
        return self.db.query(Vehicle).filter(Vehicle.current_road_id == road_id).all()
    
    def add_vehicle_telemetry(self, vehicle_id: str, lat: float, lng: float, 
                             speed_kmh: float, heading: float = 0.0) -> VehicleTelemetry:
        telemetry = VehicleTelemetry(
            vehicle_id=vehicle_id,
            lat=lat,
            lng=lng,
            speed_kmh=speed_kmh,
            heading=heading
        )
        self.db.add(telemetry)
        self.db.commit()
        return telemetry
    
    def get_vehicle_telemetry(self, vehicle_id: str, limit: int = 10) -> List[VehicleTelemetry]:
        return self.db.query(VehicleTelemetry)\
            .filter(VehicleTelemetry.vehicle_id == vehicle_id)\
            .order_by(VehicleTelemetry.timestamp.desc())\
            .limit(limit)\
            .all()
    
    # Delivery operations
    def get_all_deliveries(self) -> List[Delivery]:
        return self.db.query(Delivery).all()
    
    def get_delivery_by_id(self, delivery_id: str) -> Optional[Delivery]:
        return self.db.query(Delivery).filter(Delivery.delivery_id == delivery_id).first()
    
    def update_delivery(self, delivery_id: str, **kwargs) -> Optional[Delivery]:
        delivery = self.get_delivery_by_id(delivery_id)
        if delivery:
            for key, value in kwargs.items():
                if hasattr(delivery, key):
                    setattr(delivery, key, value)
            self.db.commit()
            self.db.refresh(delivery)
        return delivery
    
    def get_deliveries_by_vehicle(self, vehicle_id: str) -> List[Delivery]:
        return self.db.query(Delivery).filter(Delivery.vehicle_id == vehicle_id).all()
    
    def get_critical_deliveries(self) -> List[Delivery]:
        from app.database_sqlalchemy import DeliveryPriority
        return self.db.query(Delivery)\
            .filter(Delivery.priority == DeliveryPriority.CRITICAL)\
            .all()
    
    def get_deliveries_by_status(self, status) -> List[Delivery]:
        return self.db.query(Delivery).filter(Delivery.status == status).all()
    
    # Incident operations
    def get_all_incidents(self, active_only: bool = False) -> List[Incident]:
        query = self.db.query(Incident)
        if active_only:
            query = query.filter(Incident.active == True)
        return query.all()
    
    def get_incident_by_id(self, incident_id: str) -> Optional[Incident]:
        return self.db.query(Incident).filter(Incident.incident_id == incident_id).first()
    
    def create_incident(self, incident_data: Dict[str, Any]) -> Incident:
        incident = Incident(**incident_data)
        self.db.add(incident)
        self.db.commit()
        self.db.refresh(incident)
        return incident
    
    def update_incident(self, incident_id: str, **kwargs) -> Optional[Incident]:
        incident = self.get_incident_by_id(incident_id)
        if incident:
            for key, value in kwargs.items():
                if hasattr(incident, key):
                    setattr(incident, key, value)
            self.db.commit()
            self.db.refresh(incident)
        return incident
    
    def get_incidents_by_road(self, road_id: str, active_only: bool = False) -> List[Incident]:
        query = self.db.query(Incident).filter(Incident.road_id == road_id)
        if active_only:
            query = query.filter(Incident.active == True)
        return query.all()
    
    # Weather operations
    def get_latest_weather(self) -> Optional[WeatherObservation]:
        return self.db.query(WeatherObservation)\
            .order_by(WeatherObservation.timestamp.desc())\
            .first()
    
    def create_weather_observation(self, weather_data: Dict[str, Any]) -> WeatherObservation:
        weather = WeatherObservation(**weather_data)
        self.db.add(weather)
        self.db.commit()
        self.db.refresh(weather)
        return weather
    
    def update_weather(self, **kwargs) -> Optional[WeatherObservation]:
        weather = self.get_latest_weather()
        if weather:
            for key, value in kwargs.items():
                if hasattr(weather, key):
                    setattr(weather, key, value)
            self.db.commit()
            self.db.refresh(weather)
        return weather
    
    # Route operations
    def get_all_routes(self) -> List[Route]:
        return self.db.query(Route).all()
    
    def get_route_by_id(self, route_id: str) -> Optional[Route]:
        return self.db.query(Route).filter(Route.route_id == route_id).first()
    
    def get_routes_by_delivery(self, delivery_id: str) -> List[Route]:
        return self.db.query(Route).filter(Route.delivery_id == delivery_id).all()
    
    def create_route(self, route_data: Dict[str, Any]) -> Route:
        route = Route(**route_data)
        self.db.add(route)
        self.db.commit()
        self.db.refresh(route)
        return route
    
    def update_route(self, route_id: str, **kwargs) -> Optional[Route]:
        route = self.get_route_by_id(route_id)
        if route:
            for key, value in kwargs.items():
                if hasattr(route, key):
                    setattr(route, key, value)
            self.db.commit()
            self.db.refresh(route)
        return route
    
    # Alert operations
    def get_all_alerts(self, unread_only: bool = False) -> List[Alert]:
        query = self.db.query(Alert).order_by(Alert.timestamp.desc())
        if unread_only:
            query = query.filter(Alert.read == False)
        return query.all()
    
    def create_alert(self, alert_data: Dict[str, Any]) -> Alert:
        alert = Alert(**alert_data)
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        return alert
    
    def mark_alert_read(self, alert_id: str) -> Optional[Alert]:
        alert = self.db.query(Alert).filter(Alert.alert_id == alert_id).first()
        if alert:
            alert.read = True
            self.db.commit()
            self.db.refresh(alert)
        return alert
    
    def clear_all_alerts(self) -> bool:
        try:
            self.db.query(Alert).delete()
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            return False
    
    # District and Depot operations
    def get_all_districts(self) -> List[District]:
        return self.db.query(District).all()
    
    def get_district_by_id(self, district_id: str) -> Optional[District]:
        return self.db.query(District).filter(District.district_id == district_id).first()
    
    def get_all_depots(self) -> List[Depot]:
        return self.db.query(Depot).all()
    
    def get_depot_by_id(self, depot_id: str) -> Optional[Depot]:
        return self.db.query(Depot).filter(Depot.depot_id == depot_id).first()
    
    # Utility methods
    def commit(self):
        self.db.commit()
    
    def rollback(self):
        self.db.rollback()
    
    def close(self):
        self.db.close()

def get_data_service() -> DataService:
    """Factory function to get a data service instance"""
    db = next(get_db())
    return DataService(db)
