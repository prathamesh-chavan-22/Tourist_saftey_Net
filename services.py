# Business logic services for the Tourist Safety Monitoring System

import math
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Trip, AsyncSessionLocal
from config import INDIAN_TOURIST_PLACES

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance between two points in meters using Haversine formula"""
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    a = (math.sin(delta_lat / 2) ** 2 +
         math.cos(lat1_rad) * math.cos(lat2_rad) *
         math.sin(delta_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    return R * c

def is_inside_geofence(lat: float, lon: float, location_id: int = 1) -> bool:
    """Check if coordinates are inside the geofence for a specific tourist location"""
    # Find the tourist place by location_id
    tourist_place = next((place for place in INDIAN_TOURIST_PLACES if place["id"] == location_id), INDIAN_TOURIST_PLACES[0])
    
    distance = calculate_distance(
        lat, lon, 
        tourist_place["lat"], tourist_place["lon"]
    )
    return distance <= tourist_place["radius"]

def get_tourist_place_by_id(location_id: int):
    """Get tourist place details by ID"""
    return next((place for place in INDIAN_TOURIST_PLACES if place["id"] == location_id), INDIAN_TOURIST_PLACES[0])

async def create_demo_users():
    """Create demo admin and tourist users"""
    async with AsyncSessionLocal() as db:
        try:
            # Check if demo admin exists
            result = await db.execute(select(User).filter(User.email == "admin@demo.com"))
            admin_exists = result.scalar_one_or_none()
            if not admin_exists:
                admin_user = User(
                    email="admin@demo.com",
                    hashed_password=User.get_password_hash("admin123"),
                    full_name="Admin User",
                    contact_number="+1234567890",
                    age=30,
                    gender="M",
                    role="admin"
                )
                db.add(admin_user)
                
            # Check if demo tourist exists  
            result = await db.execute(select(User).filter(User.email == "tourist@demo.com"))
            tourist_exists = result.scalar_one_or_none()
            if not tourist_exists:
                tourist_user = User(
                    email="tourist@demo.com",
                    hashed_password=User.get_password_hash("tourist123"),
                    full_name="Demo Tourist",
                    contact_number="+1234567891",
                    age=25,
                    gender="F",
                    role="tourist"
                )
                db.add(tourist_user)
                # Note: Trip will be created when user starts a trip, not automatically
            
            await db.commit()
        except Exception as e:
            print(f"Error creating demo users: {e}")
            await db.rollback()