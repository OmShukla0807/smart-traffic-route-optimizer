from pathlib import Path
import sys

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import numpy as np
import pandas as pd

from ml.preprocess import run_preprocessing
from ml.train import train_and_evaluate
RAW_DIR = BASE_DIR / 'data' / 'raw'
PROCESSED_DIR = BASE_DIR / 'data' / 'processed'
MODELS_DIR = BASE_DIR / 'ml' / 'models'

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

nodes = [
    {"node_id": "NODE_CP", "node_name": "Connaught Place", "latitude": 28.6315, "longitude": 77.2167, "zone": "Central"},
    {"node_id": "NODE_IGI", "node_name": "IGI Airport", "latitude": 28.5562, "longitude": 77.1000, "zone": "South"},
    {"node_id": "NODE_CYBER", "node_name": "Cyber City", "latitude": 28.4955, "longitude": 77.0888, "zone": "Gurugram"},
    {"node_id": "NODE_KG", "node_name": "Kashmere Gate", "latitude": 28.6661, "longitude": 77.2290, "zone": "North"},
    {"node_id": "NODE_NOIDA_18", "node_name": "Noida Sector 18", "latitude": 28.5688, "longitude": 77.3342, "zone": "Noida"},
    {"node_id": "NODE_SAKET", "node_name": "Saket", "latitude": 28.5214, "longitude": 77.2013, "zone": "South"},
    {"node_id": "NODE_RK", "node_name": "Rajiv Chowk", "latitude": 28.6338, "longitude": 77.2197, "zone": "Central"},
    {"node_id": "NODE_MA", "node_name": "Mayur Vihar", "latitude": 28.5976, "longitude": 77.2935, "zone": "East"},
]

roads = [
    {"road_id": "R1", "from_node": "NODE_CP", "to_node": "NODE_RK", "road_name": "Parliament Street Link", "road_type": "Arterial", "distance_km": 2.4, "base_speed_limit_kmh": 45, "road_gradient_percent": 1.4, "lanes": 4, "flood_risk_score": 0.18, "fog_risk_score": 0.22},
    {"road_id": "R2", "from_node": "NODE_RK", "to_node": "NODE_KG", "road_name": "Ring Road East", "road_type": "Ring_Road", "distance_km": 7.5, "base_speed_limit_kmh": 55, "road_gradient_percent": 0.8, "lanes": 6, "flood_risk_score": 0.27, "fog_risk_score": 0.26},
    {"road_id": "R3", "from_node": "NODE_CP", "to_node": "NODE_IGI", "road_name": "Airport Express Link", "road_type": "Expressway", "distance_km": 12.1, "base_speed_limit_kmh": 80, "road_gradient_percent": 0.5, "lanes": 6, "flood_risk_score": 0.14, "fog_risk_score": 0.12},
    {"road_id": "R4", "from_node": "NODE_IGI", "to_node": "NODE_CYBER", "road_name": "NH-48 Connector", "road_type": "Expressway", "distance_km": 16.8, "base_speed_limit_kmh": 90, "road_gradient_percent": 0.7, "lanes": 8, "flood_risk_score": 0.16, "fog_risk_score": 0.15},
    {"road_id": "R5", "from_node": "NODE_CP", "to_node": "NODE_SAKET", "road_name": "Central Ridge Corridor", "road_type": "Arterial", "distance_km": 9.1, "base_speed_limit_kmh": 50, "road_gradient_percent": 2.2, "lanes": 4, "flood_risk_score": 0.22, "fog_risk_score": 0.29},
    {"road_id": "R6", "from_node": "NODE_SAKET", "to_node": "NODE_CYBER", "road_name": "Southern Peripheral Road", "road_type": "Highway", "distance_km": 11.0, "base_speed_limit_kmh": 70, "road_gradient_percent": 1.1, "lanes": 6, "flood_risk_score": 0.15, "fog_risk_score": 0.14},
    {"road_id": "R7", "from_node": "NODE_KG", "to_node": "NODE_MA", "road_name": "Yamuna River Road", "road_type": "Highway", "distance_km": 13.5, "base_speed_limit_kmh": 65, "road_gradient_percent": 0.9, "lanes": 6, "flood_risk_score": 0.35, "fog_risk_score": 0.18},
    {"road_id": "R8", "from_node": "NODE_MA", "to_node": "NODE_NOIDA_18", "road_name": "Noida Link Road", "road_type": "Ring_Road", "distance_km": 9.4, "base_speed_limit_kmh": 60, "road_gradient_percent": 1.7, "lanes": 6, "flood_risk_score": 0.25, "fog_risk_score": 0.19},
    {"road_id": "R9", "from_node": "NODE_CP", "to_node": "NODE_MA", "road_name": "Eastern Corridor", "road_type": "Highway", "distance_km": 15.7, "base_speed_limit_kmh": 68, "road_gradient_percent": 1.0, "lanes": 6, "flood_risk_score": 0.2, "fog_risk_score": 0.17},
    {"road_id": "R10", "from_node": "NODE_MA", "to_node": "NODE_IGI", "road_name": "Airport East Belt", "road_type": "Expressway", "distance_km": 11.2, "base_speed_limit_kmh": 75, "road_gradient_percent": 0.6, "lanes": 8, "flood_risk_score": 0.12, "fog_risk_score": 0.09},
]

