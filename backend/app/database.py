import os
import csv
import json
import time
from typing import List, Dict, Any, Optional
from app.config import DATA_DIR
from app.models.models import Road, Vehicle, Delivery, Incident, WeatherObservation, Alert

ROADS_CSV = os.path.join(DATA_DIR, "roads.csv")
VEHICLES_CSV = os.path.join(DATA_DIR, "vehicles.csv")
DELIVERIES_CSV = os.path.join(DATA_DIR, "deliveries.csv")
INCIDENTS_CSV = os.path.join(DATA_DIR, "incidents.csv")
WEATHER_CSV = os.path.join(DATA_DIR, "weather.csv")
ALERTS_CSV = os.path.join(DATA_DIR, "alerts.csv")

# Core Geographic Seed Data
SEED_ROADS = [
    # Primary NH-6 corridor (Guwahati -> Shillong -> Jowai -> Khliehriat -> Silchar)
    {
        "road_id": "R-204",
        "name": "Guwahati-Shillong Highway (NH-6)",
        "length_km": 100.0,
        "status": "OPEN",
        "rainfall_mm": 120.0,
        "terrain_risk": 62.0,
        "historical_incidents": 6,
        "road_condition": 4.5,
        "flood_risk": 40.0,
        "landslide_history": 72.0,
        "traffic_level": 62.0,
        "field_incident_severity": "None",
        "path": "26.1445,91.7362;26.1200,91.7900;26.1150,91.8900;26.0400,91.8900;25.9015,91.8800;25.7500,91.8900;25.6420,91.8950;25.5788,91.8833"
    },
    {
        "road_id": "R-207",
        "name": "Shillong-Jowai Bypass (NH-6)",
        "length_km": 65.0,
        "status": "OPEN",
        "rainfall_mm": 30.0,
        "terrain_risk": 35.0,
        "historical_incidents": 2,
        "road_condition": 7.5,
        "flood_risk": 10.0,
        "landslide_history": 30.0,
        "traffic_level": 40.0,
        "field_incident_severity": "None",
        "path": "25.5788,91.8833;25.5700,92.0500;25.4900,92.1800;25.4484,92.2032"
    },
    {
        "road_id": "R-211",
        "name": "Jowai-Khliehriat Road (NH-6)",
        "length_km": 30.0,
        "status": "OPEN",
        "rainfall_mm": 40.0,
        "terrain_risk": 30.0,
        "historical_incidents": 1,
        "road_condition": 7.0,
        "flood_risk": 15.0,
        "landslide_history": 25.0,
        "traffic_level": 45.0,
        "field_incident_severity": "None",
        "path": "25.4484,92.2032;25.3700,92.3100;25.3578,92.3689"
    },
    {
        "road_id": "R-218",
        "name": "Khliehriat-Silchar Ridge (NH-6)",
        "length_km": 95.0,
        "status": "OPEN",
        "rainfall_mm": 55.0,
        "terrain_risk": 75.0,
        "historical_incidents": 8,
        "road_condition": 5.5,
        "flood_risk": 40.0,
        "landslide_history": 80.0,
        "traffic_level": 35.0,
        "field_incident_severity": "None",
        "path": "25.3578,92.3689;25.1700,92.3800;25.1050,92.4200;24.9700,92.5700;24.8970,92.5930;24.8333,92.7789"
    },
    # Alternate NH-27/NH-54 corridor (Guwahati -> Nagaon -> Haflong -> Silchar)
    {
        "road_id": "R-301",
        "name": "Guwahati-Nagaon Expressway (NH-27)",
        "length_km": 120.0,
        "status": "OPEN",
        "rainfall_mm": 20.0,
        "terrain_risk": 10.0,
        "historical_incidents": 1,
        "road_condition": 9.0,
        "flood_risk": 30.0,
        "landslide_history": 10.0,
        "traffic_level": 70.0,
        "field_incident_severity": "None",
        "path": "26.1445,91.7362;26.1100,92.1700;26.2300,92.5200;26.3500,92.6800"
    },
    {
        "road_id": "R-302",
        "name": "Nagaon-Haflong Mountain Cut (NH-54)",
        "length_km": 150.0,
        "status": "OPEN",
        "rainfall_mm": 25.0,
        "terrain_risk": 55.0,
        "historical_incidents": 3,
        "road_condition": 7.0,
        "flood_risk": 20.0,
        "landslide_history": 40.0,
        "traffic_level": 30.0,
        "field_incident_severity": "None",
        "path": "26.3500,92.6800;26.1300,92.8900;25.9200,93.0000;25.7500,92.9500;25.5700,92.9800;25.1700,93.0300"
    },
    {
        "road_id": "R-303",
        "name": "Haflong-Silchar Link (NH-270)",
        "length_km": 100.0,
        "status": "OPEN",
        "rainfall_mm": 35.0,
        "terrain_risk": 60.0,
        "historical_incidents": 4,
        "road_condition": 6.5,
        "flood_risk": 35.0,
        "landslide_history": 50.0,
        "traffic_level": 25.0,
        "field_incident_severity": "None",
        "path": "25.1700,93.0300;25.1500,93.0300;25.1100,92.8700;24.9800,92.8500;24.8333,92.7789"
    }
]

