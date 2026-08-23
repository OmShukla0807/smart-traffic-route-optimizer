"""
Multi-Objective Route Optimizer.
Coordinates ML inference, dynamic cost weighting, and C++ Dijkstra engine
to generate Pareto-optimal route options (Fastest, Eco, Weather-Safe, Balanced).
"""

import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.core.feature_mapper import EdgeWeightEngine
from backend.app.core.cpp_bridge import CppDijkstraBridge
from backend.app.core.geometry import RoadGeometryEngine

# Fuel cost presets (INR per unit) & CO2 emissions (kg per unit)
EMISSION_FACTORS = {
    "Petrol_Sedan": {"cost_per_unit": 96.72, "co2_per_unit": 2.31, "unit": "Liters"},
    "Diesel_SUV": {"cost_per_unit": 89.62, "co2_per_unit": 2.68, "unit": "Liters"},
    "Electric_Vehicle": {"cost_per_unit": 8.50, "co2_per_unit": 0.08, "unit": "kWh"},
    "Heavy_Truck": {"cost_per_unit": 89.62, "co2_per_unit": 2.68, "unit": "Liters"},
    "Two_Wheeler": {"cost_per_unit": 96.72, "co2_per_unit": 2.31, "unit": "Liters"}
}

class MultiObjectiveRouter:
    def __init__(self):
        self.edge_engine = EdgeWeightEngine()
        self.cpp_bridge = CppDijkstraBridge()
        self.geom_engine = RoadGeometryEngine()
        
        # Load nodes
        nodes_path = os.path.join(BASE_DIR, "data", "processed", "nodes.csv")
        self.nodes_df = pd.read_csv(nodes_path)
        
        # Create node ID to Index mappings
        self.node_id_to_idx = {row["node_id"]: idx for idx, row in self.nodes_df.iterrows()}
        self.idx_to_node_id = {idx: row["node_id"] for idx, row in self.nodes_df.iterrows()}
        self.node_lookup = {row["node_id"]: row.to_dict() for _, row in self.nodes_df.iterrows()}
        self.road_lookup = self.edge_engine.road_lookup

    def _build_route_summary(
        self,
        edge_ids: List[str],
        node_indices: List[int],
        weighted_roads_df: pd.DataFrame,
        vehicle_type: str,
        weather_condition: str,
        mode_title: str,
        mode_badge: str
    ) -> Dict[str, Any]:
        """Construct detailed route metrics and step-by-step telemetry."""
        if not edge_ids:
            return {"found": False, "mode_title": mode_title}

        road_dict = weighted_roads_df.set_index("road_id").to_dict(orient="index")
        
        total_distance_km = 0.0
        total_time_min = 0.0
        total_fuel_units = 0.0
        total_hazard_penalty = 0.0
        steps = []
        path_coords = []

        # Add start node coordinate
        start_node_id = self.idx_to_node_id[node_indices[0]]
        start_node = self.node_lookup[start_node_id]
        path_coords.append({
            "node_id": start_node_id,
            "name": start_node["node_name"],
            "lat": float(start_node["latitude"]),
            "lng": float(start_node["longitude"])
        })

        weather_advisories = []

        for r_id in edge_ids:
            r = road_dict.get(r_id)
            if not r:
                continue
            
            dist = float(r["distance_km"])
            t_min = float(r["predicted_time_min"])
            fuel = float(r["predicted_fuel_units"])
            hazard = float(r.get("weather_hazard_penalty", 0.0))
            
            total_distance_km += dist
            total_time_min += t_min
            total_fuel_units += fuel
            total_hazard_penalty += hazard

            to_node = self.node_lookup[r["to_node"]]

            # Check weather advisory
            if hazard > 15.0:
                weather_advisories.append(f"Caution on {r['road_name']}: High weather disruption risk.")

            steps.append({
                "road_id": r_id,
                "road_name": r["road_name"],
                "road_type": r["road_type"],
                "from_node": r["from_node"],
                "from_name": self.node_lookup[r["from_node"]]["node_name"],
                "to_node": r["to_node"],
                "to_name": to_node["node_name"],
                "distance_km": round(dist, 2),
                "predicted_time_min": round(t_min, 1),
                "predicted_fuel_units": round(fuel, 2),
                "speed_limit_kmh": int(r["base_speed_limit_kmh"]),
                "traffic_density_index": round(float(r.get("traffic_density_index", 5.0)), 1)
            })

        # Fetch high-precision curved road coordinates following actual highways and curves
        exact_curve_coords = self.geom_engine.get_full_route_geometry(edge_ids, road_dict)
        if exact_curve_coords:
            path_coords = exact_curve_coords
        else:
            # Fallback to straight node connections
            start_node_id = self.idx_to_node_id[node_indices[0]]
            start_node = self.node_lookup[start_node_id]
            path_coords = [{"lat": float(start_node["latitude"]), "lng": float(start_node["longitude"])}]
            for r_id in edge_ids:
                r = road_dict.get(r_id)
                if r:
                    to_node = self.node_lookup[r["to_node"]]
                    path_coords.append({"lat": float(to_node["latitude"]), "lng": float(to_node["longitude"])})

        # Calculate emissions & cost
        unit_info = EMISSION_FACTORS.get(vehicle_type, EMISSION_FACTORS["Petrol_Sedan"])
        total_co2_kg = total_fuel_units * unit_info["co2_per_unit"]
        total_cost_inr = total_fuel_units * unit_info["cost_per_unit"]
        
        # Calculate weather safety score (100 = completely safe, lower = hazard exposure)
        safety_score = max(20, int(100.0 - min(80.0, total_hazard_penalty)))

        return {
            "found": True,
            "mode_title": mode_title,
            "mode_badge": mode_badge,
            "total_distance_km": round(total_distance_km, 2),
            "total_time_min": round(total_time_min, 1),
            "total_fuel_units": round(total_fuel_units, 2),
            "fuel_unit_name": unit_info["unit"],
            "total_co2_kg": round(total_co2_kg, 2),
            "total_cost_inr": round(total_cost_inr, 2),
            "weather_safety_score": safety_score,
            "weather_advisories": list(set(weather_advisories)),
            "node_sequence": [self.idx_to_node_id[i] for i in node_indices],
            "edge_sequence": edge_ids,
            "path_coordinates": path_coords,
            "steps": steps
        }

    def optimize(
        self,
        source_id: str,
        destination_id: str,
        hour_of_day: int = 9,
        day_of_week: int = 1,
        weather_condition: str = "Clear",
        vehicle_type: str = "Petrol_Sedan",
        custom_weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Generate multi-route comparison (Fastest, Eco, Weather-Safe, Custom Balanced).
        """
        if source_id not in self.node_id_to_idx or destination_id not in self.node_id_to_idx:
            return {"status": "error", "message": "Invalid source or destination node ID."}

        source_idx = self.node_id_to_idx[source_id]
        dest_idx = self.node_id_to_idx[destination_id]
        num_nodes = len(self.nodes_df)

        # 1. Compute dynamic ML edge weights
        weighted_df = self.edge_engine.compute_edge_weights(
            hour_of_day=hour_of_day,
            day_of_week=day_of_week,
            weather_condition=weather_condition,
            vehicle_type=vehicle_type
        )

        routes = {}

        # Objective Configurations
        strategies = {
            "fastest": {
                "title": "Fastest Route",
                "badge": "⚡ Lowest ETA",
                "w_time": 1.0,
                "w_fuel": 0.0,
                "w_weather": 0.0
            },
            "eco": {
                "title": "Eco-Friendly Route",
                "badge": "🌿 Lowest Fuel / CO₂",
                "w_time": 0.2,
                "w_fuel": 0.8,
                "w_weather": 0.0
            },
            "weather_safe": {
                "title": "Weather-Resilient Route",
                "badge": "🛡️ Maximum Safety & Bypass",
                "w_time": 0.2,
                "w_fuel": 0.1,
                "w_weather": 0.7
            }
        }

        # If custom weights are specified, add custom strategy
        if custom_weights:
            strategies["custom"] = {
                "title": "Custom Balanced Route",
                "badge": "🎛️ User Optimized",
                "w_time": custom_weights.get("time", 0.33),
                "w_fuel": custom_weights.get("fuel", 0.33),
                "w_weather": custom_weights.get("weather", 0.34)
            }

        # Run Dijkstra for each strategy
        for key, strat in strategies.items():
            edges_payload = []
            for _, r in weighted_df.iterrows():
                u = self.node_id_to_idx[r["from_node"]]
                v = self.node_id_to_idx[r["to_node"]]
                
                # Composite cost calculation
                # Normalizing fuel by ~5x so 1 liter has comparable scale to minutes
                t_cost = float(r["predicted_time_min"])
                f_cost = float(r["predicted_fuel_units"]) * 5.0
                w_cost = float(r.get("weather_hazard_penalty", 0.0))
                
                total_weight = (strat["w_time"] * t_cost) + (strat["w_fuel"] * f_cost) + (strat["w_weather"] * w_cost)
                
                edges_payload.append({
                    "from": u,
                    "to": v,
                    "weight": round(max(0.1, total_weight), 3),
                    "road_id": r["road_id"]
                })

            res = self.cpp_bridge.run_dijkstra_cpp(
                num_nodes=num_nodes,
                source_idx=source_idx,
                dest_idx=dest_idx,
                edges_payload=edges_payload
            )

            if res.get("found"):
                summary = self._build_route_summary(
                    edge_ids=res["edge_path"],
                    node_indices=res["node_path"],
                    weighted_roads_df=weighted_df,
                    vehicle_type=vehicle_type,
                    weather_condition=weather_condition,
                    mode_title=strat["title"],
                    mode_badge=strat["badge"]
                )
                summary["engine_used"] = res.get("engine_used", "C++ Engine")
                routes[key] = summary

        return {
            "status": "success",
            "source": self.node_lookup[source_id],
            "destination": self.node_lookup[destination_id],
            "context": {
                "hour_of_day": hour_of_day,
                "day_of_week": day_of_week,
                "weather_condition": weather_condition,
                "vehicle_type": vehicle_type
            },
            "routes": routes
        }
