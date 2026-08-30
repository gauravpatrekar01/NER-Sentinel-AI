from sqlalchemy.orm import Session
from app.database_sqlalchemy import (
    SessionLocal, Road, Vehicle, VehicleTelemetry, Delivery, Incident, 
    WeatherObservation, Route, Alert, District, Depot, Simulation,
    RoadStatus, VehicleStatus, DeliveryPriority, DeliveryStatus,
    IncidentType, IncidentSeverity, WeatherCondition
)
from datetime import datetime, timedelta
import json

def parse_coordinates(path_str: str):
    """Parse coordinate string 'lat,lon;lat,lon' into list of [lat, lon]"""
    coords = []
    if not path_str:
        return coords
    for pair in path_str.split(";"):
        if pair.strip():
            lat, lon = map(float, pair.split(","))
            coords.append([lat, lon])
    return coords

def seed_database():
    db = SessionLocal()
    
    try:
        # Clear existing data
        db.query(Alert).delete()
        db.query(Simulation).delete()
        db.query(Route).delete()
        db.query(Incident).delete()
        db.query(WeatherObservation).delete()
        db.query(Delivery).delete()
        db.query(VehicleTelemetry).delete()
        db.query(Vehicle).delete()
        db.query(Road).delete()
        db.query(Depot).delete()
        db.query(District).delete()
        db.commit()
        
        # Seed Districts
        districts = [
            District(district_id="D-GHY", name="Guwahati", state="Assam", headquarters="Guwahati", population=962334, area_sq_km=216.0, risk_level="MODERATE"),
            District(district_id="D-SHL", name="East Khasi Hills", state="Meghalaya", headquarters="Shillong", population=325432, area_sq_km=2748.0, risk_level="HIGH"),
            District(district_id="D-SIL", name="Cachar", state="Assam", headquarters="Silchar", population=2874556, area_sq_km=3787.0, risk_level="MODERATE"),
            District(district_id="D-HFL", name="Dima Hasao", state="Assam", headquarters="Haflong", population=213545, area_sq_km=4890.0, risk_level="HIGH"),
        ]
        db.add_all(districts)
        db.commit()
        
        # Seed Depots
        depots = [
            Depot(depot_id="DP-GHY-MAIN", name="Guwahati Central Depot", location="Guwahati", lat=26.1445, lng=91.7362, district_id="D-GHY", capacity=50000.0, depot_type="MAIN"),
            Depot(depot_id="DP-SHL-MAIN", name="Shillong Depot", location="Shillong", lat=25.5788, lng=91.8833, district_id="D-SHL", capacity=30000.0, depot_type="REGIONAL"),
            Depot(depot_id="DP-SIL-MAIN", name="Silchar Depot", location="Silchar", lat=24.8333, lng=92.7789, district_id="D-SIL", capacity=35000.0, depot_type="REGIONAL"),
            Depot(depot_id="DP-HFL-MAIN", name="Haflong Warehouse", location="Haflong", lat=25.1700, lng=93.0300, district_id="D-HFL", capacity=20000.0, depot_type="WAREHOUSE"),
        ]
        db.add_all(depots)
        db.commit()
        
        # Seed Roads
        roads_data = [
            {
                "road_id": "R-204",
                "name": "Guwahati-Shillong Highway (NH-6)",
                "geometry": None,
                "distance_km": 100.0,
                "road_condition": 4.5,
                "terrain_risk": 62.0,
                "flood_risk": 40.0,
                "landslide_history": 72.0,
                "traffic_level": 62.0,
                "current_status": RoadStatus.OPEN,
                "risk_score": 0.0,
                "accessibility_score": 100.0,
                "path": "26.1445,91.7362;26.1200,91.7900;26.1150,91.8900;26.0400,91.8900;25.9015,91.8800;25.7500,91.8900;25.6420,91.8950;25.5788,91.8833"
            },
            {
                "road_id": "R-207",
                "name": "Shillong-Jowai Bypass (NH-6)",
                "geometry": None,
                "distance_km": 65.0,
                "road_condition": 7.5,
                "terrain_risk": 35.0,
                "flood_risk": 10.0,
                "landslide_history": 30.0,
                "traffic_level": 40.0,
                "current_status": RoadStatus.OPEN,
                "risk_score": 0.0,
                "accessibility_score": 100.0,
                "path": "25.5788,91.8833;25.5700,92.0500;25.4900,92.1800;25.4484,92.2032"
            },
            {
                "road_id": "R-211",
                "name": "Jowai-Khliehriat Road (NH-6)",
                "geometry": None,
                "distance_km": 30.0,
                "road_condition": 7.0,
                "terrain_risk": 30.0,
                "flood_risk": 15.0,
                "landslide_history": 25.0,
                "traffic_level": 45.0,
                "current_status": RoadStatus.OPEN,
                "risk_score": 0.0,
                "accessibility_score": 100.0,
                "path": "25.4484,92.2032;25.3700,92.3100;25.3578,92.3689"
            },
            {
                "road_id": "R-218",
                "name": "Khliehriat-Silchar Ridge (NH-6)",
                "geometry": None,
                "distance_km": 95.0,
                "road_condition": 5.5,
                "terrain_risk": 75.0,
                "flood_risk": 40.0,
                "landslide_history": 80.0,
                "traffic_level": 35.0,
                "current_status": RoadStatus.OPEN,
                "risk_score": 0.0,
                "accessibility_score": 100.0,
                "path": "25.3578,92.3689;25.1700,92.3800;25.1050,92.4200;24.9700,92.5700;24.8970,92.5930;24.8333,92.7789"
            },
            {
                "road_id": "R-301",
                "name": "Guwahati-Nagaon Expressway (NH-27)",
                "geometry": None,
                "distance_km": 120.0,
                "road_condition": 9.0,
                "terrain_risk": 10.0,
                "flood_risk": 30.0,
                "landslide_history": 10.0,
                "traffic_level": 70.0,
                "current_status": RoadStatus.OPEN,
                "risk_score": 0.0,
                "accessibility_score": 100.0,
                "path": "26.1445,91.7362;26.1100,92.1700;26.2300,92.5200;26.3500,92.6800"
            },
            {
                "road_id": "R-302",
                "name": "Nagaon-Haflong Mountain Cut (NH-54)",
                "geometry": None,
                "distance_km": 150.0,
                "road_condition": 7.0,
                "terrain_risk": 55.0,
                "flood_risk": 20.0,
                "landslide_history": 40.0,
                "traffic_level": 30.0,
                "current_status": RoadStatus.OPEN,
                "risk_score": 0.0,
                "accessibility_score": 100.0,
                "path": "26.3500,92.6800;26.1300,92.8900;25.9200,93.0000;25.7500,92.9500;25.5700,92.9800;25.1700,93.0300"
            },
            {
                "road_id": "R-303",
                "name": "Haflong-Silchar Link (NH-270)",
                "geometry": None,
                "distance_km": 100.0,
                "road_condition": 6.5,
                "terrain_risk": 60.0,
                "flood_risk": 35.0,
                "landslide_history": 50.0,
                "traffic_level": 25.0,
                "current_status": RoadStatus.OPEN,
                "risk_score": 0.0,
                "accessibility_score": 100.0,
                "path": "25.1700,93.0300;25.1500,93.0300;25.1100,92.8700;24.9800,92.8500;24.8333,92.7789"
            }
        ]
        
        for road_data in roads_data:
            path_str = road_data.pop("path")
            road = Road(**road_data)
            road.geometry = json.dumps({"coordinates": parse_coordinates(path_str)})
            db.add(road)
        
        db.commit()
        
        # Seed Vehicles
        vehicles_data = [
            {
                "vehicle_id": "V-101",
                "vehicle_type": "TRUCK",
                "capacity": 5000.0,
                "current_lat": 26.0400,
                "current_lng": 91.8900,
                "current_road_id": "R-204",
                "current_route_id": "R-204",
                "original_route_id": "R-204",
                "speed_kmh": 45.0,
                "status": VehicleStatus.IN_TRANSIT
            },
            {
                "vehicle_id": "V-102",
                "vehicle_type": "TRUCK",
                "capacity": 8000.0,
                "current_lat": 25.9015,
                "current_lng": 91.8800,
                "current_road_id": "R-204",
                "current_route_id": "R-204",
                "original_route_id": "R-204",
                "speed_kmh": 40.0,
                "status": VehicleStatus.IN_TRANSIT
            },
            {
                "vehicle_id": "V-103",
                "vehicle_type": "VAN",
                "capacity": 3000.0,
                "current_lat": 25.5700,
                "current_lng": 92.0500,
                "current_road_id": "R-207",
                "current_route_id": "R-207",
                "original_route_id": "R-207",
                "speed_kmh": 35.0,
                "status": VehicleStatus.IN_TRANSIT
            },
            {
                "vehicle_id": "V-104",  # Primary Demo Vehicle
                "vehicle_type": "AMBULANCE_TRUCK",
                "capacity": 2000.0,
                "current_lat": 26.1200,
                "current_lng": 91.7900,
                "current_road_id": "R-204",
                "current_route_id": "R-204;R-207;R-211;R-218",
                "original_route_id": "R-204;R-207;R-211;R-218",
                "speed_kmh": 42.0,
                "status": VehicleStatus.IN_TRANSIT
            },
            {
                "vehicle_id": "V-105",
                "vehicle_type": "TRUCK",
                "capacity": 6000.0,
                "current_lat": 24.8970,
                "current_lng": 92.5930,
                "current_road_id": "R-218",
                "current_route_id": "R-218;R-211;R-207;R-204",
                "original_route_id": "R-218;R-211;R-207;R-204",
                "speed_kmh": 48.0,
                "status": VehicleStatus.IN_TRANSIT
            },
            {
                "vehicle_id": "V-106",
                "vehicle_type": "VAN",
                "capacity": 2500.0,
                "current_lat": 25.1100,
                "current_lng": 92.8700,
                "current_road_id": "R-303",
                "current_route_id": "R-303",
                "original_route_id": "R-303",
                "speed_kmh": 38.0,
                "status": VehicleStatus.IN_TRANSIT
            },
            {
                "vehicle_id": "V-107",
                "vehicle_type": "HEAVY_TRUCK",
                "capacity": 15000.0,
                "current_lat": 26.2300,
                "current_lng": 92.5200,
                "current_road_id": "R-301",
                "current_route_id": "R-301;R-302;R-303",
                "original_route_id": "R-301;R-302;R-303",
                "speed_kmh": 40.0,
                "status": VehicleStatus.IN_TRANSIT
            },
            {
                "vehicle_id": "V-108",
                "vehicle_type": "SPECIALIZED_VEHICLE",
                "capacity": 3000.0,
                "current_lat": 25.4900,
                "current_lng": 92.1800,
                "current_road_id": "R-207",
                "current_route_id": "R-207;R-211;R-218",
                "original_route_id": "R-207;R-211;R-218",
                "speed_kmh": 40.0,
                "status": VehicleStatus.IN_TRANSIT
            }
        ]
        
        for veh_data in vehicles_data:
            vehicle = Vehicle(**veh_data)
            db.add(vehicle)
            
            # Add initial telemetry
            telemetry = VehicleTelemetry(
                vehicle_id=veh_data["vehicle_id"],
                lat=veh_data["current_lat"],
                lng=veh_data["current_lng"],
                speed_kmh=veh_data["speed_kmh"],
                heading=0.0
            )
            db.add(telemetry)
        
        db.commit()
        
        # Seed Deliveries
        base_time = datetime.now()
        deliveries_data = [
            {
                "delivery_id": "DL-1092",
                "vehicle_id": "V-104",
                "cargo_type": "Essential Medicines",
                "priority": DeliveryPriority.CRITICAL,
                "origin": "Guwahati Central Depot",
                "destination": "Silchar District Hospital",
                "current_route": json.dumps(["R-204", "R-207", "R-211", "R-218"]),
                "distance_remaining": 270.0,
                "eta": base_time + timedelta(hours=4, minutes=40),
                "risk_score": 61.0,
                "status": DeliveryStatus.EN_ROUTE,
                "weight_kg": 450.0,
                "original_eta": base_time + timedelta(hours=4, minutes=40),
                "delay_reason": "",
                "on_time_probability": 39.0
            },
            {
                "delivery_id": "DL-1093",
                "vehicle_id": "V-103",
                "cargo_type": "Drinking Water Containers",
                "priority": DeliveryPriority.HIGH,
                "origin": "Shillong Depot",
                "destination": "Jowai Distribution Point",
                "current_route": json.dumps(["R-207"]),
                "distance_remaining": 40.0,
                "eta": base_time + timedelta(hours=1, minutes=10),
                "risk_score": 15.0,
                "status": DeliveryStatus.EN_ROUTE,
                "weight_kg": 2500.0,
                "original_eta": base_time + timedelta(hours=1, minutes=10),
                "delay_reason": "",
                "on_time_probability": 85.0
            },
            {
                "delivery_id": "DL-1094",
                "vehicle_id": "V-107",
                "cargo_type": "Construction Structural Steel",
                "priority": DeliveryPriority.MEDIUM,
                "origin": "Guwahati Steel Yard",
                "destination": "Silchar Infrastructure Project",
                "current_route": json.dumps(["R-301", "R-302", "R-303"]),
                "distance_remaining": 300.0,
                "eta": base_time + timedelta(hours=6, minutes=30),
                "risk_score": 28.0,
                "status": DeliveryStatus.EN_ROUTE,
                "weight_kg": 8500.0,
                "original_eta": base_time + timedelta(hours=6, minutes=30),
                "delay_reason": "",
                "on_time_probability": 72.0
            },
            {
                "delivery_id": "DL-1095",
                "vehicle_id": "V-101",
                "cargo_type": "Agricultural Winter Seeds",
                "priority": DeliveryPriority.NORMAL,
                "origin": "Guwahati Depot",
                "destination": "Shillong Market",
                "current_route": json.dumps(["R-204"]),
                "distance_remaining": 55.0,
                "eta": base_time + timedelta(hours=1, minutes=50),
                "risk_score": 20.0,
                "status": DeliveryStatus.EN_ROUTE,
                "weight_kg": 1200.0,
                "original_eta": base_time + timedelta(hours=1, minutes=50),
                "delay_reason": "",
                "on_time_probability": 80.0
            },
            {
                "delivery_id": "DL-1096",
                "vehicle_id": "V-102",
                "cargo_type": "Baby Food Packets",
                "priority": DeliveryPriority.HIGH,
                "origin": "Guwahati Depot",
                "destination": "Shillong Warehouse",
                "current_route": json.dumps(["R-204"]),
                "distance_remaining": 60.0,
                "eta": base_time + timedelta(hours=2, minutes=30),
                "risk_score": 25.0,
                "status": DeliveryStatus.EN_ROUTE,
                "weight_kg": 800.0,
                "original_eta": base_time + timedelta(hours=2, minutes=30),
                "delay_reason": "",
                "on_time_probability": 75.0
            },
            {
                "delivery_id": "DL-1097",
                "vehicle_id": "V-108",
                "cargo_type": "Medical Oxygen Cylinder Pack",
                "priority": DeliveryPriority.CRITICAL,
                "origin": "Shillong Medical Gas",
                "destination": "Silchar District Hospital",
                "current_route": json.dumps(["R-207", "R-211", "R-218"]),
                "distance_remaining": 160.0,
                "eta": base_time + timedelta(hours=5, minutes=15),
                "risk_score": 52.0,
                "status": DeliveryStatus.EN_ROUTE,
                "weight_kg": 600.0,
                "original_eta": base_time + timedelta(hours=5, minutes=15),
                "delay_reason": "",
                "on_time_probability": 48.0
            },
            {
                "delivery_id": "DL-1098",
                "vehicle_id": "V-106",
                "cargo_type": "Hygiene & Sanitation Kits",
                "priority": DeliveryPriority.MEDIUM,
                "origin": "Haflong Warehouse",
                "destination": "Silchar NGO Center",
                "current_route": json.dumps(["R-303"]),
                "distance_remaining": 80.0,
                "eta": base_time + timedelta(hours=3, minutes=50),
                "risk_score": 32.0,
                "status": DeliveryStatus.EN_ROUTE,
                "weight_kg": 400.0,
                "original_eta": base_time + timedelta(hours=3, minutes=50),
                "delay_reason": "",
                "on_time_probability": 68.0
            }
        ]
        
        for deliv_data in deliveries_data:
            delivery = Delivery(**deliv_data)
            db.add(delivery)
            
            # Create initial route record
            route = Route(
                route_id=f"RT-{deliv_data['delivery_id']}",
                delivery_id=deliv_data["delivery_id"],
                name=f"Route for {deliv_data['delivery_id']}",
                path=json.dumps([]),  # Will be populated by route service
                distance_km=deliv_data["distance_remaining"],
                travel_time_minutes=0.0,
                road_ids=deliv_data["current_route"],
                is_alternative=False
            )
            db.add(route)
        
        db.commit()
        
        # Seed Weather
        weather = WeatherObservation(
            location="NER-Region",
            rainfall_mm=142.0,
            visibility_km=3.0,
            temperature=28.0,
            weather_condition=WeatherCondition.HEAVY_RAIN,
            forecast_risk=0.7
        )
        db.add(weather)
        db.commit()
        
        print("Database seeded successfully!")
        return True
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
        return False
    finally:
        db.close()

if __name__ == "__main__":
    from app.database_sqlalchemy import init_db
    init_db()
    seed_database()
