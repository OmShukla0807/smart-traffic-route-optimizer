"""
Comprehensive Data Generation Script for Smart Traffic Route Optimizer.
Generates:
1. data/processed/nodes.csv (20 prominent Delhi NCR transit hubs)
2. data/processed/roads.csv (84 real interconnected Delhi NCR corridors with exact geodesic distances and AQI pollution levels)
3. data/raw/delhi_traffic.csv (180,000+ multi-factor traffic records for ML training)
"""

import os
import sys
import math
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "data" / "raw"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
MODELS_DIR = BASE_DIR / "ml" / "models"

RAW_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# 20 Prominent Delhi NCR Transit Nodes
NODES = [
    {"node_id": "NODE_CP", "node_name": "Connaught Place", "latitude": 28.6315, "longitude": 77.2167, "zone": "Central Delhi", "landmark": "Rajiv Chowk Metro Hub"},
    {"node_id": "NODE_IG", "node_name": "India Gate", "latitude": 28.6129, "longitude": 77.2295, "zone": "Central Delhi", "landmark": "Kartavya Path"},
    {"node_id": "NODE_KG", "node_name": "Kashmere Gate ISBT", "latitude": 28.6661, "longitude": 77.2290, "zone": "North Delhi", "landmark": "Inter-State Bus Terminal"},
    {"node_id": "NODE_CYBER", "node_name": "Gurgaon Cyber City", "latitude": 28.4955, "longitude": 77.0888, "zone": "Gurugram", "landmark": "DLF CyberHub"},
    {"node_id": "NODE_IGI", "node_name": "IGI Airport Terminal 3", "latitude": 28.5562, "longitude": 77.1000, "zone": "South-West Delhi", "landmark": "Airport Express Terminal"},
    {"node_id": "NODE_NOIDA_18", "node_name": "Noida Sector 18", "latitude": 28.5688, "longitude": 77.3342, "zone": "Noida", "landmark": "Atta Market / Mall of India"},
    {"node_id": "NODE_SAKET", "node_name": "Saket Citywalk", "latitude": 28.5214, "longitude": 77.2013, "zone": "South Delhi", "landmark": "Select Citywalk Mall"},
    {"node_id": "NODE_HK", "node_name": "Hauz Khas", "latitude": 28.5494, "longitude": 77.2001, "zone": "South Delhi", "landmark": "IIT Delhi / HKV"},
    {"node_id": "NODE_NP", "node_name": "Nehru Place", "latitude": 28.5492, "longitude": 77.2514, "zone": "South-East Delhi", "landmark": "IT & Electronics Hub"},
    {"node_id": "NODE_ROH", "node_name": "Rohini West", "latitude": 28.7144, "longitude": 77.1147, "zone": "North-West Delhi", "landmark": "Swarn Jayanti Park"},
    {"node_id": "NODE_JAN", "node_name": "Janakpuri West", "latitude": 28.6294, "longitude": 77.0782, "zone": "West Delhi", "landmark": "District Centre"},
    {"node_id": "NODE_AKSHAR", "node_name": "Akshardham", "latitude": 28.6127, "longitude": 77.2773, "zone": "East Delhi", "landmark": "Swaminarayan Complex"},
    {"node_id": "NODE_KB", "node_name": "Karol Bagh", "latitude": 28.6517, "longitude": 77.1906, "zone": "Central Delhi", "landmark": "Ghaffar Market"},
    {"node_id": "NODE_LN", "node_name": "Lajpat Nagar", "latitude": 28.5677, "longitude": 77.2433, "zone": "South Delhi", "landmark": "Central Market"},
    {"node_id": "NODE_DK", "node_name": "Dhaula Kuan", "latitude": 28.5921, "longitude": 77.1617, "zone": "Central-South Delhi", "landmark": "Ring Road Interchange"},
    {"node_id": "NODE_DWK", "node_name": "Dwarka Sector 21", "latitude": 28.5523, "longitude": 77.0583, "zone": "South-West Delhi", "landmark": "Dwarka Expressway Entry"},
    {"node_id": "NODE_ANAND", "node_name": "Anand Vihar ISBT", "latitude": 28.6469, "longitude": 77.3160, "zone": "East Delhi", "landmark": "Anand Vihar Terminal"},
    {"node_id": "NODE_GR_NOIDA", "node_name": "Pari Chowk", "latitude": 28.4639, "longitude": 77.5110, "zone": "Greater Noida", "landmark": "Expo Mart Hub"},
    {"node_id": "NODE_FBD", "node_name": "Faridabad Sector 15", "latitude": 28.4089, "longitude": 77.3178, "zone": "Faridabad", "landmark": "Bata Chowk Corridor"},
    {"node_id": "NODE_GZB", "node_name": "Ghaziabad Vaishali", "latitude": 28.6471, "longitude": 77.3400, "zone": "Ghaziabad", "landmark": "Max Hospital Hub"}
]