SEED_VEHICLES = [
    {
        "vehicle_id": "V-101",
        "cargo": "Agricultural Seeds",
        "origin": "Guwahati Depot",
        "destination": "Shillong Market",
        "current_lat": 26.0400,
        "current_lon": 91.8900,
        "speed_kmh": 45.0,
        "current_route_id": "R-204",
        "original_route_id": "R-204",
        "eta_str": "12:50",
        "original_eta_str": "12:50",
        "delivery_risk_pct": 20.0,
        "progress": 0.45,
        "status": "EN_ROUTE"
    },
    {
        "vehicle_id": "V-102",
        "cargo": "Food Supplies",
        "origin": "Guwahati Depot",
        "destination": "Shillong Warehouse",
        "current_lat": 25.9015,
        "current_lon": 91.8800,
        "speed_kmh": 40.0,
        "current_route_id": "R-204",
        "original_route_id": "R-204",
        "eta_str": "13:30",
        "original_eta_str": "13:30",
        "delivery_risk_pct": 25.0,
        "progress": 0.65,
        "status": "EN_ROUTE"
    },
    {
        "vehicle_id": "V-103",
        "cargo": "Drinking Water",
        "origin": "Shillong Depot",
        "destination": "Jowai Distribution Point",
        "current_lat": 25.5700,
        "current_lon": 92.0500,
        "speed_kmh": 35.0,
        "current_route_id": "R-207",
        "original_route_id": "R-207",
        "eta_str": "13:10",
        "original_eta_str": "13:10",
        "delivery_risk_pct": 15.0,
        "progress": 0.30,
        "status": "EN_ROUTE"
    },
    {
        "vehicle_id": "V-104",  # Primary Demo Vehicle
        "cargo": "Essential Medicines",
        "origin": "Guwahati Central Depot",
        "destination": "Silchar District Hospital",
        "current_lat": 26.1200,
        "current_lon": 91.7900,
        "speed_kmh": 42.0,
        "current_route_id": "R-204;R-207;R-211;R-218",
        "original_route_id": "R-204;R-207;R-211;R-218",
        "eta_str": "16:40",
        "original_eta_str": "16:40",
        "delivery_risk_pct": 61.0,
        "progress": 0.12,
        "status": "EN_ROUTE"
    },
    {
        "vehicle_id": "V-105",
        "cargo": "Return Cargo (Empty crates)",
        "origin": "Silchar Depot",
        "destination": "Guwahati Depot",
        "current_lat": 24.8970,
        "current_lon": 92.5930,
        "speed_kmh": 48.0,
        "current_route_id": "R-218;R-211;R-207;R-204",
        "original_route_id": "R-218;R-211;R-207;R-204",
        "eta_str": "18:20",
        "original_eta_str": "18:20",
        "delivery_risk_pct": 45.0,
        "progress": 0.10,
        "status": "EN_ROUTE"
    },
    {
        "vehicle_id": "V-106",
        "cargo": "Sanitation Kits",
        "origin": "Haflong Warehouse",
        "destination": "Silchar NGO Center",
        "current_lat": 25.1100,
        "current_lon": 92.8700,
        "speed_kmh": 38.0,
        "current_route_id": "R-303",
        "original_route_id": "R-303",
        "eta_str": "14:50",
        "original_eta_str": "14:50",
        "delivery_risk_pct": 32.0,
        "progress": 0.50,
        "status": "EN_ROUTE"
    },
    {
        "vehicle_id": "V-107",
        "cargo": "Construction Material",
        "origin": "Guwahati Steel Yard",
        "destination": "Silchar Infrastructure Project",
        "current_lat": 26.2300,
        "current_lon": 92.5200,
        "speed_kmh": 40.0,
        "current_route_id": "R-301;R-302;R-303",
        "original_route_id": "R-301;R-302;R-303",
        "eta_str": "19:30",
        "original_eta_str": "19:30",
        "delivery_risk_pct": 28.0,
        "progress": 0.18,
        "status": "EN_ROUTE"
    },
    {
        "vehicle_id": "V-108",
        "cargo": "Medical Oxygen Cylinders",
        "origin": "Shillong Medical Gas",
        "destination": "Silchar District Hospital",
        "current_lat": 25.4900,
        "current_lon": 92.1800,
        "speed_kmh": 40.0,
        "current_route_id": "R-207;R-211;R-218",
        "original_route_id": "R-207;R-211;R-218",
        "eta_str": "17:15",
        "original_eta_str": "17:15",
        "delivery_risk_pct": 52.0,
        "progress": 0.25,
        "status": "EN_ROUTE"
    }
]

