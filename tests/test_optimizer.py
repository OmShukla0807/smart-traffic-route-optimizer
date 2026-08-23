"""
Automated Test Suite for Smart Traffic Route Optimizer.
Tests ML Model, C++ Engine Bridge, Route Optimization, and Database logging.
"""

import os
import sys
import pytest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.core.feature_mapper import EdgeWeightEngine
from backend.app.core.cpp_bridge import CppDijkstraBridge
from backend.app.core.router import MultiObjectiveRouter
from database.db import init_db, log_route_query, get_recent_history

@pytest.fixture(scope="module")
def setup_environment():
    init_db()

def test_edge_weight_engine(setup_environment):
    engine = EdgeWeightEngine()
    df = engine.compute_edge_weights(
        hour_of_day=9,
        day_of_week=1,
        weather_condition="Clear",
        vehicle_type="Petrol_Sedan"
    )
    assert len(df) > 0
    assert "predicted_time_min" in df.columns
    assert "predicted_fuel_units" in df.columns
    assert (df["predicted_time_min"] > 0).all()
    assert (df["predicted_fuel_units"] > 0).all()

def test_weather_hazard_penalty(setup_environment):
    engine = EdgeWeightEngine()
    df_storm = engine.compute_edge_weights(
        hour_of_day=18,
        day_of_week=2,
        weather_condition="Storm",
        vehicle_type="Diesel_SUV"
    )
    assert (df_storm["weather_hazard_penalty"] > 0).any()

def test_cpp_dijkstra_bridge(setup_environment):
    bridge = CppDijkstraBridge()
    # Simple triangle test graph: 0 -> 1 (weight 2), 1 -> 2 (weight 3), 0 -> 2 (weight 10)
    edges = [
        {"from": 0, "to": 1, "weight": 2.0, "road_id": "R1"},
        {"from": 1, "to": 2, "weight": 3.0, "road_id": "R2"},
        {"from": 0, "to": 2, "weight": 10.0, "road_id": "R3"}
    ]
    res = bridge.run_dijkstra_cpp(num_nodes=3, source_idx=0, dest_idx=2, edges_payload=edges)
    assert res["status"] == "success"
    assert res["found"] is True
    assert res["node_path"] == [0, 1, 2]
    assert res["edge_path"] == ["R1", "R2"]
    assert res["total_cost"] == 5.0

def test_multi_objective_route_optimization(setup_environment):
    router = MultiObjectiveRouter()
    res = router.optimize(
        source_id="NODE_CP",
        destination_id="NODE_CYBER",
        hour_of_day=9,
        day_of_week=1,
        weather_condition="Clear",
        vehicle_type="Petrol_Sedan"
    )
    assert res["status"] == "success"
    assert "fastest" in res["routes"]
    assert "eco" in res["routes"]
    assert "weather_safe" in res["routes"]
    
    fastest = res["routes"]["fastest"]
    assert fastest["found"] is True
    assert fastest["total_distance_km"] > 0
    assert fastest["total_time_min"] > 0
    assert fastest["total_fuel_units"] > 0
    assert len(fastest["steps"]) > 0
    assert len(fastest["path_coordinates"]) > 0

def test_storm_weather_rerouting(setup_environment):
    """Verify that severe storm conditions change the routing decision and apply safety warnings."""
    router = MultiObjectiveRouter()
    res_storm = router.optimize(
        source_id="NODE_KG",
        destination_id="NODE_NOIDA_18",
        hour_of_day=18,
        day_of_week=3,
        weather_condition="Storm",
        vehicle_type="Petrol_Sedan"
    )
    assert res_storm["status"] == "success"
    safe_route = res_storm["routes"]["weather_safe"]
    assert safe_route["found"] is True

def test_database_logging(setup_environment):
    log_route_query(
        source_id="NODE_CP",
        destination_id="NODE_IGI",
        vehicle_type="Electric_Vehicle",
        weather_condition="Clear",
        hour_of_day=14,
        fastest_time_min=18.5,
        eco_fuel_saved_percent=12.4,
        engine_used="C++ Engine"
    )
    history = get_recent_history(limit=5)
    assert len(history) > 0
    assert history[0]["source_id"] == "NODE_CP"
    assert history[0]["destination_id"] == "NODE_IGI"
