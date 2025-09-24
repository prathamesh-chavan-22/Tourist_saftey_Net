# Admin routes for the Tourist Safety Monitoring System

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from models import User, Trip, GuideLocation, get_db
from schemas import TripData
from services import get_tourist_place_by_id
from auth import require_admin
from config import INDIAN_TOURIST_PLACES
from datetime import datetime, timedelta

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all active trips and guide locations data for dashboard"""
    # Get active tourist trips
    result = await db.execute(select(Trip).filter(Trip.is_active == True))
    trips = result.scalars().all()
    trip_data = []
    for trip in trips:
        # Get user data for the trip
        user_result = await db.execute(select(User).filter(User.id == trip.user_id))
        user = user_result.scalar_one_or_none()
        trip_data.append({
            "id": trip.id,
            "user_name": user.full_name if user else "Unknown",
            "blockchain_id": trip.blockchain_id,
            "starting_location": trip.starting_location,
            "last_lat": trip.last_lat,
            "last_lon": trip.last_lon,
            "status": trip.status,
            "tourist_destination_id": trip.tourist_destination_id,
            "tourist_destination_name": get_tourist_place_by_id(int(str(trip.tourist_destination_id)))["name"],
            "hotels": trip.hotels,
            "mode_of_travel": trip.mode_of_travel,
            "is_active": trip.is_active
        })
    
    # Get active guide locations (updated within last 10 minutes)
    ten_minutes_ago = datetime.utcnow() - timedelta(minutes=10)
    guide_result = await db.execute(
        select(GuideLocation, User)
        .join(User, GuideLocation.guide_id == User.id)
        .filter(GuideLocation.updated_at > ten_minutes_ago)
    )
    guide_locations = guide_result.all()
    
    guide_data = []
    for guide_location, guide_user in guide_locations:
        # Count assigned tourists for this guide
        assigned_trips_result = await db.execute(
            select(Trip).filter(Trip.guide_id == guide_user.id, Trip.is_active == True)
        )
        assigned_count = len(assigned_trips_result.scalars().all())
        
        guide_data.append({
            "id": guide_user.id,
            "guide_name": guide_user.full_name,
            "guide_email": guide_user.email,
            "latitude": guide_location.latitude,
            "longitude": guide_location.longitude,
            "updated_at": guide_location.updated_at.isoformat(),
            "assigned_tourist_count": assigned_count,
            "status": "active"
        })
    
    return {
        "tourists": trip_data,
        "guides": guide_data,
        "total_tourists": len(trip_data),
        "total_guides": len(guide_data)
    }

@router.get("/tourist-places")
async def get_tourist_places():
    """Get all available Indian tourist places"""
    return INDIAN_TOURIST_PLACES