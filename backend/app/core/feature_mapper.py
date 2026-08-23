"""
Feature Mapper & Edge Weight Engine.
Bridges static road network attributes with live contextual parameters
(weather, time of day, vehicle profile) and runs ML inference to generate
dynamic edge weights for the C++ Dijkstra Router.
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

# Ensure project root is accessible
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ml.preprocess import TrafficDataPreprocessor, engineer_features

# Weather presets
WEATHER_DEFAULTS = {
    "Clear": {"temp": 28.0, "vis": 8.0, "precip": 0.0, "wind": 10.0},
    "Light_Rain": {"temp": 24.0, "vis": 4.5, "precip": 4.0, "wind": 20.0},
    "Heavy_Rain": {"temp": 22.0, "vis": 1.5, "precip": 25.0, "wind": 35.0},
    "Dense_Fog": {"temp": 8.0, "vis": 0.2, "precip": 0.0, "wind": 5.0},
    "Extreme_Heat": {"temp": 45.0, "vis": 6.0, "precip": 0.0, "wind": 15.0},
    "Storm": {"temp": 20.0, "vis": 0.8, "precip": 40.0, "wind": 60.0}
}

class EdgeWeightEngine:
    def __init__(self, model_path: Optional[str] = None, roads_csv_path: Optional[str] = None):
        if model_path is None:
            model_path = os.path.join(BASE_DIR, "ml", "models", "traffic_model.joblib")
        if roads_csv_path is None:
            roads_csv_path = os.path.join(BASE_DIR, "data", "processed", "roads.csv")
            
        print(f"Loading ML Model Artifact from {model_path}...")
        artifact = joblib.load(model_path)
        self.time_model = artifact["time_model"]
        self.fuel_model = artifact["fuel_model"]
        self.preprocessor: TrafficDataPreprocessor = artifact["preprocessor"]
        
        print(f"Loading Road Network from {roads_csv_path}...")
        self.roads_df = pd.read_csv(roads_csv_path)
        self.road_lookup = {row["road_id"]: row.to_dict() for _, row in self.roads_df.iterrows()}

    def _estimate_traffic_density(self, hour: int, day: int, road_type: str, weather: str) -> float:
        is_weekday = day < 5
        base_density = 3.0
        
        # Rush hours in Delhi (8-11 AM, 5-9 PM)
        if is_weekday:
            if 8 <= hour <= 10 or 17 <= hour <= 20:
                base_density = 8.5
            elif 11 <= hour <= 16 or 21 <= hour <= 22:
                base_density = 5.5
            else:
                base_density = 2.0
        else:
            if 14 <= hour <= 21:
                base_density = 6.8
            else:
                base_density = 2.5

        # Weather slowdown factor
        if weather in ["Heavy_Rain", "Storm"]:
            base_density = min(10.0, base_density + 2.0)
        elif weather == "Dense_Fog":
            base_density = min(10.0, base_density + 1.5)
            
        if road_type in ["Ring_Road", "Arterial"]:
            base_density = min(10.0, base_density + 0.8)
            
        return float(np.clip(base_density, 1.0, 10.0))

    def compute_edge_weights(
        self,
        hour_of_day: int = 9,
        day_of_week: int = 1,
        weather_condition: str = "Clear",
        vehicle_type: str = "Petrol_Sedan",
        custom_traffic_factor: Optional[float] = None
    ) -> pd.DataFrame:
        """
        Build feature vectors for all roads and predict segment travel times & fuel.
        """
        weather_info = WEATHER_DEFAULTS.get(weather_condition, WEATHER_DEFAULTS["Clear"])
        
        records = []
        for _, road in self.roads_df.iterrows():
            density = self._estimate_traffic_density(hour_of_day, day_of_week, road["road_type"], weather_condition)
            if custom_traffic_factor is not None:
                density = float(np.clip(density * custom_traffic_factor, 1.0, 10.0))
                
            record = {
                "segment_id": road["road_id"],
                "road_type": road["road_type"],
                "distance_km": float(road["distance_km"]),
                "base_speed_limit_kmh": int(road["base_speed_limit_kmh"]),
                "hour_of_day": int(hour_of_day),
                "day_of_week": int(day_of_week),
                "traffic_density_index": density,
                "weather_condition": weather_condition,
                "temperature_c": weather_info["temp"],
                "visibility_km": weather_info["vis"],
                "precipitation_mm": weather_info["precip"],
                "wind_speed_kmh": weather_info["wind"],
                "road_gradient_percent": float(road["road_gradient_percent"]),
                "vehicle_type": vehicle_type
            }
            records.append(record)

        feature_df = pd.DataFrame(records)
        
        # Preprocess features
        X_matrix = self.preprocessor.transform(feature_df)
        
        # Predict travel time (min) and fuel units (L or kWh)
        pred_times = self.time_model.predict(X_matrix)
        pred_fuels = self.fuel_model.predict(X_matrix)
        
        results_df = self.roads_df.copy()
        results_df["predicted_time_min"] = np.maximum(0.5, np.round(pred_times, 2))
        results_df["predicted_fuel_units"] = np.maximum(0.01, np.round(pred_fuels, 3))
        results_df["traffic_density_index"] = feature_df["traffic_density_index"].values
        
        # Calculate dynamic weather hazard score for each road
        flood_risk = results_df["flood_risk_score"].values
        fog_risk = results_df["fog_risk_score"].values
        
        hazard_penalties = []
        for i, row in results_df.iterrows():
            pen = 0.0
            if weather_condition in ["Heavy_Rain", "Storm"]:
                # High flood-prone roads become dangerous/impassable
                pen += flood_risk[i] * 35.0 + (10.0 if weather_condition == "Storm" else 5.0)
            elif weather_condition == "Dense_Fog":
                # Fog-prone expressways / highways have low visibility danger
                pen += fog_risk[i] * 25.0
            elif weather_condition == "Light_Rain":
                pen += flood_risk[i] * 5.0
            hazard_penalties.append(np.round(pen, 2))
            
        results_df["weather_hazard_penalty"] = hazard_penalties
        return results_df
