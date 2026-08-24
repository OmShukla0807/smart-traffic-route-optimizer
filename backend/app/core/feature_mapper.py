"""
Feature Mapper & Dynamic Edge Weight Engine.
Bridges static road network topology with contextual variables (weather, hour, day, vehicle powertrain, AQI pollution)
and active incident blockades to generate dynamic multi-objective weights for C++ Dijkstra routing.
"""

import os
import sys
import joblib
import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from ml.preprocess import TrafficDataPreprocessor, engineer_features
from database.db import get_active_incidents

WEATHER_DEFAULTS = {
    "Clear": {"temp": 28.0, "vis": 8.0, "precip": 0.0, "wind": 10.0},
    "Light_Rain": {"temp": 24.0, "vis": 4.5, "precip": 4.0, "wind": 20.0},
    "Heavy_Rain": {"temp": 22.0, "vis": 1.5, "precip": 25.0, "wind": 35.0},
    "Dense_Fog": {"temp": 8.0, "vis": 0.2, "precip": 0.0, "wind": 5.0},
    "Extreme_Heat": {"temp": 45.0, "vis": 6.0, "precip": 0.0, "wind": 15.0},
    "Storm": {"temp": 20.0, "vis": 0.8, "precip": 40.0, "wind": 60.0}
}

def get_pollution_level(aqi: float) -> str:
    if aqi <= 100:
        return "Good (Clean Air)"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor (Unhealthy)"
    elif aqi <= 400:
        return "Very Poor (Severe)"
    else:
        return "Hazardous (Smog Hotspot)"

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
        
        # Delhi Peak Traffic Hours
        if is_weekday:
            if 8 <= hour <= 11 or 17 <= hour <= 21:
                base_density = 8.2 # Peak rush
            elif 12 <= hour <= 16 or 22 <= hour <= 23:
                base_density = 5.2 # Normal daytime
            else:
                base_density = 2.0 # Late night
        else:
            if 13 <= hour <= 21:
                base_density = 6.8 # Weekend rush
            else:
                base_density = 2.8

        # Weather slowdown adjustment
        if weather in ["Heavy_Rain", "Storm"]:
            base_density = min(10.0, base_density + 2.2)
        elif weather == "Dense_Fog":
            base_density = min(10.0, base_density + 1.8)
            
        if road_type in ["Ring_Road", "Arterial"]:
            base_density = min(10.0, base_density + 0.8)
        elif road_type == "Expressway":
            base_density = max(1.0, base_density - 0.5)
            
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
        Build feature vectors for all roads and run ML inference for segment travel times, fuel, and AQI pollution.
        Integrates dynamic incident blockades from SQLite database.
        """
        weather_info = WEATHER_DEFAULTS.get(weather_condition, WEATHER_DEFAULTS["Clear"])
        
        # Check active incident blockades
        active_incidents = {}
        try:
            inc_list = get_active_incidents()
            for inc in inc_list:
                active_incidents[inc["road_id"]] = inc
        except Exception as e:
            print(f"[Warning] Could not fetch active incidents: {e}")
        
        records = []
        dynamic_aqi_list = []

        for _, road in self.roads_df.iterrows():
            density = self._estimate_traffic_density(hour_of_day, day_of_week, road["road_type"], weather_condition)
            if custom_traffic_factor is not None:
                density = float(np.clip(density * custom_traffic_factor, 1.0, 10.0))
                
            base_aqi = float(road.get("aqi_index", 160.0))
            # Weather & rush-hour impacts on AQI
            if weather_condition in ["Heavy_Rain", "Light_Rain", "Storm"]:
                cur_aqi = max(45.0, base_aqi * 0.55)
            elif weather_condition == "Dense_Fog":
                cur_aqi = min(500.0, base_aqi * 1.35)
            elif hour_of_day in [8, 9, 10, 18, 19, 20]:
                cur_aqi = min(500.0, base_aqi * 1.15)
            else:
                cur_aqi = base_aqi

            dynamic_aqi_list.append(round(cur_aqi, 1))

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
                "road_gradient_percent": float(road.get("road_gradient_percent", 0.0)),
                "flood_risk_score": float(road.get("flood_risk_score", 0.0)),
                "fog_risk_score": float(road.get("fog_risk_score", 0.0)),
                "aqi_index": cur_aqi,
                "pollution_exposure_score": round(min(1.0, cur_aqi / 450.0), 2),
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
        results_df["aqi_index"] = dynamic_aqi_list
        results_df["pollution_exposure_score"] = [round(min(1.0, a / 450.0), 2) for a in dynamic_aqi_list]
        results_df["pollution_level"] = [get_pollution_level(a) for a in dynamic_aqi_list]
        
        # Dynamic weather & incident hazard penalties
        flood_risk = results_df["flood_risk_score"].values
        fog_risk = results_df["fog_risk_score"].values
        
        hazard_penalties = []
        for i, row in results_df.iterrows():
            pen = 0.0
            r_id = row["road_id"]

            if weather_condition in ["Heavy_Rain", "Storm"]:
                pen += flood_risk[i] * 35.0 + (12.0 if weather_condition == "Storm" else 6.0)
            elif weather_condition == "Dense_Fog":
                pen += fog_risk[i] * 28.0
            elif weather_condition == "Light_Rain":
                pen += flood_risk[i] * 6.0
                
            # Apply active incident modifications
            if r_id in active_incidents:
                inc = active_incidents[r_id]
                sev = inc.get("severity", "Severe")
                if sev == "Impassable":
                    pen += 1000.0
                    results_df.at[i, "predicted_time_min"] += 999.0
                elif sev == "Severe":
                    pen += 80.0
                    results_df.at[i, "predicted_time_min"] *= 3.0
                elif sev == "Moderate":
                    pen += 40.0
                    results_df.at[i, "predicted_time_min"] *= 1.8
                else: # Minor
                    pen += 15.0
                    results_df.at[i, "predicted_time_min"] *= 1.3

            hazard_penalties.append(np.round(pen, 2))
            
        results_df["weather_hazard_penalty"] = hazard_penalties
        return results_df
