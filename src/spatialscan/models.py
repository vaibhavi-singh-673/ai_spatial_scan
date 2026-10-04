from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Literal, Optional

class CI(BaseModel):
    estimate_m: float
    low_m: float
    high_m: float
    confidence: float = 0.95
    method: str

class Measurement(BaseModel):
    id: str
    kind: Literal["wall_length","opening_width","ceiling_height","floor_area","damage_extent"]
    room_id: str
    value: float
    unit: str
    interval: CI

class Opening(BaseModel):
    id: str
    room_id: str
    type: str
    width: Measurement
    detected: bool = True

class DamageRegion(BaseModel):
    id: str
    room_id: str
    surface: str
    damage_class: str
    extent_m2: Optional[Measurement] = None
    polygon_xy_m: list[list[float]] = Field(default_factory=list)
    confidence: float = 0.0

class ScopeItem(BaseModel):
    id: str
    surface_id: str
    action: str
    quantity: float
    unit: str
    confidence: float

class Room(BaseModel):
    id: str
    name: str
    polygon_xy_m: list[list[float]]
    floor_area_m2: Measurement
    ceiling_height_m: Measurement
    walls: list[Measurement] = Field(default_factory=list)
    openings: list[Opening] = Field(default_factory=list)

class Plan(BaseModel):
    rooms: list[Room]
    adjacency: list[dict]
    stitched_polygon_xy_m: list[list[float]]
    drift: dict

class CaptureResult(BaseModel):
    schema_version: str = "1.0"
    capture_id: str
    tier: Literal["photos","video","lidar"]
    device: dict
    rooms: list[Room]
    plan: Plan
    damage: list[DamageRegion]
    scope: list[ScopeItem]
    diagnostics: dict