# Helper function to compute real geodesic distance (Haversine formula + road curvature factor)
def compute_real_distance(lat1, lon1, lat2, lon2, road_type):
    R = 6371.0 # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    crow_dist = R * c
    
    # Real road curvature factors in Delhi:
    # Expressways are straighter (1.12x - 1.18x), Arterials have curves/bypasses (1.20x - 1.30x)
    curve_factor = 1.14 if road_type == "Expressway" else (1.20 if road_type in ["Highway", "Ring_Road"] else 1.25)
    return round(max(1.8, crow_dist * curve_factor), 1)

node_dict = {n["node_id"]: n for n in NODES}

# 84 Bidirectional Real Road Corridors across Delhi NCR
# Including actual Delhi road names, real speed limits, gradients, flood/fog risk, and localized AQI (Air Quality Index)
ROAD_TEMPLATES = [
    # 1. Central Core Corridors
    ("NODE_CP", "NODE_IG", "Janpath & Kartavya Path", "Arterial", 50, 0.4, 6, 0.10, 0.12, 145),
    ("NODE_CP", "NODE_KB", "Pusa Road Corridor", "Arterial", 45, 1.0, 4, 0.20, 0.18, 220),
    ("NODE_CP", "NODE_KG", "Netaji Subhash Marg / Red Fort Trunk", "Arterial", 50, 0.8, 6, 0.25, 0.22, 280),
    ("NODE_CP", "NODE_DK", "Sardar Patel Marg / Ridge Road", "Arterial", 60, 2.2, 6, 0.08, 0.20, 130), # Clean air ridge
    ("NODE_CP", "NODE_HK", "Sri Aurobindo Marg North", "Arterial", 50, 1.2, 4, 0.15, 0.18, 160),
    ("NODE_CP", "NODE_LN", "Barapullah Inbound Link / Lodhi Road", "Arterial", 55, 0.6, 6, 0.14, 0.16, 175),
    ("NODE_CP", "NODE_AKSHAR", "Vikas Marg Central (ITO Bridge)", "Highway", 60, 0.5, 6, 0.38, 0.35, 310), # High AQI Yamuna bank

    # 2. India Gate & South-Central Corridors
    ("NODE_IG", "NODE_LN", "Lala Lajpat Rai Marg", "Arterial", 55, 0.6, 6, 0.15, 0.16, 180),
    ("NODE_IG", "NODE_DK", "Shanti Path / Chanakyapuri Diplomatic Corridor", "Arterial", 60, 0.8, 6, 0.06, 0.15, 110), # Very clean air
    ("NODE_IG", "NODE_AKSHAR", "Vikas Marg South / Pragati Maidan Tunnel", "Highway", 65, 0.4, 6, 0.35, 0.32, 290),
    ("NODE_IG", "NODE_NP", "Lodhi Road - Nehru Place Express Line", "Arterial", 55, 0.7, 6, 0.16, 0.15, 195),

    # 3. North & West Corridors (Karol Bagh, Rohini, Janakpuri, Kashmere Gate)
    ("NODE_KB", "NODE_JAN", "Najafgarh Road Westbound", "Arterial", 55, 0.6, 6, 0.22, 0.18, 260),
    ("NODE_KB", "NODE_ROH", "Rohtak Road / Ring Road North-West", "Highway", 65, 0.8, 6, 0.20, 0.22, 275),
    ("NODE_KB", "NODE_DK", "Vande Mataram Marg South Link", "Arterial", 60, 2.0, 4, 0.10, 0.22, 140),
    ("NODE_KG", "NODE_ROH", "GT Karnal Road (NH-44 North Link)", "Highway", 70, 0.7, 6, 0.28, 0.32, 340),
    ("NODE_KG", "NODE_ANAND", "ISBT Link / NH-9 Eastbound", "Highway", 65, 0.5, 6, 0.32, 0.30, 390), # Very high AQI
    ("NODE_KG", "NODE_AKSHAR", "Ring Road Yamuna Bank Bypass", "Ring_Road", 60, 0.4, 6, 0.42, 0.36, 360),
    ("NODE_JAN", "NODE_ROH", "Outer Ring Road (Peeragarhi - Rohini)", "Ring_Road", 65, 0.6, 6, 0.18, 0.24, 250),
    ("NODE_JAN", "NODE_DWK", "Pankha Road Elevated Flyway", "Arterial", 55, 0.8, 6, 0.18, 0.16, 230),
    ("NODE_JAN", "NODE_DK", "Jail Road / Ring Road West Link", "Arterial", 55, 0.7, 6, 0.16, 0.18, 220),

    # 4. South-West, Airport & Gurugram Corridors (Multiple Alternative Corridors to Gurugram)
    ("NODE_DK", "NODE_IGI", "Airport Expressway NH-48", "Expressway", 80, 0.5, 8, 0.08, 0.18, 160),
    ("NODE_DK", "NODE_HK", "Benito Juarez Marg / Outer Ring South", "Ring_Road", 65, 1.2, 6, 0.12, 0.16, 150),
    ("NODE_DK", "NODE_DWK", "Delhi Cantonment - Dwarka Link Road", "Highway", 70, 0.6, 6, 0.10, 0.18, 170),
    ("NODE_IGI", "NODE_CYBER", "NH-48 Delhi-Gurgaon Expressway", "Expressway", 90, 0.6, 8, 0.14, 0.24, 210), # High-speed artery
    ("NODE_IGI", "NODE_DWK", "Urban Extension Road II / Airport Tunnel", "Expressway", 80, 0.4, 6, 0.10, 0.14, 155),
    ("NODE_DWK", "NODE_CYBER", "Dwarka Expressway (NH-248BB)", "Expressway", 100, 0.4, 8, 0.06, 0.28, 140), # Low congestion / clean alternative
    ("NODE_HK", "NODE_SAKET", "Aurobindo Marg South (IIT - Saket)", "Arterial", 50, 1.4, 4, 0.16, 0.20, 150),
    ("NODE_HK", "NODE_NP", "Outer Ring Road (Chirag Delhi Flyover)", "Ring_Road", 65, 0.8, 6, 0.22, 0.15, 210),
    ("NODE_HK", "NODE_CYBER", "Nelson Mandela Marg / MG Road Bypass", "Highway", 70, 1.6, 6, 0.12, 0.24, 145), # Ridge Clean Air route
    ("NODE_SAKET", "NODE_CYBER", "Mehrauli-Gurgaon (MG) Road", "Highway", 70, 1.8, 6, 0.15, 0.26, 165), # Eco-friendly alternative
    ("NODE_SAKET", "NODE_NP", "Press Enclave Marg Corridor", "Arterial", 50, 0.8, 4, 0.16, 0.18, 180),
    ("NODE_SAKET", "NODE_FBD", "Mehrauli-Badarpur & Surajkund Hill Road", "Highway", 65, 2.5, 4, 0.18, 0.22, 175),

    # 5. South-East & East Corridors (Noida, Akshardham, Anand Vihar, Faridabad)
    ("NODE_LN", "NODE_NP", "Inner Ring Road South-East Segment", "Ring_Road", 60, 0.7, 6, 0.16, 0.14, 210),
    ("NODE_LN", "NODE_NOIDA_18", "DND Flyway & Barapullah Elevated", "Expressway", 80, 0.4, 8, 0.32, 0.30, 240),
    ("NODE_NP", "NODE_FBD", "Mathura Road (NH-19 South Corridor)", "Highway", 70, 0.8, 6, 0.28, 0.26, 320),
    ("NODE_NP", "NODE_NOIDA_18", "Kalindi Kunj Bypass & Okhla Flyway", "Arterial", 60, 0.5, 6, 0.35, 0.32, 330),
    ("NODE_AKSHAR", "NODE_NOIDA_18", "Noida Link Road & Chilla Elevated", "Expressway", 75, 0.3, 8, 0.20, 0.24, 250),
    ("NODE_AKSHAR", "NODE_ANAND", "NH-9 Delhi-Meerut Expressway", "Expressway", 85, 0.4, 8, 0.15, 0.28, 380),
    ("NODE_ANAND", "NODE_GZB", "Link Road Sahibabad / Kaushambi", "Arterial", 50, 0.6, 4, 0.26, 0.30, 420), # Hotspot AQI
    ("NODE_NOIDA_18", "NODE_GR_NOIDA", "Noida-Greater Noida Expressway", "Expressway", 100, 0.2, 8, 0.08, 0.40, 190),
    ("NODE_NOIDA_18", "NODE_FBD", "Faridabad-Noida-Ghaziabad (FNG) Corridor", "Highway", 75, 0.4, 6, 0.22, 0.32, 280),
    ("NODE_GR_NOIDA", "NODE_FBD", "Yamuna Expressway - Faridabad Bypass", "Highway", 75, 0.3, 6, 0.15, 0.35, 220)
]

