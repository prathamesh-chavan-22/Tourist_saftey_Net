# Tourist routes for the Tourist Safety Monitoring System

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import json

from models import User, Trip, Incident, get_db
from schemas import LocationUpdate
from services import get_tourist_place_by_id, is_inside_geofence
from websocket_manager import ConnectionManager
from config import INDIAN_TOURIST_PLACES
from auth import get_current_active_user, get_current_active_user_flexible, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/tourist", tags=["tourist"])

# This will be injected from main app
manager: ConnectionManager

def set_connection_manager(connection_manager: ConnectionManager):
    """Set the connection manager for this router"""
    global manager
    manager = connection_manager

@router.post("/register")
async def register_tourist(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    contact_number: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Register a new tourist with both user account and tourist profile"""
    try:
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            from fastapi.templating import Jinja2Templates
            templates = Jinja2Templates(directory="templates")
            return templates.TemplateResponse("register.html", {
                "request": request,
                "error": "Email already registered"
            })
        
        # Create user account
        hashed_password = User.get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            contact_number=contact_number,
            age=age,
            gender="M",  # Default gender - can be updated later in profile
            role="tourist"
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create access token for auto-login
        access_token = create_access_token(data={"sub": new_user.email})
        
        # Create response to redirect to tourist dashboard and set login cookie
        response = RedirectResponse(url="/tourist-dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            path="/",
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        # Return to registration form with error message
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Registration failed: {str(e)}"
        })

@router.post("/update_location")
async def update_location(
    location_data: LocationUpdate, 
    current_user: User = Depends(get_current_active_user_flexible),
    db: AsyncSession = Depends(get_db)
):
    """Update tourist location and check geofence status"""
    # Validate coordinates
    try:
        location_data.validate_coordinates()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    result = await db.execute(select(Trip).filter(Trip.id == location_data.trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # SECURITY: Default-deny authorization - only allow role="tourist" and "guide" to update positions
    # All other roles are explicitly denied
    if str(current_user.role) not in ["tourist", "guide"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only tourists and guides can update location positions"
        )
    
    # Authorization: tourists can update their own trip location, guides can update trips they are assigned to
    if str(current_user.role) == "tourist":
        if int(str(trip.user_id)) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only update your own trip location"
            )
    elif str(current_user.role) == "guide":
        # Guides can update location for trips they are assigned to or their own location if they have a trip
        guide_id = trip.guide_id if trip.guide_id is not None else 0
        if int(str(guide_id)) != current_user.id and int(str(trip.user_id)) != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: You can only update location for trips assigned to you"
            )
    
    # Store trip data before session operations to avoid detachment issues
    trip_id = trip.id
    trip_user_id = trip.user_id
    # Get user name for the trip
    user_result = await db.execute(select(User).filter(User.id == trip.user_id))
    user = user_result.scalar_one_or_none()
    trip_user_name = user.full_name if user else "Unknown"
    
    # Update location
    trip.last_lat = location_data.latitude  # type: ignore
    trip.last_lon = location_data.longitude  # type: ignore
    
    # Check geofence status for trip's destination
    inside_fence = is_inside_geofence(location_data.latitude, location_data.longitude, int(str(trip.tourist_destination_id)))
    new_status = "Safe" if inside_fence else "Critical"
    
    # Log incident if status changed to Critical
    current_status = str(trip.status)
    if current_status != "Critical" and new_status == "Critical":
        incident = Incident(trip_id=trip_id, severity="Critical")
        db.add(incident)
    
    trip.status = new_status  # type: ignore
    await db.commit()
    
    # Broadcast location update via WebSocket using stored values with role-based filtering
    update_message = {
        "type": "location_update",
        "trip_id": int(str(trip_id)),
        "tourist_id": int(str(trip_user_id)),
        "name": trip_user_name,
        "latitude": location_data.latitude,
        "longitude": location_data.longitude,
        "status": new_status,
        "inside_fence": inside_fence
    }
    await manager.broadcast_location_update(int(str(trip_id)), update_message)
    
    return {"status": new_status, "inside_fence": inside_fence}

@router.get("/map/{trip_id}")
async def get_map_data(
    trip_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get initial map data for a specific trip"""
    result = await db.execute(select(Trip).filter(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check if user has permission to view this trip's data
    if str(current_user.role) == "tourist" and int(str(trip.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own trip data"
        )
    
    # Get the trip's destination location
    tourist_place = get_tourist_place_by_id(int(str(trip.tourist_destination_id)))
    
    # Get user data for the trip
    user_result = await db.execute(select(User).filter(User.id == trip.user_id))
    user = user_result.scalar_one_or_none()
    
    return {
        "trip": {
            "id": trip.id,
            "user_name": user.full_name if user else "Unknown",
            "last_lat": trip.last_lat,
            "last_lon": trip.last_lon,
            "status": trip.status,
            "tourist_destination_id": trip.tourist_destination_id,
            "blockchain_id": trip.blockchain_id,
            "starting_location": trip.starting_location,
            "hotels": trip.hotels,
            "mode_of_travel": trip.mode_of_travel
        },
        "geofence": {
            "center_lat": tourist_place["lat"],
            "center_lon": tourist_place["lon"],
            "radius": tourist_place["radius"],
            "name": tourist_place["name"]
        }
    }