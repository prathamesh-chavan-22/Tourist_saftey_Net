# Pydantic models for request/response validation

from pydantic import BaseModel
from typing import Optional, List

class UserRegistration(BaseModel):
    full_name: str
    email: str
    password: str
    contact_number: str
    age: int
    gender: str  # 'M' or 'F'

class TripCreation(BaseModel):
    starting_location: str
    tourist_destination_id: int
    hotels: Optional[str] = None  # JSON string of hotel list
    mode_of_travel: str  # car, train, bus, flight
    guide_email: Optional[str] = None  # Optional guide assignment by email

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
    trip_id: int
    latitude: float
    longitude: float
    
    def validate_coordinates(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")

class GuideLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    
    def validate_coordinates(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")

class TripData(BaseModel):
    id: int
    user_name: str
    blockchain_id: str
    starting_location: str
    tourist_destination_id: int
    tourist_destination_name: str
    hotels: Optional[str]
    mode_of_travel: str
    last_lat: Optional[float]
    last_lon: Optional[float]
    status: str
    is_active: bool
    created_at: str

class TripClose(BaseModel):
    trip_id: int

class MapData(BaseModel):
    trip: dict
    geofence: dict