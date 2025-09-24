# Tourist routes for the Tourist Safety Monitoring System

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User, Trip, Incident, get_db
from schemas import LocationUpdate
from services import get_tourist_place_by_id, is_inside_geofence
from websocket_manager import ConnectionManager
from config import INDIAN_TOURIST_PLACES
from auth import get_current_active_user, get_current_active_user_flexible

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
    email: str = Form(...),
    password: str = Form(...),
    location_id: int = Form(...),
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
                "error": "Email already registered",
                "tourist_places": INDIAN_TOURIST_PLACES
            })
        
        # Create user account (TODO: This should be updated to use new UserRegistration schema with contact_number, age, gender)
        hashed_password = User.get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            contact_number="+000000000",  # Temporary placeholder - need to update registration form
            age=25,  # Temporary placeholder - need to update registration form  
            gender="M",  # Temporary placeholder - need to update registration form
            role="tourist"
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # TODO: Update to new trip-based flow - should redirect to trip creation instead of auto-creating trip
        # Create initial trip profile for backward compatibility
        blockchain_id = Trip.generate_blockchain_id(name, get_tourist_place_by_id(location_id)["name"])
        tourist_place = get_tourist_place_by_id(location_id)
        
        new_trip = Trip(
            user_id=new_user.id,
            blockchain_id=blockchain_id,
            starting_location="Not specified",  # Placeholder - need trip creation form
            tourist_destination_id=location_id,
            hotels=None,
            mode_of_travel="Not specified",  # Placeholder - need trip creation form
            last_lat=tourist_place["lat"],
            last_lon=tourist_place["lon"]
        )
        
        db.add(new_trip)
        await db.commit()
        await db.refresh(new_trip)
        
        # Redirect to login page with success message
        return RedirectResponse(url="/login?message=Registration successful! Please login.", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        # Return to registration form with error message
        from fastapi.templating import Jinja2Templates
        templates = Jinja2Templates(directory="templates")
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Registration failed: {str(e)}",
            "tourist_places": INDIAN_TOURIST_PLACES
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
    
    # SECURITY: Default-deny authorization - only allow role="tourist" to update their own positions
    # All other roles are explicitly denied
    if str(current_user.role) != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only tourists can update location positions"
        )
    
    # Tourist users can only update their own trip location
    if int(str(trip.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only update your own trip location"
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