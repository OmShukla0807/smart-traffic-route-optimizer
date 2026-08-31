"""
Generates clean, professional Jupyter Notebooks (.ipynb) for Exploratory Data Analysis,
Model Benchmarks (with AQI Pollution), and Graph Topology & Dijkstra routing.
"""

import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
NOTEBOOKS_DIR = BASE_DIR / "notebooks"
NOTEBOOKS_DIR.mkdir(parents=True, exist_ok=True)

def make_notebook(cells):
    return {
        "cells": cells,
        "metadata": {
            "kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
            "language_info": {
                "codemirror_mode": {"name": "ipython", "version": 3},
                "file_extension": ".py",
                "mimetype": "text/x-python",
                "name": "python",
                "nbconvert_exporter": "python",
                "version": "3.10"
            }
        },
        "nbformat": 4,
        "nbformat_minor": 4
    }

def code_cell(source):
    lines = [line + "\n" for line in source.strip().split("\n")]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": lines
    }

def markdown_cell(source):
    lines = [line + "\n" for line in source.strip().split("\n")]
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return {
        "cell_type": "markdown",
        "metadata": {},
        "source": lines
    }

# Notebook 1: EDA & Traffic Insights
nb1_cells = [
    markdown_cell("# 🚦 Path Pilot — Exploratory Data Analysis (EDA)\n## Delhi-NCR Probe, Traffic Analytics & AQI Pollution\nThis notebook analyzes speed distributions, congestion density indices, weather slowdown factors, vehicle powertrain energy usage, and Air Quality Index (AQI) variations across 84 Delhi NCR transit corridors."),
    code_cell("""
import os
import pandas as pd
import numpy as np

# Load the generated 210K+ Delhi traffic dataset
data_path = os.path.join('..', 'data', 'raw', 'delhi_traffic.csv')
df = pd.read_csv(data_path)
print(f"Dataset Shape: {df.shape}")
df.head(10)
"""),
    markdown_cell("### 1. Summary Statistics & Data Types"),
    code_cell("""
df.info()
df.describe().round(2)
"""),
    markdown_cell("### 2. Traffic Density Distribution by Hour & Road Type"),
    code_cell("""
# Group traffic density by hour of day and road type
hourly_density = df.groupby(['hour_of_day', 'road_type'])['traffic_density_index'].mean().unstack()
print("Average Traffic Density Index (1-10) by Hour:")
hourly_density.round(2)
"""),
    markdown_cell("### 3. AQI Air Quality & Weather Disruption Analysis"),
    code_cell("""
# Analyze travel time and AQI across weather profiles
weather_impact = df.groupby('weather_condition')[['travel_time_minutes', 'fuel_consumption_units', 'aqi_index', 'visibility_km']].mean()
print("Impact of Weather Extremes on Travel Times, Fuel, and AQI:")
weather_impact.round(2)
"""),
    markdown_cell("### 4. Vehicle Powertrain Energy Profiling"),
    code_cell("""
# Fuel and energy consumption across vehicle types
veh_stats = df.groupby('vehicle_type')[['fuel_consumption_units', 'travel_time_minutes']].mean()
print("Energy & Fuel Consumption by Powertrain:")
veh_stats.round(3)
""")
]

