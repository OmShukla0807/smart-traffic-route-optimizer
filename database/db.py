"""
Database layer using SQLite.
Phase 13: Stores the Delhi road network and logs route optimization queries/history.
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

    # Table: Nodes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nodes (
        node_id TEXT PRIMARY KEY,
        node_name TEXT NOT NULL,
        latitude REAL NOT NULL,
        longitude REAL NOT NULL,
        zone TEXT
    )
    """)

    # Table: Roads
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
        FOREIGN KEY(from_node) REFERENCES nodes(node_id),
        FOREIGN KEY(to_node) REFERENCES nodes(node_id)
    )
    """)

    # Table: Route Query History
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

    conn.commit()

    # Populate/Update nodes from CSV
    nodes_csv = os.path.join(BASE_DIR, "data", "processed", "nodes.csv")
    if os.path.exists(nodes_csv):
        cursor.execute("DELETE FROM nodes")
        df_nodes = pd.read_csv(nodes_csv)
        for _, row in df_nodes.iterrows():
            cursor.execute(
                "INSERT OR REPLACE INTO nodes (node_id, node_name, latitude, longitude, zone) VALUES (?, ?, ?, ?, ?)",
                (row["node_id"], row["node_name"], row["latitude"], row["longitude"], row["zone"])
            )
        conn.commit()
        print(f"Populated {len(df_nodes)} nodes into SQLite database.")

    # Populate/Update roads from CSV
    roads_csv = os.path.join(BASE_DIR, "data", "processed", "roads.csv")
    if os.path.exists(roads_csv):
        cursor.execute("DELETE FROM roads")
        df_roads = pd.read_csv(roads_csv)
        for _, row in df_roads.iterrows():
            cursor.execute(
                """INSERT OR REPLACE INTO roads (
                    road_id, from_node, to_node, road_name, road_type, 
                    distance_km, base_speed_limit_kmh, road_gradient_percent, 
                    lanes, flood_risk_score, fog_risk_score
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    row["road_id"], row["from_node"], row["to_node"], row["road_name"], row["road_type"],
                    row["distance_km"], row["base_speed_limit_kmh"], row["road_gradient_percent"],
                    row["lanes"], row["flood_risk_score"], row["fog_risk_score"]
                )
            )
        conn.commit()
        print(f"Populated {len(df_roads)} roads into SQLite database.")

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
):
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
    conn.close()

def get_recent_history(limit: int = 15) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM route_history ORDER BY id DESC LIMIT ?", (limit,))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully at:", DB_PATH)
