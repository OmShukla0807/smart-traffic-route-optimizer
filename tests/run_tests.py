"""
Standalone Test Runner using standard library unittest.
"""

import os
import sys
import unittest

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.core.feature_mapper import EdgeWeightEngine
from backend.app.core.cpp_bridge import CppDijkstraBridge
from backend.app.core.router import MultiObjectiveRouter
from database.db import init_db, log_route_query, get_recent_history

class TestTrafficRouteOptimizer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        init_db()

    def test_01_edge_weight_engine(self):
        engine = EdgeWeightEngine()
        df = engine.compute_edge_weights(
            hour_of_day=9,
            day_of_week=1,
            weather_condition="Clear",
            vehicle_type="Petrol_Sedan"
        )
        self.assertGreater(len(df), 0)
        self.assertIn("predicted_time_min", df.columns)
        self.assertIn("predicted_fuel_units", df.columns)
        self.assertTrue((df["predicted_time_min"] > 0).all())
        self.assertTrue((df["predicted_fuel_units"] > 0).all())
        print(" [PASS] test_01_edge_weight_engine")

    def test_02_weather_hazard_penalty(self):
        engine = EdgeWeightEngine()
        df_storm = engine.compute_edge_weights(
            hour_of_day=18,
            day_of_week=2,
            weather_condition="Storm",
            vehicle_type="Diesel_SUV"
        )
        self.assertTrue((df_storm["weather_hazard_penalty"] > 0).any())
        print(" [PASS] test_02_weather_hazard_penalty")

    def test_03_cpp_dijkstra_bridge(self):
        bridge = CppDijkstraBridge()
        edges = [
            {"from": 0, "to": 1, "weight": 2.0, "road_id": "R1"},
            {"from": 1, "to": 2, "weight": 3.0, "road_id": "R2"},
            {"from": 0, "to": 2, "weight": 10.0, "road_id": "R3"}
        ]
        res = bridge.run_dijkstra_cpp(num_nodes=3, source_idx=0, dest_idx=2, edges_payload=edges)
        self.assertEqual(res["status"], "success")
        self.assertTrue(res["found"])
        self.assertEqual(res["node_path"], [0, 1, 2])
        self.assertEqual(res["edge_path"], ["R1", "R2"])
        self.assertEqual(res["total_cost"], 5.0)
        print(" [PASS] test_03_cpp_dijkstra_bridge")

    def test_04_multi_objective_route_optimization(self):
        router = MultiObjectiveRouter()
        res = router.optimize(
            source_id="NODE_CP",
            destination_id="NODE_CYBER",
            hour_of_day=9,
            day_of_week=1,
            weather_condition="Clear",
            vehicle_type="Petrol_Sedan"
        )
        self.assertEqual(res["status"], "success")
        self.assertIn("fastest", res["routes"])
        self.assertIn("eco", res["routes"])
        self.assertIn("weather_safe", res["routes"])
        
        fastest = res["routes"]["fastest"]
        self.assertTrue(fastest["found"])
        self.assertGreater(fastest["total_distance_km"], 0)
        self.assertGreater(fastest["total_time_min"], 0)
        self.assertGreater(fastest["total_fuel_units"], 0)
        self.assertGreater(len(fastest["steps"]), 0)
        self.assertGreater(len(fastest["path_coordinates"]), 0)
        print(f" [PASS] test_04_multi_objective_route_optimization: Fastest Time = {fastest['total_time_min']} min, Fuel = {fastest['total_fuel_units']} {fastest['fuel_unit_name']}")

    def test_05_database_logging(self):
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
        self.assertGreater(len(history), 0)
        self.assertEqual(history[0]["source_id"], "NODE_CP")
        self.assertEqual(history[0]["destination_id"], "NODE_IGI")
        print(" [PASS] test_05_database_logging")

if __name__ == "__main__":
    unittest.main()
