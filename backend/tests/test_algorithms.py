"""
Tests for the 7 core algorithms integrated into the CSV-based backend.
"""

import pytest
from app.database import reset_database, load_roads, save_roads, load_weather, save_weather, load_incidents, save_incidents
from app.models.models import WeatherObservation, Incident
from app.services.risk_engine import calculate_road_risk, classify_risk_level, cluster_incidents_dbscan
from app.services.graph_engine import (
    compute_accessibility_score,
    compute_risk_score,
    calculate_edge_cost,
    build_road_graph,
    detect_bottlenecks,
    calculate_district_connectivity,
    get_road_edge_attributes,
)
from app.services.routing_engine import find_best_route, calculate_route_cost, astar_find_path
from app.services.geofence_service import calculate_route_deviation, distance_to_planned_route, haversine_km
from app.services.eta_engine import calculate_vehicle_eta
from app.services.alert_engine import evaluate_alerts
from app.services.decision_engine import run_decision_pipeline
from app.services.incident_service import register_incident_and_cascade
from app.database import load_vehicles, load_deliveries
from app.ml.disruption_model import predict_disruption
from app.ml.delay_model import predict_delay
import time


@pytest.fixture(autouse=True)
def clean_db():
    reset_database()
    yield


class TestRiskEngine:
    def test_risk_calculation(self):
        roads = load_roads()
        weather = load_weather()
        result = calculate_road_risk(roads[0], weather)
        assert 0 <= result["risk_score"] <= 100
        assert result["risk_level"] in ("LOW", "MODERATE", "HIGH", "CRITICAL", "BLOCKED")
        assert len(result["factors"]) > 0

    def test_risk_classification(self):
        assert classify_risk_level(20) == "LOW"
        assert classify_risk_level(45) == "MODERATE"
        assert classify_risk_level(70) == "HIGH"
        assert classify_risk_level(90) == "CRITICAL"

    def test_accessibility_score(self):
        roads = load_roads()
        score = compute_accessibility_score(roads[0])
        assert 0 <= score <= 100

    def test_rainfall_increases_risk(self):
        roads = load_roads()
        road = next(r for r in roads if r.road_id == "R-204")
        low_weather = WeatherObservation(rainfall_mm=20, forecast="Clear", visibility_km=8, weather_risk_level="LOW")
        high_weather = WeatherObservation(rainfall_mm=150, forecast="Heavy Rain", visibility_km=1, weather_risk_level="CRITICAL")
        low_risk = calculate_road_risk(road, low_weather)["risk_score"]
        high_risk = calculate_road_risk(road, high_weather)["risk_score"]
        assert high_risk > low_risk


class TestGraphEngine:
    def test_build_graph(self):
        roads = load_roads()
        g = build_road_graph(roads, force_rebuild=True)
        assert g.number_of_nodes() >= 7
        assert g.number_of_edges() >= 7

    def test_edge_attributes(self):
        roads = load_roads()
        edge = get_road_edge_attributes(roads[0])
        assert "dynamic_cost" in edge
        assert "risk_score" in edge
        assert "accessibility_score" in edge

    def test_blocked_road_infinite_cost(self):
        roads = load_roads()
        roads[0].status = "BLOCKED"
        cost = calculate_edge_cost(roads[0])
        assert cost == float("inf")

    def test_bottleneck_detection(self):
        roads = load_roads()
        bottlenecks = detect_bottlenecks(roads)
        assert isinstance(bottlenecks, list)

    def test_district_connectivity(self):
        roads = load_roads()
        districts = calculate_district_connectivity(roads)
        assert len(districts) > 0
        assert "connectivity_score" in districts[0]


class TestRoutingEngine:
    def test_astar_finds_path(self):
        roads = load_roads()
        g = build_road_graph(roads, force_rebuild=True)
        path = astar_find_path(g, "J-GUW", "J-SIL")
        assert path is not None
        assert len(path) >= 3

    def test_blocked_road_handling(self):
        roads = load_roads()
        for r in roads:
            if r.road_id == "R-204":
                r.status = "BLOCKED"
        route = find_best_route("Guwahati", "Silchar", roads, blocked_roads=["R-204"])
        assert route.get("road_ids")
        assert "R-204" not in route["road_ids"]

    def test_alternative_route_selection(self):
        roads = load_roads()
        for r in roads:
            if r.road_id == "R-204":
                r.status = "BLOCKED"
        route = find_best_route("Guwahati", "Silchar", roads, priority="CRITICAL")
        assert route["risk_score"] < 100 or route.get("is_blocked") is False

    def test_route_cost_increases_with_risk(self):
        roads = load_roads()
        roads_dict = {r.road_id: r for r in roads}
        low_cost = calculate_route_cost(["R-301", "R-302", "R-303"], roads_dict)
        for r in roads:
            if r.road_id == "R-302":
                r.traffic_level = 95
                r.road_condition = 2
        roads_dict = {r.road_id: r for r in roads}
        high_cost = calculate_route_cost(["R-301", "R-302", "R-303"], roads_dict)
        assert high_cost["total_cost"] >= low_cost["total_cost"]


