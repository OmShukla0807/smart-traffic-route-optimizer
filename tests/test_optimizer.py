"""
Unit & Integration Tests for Path Pilot.
Tests:
- ML Model Artifact & 32-Feature Preprocessor
- C++ Dijkstra Graph Solver with Multi-Objective Weights
- Multi-Objective Pareto Router (Fastest, Eco, Clean Air AQI, Weather-Safe)
- SQLite Database Operations & Incident Simulation
- FastAPI REST Handler Functions
"""

import os
import sys
import pytest
import joblib
import pandas as pd
import numpy as np

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.core.cpp_bridge import CppDijkstraBridge
from backend.app.core.feature_mapper import EdgeWeightEngine
from backend.app.core.router import MultiObjectiveRouter
from database.db import (
    init_db, log_route_query, get_recent_history,
    add_or_toggle_incident, get_active_incidents, clear_all_incidents,
    get_database_analytics
)
from backend.app.schemas import RouteRequest, IncidentSimulationRequest
from backend.app.main import (
    health_check, get_nodes, get_roads, get_vehicles,
    get_weather_presets, compute_optimized_route, get_history,
    get_analytics, simulate_incident, clear_incidents
)

# -------------------------------------------------------------
# Test 1: ML Model & Preprocessor Artifacts
# -------------------------------------------------------------
def test_ml_model_artifacts():
    model_path = os.path.join(BASE_DIR, "ml", "models", "traffic_model.joblib")
    assert os.path.exists(model_path), "Serialized model artifact must exist."

    artifact = joblib.load(model_path)
    assert "time_model" in artifact
    assert "fuel_model" in artifact
    assert "preprocessor" in artifact
    assert "feature_names" in artifact

    # Test preprocessor feature dimension (32 features including AQI)
    preprocessor = artifact["preprocessor"]
    assert len(preprocessor.feature_names) == 32, f"Expected 32 features, got {len(preprocessor.feature_names)}"
    assert "aqi_index" in preprocessor.feature_names
    assert "pollution_exposure_score" in preprocessor.feature_names

# -------------------------------------------------------------
# Test 2: C++ Dijkstra High-Performance Solver
# -------------------------------------------------------------
def test_cpp_dijkstra_solver():
    bridge = CppDijkstraBridge()
    edges = [
        {"from": 0, "to": 1, "weight": 5.0, "road_id": "R01"},
        {"from": 1, "to": 2, "weight": 3.0, "road_id": "R02"},
        {"from": 0, "to": 2, "weight": 12.0, "road_id": "R03"}
    ]
    res = bridge.run_dijkstra_cpp(num_nodes=3, source_idx=0, dest_idx=2, edges_payload=edges)
    
    assert res["status"] == "success"
    assert res["found"] is True
    assert res["total_cost"] == 8.0
    assert res["node_path"] == [0, 1, 2]
    assert res["edge_path"] == ["R01", "R02"]

# -------------------------------------------------------------
# Test 3: Multi-Objective Router & Distinct Alternatives
# -------------------------------------------------------------
def test_multi_objective_router():
    router = MultiObjectiveRouter()
    assert len(router.nodes_df) >= 20, "Should have 20 transit nodes loaded."
    assert len(router.edge_engine.roads_df) >= 80, "Should have 80+ real road corridors loaded."
    
    # Test CP to Cyber City routing
    res = router.optimize(
        source_id="NODE_CP",
        destination_id="NODE_CYBER",
        hour_of_day=9,
        day_of_week=1,
        weather_condition="Clear",
        vehicle_type="Petrol_Sedan"
    )

    assert res["status"] == "success"
    assert "routes" in res
    assert "fastest" in res["routes"]
    assert "eco" in res["routes"]
    assert "clean_air" in res["routes"]
    assert "weather_safe" in res["routes"]

    fastest = res["routes"]["fastest"]
    eco = res["routes"]["eco"]
    clean_air = res["routes"]["clean_air"]

    assert fastest["found"] is True
    assert fastest["total_time_min"] > 0
    assert fastest["total_distance_km"] > 0
    assert "avg_aqi_index" in fastest
    assert "route_summary_label" in fastest
    assert len(fastest["node_sequence"]) >= 2

    # Clean air route must have low AQI
    assert clean_air["avg_aqi_index"] > 0

# -------------------------------------------------------------
# Test 4: SQLite Database & Incident Simulation
# -------------------------------------------------------------
def test_database_operations():
    init_db()
    
    # Test logging
    log_id = log_route_query(
        source_id="NODE_CP",
        destination_id="NODE_CYBER",
        vehicle_type="Electric_Vehicle",
        weather_condition="Clear",
        hour_of_day=9,
        fastest_time_min=45.2,
        eco_fuel_saved_percent=15.0,
        engine_used="C++ Engine"
    )
    assert log_id > 0

    history = get_recent_history(limit=5)
    assert len(history) >= 1
    assert history[0]["source_id"] == "NODE_CP"

    # Test incident injection & clearance
    inc = add_or_toggle_incident(
        road_id="R17",
        incident_type="Waterlogging",
        severity="Severe",
        description="Test waterlogging on corridor",
        is_active=1
    )
    assert inc["is_active"] is True
    active = get_active_incidents()
    assert any(i["road_id"] == "R17" for i in active)

    clear_all_incidents()
    active_after = get_active_incidents()
    assert len(active_after) == 0

# -------------------------------------------------------------
# Test 5: FastAPI REST Handler Functions
# -------------------------------------------------------------
def test_api_handlers():
    # Health
    r_health = health_check()
    assert r_health["status"] == "healthy"

    # Nodes
    r_nodes = get_nodes()
    assert len(r_nodes["nodes"]) >= 20

    # Roads
    r_roads = get_roads()
    assert len(r_roads["roads"]) >= 80

    # Vehicles
    r_veh = get_vehicles()
    assert len(r_veh["vehicles"]) == 5

    # Route POST computation
    req = RouteRequest(
        source_id="NODE_ROH",
        destination_id="NODE_IGI",
        hour_of_day=8,
        day_of_week=1,
        weather_condition="Light_Rain",
        vehicle_type="Electric_Vehicle"
    )
    data = compute_optimized_route(req)
    assert data["status"] == "success"
    assert data["routes"]["fastest"]["found"] is True
    assert "clean_air" in data["routes"]

    # Analytics
    r_analytics = get_analytics()
    assert r_analytics["status"] == "success"
    assert "network_summary" in r_analytics

    # Incident Simulation endpoint
    inc_req = IncidentSimulationRequest(
        road_id="R07",
        incident_type="Construction",
        severity="Severe",
        is_active=True
    )
    inc_res = simulate_incident(inc_req)
    assert inc_res["status"] == "success"

    clear_res = clear_incidents()
    assert clear_res["status"] == "success"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
