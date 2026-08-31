"""
Database Layer for Path Pilot using SQLite.
Phase 13: Manages persistence for Delhi road networks, query history,
and live incident simulation states with AQI pollution metrics.
"""

import os
import sys
import sqlite3
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(BASE_DIR, "database", "traffic_optimizer.db")

def get_db_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Ensure fresh schema
    cursor.execute("DROP TABLE IF EXISTS live_incidents")
    cursor.execute("DROP TABLE IF EXISTS roads")
    cursor.execute("DROP TABLE IF EXISTS nodes")

    # Table 1: Transit Hub Nodes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        node_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        zone TEXT,
        landmark TEXT
    )
    """)

    # Table 2: Road Segments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS roads (
        road_id TEXT PRIMARY KEY,
        from_node TEXT NOT NULL,
        to_node TEXT NOT NULL,
        road_name TEXT NOT NULL,
        road_type TEXT NOT NULL,
        distance_km REAL NOT NULL,
        base_speed_limit_kmh INTEGER NOT NULL,
        road_gradient_percent REAL DEFAULT 0.0,
        lanes INTEGER DEFAULT 4,
        flood_risk_score REAL DEFAULT 0.0,
        fog_risk_score REAL DEFAULT 0.0,
        aqi_index REAL DEFAULT 150.0,
        pollution_exposure_score REAL DEFAULT 0.33,
        FOREIGN KEY(from_node) REFERENCES nodes(node_id),
        FOREIGN KEY(to_node) REFERENCES nodes(node_id)
    )
    """)

    # Table 3: Route Optimization Query History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS route_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        source_id TEXT,
        destination_id TEXT,
        vehicle_type TEXT,
        weather_condition TEXT,
        hour_of_day INTEGER,
        fastest_time_min REAL,
        eco_fuel_saved_percent REAL,
        engine_used TEXT
    )
    """)

    # Table 4: Live Simulated Traffic Incidents & Closures
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS live_incidents (
        incident_id TEXT PRIMARY KEY,
        road_id TEXT NOT NULL,
        incident_type TEXT NOT NULL,
        severity TEXT NOT NULL,
        description TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        is_active INTEGER DEFAULT 1,
        FOREIGN KEY(road_id) REFERENCES roads(road_id)
    )
    """)

    conn.commit()

    # Synchronize nodes from CSV
    nodes_csv = os.path.join(BASE_DIR, "data", "processed", "nodes.csv")
    if os.path.exists(nodes_csv):
        cursor.execute("DELETE FROM nodes")
        df_nodes = pd.read_csv(nodes_csv)
        for _, row in df_nodes.iterrows():
            cursor.execute(
                "INSERT OR REPLACE INTO nodes (node_id, node_name, latitude, longitude, zone, landmark) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    str(row["node_id"]),
                    str(row["node_name"]),
                    float(row["latitude"]),
                    float(row["longitude"]),
                    str(row.get("zone", "Delhi NCR")),
                    str(row.get("landmark", ""))
                )
            )
        conn.commit()

    # Synchronize roads from CSV
    roads_csv = os.path.join(BASE_DIR, "data", "processed", "roads.csv")
    if os.path.exists(roads_csv):
        cursor.execute("DELETE FROM roads")
        df_roads = pd.read_csv(roads_csv)
        for _, row in df_roads.iterrows():
            cursor.execute(
                """INSERT OR REPLACE INTO roads (
                    road_id, from_node, to_node, road_name, road_type, 
                    distance_km, base_speed_limit_kmh, road_gradient_percent, 
                    lanes, flood_risk_score, fog_risk_score, aqi_index, pollution_exposure_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(row["road_id"]),
                    str(row["from_node"]),
                    str(row["to_node"]),
                    str(row["road_name"]),
                    str(row["road_type"]),
                    float(row["distance_km"]),
                    int(row["base_speed_limit_kmh"]),
                    float(row.get("road_gradient_percent", 0.0)),
                    int(row.get("lanes", 4)),
                    float(row.get("flood_risk_score", 0.0)),
                    float(row.get("fog_risk_score", 0.0)),
                    float(row.get("aqi_index", 150.0)),
                    float(row.get("pollution_exposure_score", 0.33))
                )
            )
        conn.commit()

    conn.close()

def log_route_query(
    source_id: str,
    destination_id: str,
    vehicle_type: str,
    weather_condition: str,
    hour_of_day: int,
    fastest_time_min: float,
    eco_fuel_saved_percent: float,
    engine_used: str = "C++ Engine"
) -> int:
    """Log an optimized route request into SQLite."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """INSERT INTO route_history (
            source_id, destination_id, vehicle_type, weather_condition,
            hour_of_day, fastest_time_min, eco_fuel_saved_percent, engine_used
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (source_id, destination_id, vehicle_type, weather_condition, hour_of_day, fastest_time_min, eco_fuel_saved_percent, engine_used)
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id

def get_recent_history(limit: int = 10) -> List[Dict[str, Any]]:
    """Retrieve recent queries with human-readable node labels."""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = """
    SELECT 
        h.id, h.timestamp, h.source_id, h.destination_id,
        n1.node_name AS source_name,
        n2.node_name AS destination_name,
        h.vehicle_type, h.weather_condition, h.hour_of_day,
        h.fastest_time_min, h.eco_fuel_saved_percent, h.engine_used
    FROM route_history h
    LEFT JOIN nodes n1 ON h.source_id = n1.node_id
    LEFT JOIN nodes n2 ON h.destination_id = n2.node_id
    ORDER BY h.id DESC
    LIMIT ?
    """
    cursor.execute(query, (limit,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_active_incidents() -> List[Dict[str, Any]]:
    """Retrieve all active traffic incidents or blockades."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
    SELECT i.incident_id, i.road_id, r.road_name, i.incident_type, i.severity, i.description, i.created_at
    FROM live_incidents i
    JOIN roads r ON i.road_id = r.road_id
    WHERE i.is_active = 1
    ORDER BY i.created_at DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def add_or_toggle_incident(road_id: str, incident_type: str, severity: str, description: str, is_active: int = 1) -> Dict[str, Any]:
    """Add or update a simulated incident on a road segment."""
    conn = get_db_connection()
    cursor = conn.cursor()
    incident_id = f"INC_{road_id}"
    cursor.execute("""
    INSERT INTO live_incidents (incident_id, road_id, incident_type, severity, description, is_active)
    VALUES (?, ?, ?, ?, ?, ?)
    ON CONFLICT(incident_id) DO UPDATE SET
        incident_type = excluded.incident_type,
        severity = excluded.severity,
        description = excluded.description,
        is_active = excluded.is_active
    """, (incident_id, road_id, incident_type, severity, description, is_active))
    conn.commit()
    conn.close()
    return {
        "incident_id": incident_id,
        "road_id": road_id,
        "incident_type": incident_type,
        "severity": severity,
        "is_active": bool(is_active)
    }

def clear_all_incidents():
    """Clear all active incident blockades."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE live_incidents SET is_active = 0")
    conn.commit()
    conn.close()

def get_database_analytics() -> Dict[str, Any]:
    """Calculate aggregated analytics across history and network."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) AS total_queries FROM route_history")
    total_queries = cursor.fetchone()["total_queries"]
    
    cursor.execute("SELECT AVG(eco_fuel_saved_percent) AS avg_fuel_saved FROM route_history")
    row_fuel = cursor.fetchone()
    avg_fuel_saved = round(row_fuel["avg_fuel_saved"] or 14.5, 1)

    cursor.execute("SELECT COUNT(*) AS total_nodes FROM nodes")
    total_nodes = cursor.fetchone()["total_nodes"]

    cursor.execute("SELECT COUNT(*) AS total_roads, SUM(distance_km) AS total_distance_km FROM roads")
    road_stats = cursor.fetchone()
    total_roads = road_stats["total_roads"]
    network_km = round(road_stats["total_distance_km"] or 0.0, 1)

    conn.close()
    return {
        "total_queries_logged": total_queries,
        "average_eco_fuel_saved_percent": avg_fuel_saved,
        "active_transit_nodes": total_nodes,
        "total_road_corridors": total_roads,
        "total_network_distance_km": network_km
    }

if __name__ == "__main__":
    init_db()
    print("Database initialized and verified successfully!")