class TestGeofencing:
    def test_haversine(self):
        d = haversine_km(26.1445, 91.7362, 25.5788, 91.8833)
        assert 50 < d < 120

    def test_route_deviation(self):
        vehicles = load_vehicles()
        roads = load_roads()
        roads_dict = {r.road_id: r for r in roads}
        veh = vehicles[0]
        result = calculate_route_deviation(veh, roads_dict, threshold_km=50.0)
        assert "route_deviation" in result
        assert "distance_from_route_km" in result


class TestMLModels:
    def test_disruption_prediction(self):
        result = predict_disruption({
            "rainfall": 150, "traffic": 70, "road_condition": 3,
            "road_risk": 80, "historical_incidents": 5, "incident_count": 2,
            "terrain_risk": 60, "vehicle_speed": 30, "distance": 200,
            "historical_travel_time": 4,
        })
        assert "probability" in result
        assert "risk_level" in result

    def test_delay_prediction(self):
        result = predict_delay({
            "rainfall": 150, "traffic": 70, "road_risk": 80,
            "distance": 200, "vehicle_speed": 30, "historical_travel_time": 4,
            "incident_count": 2, "terrain_risk": 60,
        })
        assert "predicted_delay_minutes" in result
        assert result["predicted_delay_minutes"] >= 0


class TestDBSCAN:
    def test_incident_clustering(self):
        incidents = [
            Incident(incident_id="I1", road_id="R-204", lat=25.90, lon=91.88, type="Landslide",
                     severity="CRITICAL", description="a", timestamp=time.time(), active=True),
            Incident(incident_id="I2", road_id="R-204", lat=25.91, lon=91.89, type="Landslide",
                     severity="HIGH", description="b", timestamp=time.time(), active=True),
            Incident(incident_id="I3", road_id="R-204", lat=25.905, lon=91.885, type="Flood",
                     severity="HIGH", description="c", timestamp=time.time(), active=True),
        ]
        result = cluster_incidents_dbscan(incidents, eps_km=20, min_samples=2)
        assert result["total_active_incidents"] == 3


class TestAlertEngine:
    def test_critical_risk_alert(self):
        roads = load_roads()
        for r in roads:
            r.disruption_probability = 0.9
            r.risk_level = "CRITICAL"
        alerts = evaluate_alerts(roads, ml_predictions={"probability": 0.9, "risk_level": "CRITICAL"})
        assert len(alerts) > 0

    def test_blocked_road_alert(self):
        roads = load_roads()
        roads[0].status = "BLOCKED"
        alerts = evaluate_alerts(roads)
        assert any(a.type == "ROAD_BLOCKED" for a in alerts)


class TestIncidentChain:
    def test_landslide_cascade(self):
        result = register_incident_and_cascade(
            road_id="R-204", lat=25.9015, lon=91.8800,
            incident_type="Landslide", severity="CRITICAL",
            description="Test landslide",
        )
        assert result["road_blocked"] is True
        roads = load_roads()
        r204 = next(r for r in roads if r.road_id == "R-204")
        assert r204.status == "BLOCKED"

    def test_end_to_end_disruption(self):
        weather = WeatherObservation(rainfall_mm=150, forecast="Heavy Rain", visibility_km=1, weather_risk_level="CRITICAL")
        save_weather(weather)
        from app.services.risk_service import recalculate_all_roads_risk
        recalculate_all_roads_risk()

        result = register_incident_and_cascade(
            road_id="R-204", lat=25.9015, lon=91.8800,
            incident_type="Landslide", severity="CRITICAL",
            description="Demo landslide",
        )
        assert result["affected_vehicles_count"] > 0
        pipeline = run_decision_pipeline(trigger="test")
        assert "decisions" in pipeline
        assert pipeline["alerts_generated"] >= 0


class TestETA:
    def test_eta_calculation(self):
        vehicles = load_vehicles()
        deliveries = load_deliveries()
        roads = load_roads()
        roads_dict = {r.road_id: r for r in roads}
        veh = next(v for v in vehicles if v.vehicle_id == "V-104")
        deliv = next(d for d in deliveries if d.vehicle_id == "V-104")
        result = calculate_vehicle_eta(veh, deliv, roads_dict)
        assert "eta_str" in result
        assert "explanation" in result
