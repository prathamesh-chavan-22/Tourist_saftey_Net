# Pydantic models for request/response validation

from pydantic import BaseModel
from typing import Optional

class TouristRegistration(BaseModel):
    name: str
    email: str
    password: str
    location_id: int = 1  # Default to Taj Mahal

class UserLogin(BaseModel):
    email: str
    password: str

class UserCreate(BaseModel):
    email: str
    password: str
    full_name: str
    role: str = "tourist"  # admin or tourist

class Token(BaseModel):
    access_token: str
    token_type: str

class LocationUpdate(BaseModel):
    tourist_id: int
    latitude: float
    longitude: float
    
    def validate_coordinates(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")

class TouristData(BaseModel):
    id: int
    name: str
    blockchain_id: str
    last_lat: float
    last_lon: float
    status: str
    location_id: int
    location_name: str

class MapData(BaseModel):
    tourist: dict
    geofence: dict