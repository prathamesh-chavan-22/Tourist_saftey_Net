# Admin routes for the Tourist Safety Monitoring System

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from models import User, Tourist, get_db
from schemas import TouristData
from services import get_tourist_place_by_id
from auth import require_admin
from config import INDIAN_TOURIST_PLACES

router = APIRouter(prefix="/admin", tags=["admin"])

@router.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get all tourists data for dashboard"""
    result = await db.execute(select(Tourist))
    tourists = result.scalars().all()
    return [
        {
            "id": tourist.id,
            "name": tourist.name,
            "blockchain_id": tourist.blockchain_id,
            "last_lat": tourist.last_lat,
            "last_lon": tourist.last_lon,
            "status": tourist.status,
            "location_id": tourist.location_id,
            "location_name": get_tourist_place_by_id(int(str(tourist.location_id)))["name"]
        }
        for tourist in tourists
    ]

@router.get("/tourist-places")
async def get_tourist_places():
    """Get all available Indian tourist places"""
    return INDIAN_TOURIST_PLACES