nodes_df = pd.DataFrame(nodes)
roads_df = pd.DataFrame(roads)

nodes_df.to_csv(PROCESSED_DIR / 'nodes.csv', index=False)
roads_df.to_csv(PROCESSED_DIR / 'roads.csv', index=False)

weather_defaults = {
    'Clear': (28.0, 8.0, 0.0, 10.0),
    'Light_Rain': (24.0, 4.5, 4.0, 20.0),
    'Heavy_Rain': (22.0, 1.5, 25.0, 35.0),
    'Dense_Fog': (8.0, 0.2, 0.0, 5.0),
    'Extreme_Heat': (45.0, 6.0, 0.0, 15.0),
    'Storm': (20.0, 0.8, 40.0, 60.0),
}
vehicle_factors = {
    'Petrol_Sedan': (1.0, 0.16),
    'Diesel_SUV': (1.2, 0.18),
    'Electric_Vehicle': (0.5, 0.05),
    'Heavy_Truck': (1.7, 0.24),
    'Two_Wheeler': (0.65, 0.12),
}

hours = [7, 9, 11, 13, 15, 18, 21]
days = [0, 1, 2, 3, 4, 5, 6]
records = []

rng = np.random.default_rng(42)
for road in roads:
    road_type = road['road_type']
    for weather, (temp, vis, precip, wind) in weather_defaults.items():
        for vehicle_type, (veh_mult, fuel_mult) in vehicle_factors.items():
            for day in days:
                # Use a smaller but representative subset of hours to balance training
                for hour in hours:
                    is_weekday = day < 5
                    base_density = 3.0
                    if is_weekday and (8 <= hour <= 10 or 17 <= hour <= 20):
                        base_density = 8.5
                    elif is_weekday and (11 <= hour <= 16 or 21 <= hour <= 22):
                        base_density = 5.5
                    elif not is_weekday and 14 <= hour <= 21:
                        base_density = 6.8
                    else:
                        base_density = 2.5
                    if weather in ['Heavy_Rain', 'Storm']:
                        base_density = min(10.0, base_density + 2.0)
                    elif weather == 'Dense_Fog':
                        base_density = min(10.0, base_density + 1.5)
                    if road_type in ['Ring_Road', 'Arterial']:
                        base_density = min(10.0, base_density + 0.8)

                    distance = float(road['distance_km'])
                    speed_limit = float(road['base_speed_limit_kmh'])
                    hazard = 0.0
                    if weather in ['Heavy_Rain', 'Storm']:
                        hazard += road['flood_risk_score'] * 35.0 + (10.0 if weather == 'Storm' else 5.0)
                    elif weather == 'Dense_Fog':
                        hazard += road['fog_risk_score'] * 25.0
                    elif weather == 'Light_Rain':
                        hazard += road['flood_risk_score'] * 5.0

                    effective_speed = max(12.0, speed_limit * (1.0 - 0.25 * (base_density / 10.0)) * (1.0 - 0.1 * (precip / 40.0)))
                    time_minutes = distance / max(5.0, effective_speed) * 60.0 * (1.0 + 0.12 * (base_density / 10.0)) + 1.2
                    fuel_units = max(0.1, distance * fuel_mult * (0.7 + 0.14 * base_density / 10.0) * (1.0 + 0.12 * (precip / 30.0))) * veh_mult
                    time_minutes += rng.normal(0, 1.8)
                    fuel_units += rng.normal(0, 0.08)

                    records.append({
                        'road_type': road_type,
                        'weather_condition': weather,
                        'vehicle_type': vehicle_type,
                        'distance_km': round(distance, 2),
                        'base_speed_limit_kmh': int(speed_limit),
                        'traffic_density_index': round(float(np.clip(base_density, 1.0, 10.0)), 2),
                        'temperature_c': round(float(temp), 1),
                        'visibility_km': round(float(vis), 2),
                        'precipitation_mm': round(float(precip), 1),
                        'wind_speed_kmh': round(float(wind), 1),
                        'road_gradient_percent': round(float(road['road_gradient_percent']), 2),
                        'hour_of_day': int(hour),
                        'day_of_week': int(day),
                        'travel_time_minutes': round(float(max(3.0, time_minutes)), 2),
                        'fuel_consumption_units': round(float(max(0.1, fuel_units)), 3),
                        'flood_risk_score': round(float(road['flood_risk_score']), 3),
                        'fog_risk_score': round(float(road['fog_risk_score']), 3),
                    })

raw_df = pd.DataFrame(records)
raw_path = RAW_DIR / 'delhi_traffic.csv'
raw_df.to_csv(raw_path, index=False)
print(f'Created raw dataset with {len(raw_df)} rows at {raw_path}')

run_preprocessing(str(raw_path), str(PROCESSED_DIR))

npz_path = PROCESSED_DIR / 'train_test_data.npz'
preprocessor_path = PROCESSED_DIR / 'preprocessor.joblib'
train_and_evaluate(str(npz_path), str(preprocessor_path), str(MODELS_DIR))

print('Asset generation complete.')