SEED_DELIVERIES = [
    {
        "delivery_id": "DL-1092",
        "cargo": "Essential Medicines",
        "priority": "CRITICAL",
        "vehicle_id": "V-104",
        "origin": "Guwahati Central Depot",
        "destination": "Silchar District Hospital",
        "status": "EN_ROUTE",
        "weight_kg": 450.0,
        "eta_str": "16:40",
        "original_eta_str": "16:40",
        "delay_reason": "",
        "delivery_risk_pct": 61.0,
        "on_time_probability": 39.0
    },
    {
        "delivery_id": "DL-1093",
        "cargo": "Drinking Water Containers",
        "priority": "HIGH",
        "vehicle_id": "V-103",
        "origin": "Shillong Depot",
        "destination": "Jowai Distribution Point",
        "status": "EN_ROUTE",
        "weight_kg": 2500.0,
        "eta_str": "13:10",
        "original_eta_str": "13:10",
        "delay_reason": "",
        "delivery_risk_pct": 15.0,
        "on_time_probability": 85.0
    },
    {
        "delivery_id": "DL-1094",
        "cargo": "Construction Structural Steel",
        "priority": "MEDIUM",
        "vehicle_id": "V-107",
        "origin": "Guwahati Steel Yard",
        "destination": "Silchar Infrastructure Project",
        "status": "EN_ROUTE",
        "weight_kg": 8500.0,
        "eta_str": "19:30",
        "original_eta_str": "19:30",
        "delay_reason": "",
        "delivery_risk_pct": 28.0,
        "on_time_probability": 72.0
    },
    {
        "delivery_id": "DL-1095",
        "cargo": "Agricultural Winter Seeds",
        "priority": "NORMAL",
        "vehicle_id": "V-101",
        "origin": "Guwahati Depot",
        "destination": "Shillong Market",
        "status": "EN_ROUTE",
        "weight_kg": 1200.0,
        "eta_str": "12:50",
        "original_eta_str": "12:50",
        "delay_reason": "",
        "delivery_risk_pct": 20.0,
        "on_time_probability": 80.0
    },
    {
        "delivery_id": "DL-1096",
        "cargo": "Baby Food Packets",
        "priority": "HIGH",
        "vehicle_id": "V-102",
        "origin": "Guwahati Depot",
        "destination": "Shillong Warehouse",
        "status": "EN_ROUTE",
        "weight_kg": 800.0,
        "eta_str": "13:30",
        "original_eta_str": "13:30",
        "delay_reason": "",
        "delivery_risk_pct": 25.0,
        "on_time_probability": 75.0
    },
    {
        "delivery_id": "DL-1097",
        "cargo": "Medical Oxygen Cylinder Pack",
        "priority": "CRITICAL",
        "vehicle_id": "V-108",
        "origin": "Shillong Medical Gas",
        "destination": "Silchar District Hospital",
        "status": "EN_ROUTE",
        "weight_kg": 600.0,
        "eta_str": "17:15",
        "original_eta_str": "17:15",
        "delay_reason": "",
        "delivery_risk_pct": 52.0,
        "on_time_probability": 48.0
    },
    {
        "delivery_id": "DL-1098",
        "cargo": "Hygiene & Sanitation Kits",
        "priority": "MEDIUM",
        "vehicle_id": "V-106",
        "origin": "Haflong Warehouse",
        "destination": "Silchar NGO Center",
        "status": "EN_ROUTE",
        "weight_kg": 400.0,
        "eta_str": "14:50",
        "original_eta_str": "14:50",
        "delay_reason": "",
        "delivery_risk_pct": 32.0,
        "on_time_probability": 68.0
    }
]

