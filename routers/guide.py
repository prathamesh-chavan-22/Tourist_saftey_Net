# Guide dashboard routes for the Tourist Safety Monitoring System

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Trip, get_db
from auth import require_guide
from services import get_tourist_place_by_id

router = APIRouter(prefix="/guide", tags=["guide"])

@router.get("/dashboard")
async def get_guide_dashboard_data(
    current_user: User = Depends(require_guide),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard data for the current guide - only shows tourists assigned to this guide"""
    # Get all active trips where this guide is assigned
    result = await db.execute(
        select(Trip).filter(Trip.guide_id == current_user.id, Trip.is_active == True)
    )
    trips = result.scalars().all()
    
    trip_data = []
    for trip in trips:
        # Get user data for the trip
        user_result = await db.execute(select(User).filter(User.id == trip.user_id))
        user = user_result.scalar_one_or_none()
        
        if user:
            tourist_place = get_tourist_place_by_id(int(str(trip.tourist_destination_id)))
            trip_data.append({
                "id": trip.id,
                "user_name": user.full_name,
                "user_email": user.email,
                "user_contact": user.contact_number,
                "user_age": user.age,
                "user_gender": user.gender,
                "blockchain_id": trip.blockchain_id,
                "starting_location": trip.starting_location,
                "last_lat": trip.last_lat,
                "last_lon": trip.last_lon,
                "status": trip.status,
                "tourist_destination_id": trip.tourist_destination_id,
                "tourist_destination_name": tourist_place["name"],
                "hotels": trip.hotels,
                "mode_of_travel": trip.mode_of_travel,
                "is_active": trip.is_active,
                "created_at": trip.created_at.isoformat() if trip.created_at is not None else None
            })
    
    return {
        "guide_name": current_user.full_name,
        "guide_email": current_user.email,
        "assigned_tourists": trip_data,
        "total_assigned": len(trip_data)
    }