ROADS = []
road_counter = 1

for u, v, rname, rtype, spd, grad, lanes, flood, fog, aqi in ROAD_TEMPLATES:
    node_u = node_dict[u]
    node_v = node_dict[v]
    real_dist = compute_real_distance(node_u["latitude"], node_u["longitude"], node_v["latitude"], node_v["longitude"], rtype)
    
    # Forward direction
    r_id_fwd = f"R{road_counter:02d}"
    ROADS.append({
        "road_id": r_id_fwd,
        "from_node": u,
        "to_node": v,
        "road_name": rname,
        "road_type": rtype,
        "distance_km": real_dist,
        "base_speed_limit_kmh": spd,
        "road_gradient_percent": grad,
        "lanes": lanes,
        "flood_risk_score": flood,
        "fog_risk_score": fog,
        "aqi_index": aqi,
        "pollution_exposure_score": round(min(1.0, aqi / 450.0), 2)
    })
    road_counter += 1

    # Reverse return direction
    r_id_rev = f"R{road_counter:02d}"
    ROADS.append({
        "road_id": r_id_rev,
        "from_node": v,
        "to_node": u,
        "road_name": f"{rname} (Return)",
        "road_type": rtype,
        "distance_km": real_dist,
        "base_speed_limit_kmh": spd,
        "road_gradient_percent": grad,
        "lanes": lanes,
        "flood_risk_score": flood,
        "fog_risk_score": fog,
        "aqi_index": aqi,
        "pollution_exposure_score": round(min(1.0, aqi / 450.0), 2)
    })
    road_counter += 1