SEED_WEATHER = {
    "rainfall_mm": 142.0,
    "forecast": "Heavy Rain",
    "visibility_km": 3.0,
    "weather_risk_level": "HIGH"
}

def parse_coordinates(path_str: str) -> List[List[float]]:
    coords = []
    if not path_str:
        return coords
    for pair in path_str.split(";"):
        if pair.strip():
            lat, lon = map(float, pair.split(","))
            coords.append([lat, lon])
    return coords

def stringify_coordinates(coords: List[List[float]]) -> str:
    return ";".join(f"{c[0]},{c[1]}" for c in coords)

def reset_database():
    # Seed Roads
    with open(ROADS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["road_id", "name", "length_km", "status", "rainfall_mm", "terrain_risk", 
                         "historical_incidents", "road_condition", "flood_risk", "landslide_history", 
                         "traffic_level", "field_incident_severity", "accessibility_score",
                         "disruption_probability", "risk_level", "path"])
        for road in SEED_ROADS:
            writer.writerow([
                road["road_id"], road["name"], road["length_km"], road["status"], road["rainfall_mm"],
                road["terrain_risk"], road["historical_incidents"], road["road_condition"],
                road["flood_risk"], road["landslide_history"], road["traffic_level"],
                road["field_incident_severity"], 100.0, 0.0, "LOW", road["path"]
            ])

    # Seed Vehicles
    with open(VEHICLES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["vehicle_id", "cargo", "origin", "destination", "current_lat", "current_lon",
                         "speed_kmh", "current_route_id", "original_route_id", "eta_str", "original_eta_str",
                         "delivery_risk_pct", "progress", "status", "last_updated"])
        for veh in SEED_VEHICLES:
            writer.writerow([
                veh["vehicle_id"], veh["cargo"], veh["origin"], veh["destination"], veh["current_lat"],
                veh["current_lon"], veh["speed_kmh"], veh["current_route_id"], veh["original_route_id"],
                veh["eta_str"], veh["original_eta_str"], veh["delivery_risk_pct"], veh["progress"],
                veh["status"], time.time()
            ])

    # Seed Deliveries
    with open(DELIVERIES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["delivery_id", "cargo", "priority", "vehicle_id", "origin", "destination",
                         "status", "weight_kg", "eta_str", "original_eta_str", "delay_reason",
                         "delivery_risk_pct", "on_time_probability"])
        for deliv in SEED_DELIVERIES:
            writer.writerow([
                deliv["delivery_id"], deliv["cargo"], deliv["priority"], deliv["vehicle_id"],
                deliv["origin"], deliv["destination"], deliv["status"], deliv["weight_kg"],
                deliv["eta_str"], deliv["original_eta_str"], deliv["delay_reason"],
                deliv["delivery_risk_pct"], deliv["on_time_probability"]
            ])

    # Seed Incidents (Empty initially)
    with open(INCIDENTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["incident_id", "road_id", "lat", "lon", "type", "severity", "description", 
                         "photo_url", "timestamp", "active"])

    # Seed Weather
    with open(WEATHER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rainfall_mm", "forecast", "visibility_km", "weather_risk_level"])
        writer.writerow([
            SEED_WEATHER["rainfall_mm"], SEED_WEATHER["forecast"],
            SEED_WEATHER["visibility_km"], SEED_WEATHER["weather_risk_level"]
        ])

    # Seed Alerts (Empty initially)
    with open(ALERTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["alert_id", "type", "message", "timestamp", "severity", "read"])

# Initial creation on startup if files don't exist
if not os.path.exists(ROADS_CSV) or not os.path.exists(VEHICLES_CSV) or not os.path.exists(DELIVERIES_CSV):
    reset_database()

# Loader/Saver functions
def load_roads() -> List[Road]:
    roads = []
    if not os.path.exists(ROADS_CSV):
        reset_database()
    with open(ROADS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            roads.append(Road(
                road_id=row["road_id"],
                name=row["name"],
                length_km=float(row["length_km"]),
                status=row["status"],
                rainfall_mm=float(row["rainfall_mm"]),
                terrain_risk=float(row["terrain_risk"]),
                historical_incidents=int(row["historical_incidents"]),
                road_condition=float(row["road_condition"]),
                flood_risk=float(row["flood_risk"]),
                landslide_history=float(row["landslide_history"]),
                traffic_level=float(row["traffic_level"]),
                field_incident_severity=row["field_incident_severity"] if row["field_incident_severity"] != "None" else None,
                accessibility_score=float(row.get("accessibility_score", 100.0)),
                disruption_probability=float(row.get("disruption_probability", 0.0)),
                risk_level=row.get("risk_level", "LOW"),
                path=parse_coordinates(row["path"])
            ))
    return roads

def save_roads(roads: List[Road]):
    with open(ROADS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["road_id", "name", "length_km", "status", "rainfall_mm", "terrain_risk", 
                         "historical_incidents", "road_condition", "flood_risk", "landslide_history", 
                         "traffic_level", "field_incident_severity", "accessibility_score",
                         "disruption_probability", "risk_level", "path"])
        for r in roads:
            writer.writerow([
                r.road_id, r.name, r.length_km, r.status, r.rainfall_mm, r.terrain_risk,
                r.historical_incidents, r.road_condition, r.flood_risk, r.landslide_history,
                r.traffic_level, r.field_incident_severity if r.field_incident_severity else "None",
                r.accessibility_score, r.disruption_probability, r.risk_level,
                stringify_coordinates(r.path)
            ])

def load_vehicles() -> List[Vehicle]:
    vehicles = []
    if not os.path.exists(VEHICLES_CSV):
        reset_database()
    with open(VEHICLES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            vehicles.append(Vehicle(
                vehicle_id=row["vehicle_id"],
                cargo=row["cargo"],
                origin=row["origin"],
                destination=row["destination"],
                current_lat=float(row["current_lat"]),
                current_lon=float(row["current_lon"]),
                speed_kmh=float(row["speed_kmh"]),
                current_route_id=row["current_route_id"],
                original_route_id=row["original_route_id"],
                eta_str=row["eta_str"],
                original_eta_str=row["original_eta_str"],
                delivery_risk_pct=float(row["delivery_risk_pct"]),
                progress=float(row["progress"]),
                status=row["status"],
                last_updated=float(row["last_updated"]) if row.get("last_updated") else time.time()
            ))
    return vehicles

def save_vehicles(vehicles: List[Vehicle]):
    with open(VEHICLES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["vehicle_id", "cargo", "origin", "destination", "current_lat", "current_lon",
                         "speed_kmh", "current_route_id", "original_route_id", "eta_str", "original_eta_str",
                         "delivery_risk_pct", "progress", "status", "last_updated"])
        for v in vehicles:
            writer.writerow([
                v.vehicle_id, v.cargo, v.origin, v.destination, v.current_lat, v.current_lon,
                v.speed_kmh, v.current_route_id, v.original_route_id, v.eta_str, v.original_eta_str,
                v.delivery_risk_pct, v.progress, v.status, v.last_updated
            ])

def load_deliveries() -> List[Delivery]:
    deliveries = []
    if not os.path.exists(DELIVERIES_CSV):
        reset_database()
    with open(DELIVERIES_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            deliveries.append(Delivery(
                delivery_id=row["delivery_id"],
                cargo=row["cargo"],
                priority=row["priority"],
                vehicle_id=row["vehicle_id"],
                origin=row["origin"],
                destination=row["destination"],
                status=row["status"],
                weight_kg=float(row["weight_kg"]),
                eta_str=row["eta_str"],
                original_eta_str=row["original_eta_str"],
                delay_reason=row.get("delay_reason", ""),
                delivery_risk_pct=float(row["delivery_risk_pct"]),
                on_time_probability=float(row["on_time_probability"])
            ))
    return deliveries

def save_deliveries(deliveries: List[Delivery]):
    with open(DELIVERIES_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["delivery_id", "cargo", "priority", "vehicle_id", "origin", "destination",
                         "status", "weight_kg", "eta_str", "original_eta_str", "delay_reason",
                         "delivery_risk_pct", "on_time_probability"])
        for d in deliveries:
            writer.writerow([
                d.delivery_id, d.cargo, d.priority, d.vehicle_id, d.origin, d.destination,
                d.status, d.weight_kg, d.eta_str, d.original_eta_str, d.delay_reason or "",
                d.delivery_risk_pct, d.on_time_probability
            ])

def load_incidents() -> List[Incident]:
    incidents = []
    if not os.path.exists(INCIDENTS_CSV):
        reset_database()
    with open(INCIDENTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            incidents.append(Incident(
                incident_id=row["incident_id"],
                road_id=row["road_id"],
                lat=float(row["lat"]),
                lon=float(row["lon"]),
                type=row["type"],
                severity=row["severity"],
                description=row["description"],
                photo_url=row["photo_url"] if row["photo_url"] else None,
                timestamp=float(row["timestamp"]),
                active=row["active"] == "True" or row["active"] == "1"
            ))
    return incidents

def save_incidents(incidents: List[Incident]):
    with open(INCIDENTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["incident_id", "road_id", "lat", "lon", "type", "severity", "description", 
                         "photo_url", "timestamp", "active"])
        for i in incidents:
            writer.writerow([
                i.incident_id, i.road_id, i.lat, i.lon, i.type, i.severity, i.description,
                i.photo_url if i.photo_url else "", i.timestamp, str(i.active)
            ])

def load_weather() -> WeatherObservation:
    if not os.path.exists(WEATHER_CSV):
        reset_database()
    with open(WEATHER_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        row = next(reader)
        return WeatherObservation(
            rainfall_mm=float(row["rainfall_mm"]),
            forecast=row["forecast"],
            visibility_km=float(row["visibility_km"]),
            weather_risk_level=row["weather_risk_level"]
        )

def save_weather(w: WeatherObservation):
    with open(WEATHER_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["rainfall_mm", "forecast", "visibility_km", "weather_risk_level"])
        writer.writerow([w.rainfall_mm, w.forecast, w.visibility_km, w.weather_risk_level])

def load_alerts() -> List[Alert]:
    alerts = []
    if not os.path.exists(ALERTS_CSV):
        reset_database()
    with open(ALERTS_CSV, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            alerts.append(Alert(
                alert_id=row["alert_id"],
                type=row["type"],
                message=row["message"],
                timestamp=float(row["timestamp"]),
                severity=row["severity"],
                read=row["read"] == "True" or row["read"] == "1"
            ))
    return alerts

def save_alerts(alerts: List[Alert]):
    with open(ALERTS_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["alert_id", "type", "message", "timestamp", "severity", "read"])
        for a in alerts:
            writer.writerow([
                a.alert_id, a.type, a.message, a.timestamp, a.severity, str(a.read)
            ])
