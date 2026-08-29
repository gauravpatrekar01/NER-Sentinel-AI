import urllib.request
import urllib.parse
import json

BASE_URL = "http://127.0.0.1:8000"

def get(url):
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode())

def post(url, data):
    req = urllib.request.Request(
        url, 
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        return response.status, json.loads(response.read().decode())

def run_tests():
    print("--------------------------------------------------")
    print("RUNNING NER-SENTINEL AI END-TO-END API TESTS")
    print("--------------------------------------------------")

    # Test 1: Health check
    try:
        status, res = get(f"{BASE_URL}/")
        assert status == 200
        print("[PASS] Test 1: Health check endpoint responds successfully.")
    except Exception as e:
        print(f"[FAIL] Test 1: Health check endpoint failed. {e}")
        return

    # Test 2: Get Roads
    try:
        status, roads = get(f"{BASE_URL}/api/roads")
        assert status == 200
        assert len(roads) > 0
        r204 = next((r for r in roads if r["road_id"] == "R-204"), None)
        assert r204 is not None
        print(f"[PASS] Test 2: Roads endpoint. R-204 status is: {r204['status']}. Risk score is: {r204['accessibility_score']}/100.")
    except Exception as e:
        print(f"[FAIL] Test 2: Roads endpoint failed. {e}")
        return

    # Test 3: Get Vehicles
    try:
        status, vehicles = get(f"{BASE_URL}/api/vehicles")
        assert status == 200
        assert len(vehicles) > 0
        v104 = next((v for v in vehicles if v["vehicle_id"] == "V-104"), None)
        assert v104 is not None
        print(f"[PASS] Test 3: Vehicles endpoint. V-104 speed: {v104['speed_kmh']} km/h, original route: {v104['original_route_id']}.")
    except Exception as e:
        print(f"[FAIL] Test 3: Vehicles endpoint failed. {e}")
        return

    # Test 4: Post Incident (Trigger Landslide Cascade)
    try:
        payload = {
            "road_id": "R-204",
            "lat": 25.9015,
            "lon": 91.8800,
            "type": "Landslide",
            "severity": "CRITICAL",
            "description": "Test landslide block",
            "photo_url": None,
            "optimize_immediately": True
        }
        status, res = post(f"{BASE_URL}/api/incidents", payload)
        assert status == 200
        print(f"[PASS] Test 4: Incident registered successfully. Cascade returned affected vehicle count: {res['affected_vehicles_count']}.")
    except Exception as e:
        print(f"[FAIL] Test 4: Incident cascade failed. {e}")
        return

    # Test 5: Verify Cascade (Check if R-204 is blocked and V-104 is rerouted)
    try:
        status, roads = get(f"{BASE_URL}/api/roads")
        r204 = next((r for r in roads if r["road_id"] == "R-204"), None)
        assert r204["status"] == "BLOCKED"
        
        status, vehicles = get(f"{BASE_URL}/api/vehicles")
        v104 = next((v for v in vehicles if v["vehicle_id"] == "V-104"), None)
        # Check that current route is different from original route (meaning it rerouted to alternate R-301/R-302/R-303!)
        assert v104["current_route_id"] != v104["original_route_id"]
        
        status, deliveries = get(f"{BASE_URL}/api/deliveries")
        dl1092 = next((d for d in deliveries if d["delivery_id"] == "DL-1092"), None)
        assert dl1092["delivery_risk_pct"] == 18.0 or dl1092["delivery_risk_pct"] < 30.0 # Rerouted to safer route
        
        print(f"[PASS] Test 5: Verification of blockage and rerouting cascade. V-104 successfully rerouted. DL-1092 risk decreased to {dl1092['delivery_risk_pct']}% on alternate path.")
    except Exception as e:
        print(f"[FAIL] Test 5: Rerouting cascade verification failed. {e}")
        return

    # Test 6: Run Simulator Scenario
    try:
        sim_payload = {
            "scenario": "landslide",
            "rainfall_mm": 180.0
        }
        status, sim_res = post(f"{BASE_URL}/api/simulation/run", sim_payload)
        assert status == 200
        assert sim_res["baseline_delayed_count"] > sim_res["optimized_delayed_count"]
        print(f"[PASS] Test 6: Scenario Simulator executed successfully. Baseline delays: {sim_res['baseline_delayed_count']} vs Optimized delays: {sim_res['optimized_delayed_count']}.")
    except Exception as e:
        print(f"[FAIL] Test 6: Scenario simulation failed. {e}")
        return

    # Test 7: Reset Demo
    try:
        status, reset_res = post(f"{BASE_URL}/api/reset", {})
        assert status == 200
        
        status, roads = get(f"{BASE_URL}/api/roads")
        r204 = next((r for r in roads if r["road_id"] == "R-204"), None)
        assert r204["status"] == "OPEN" or r204["status"] == "HIGH RISK" # Not blocked
        
        status, vehicles = get(f"{BASE_URL}/api/vehicles")
        v104 = next((v for v in vehicles if v["vehicle_id"] == "V-104"), None)
        assert v104["current_route_id"] == v104["original_route_id"]
        
        print("[PASS] Test 7: Demo successfully reset to initial states. R-204 is clear and vehicles restored.")
    except Exception as e:
        print(f"[FAIL] Test 7: Demo reset failed. {e}")
        return

    print("--------------------------------------------------")
    print("ALL END-TO-END TESTS PASSED SUCCESSFULLY!")
    print("--------------------------------------------------")

if __name__ == "__main__":
    run_tests()