def generate_network_files():
    nodes_df = pd.DataFrame(NODES)
    roads_df = pd.DataFrame(ROADS)

    nodes_path = PROCESSED_DIR / "nodes.csv"
    roads_path = PROCESSED_DIR / "roads.csv"

    nodes_df.to_csv(nodes_path, index=False)
    roads_df.to_csv(roads_path, index=False)
    print(f"[OK] Saved {len(nodes_df)} transit nodes to: {nodes_path}")
    print(f"[OK] Saved {len(roads_df)} real road corridors to: {roads_path}")

def generate_traffic_dataset():
    """Generate 180,000+ realistic traffic and probe records across all 84 corridors, weather, AQI, powertrains, and time windows."""
    print("Generating comprehensive Delhi multi-factor traffic dataset with AQI pollution...")
    
    weather_profiles = {
        "Clear": {"temp": 28.0, "vis": 8.0, "precip": 0.0, "wind": 10.0, "speed_mult": 1.0, "density_add": 0.0},
        "Light_Rain": {"temp": 24.0, "vis": 4.5, "precip": 4.0, "wind": 20.0, "speed_mult": 0.85, "density_add": 1.0},
        "Heavy_Rain": {"temp": 22.0, "vis": 1.5, "precip": 25.0, "wind": 35.0, "speed_mult": 0.60, "density_add": 2.2},
        "Dense_Fog": {"temp": 8.0, "vis": 0.2, "precip": 0.0, "wind": 5.0, "speed_mult": 0.65, "density_add": 1.8},
        "Extreme_Heat": {"temp": 45.0, "vis": 6.0, "precip": 0.0, "wind": 15.0, "speed_mult": 0.95, "density_add": 0.5},
        "Storm": {"temp": 20.0, "vis": 0.8, "precip": 40.0, "wind": 60.0, "speed_mult": 0.45, "density_add": 3.0}
    }

    powertrain_profiles = {
        "Petrol_Sedan": {"base_fuel_per_km": 0.075, "idle_fuel_per_min": 0.015, "speed_factor": 1.0},
        "Diesel_SUV": {"base_fuel_per_km": 0.088, "idle_fuel_per_min": 0.018, "speed_factor": 0.98},
        "Electric_Vehicle": {"base_fuel_per_km": 0.160, "idle_fuel_per_min": 0.005, "speed_factor": 1.02}, # kWh/km
        "Heavy_Truck": {"base_fuel_per_km": 0.280, "idle_fuel_per_min": 0.045, "speed_factor": 0.78},
        "Two_Wheeler": {"base_fuel_per_km": 0.028, "idle_fuel_per_min": 0.006, "speed_factor": 1.10}
    }

    records = []
    rng = np.random.default_rng(42)

    hours = list(range(0, 24, 2)) # 12 representative hour buckets
    days = list(range(7)) # Mon - Sun

    for road in ROADS:
        dist = float(road["distance_km"])
        speed_limit = float(road["base_speed_limit_kmh"])
        road_type = road["road_type"]
        grad = float(road["road_gradient_percent"])
        flood_risk = float(road["flood_risk_score"])
        fog_risk = float(road["fog_risk_score"])
        base_aqi = float(road["aqi_index"])

        for weather_name, w_info in weather_profiles.items():
            for veh_name, v_info in powertrain_profiles.items():
                for day in days:
                    for hour in hours:
                        is_weekday = day < 5
                        # Base traffic density modeling for Delhi
                        if is_weekday:
                            if 8 <= hour <= 11 or 17 <= hour <= 21:
                                base_density = 8.2 + rng.uniform(-0.5, 0.7) # Peak office rush
                            elif 12 <= hour <= 16 or 22 <= hour <= 23:
                                base_density = 5.2 + rng.uniform(-0.4, 0.5)
                            else:
                                base_density = 2.0 + rng.uniform(-0.3, 0.4)
                        else:
                            if 13 <= hour <= 21:
                                base_density = 6.8 + rng.uniform(-0.5, 0.6)
                            else:
                                base_density = 2.8 + rng.uniform(-0.4, 0.4)

                        # Road type adjustment
                        if road_type in ["Ring_Road", "Arterial"]:
                            base_density += 0.8
                        elif road_type == "Expressway":
                            base_density -= 0.5

                        density = np.clip(base_density + w_info["density_add"], 1.0, 10.0)

                        # Dynamic AQI variation (winter fog / smog increases AQI by +40%, rain washes down by -50%)
                        cur_aqi = base_aqi
                        if weather_name in ["Heavy_Rain", "Light_Rain", "Storm"]:
                            cur_aqi = max(50.0, cur_aqi * 0.55)
                        elif weather_name == "Dense_Fog":
                            cur_aqi = min(500.0, cur_aqi * 1.35)
                        elif hour in [8, 9, 10, 18, 19, 20]:
                            cur_aqi = min(500.0, cur_aqi * 1.15) # Peak emission spike

                        # Speed and travel time calculation
                        congestion_slowdown = max(0.20, 1.0 - (density / 12.0) ** 1.3)
                        weather_slowdown = w_info["speed_mult"]
                        
                        if weather_name in ["Heavy_Rain", "Storm"]:
                            weather_slowdown *= max(0.4, 1.0 - flood_risk * 0.7)
                        elif weather_name == "Dense_Fog":
                            weather_slowdown *= max(0.5, 1.0 - fog_risk * 0.6)

                        effective_speed = speed_limit * congestion_slowdown * weather_slowdown * v_info["speed_factor"]
                        effective_speed = max(8.0, effective_speed + rng.normal(0, 1.2))

                        free_flow_min = (dist / effective_speed) * 60.0
                        junction_delay = (density * 0.35) if road_type == "Arterial" else (density * 0.12)
                        travel_time_min = round(free_flow_min + junction_delay, 2)

                        # Fuel consumption modeling
                        speed_efficiency_factor = 1.0 + max(0.0, (35.0 - min(35.0, effective_speed)) / 25.0) * 0.6
                        gradient_factor = 1.0 + (grad * 0.08)
                        heat_factor = 1.15 if weather_name == "Extreme_Heat" else 1.0
                        
                        driving_fuel = dist * v_info["base_fuel_per_km"] * speed_efficiency_factor * gradient_factor * heat_factor
                        idle_fuel = (travel_time_min - (dist / speed_limit * 60.0)) * v_info["idle_fuel_per_min"]
                        total_fuel = round(max(0.02, driving_fuel + max(0.0, idle_fuel)), 3)

                        records.append({
                            "road_type": road_type,
                            "weather_condition": weather_name,
                            "vehicle_type": veh_name,
                            "distance_km": dist,
                            "base_speed_limit_kmh": int(speed_limit),
                            "traffic_density_index": round(density, 2),
                            "temperature_c": w_info["temp"],
                            "visibility_km": w_info["vis"],
                            "precipitation_mm": w_info["precip"],
                            "wind_speed_kmh": w_info["wind"],
                            "road_gradient_percent": grad,
                            "hour_of_day": hour,
                            "day_of_week": day,
                            "travel_time_minutes": travel_time_min,
                            "fuel_consumption_units": total_fuel,
                            "flood_risk_score": flood_risk,
                            "fog_risk_score": fog_risk,
                            "aqi_index": round(cur_aqi, 1),
                            "pollution_exposure_score": round(min(1.0, cur_aqi / 450.0), 2)
                        })

    df = pd.DataFrame(records)
    raw_path = RAW_DIR / "delhi_traffic.csv"
    df.to_csv(raw_path, index=False)
    print(f"[OK] Generated {len(df)} traffic, weather, and AQI probe observations to: {raw_path}")

if __name__ == "__main__":
    generate_network_files()
    generate_traffic_dataset()
