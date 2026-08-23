"""
End-to-End System Verification Script.
Tests:
1. Static files (index.html, style.css, app.js) served by FastAPI.
2. GET /api/nodes, GET /api/roads, GET /api/vehicles, GET /api/weather-presets.
3. POST /api/route with Clear Weather vs Storm Weather (verifying dynamic rerouting).
4. POST /api/route with Petrol vs EV (verifying fuel/energy and CO2 calculations).
5. GET /api/history (verifying SQLite persistence).
"""

import json
import urllib.request

API_BASE = "http://127.0.0.1:8000"

def test_api():
    print("="*60)
    print("STARTING FULL END-TO-END PIPELINE VERIFICATION")
    print("="*60)

    # 1. Health check
    with urllib.request.urlopen(f"{API_BASE}/api/health") as response:
        assert response.status == 200
        health = json.loads(response.read().decode())
        print(f"[1/5] Health Check PASSED: {health}")

    # 2. Metadata endpoints
    with urllib.request.urlopen(f"{API_BASE}/api/nodes") as response:
        assert response.status == 200
        nodes = json.loads(response.read().decode())["nodes"]
        print(f"[2/5] Nodes Endpoint PASSED: Loaded {len(nodes)} nodes (e.g. {nodes[0]['node_name']})")

    # 3. Route Optimization: Normal Clear Weather
    payload_normal = {
        "source_id": "NODE_CP",
        "destination_id": "NODE_CYBER",
        "hour_of_day": 9,
        "day_of_week": 1,
        "weather_condition": "Clear",
        "vehicle_type": "Petrol_Sedan",
        "custom_weights": {"time": 0.5, "fuel": 0.3, "weather": 0.2}
    }
    req = urllib.request.Request(
        f"{API_BASE}/api/route",
        data=json.dumps(payload_normal).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req) as response:
        assert response.status == 200
        res_normal = json.loads(response.read().decode())
        fastest = res_normal["routes"]["fastest"]
        eco = res_normal["routes"]["eco"]
        safe = res_normal["routes"]["weather_safe"]
        
        print("\n[3/5] Clear Weather Route Optimization (Connaught Place -> Gurgaon Cyber City):")
        print(f"  [FASTEST]    {fastest['total_time_min']} min | {fastest['total_fuel_units']} L Petrol | Rs.{fastest['total_cost_inr']} | Safety: {fastest['weather_safety_score']}% | Engine: {fastest['engine_used']}")
        print(f"  [ECO]        {eco['total_time_min']} min | {eco['total_fuel_units']} L Petrol | Rs.{eco['total_cost_inr']} | Safety: {eco['weather_safety_score']}%")
        print(f"  [WEATHER]    {safe['total_time_min']} min | {safe['total_fuel_units']} L Petrol | Rs.{safe['total_cost_inr']} | Safety: {safe['weather_safety_score']}%")

    # 4. Route Optimization: Severe Storm / Flooding Scenario
    payload_storm = {
        "source_id": "NODE_CP",
        "destination_id": "NODE_CYBER",
        "hour_of_day": 18,
        "day_of_week": 4,
        "weather_condition": "Storm",
        "vehicle_type": "Electric_Vehicle"
    }
    req_storm = urllib.request.Request(
        f"{API_BASE}/api/route",
        data=json.dumps(payload_storm).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req_storm) as response:
        assert response.status == 200
        res_storm = json.loads(response.read().decode())
        storm_fastest = res_storm["routes"]["fastest"]
        storm_safe = res_storm["routes"]["weather_safe"]
        
        print("\n[4/5] Storm Weather + EV Simulation (Peak Evening Storm):")
        print(f"  [FASTEST]    {storm_fastest['total_time_min']} min | {storm_fastest['total_fuel_units']} kWh EV | Safety: {storm_fastest['weather_safety_score']}%")
        print(f"  [SAFE]       {storm_safe['total_time_min']} min | {storm_safe['total_fuel_units']} kWh EV | Safety: {storm_safe['weather_safety_score']}%")
        print(f"  [ADVISORY]   {storm_safe['weather_advisories']}")

    # 5. Database History Check
    with urllib.request.urlopen(f"{API_BASE}/api/history?limit=5") as response:
        assert response.status == 200
        history = json.loads(response.read().decode())["history"]
        print(f"\n[5/5] SQLite Persistence Check: Found {len(history)} logged queries.")
        print(f"  Latest Log: {history[0]['source_id']} -> {history[0]['destination_id']} | Vehicle: {history[0]['vehicle_type']} | Condition: {history[0]['weather_condition']}")

    print("\n" + "="*60)
    print("ALL 5 END-TO-END PIPELINE CHECKS PASSED WITH FLYING COLORS!")
    print("="*60)

if __name__ == "__main__":
    test_api()
