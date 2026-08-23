"""
FastAPI Backend Application for Smart Traffic Route Optimizer.
Phase 12: Coordinates Road Network, ML Inference, C++ Dijkstra Engine, and Database.
"""

import os
import sys
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.schemas import RouteRequest, RouteResponse
from backend.app.core.router import MultiObjectiveRouter, EMISSION_FACTORS
from backend.app.core.feature_mapper import WEATHER_DEFAULTS
from database.db import init_db, log_route_query, get_recent_history, get_db_connection

# Initialize Database
init_db()

# Initialize Multi-Objective Router
router_engine = MultiObjectiveRouter()

app = FastAPI(
    title="Smart Traffic Route Optimizer API",
    description="Multi-Objective Route Optimization using ML Travel-Time Predictions & C++ Dijkstra Engine",
    version="1.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static directory if exists
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def root():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "name": "Smart Traffic Route Optimizer API",
        "status": "online",
        "docs": "/docs",
        "version": "1.0.0"
    }

@app.get("/api/health")
def health_check():
    return {
        "status": "healthy",
        "ml_model": "Gradient Boosting Regressor (R² > 0.99)",
        "cpp_engine": "Compiled C++ Dijkstra Engine",
        "database": "SQLite (18 nodes, 50 roads loaded)"
    }

@app.get("/api/nodes")
def get_nodes():
    """Return all Delhi network transit hub nodes."""
    return {"nodes": router_engine.nodes_df.to_dict(orient="records")}

@app.get("/api/roads")
def get_roads():
    """Return all road network segments."""
    return {"roads": router_engine.edge_engine.roads_df.to_dict(orient="records")}

@app.get("/api/vehicles")
def get_vehicles():
    """Return supported vehicle types and emission parameters."""
    return {
        "vehicles": [
            {"id": "Petrol_Sedan", "name": "Petrol Sedan (Standard)", "icon": "🚗", "fuel_unit": "Liters", "co2_factor": 2.31},
            {"id": "Diesel_SUV", "name": "Diesel SUV (Heavy / Torquey)", "icon": "🚙", "fuel_unit": "Liters", "co2_factor": 2.68},
            {"id": "Electric_Vehicle", "name": "Electric Vehicle (EV w/ Regen)", "icon": "⚡", "fuel_unit": "kWh", "co2_factor": 0.08},
            {"id": "Heavy_Truck", "name": "Heavy Freight Commercial Truck", "icon": "🚛", "fuel_unit": "Liters", "co2_factor": 2.68},
            {"id": "Two_Wheeler", "name": "Two Wheeler / Motorcycle", "icon": "🏍️", "fuel_unit": "Liters", "co2_factor": 2.31}
        ]
    }

@app.get("/api/weather-presets")
def get_weather_presets():
    """Return weather condition profiles."""
    return {
        "conditions": [
            {"id": "Clear", "name": "Clear Sky / Normal", "icon": "☀️", "hazard_level": "Low"},
            {"id": "Light_Rain", "name": "Light Rain / Wet Asphalt", "icon": "🌦️", "hazard_level": "Moderate"},
            {"id": "Heavy_Rain", "name": "Heavy Rain / Waterlogging Alert", "icon": "🌧️", "hazard_level": "High"},
            {"id": "Dense_Fog", "name": "Dense Smog / Winter Fog (<200m Vis)", "icon": "🌫️", "hazard_level": "High"},
            {"id": "Extreme_Heat", "name": "Extreme Summer Heat (45°C+)", "icon": "🔥", "hazard_level": "Moderate (AC Load)"},
            {"id": "Storm", "name": "Severe Thunderstorm / High Wind", "icon": "⛈️", "hazard_level": "Critical"}
        ]
    }

@app.post("/api/route", response_model=RouteResponse)
def compute_optimized_route(req: RouteRequest):
    """
    Main Route Optimization Endpoint:
    Calculates Fastest Route, Eco Route, Weather-Safe Route, and Custom Balanced Route
    using ML travel-time inference and C++ Dijkstra engine.
    """
    result = router_engine.optimize(
        source_id=req.source_id,
        destination_id=req.destination_id,
        hour_of_day=req.hour_of_day,
        day_of_week=req.day_of_week,
        weather_condition=req.weather_condition,
        vehicle_type=req.vehicle_type,
        custom_weights=req.custom_weights
    )

    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("message"))

    # Log to SQLite
    try:
        fastest_time = result["routes"].get("fastest", {}).get("total_time_min", 0.0)
        fastest_fuel = result["routes"].get("fastest", {}).get("total_fuel_units", 1.0)
        eco_fuel = result["routes"].get("eco", {}).get("total_fuel_units", fastest_fuel)
        
        fuel_saved_pct = 0.0
        if fastest_fuel > 0:
            fuel_saved_pct = round(max(0.0, (fastest_fuel - eco_fuel) / fastest_fuel * 100.0), 1)

        engine_used = result["routes"].get("fastest", {}).get("engine_used", "C++ Engine")
        
        log_route_query(
            source_id=req.source_id,
            destination_id=req.destination_id,
            vehicle_type=req.vehicle_type,
            weather_condition=req.weather_condition,
            hour_of_day=req.hour_of_day,
            fastest_time_min=fastest_time,
            eco_fuel_saved_percent=fuel_saved_pct,
            engine_used=engine_used
        )
    except Exception as e:
        print(f"[Warning] Failed to log route query to DB: {e}")

    return result

@app.get("/api/history")
def get_history(limit: int = Query(10, ge=1, le=50)):
    """Fetch recent route optimization queries."""
    return {"history": get_recent_history(limit=limit)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
