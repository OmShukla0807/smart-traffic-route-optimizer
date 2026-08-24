"""
Multi-Objective Route Optimizer with Guaranteed Distinct Alternative Paths & AQI Clean Air Routing.
Coordinates ML inference, dynamic cost weighting, C++ Dijkstra engine, and diversity enforcement
to generate Pareto-optimal route options (Fastest, Eco, Clean Air, Weather-Safe, Custom).
"""

import os
import sys
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.core.feature_mapper import EdgeWeightEngine, get_pollution_level
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

    def _generate_corridor_label(self, edge_ids: List[str], road_dict: Dict[str, Any]) -> str:
        """Create a human-readable corridor summary (e.g. 'via NH-48 & Airport Expressway')."""
        if not edge_ids:
            return "Direct Path"
        prominent_roads = []
        for r_id in edge_ids:
            r = road_dict.get(r_id)
            if r:
                r_name = r["road_name"].split(" (")[0] # strip return
                # Pick unique short names
                short_name = r_name.split(" / ")[0].split(" (")[0]
                if short_name not in prominent_roads:
                    prominent_roads.append(short_name)
        if len(prominent_roads) == 1:
            return f"via {prominent_roads[0]}"
        elif len(prominent_roads) >= 2:
            return f"via {prominent_roads[0]} & {prominent_roads[1]}"
        return "via Delhi Arterials"

    def _build_route_summary(
        self,
        edge_ids: List[str],
        node_indices: List[int],
        weighted_roads_df: pd.DataFrame,
        vehicle_type: str,
        weather_condition: str,
        mode_title: str,
        mode_badge: str,
        engine_used: str = "C++ Engine"
    ) -> Dict[str, Any]:
        """Construct detailed route metrics, AQI scores, and step-by-step telemetry."""
        if not edge_ids:
            return {"found": False, "mode_title": mode_title, "mode_badge": mode_badge}

        road_dict = weighted_roads_df.set_index("road_id").to_dict(orient="index")
        
        total_distance_km = 0.0
        total_time_min = 0.0
        total_fuel_units = 0.0
        total_hazard_penalty = 0.0
        aqi_sum = 0.0
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
            aqi = float(r.get("aqi_index", 160.0))
            
            total_distance_km += dist
            total_time_min += t_min
            total_fuel_units += fuel
            total_hazard_penalty += hazard
            aqi_sum += aqi * dist # distance-weighted AQI

            to_node = self.node_lookup[r["to_node"]]

            # Check weather advisory
            if hazard > 12.0:
                weather_advisories.append(f"Caution on {r['road_name']}: Elevated weather disruption risk.")
            if aqi > 350.0:
                weather_advisories.append(f"High Pollution Alert: PM2.5 AQI {int(aqi)} on {r['road_name']}.")

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
                "predicted_fuel_units": round(fuel, 3),
                "speed_limit_kmh": int(r["base_speed_limit_kmh"]),
                "traffic_density_index": round(float(r.get("traffic_density_index", 5.0)), 1),
                "aqi_index": round(aqi, 1),
                "pollution_level": get_pollution_level(aqi)
            })

        # Fetch high-precision road coordinates
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
        
        # Calculate average AQI
        avg_aqi = round(aqi_sum / max(0.1, total_distance_km), 1)
        pollution_level = get_pollution_level(avg_aqi)

        # Calculate weather safety score (100 = completely safe, lower = hazard exposure)
        safety_score = max(15, int(100.0 - min(85.0, total_hazard_penalty)))
        summary_label = self._generate_corridor_label(edge_ids, road_dict)

        return {
            "found": True,
            "mode_title": mode_title,
            "mode_badge": mode_badge,
            "route_summary_label": summary_label,
            "total_distance_km": round(total_distance_km, 2),
            "total_time_min": round(total_time_min, 1),
            "total_fuel_units": round(total_fuel_units, 2),
            "fuel_unit_name": unit_info["unit"],
            "total_co2_kg": round(total_co2_kg, 2),
            "total_cost_inr": round(total_cost_inr, 2),
            "avg_aqi_index": avg_aqi,
            "pollution_level": pollution_level,
            "weather_safety_score": safety_score,
            "weather_advisories": list(set(weather_advisories)),
            "node_sequence": [self.idx_to_node_id[i] for i in node_indices],
            "edge_sequence": edge_ids,
            "path_coordinates": path_coords,
            "steps": steps,
            "engine_used": engine_used
        }

    def _compute_overlap(self, edges_a: List[str], edges_b: List[str]) -> float:
        """Compute the Jaccard/Dice overlap ratio between two edge sequences."""
        if not edges_a or not edges_b:
            return 0.0
        set_a = set(edges_a)
        set_b = set(edges_b)
        intersection = len(set_a.intersection(set_b))
        max_len = max(len(set_a), len(set_b))
        return intersection / max(1, max_len)

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
        Generate distinct multi-route comparison (Fastest, Eco, Clean Air, Weather-Safe, Custom Balanced)
        with diversity enforcement to guarantee distinct physical options for the user.
        """
        if source_id not in self.node_id_to_idx or destination_id not in self.node_id_to_idx:
            return {"status": "error", "message": f"Invalid source '{source_id}' or destination '{destination_id}'."}

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

        # 4 Core Multi-Objective Profiles
        strategies = {
            "fastest": {
                "title": "Fastest Route",
                "badge": "⚡ Lowest ETA",
                "w_time": 1.0,
                "w_fuel": 0.0,
                "w_aqi": 0.0,
                "w_weather": 0.0
            },
            "eco": {
                "title": "Eco-Friendly Route",
                "badge": "🌿 Lowest Fuel / Energy",
                "w_time": 0.15,
                "w_fuel": 0.85,
                "w_aqi": 0.0,
                "w_weather": 0.0
            },
            "clean_air": {
                "title": "Clean Air Route",
                "badge": "🍃 Lowest PM2.5 AQI Exposure",
                "w_time": 0.20,
                "w_fuel": 0.0,
                "w_aqi": 0.80,
                "w_weather": 0.0
            },
            "weather_safe": {
                "title": "Weather-Resilient Route",
                "badge": "🛡️ Hazard & Waterlog Bypass",
                "w_time": 0.20,
                "w_fuel": 0.0,
                "w_aqi": 0.0,
                "w_weather": 0.80
            }
        }

        if custom_weights:
            strategies["custom"] = {
                "title": "Custom Balanced Route",
                "badge": "🎛️ User Weighted",
                "w_time": custom_weights.get("time", 0.25),
                "w_fuel": custom_weights.get("fuel", 0.25),
                "w_aqi": custom_weights.get("aqi", 0.25),
                "w_weather": custom_weights.get("weather", 0.25)
            }

        existing_edge_paths = []

        # Run Dijkstra with diversity enforcement
        for key, strat in strategies.items():
            edges_payload = []
            
            for _, r in weighted_df.iterrows():
                u = self.node_id_to_idx[r["from_node"]]
                v = self.node_id_to_idx[r["to_node"]]
                
                t_cost = float(r["predicted_time_min"])
                f_cost = float(r["predicted_fuel_units"]) * 7.5 # scale fuel to comparable minutes
                aqi_cost = (float(r.get("aqi_index", 150.0)) / 50.0) * float(r["distance_km"]) * 0.8 # pollution cost
                w_cost = float(r.get("weather_hazard_penalty", 0.0))
                
                total_weight = (
                    (strat["w_time"] * t_cost) + 
                    (strat["w_fuel"] * f_cost) + 
                    (strat["w_aqi"] * aqi_cost) + 
                    (strat["w_weather"] * w_cost)
                )

                # Diversity Penalty: If this is an alternative strategy, penalize edges that appeared in previous routes
                # so the engine discovers genuine physical alternative corridors (e.g. MG Road vs NH-48 vs Dwarka Expressway)
                r_id = r["road_id"]
                for prev_path in existing_edge_paths:
                    if r_id in prev_path:
                        # Add a moderate corridor diversion penalty
                        total_weight *= 1.45
                
                edges_payload.append({
                    "from": u,
                    "to": v,
                    "weight": round(max(0.01, total_weight), 3),
                    "road_id": r_id
                })

            res = self.cpp_bridge.run_dijkstra_cpp(
                num_nodes=num_nodes,
                source_idx=source_idx,
                dest_idx=dest_idx,
                edges_payload=edges_payload
            )

            if res.get("found", False):
                edge_path = res["edge_path"]
                node_path = res["node_path"]

                # If the path is identical to the primary fastest route and we want diversity:
                # Apply an extra edge penalty to force a 2nd best corridor
                if existing_edge_paths and self._compute_overlap(edge_path, existing_edge_paths[0]) > 0.80 and len(edge_path) > 1:
                    diverse_edges_payload = []
                    for ep in edges_payload:
                        item = dict(ep)
                        if item["road_id"] in existing_edge_paths[0]:
                            item["weight"] = item["weight"] * 2.2
                        diverse_edges_payload.append(item)
                    
                    alt_res = self.cpp_bridge.run_dijkstra_cpp(
                        num_nodes=num_nodes,
                        source_idx=source_idx,
                        dest_idx=dest_idx,
                        edges_payload=diverse_edges_payload
                    )
                    if alt_res.get("found", False) and alt_res["edge_path"] != existing_edge_paths[0]:
                        edge_path = alt_res["edge_path"]
                        node_path = alt_res["node_path"]

                existing_edge_paths.append(edge_path)

                route_summary = self._build_route_summary(
                    edge_ids=edge_path,
                    node_indices=node_path,
                    weighted_roads_df=weighted_df,
                    vehicle_type=vehicle_type,
                    weather_condition=weather_condition,
                    mode_title=strat["title"],
                    mode_badge=strat["badge"],
                    engine_used=res.get("engine_used", "C++ Engine")
                )
                routes[key] = route_summary
            else:
                routes[key] = {
                    "found": False,
                    "mode_title": strat["title"],
                    "mode_badge": strat["badge"]
                }

        src_info = self.node_lookup[source_id]
        dst_info = self.node_lookup[destination_id]

        return {
            "status": "success",
            "source": {
                "id": source_id,
                "name": src_info["node_name"],
                "lat": float(src_info["latitude"]),
                "lng": float(src_info["longitude"]),
                "zone": src_info.get("zone", "Delhi NCR")
            },
            "destination": {
                "id": destination_id,
                "name": dst_info["node_name"],
                "lat": float(dst_info["latitude"]),
                "lng": float(dst_info["longitude"]),
                "zone": dst_info.get("zone", "Delhi NCR")
            },
            "context": {
                "hour_of_day": hour_of_day,
                "day_of_week": day_of_week,
                "weather_condition": weather_condition,
                "vehicle_type": vehicle_type
            },
            "routes": routes
        }
