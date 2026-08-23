"""
Pydantic Schemas for Smart Traffic Route Optimizer API.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class RouteRequest(BaseModel):
    source_id: str = Field(..., example="NODE_CP", description="Source Node ID (e.g. NODE_CP)")
    destination_id: str = Field(..., example="NODE_CYBER", description="Destination Node ID (e.g. NODE_CYBER)")
    hour_of_day: int = Field(9, ge=0, le=23, description="Hour of the day (0-23)")
    day_of_week: int = Field(1, ge=0, le=6, description="Day of week (0=Mon, 6=Sun)")
    weather_condition: str = Field("Clear", description="Clear, Light_Rain, Heavy_Rain, Dense_Fog, Extreme_Heat, Storm")
    vehicle_type: str = Field("Petrol_Sedan", description="Petrol_Sedan, Diesel_SUV, Electric_Vehicle, Heavy_Truck, Two_Wheeler")
    custom_weights: Optional[Dict[str, float]] = Field(None, description="Custom weight multipliers: {'time': 0.5, 'fuel': 0.3, 'weather': 0.2}")

class NodeInfo(BaseModel):
    node_id: str
    node_name: str
    latitude: float
    longitude: float
    zone: str

class RoadInfo(BaseModel):
    road_id: str
    from_node: str
    to_node: str
    road_name: str
    road_type: str
    distance_km: float
    base_speed_limit_kmh: int
    lanes: int
    flood_risk_score: float
    fog_risk_score: float

class RouteStep(BaseModel):
    road_id: str
    road_name: str
    road_type: str
    from_node: str
    from_name: str
    to_node: str
    to_name: str
    distance_km: float
    predicted_time_min: float
    predicted_fuel_units: float
    speed_limit_kmh: int
    traffic_density_index: float

class PathCoordinate(BaseModel):
    node_id: Optional[str] = None
    name: Optional[str] = None
    lat: float
    lng: float

class RouteOption(BaseModel):
    found: bool
    mode_title: str
    mode_badge: str
    total_distance_km: float
    total_time_min: float
    total_fuel_units: float
    fuel_unit_name: str
    total_co2_kg: float
    total_cost_inr: float
    weather_safety_score: int
    weather_advisories: List[str]
    node_sequence: List[str]
    edge_sequence: List[str]
    path_coordinates: List[PathCoordinate]
    steps: List[RouteStep]
    engine_used: Optional[str] = None

class RouteResponse(BaseModel):
    status: str
    source: Dict[str, Any]
    destination: Dict[str, Any]
    context: Dict[str, Any]
    routes: Dict[str, RouteOption]