# Notebook 2: Model Training & Benchmarks
nb2_cells = [
    markdown_cell("# 🧠 Machine Learning Model Training & Comparative Benchmarking\n## Predicting Segment Travel Time & Fuel Consumption with AQI\nThis notebook evaluates Linear Regression, Ridge, Random Forest, and Gradient Boosting models, inspects feature importances, and verifies model serialization."),
    code_cell("""
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

# Load preprocessed arrays
npz_path = os.path.join('..', 'data', 'processed', 'train_test_data.npz')
data = np.load(npz_path)

X_train = data['X_train']
X_test = data['X_test']
y_train_time = data['y_train_time']
y_test_time = data['y_test_time']
y_train_fuel = data['y_train_fuel']
y_test_fuel = data['y_test_fuel']

preprocessor = joblib.load(os.path.join('..', 'data', 'processed', 'preprocessor.joblib'))
feature_names = preprocessor.feature_names
print(f"X_train shape: {X_train.shape} | X_test shape: {X_test.shape}")
"""),
    markdown_cell("### 1. Travel Time Model Benchmark Comparison"),
    code_cell("""
models = {
    "Linear Regression (Baseline)": LinearRegression(),
    "Ridge Regression": Ridge(alpha=1.0),
    "Random Forest": RandomForestRegressor(n_estimators=50, max_depth=12, random_state=42),
    "Gradient Boosting": GradientBoostingRegressor(n_estimators=100, max_depth=6, random_state=42)
}

results = []
for name, model in models.items():
    model.fit(X_train, y_train_time)
    preds = model.predict(X_test)
    mae = mean_absolute_error(y_test_time, preds)
    rmse = np.sqrt(mean_squared_error(y_test_time, preds))
    r2 = r2_score(y_test_time, preds)
    results.append({"Model": name, "MAE (min)": round(mae, 3), "RMSE": round(rmse, 3), "R² Score": round(r2, 4)})

pd.DataFrame(results)
"""),
    markdown_cell("### 2. Feature Importances for Travel Time Prediction"),
    code_cell("""
gb_model = models["Gradient Boosting"]
importances = gb_model.feature_importances_
sorted_indices = np.argsort(importances)[::-1]

print("Top 10 Most Influential Features:")
for rank, idx in enumerate(sorted_indices[:10], 1):
    print(f"{rank:2d}. {feature_names[idx]:30s} -> {importances[idx]:.4f}")
""")
]

# Notebook 3: Graph Topology & Multi-Route Dijkstra
nb3_cells = [
    markdown_cell("# ⚡ Graph Topology & C++ Dijkstra Routing Engine\n## Multi-Objective Pareto Optimal Routing Across 84 Delhi Corridors\nThis notebook demonstrates graph construction, dynamic edge weighting, C++ Dijkstra solver execution, and Pareto trade-off comparisons across 4 distinct routes."),
    code_cell("""
import os
import sys
import pandas as pd

# Add project root to path
sys.path.insert(0, os.path.abspath('..'))

from backend.app.core.router import MultiObjectiveRouter

router = MultiObjectiveRouter()
print(f"Loaded {len(router.nodes_df)} Delhi Transit Hubs and {len(router.edge_engine.roads_df)} Corridors.")
router.nodes_df[['node_id', 'node_name', 'zone', 'landmark']].head(10)
"""),
    markdown_cell("### 1. Multi-Objective Route Optimization Test (CP to Cyber City)"),
    code_cell("""
result = router.optimize(
    source_id="NODE_CP",
    destination_id="NODE_CYBER",
    hour_of_day=9,
    day_of_week=1,
    weather_condition="Clear",
    vehicle_type="Petrol_Sedan"
)

for k, r in result['routes'].items():
    print(f"=== {r['mode_title'].upper()} ===")
    print(f"Corridor: {r['route_summary_label']}")
    print(f"ETA: {r['total_time_min']} min | Distance: {r['total_distance_km']} km | Fuel: {r['total_fuel_units']} {r['fuel_unit_name']} | AQI: {r['avg_aqi_index']}\\n")
"""),
    markdown_cell("### 2. Extreme Storm & Flood Bypass Demonstration"),
    code_cell("""
storm_result = router.optimize(
    source_id="NODE_CP",
    destination_id="NODE_CYBER",
    hour_of_day=18,
    day_of_week=4,
    weather_condition="Storm",
    vehicle_type="Electric_Vehicle"
)

print(f"Storm Fastest: {storm_result['routes']['fastest']['total_time_min']} min | Safety: {storm_result['routes']['fastest']['weather_safety_score']}%")
print(f"Storm Safe:    {storm_result['routes']['weather_safe']['total_time_min']} min | Safety: {storm_result['routes']['weather_safe']['weather_safety_score']}%")
""")
]

with open(NOTEBOOKS_DIR / "01_eda_and_traffic_insights.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(nb1_cells), f, indent=2)

with open(NOTEBOOKS_DIR / "02_model_training_and_benchmarks.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(nb2_cells), f, indent=2)

with open(NOTEBOOKS_DIR / "03_graph_topology_and_dijkstra.ipynb", "w", encoding="utf-8") as f:
    json.dump(make_notebook(nb3_cells), f, indent=2)

print("Saved all 3 Jupyter notebooks successfully!")
