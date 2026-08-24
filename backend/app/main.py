"""
FastAPI Backend Application for Smart Traffic Route Optimizer.
Coordinates Road Network, ML Inference, C++ Dijkstra Engine, SQLite Database, and Live Incident Simulation.
"""

import os
import sys
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import Dict, Any, List

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.app.schemas import (
    RouteRequest, RouteResponse, IncidentSimulationRequest, AnalyticsResponse
)
from backend.app.core.router import MultiObjectiveRouter, EMISSION_FACTORS
from backend.app.core.feature_mapper import WEATHER_DEFAULTS
from database.db import (
    init_db, log_route_query, get_recent_history, get_active_incidents,
    add_or_toggle_incident, clear_all_incidents, get_database_analytics
)

# Initialize Database on application startup
init_db()

# Initialize Router Engine
router_engine = MultiObjectiveRouter()

app = FastAPI(
    title="Smart Traffic Route Optimizer API",
    description="Multi-Objective AI Route Optimization using ML Travel-Time Predictions & C++ Dijkstra Engine",
    version="2.0.0"
)

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount frontend static files directory
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def root():
    """Serve the single-page mission control application."""
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "name": "Smart Traffic Route Optimizer API",
        "status": "online",
        "docs": "/docs",
        "version": "2.0.0"
    }

@app.get("/api/health")
def health_check():
    """System health check and component telemetry."""
    return {
        "status": "healthy",
        "ml_time_model": "Gradient Boosting Regressor (R² = 0.979)",
        "ml_fuel_model": "Gradient Boosting Regressor (R² = 0.996)",
        "cpp_engine": "Compiled Native C++ Dijkstra Engine (Min-Heap Priority Queue)",
        "database": "SQLite (20 Nodes, 52 Corridors Synchronized)",
        "incidents_active": len(get_active_incidents())
    }

@app.get("/api/nodes")
def get_nodes():
    """Return all 20 Delhi NCR transit hub nodes."""
    return {"nodes": router_engine.nodes_df.to_dict(orient="records")}

@app.get("/api/roads")
def get_roads():
    """Return all 52 road network segments with live metadata."""
    return {"roads": router_engine.edge_engine.roads_df.to_dict(orient="records")}

@app.get("/api/vehicles")
def get_vehicles():
    """Return supported vehicle powertrains and emission characteristics."""
    return {
        "vehicles": [
            {"id": "Petrol_Sedan", "name": "Petrol Sedan (Internal Combustion)", "icon": "🚗", "fuel_unit": "Liters", "co2_factor": 2.31, "efficiency_desc": "Standard fuel consumption with stop-and-go penalty."},
            {"id": "Diesel_SUV", "name": "Diesel SUV (Heavy / High Torque)", "icon": "🚙", "fuel_unit": "Liters", "co2_factor": 2.68, "efficiency_desc": "High torque, heavier gradient fuel penalty."},
            {"id": "Electric_Vehicle", "name": "Electric Vehicle (EV w/ Regenerative Braking)", "icon": "⚡", "fuel_unit": "kWh", "co2_factor": 0.08, "efficiency_desc": "High urban efficiency, zero direct tailpipe emissions."},
            {"id": "Heavy_Truck", "name": "Commercial Heavy Freight Truck", "icon": "🚛", "fuel_unit": "Liters", "co2_factor": 2.68, "efficiency_desc": "High payload, lower top speeds on arterial roads."},
            {"id": "Two_Wheeler", "name": "Two-Wheeler / Motorbike", "icon": "🏍️", "fuel_unit": "Liters", "co2_factor": 2.31, "efficiency_desc": "Nimble in congestion, higher vulnerability to weather."}
        ]
    }

@app.get("/api/weather-presets")
def get_weather_presets():
    """Return weather condition profiles with hazard levels."""
    return {
        "conditions": [
            {"id": "Clear", "name": "Clear Sky / Normal", "icon": "☀️", "hazard_level": "Low", "description": "Optimal road grip and full visibility (8 km)."},
            {"id": "Light_Rain", "name": "Light Rain / Wet Asphalt", "icon": "🌦️", "hazard_level": "Moderate", "description": "Slight road grip reduction, +15% braking distance."},
            {"id": "Heavy_Rain", "name": "Heavy Monsoon Rain (Waterlogging Alerts)", "icon": "🌧️", "hazard_level": "High", "description": "Severe waterlogging risk on underpasses and low-lying corridors."},
            {"id": "Dense_Fog", "name": "Dense Smog / Winter Fog (<200m Vis)", "icon": "🌫️", "hazard_level": "High", "description": "Critical visibility hazard on expressways and Yamuna bridges."},
            {"id": "Extreme_Heat", "name": "Extreme Summer Heatwave (45°C+)", "icon": "🔥", "hazard_level": "Moderate", "description": "AC load elevates energy consumption by +15%."},
            {"id": "Storm", "name": "Severe Thunderstorm / Squall (60km/h Wind)", "icon": "⛈️", "hazard_level": "Critical", "description": "Debris, tree fall hazard, major expressway speed restrictions."}
        ]
    }

@app.post("/api/route", response_model=RouteResponse)
def compute_optimized_route(req: RouteRequest):
    """
    Main Multi-Objective Route Optimization Endpoint:
    Calculates Fastest Route, Eco Route, Weather-Safe Route, and Custom Balanced Route
    using ML inference & C++ Dijkstra engine.
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

    # Log query to SQLite
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
        print(f"[Warning] Failed to log route query to SQLite: {e}")

    return result

@app.get("/api/history")
def get_history(limit: int = Query(10, ge=1, le=50)):
    """Fetch recent route optimization query logs from SQLite."""
    return {"history": get_recent_history(limit=limit)}

@app.get("/api/analytics")
def get_analytics():
    """Retrieve network summary, active incidents, and model benchmarks."""
    db_stats = get_database_analytics()
    active_incidents = get_active_incidents()
    
    # Load model comparison metrics if available
    metrics_path = os.path.join(BASE_DIR, "ml", "models", "model_comparison_metrics.csv")
    metrics_data = []
    if os.path.exists(metrics_path):
        try:
            df_m = pd.read_csv(metrics_path)
            metrics_data = df_m.to_dict(orient="records")
        except Exception:
            pass

    return {
        "status": "success",
        "network_summary": db_stats,
        "active_incidents": active_incidents,
        "model_benchmarks": metrics_data
    }

@app.post("/api/simulate-incident")
def simulate_incident(req: IncidentSimulationRequest):
    """
    Live Incident Simulator:
    Trigger or clear real-time road closures or congestion to observe instant C++ rerouting.
    """
    res = add_or_toggle_incident(
        road_id=req.road_id,
        incident_type=req.incident_type,
        severity=req.severity,
        description=req.description or "Active road incident.",
        is_active=1 if req.is_active else 0
    )
    return {"status": "success", "incident": res}

@app.post("/api/clear-incidents")
def clear_incidents():
    """Clear all active incident blockades."""
    clear_all_incidents()
    return {"status": "success", "message": "All incident blockades cleared."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)
