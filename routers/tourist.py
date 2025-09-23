# Tourist routes for the Tourist Safety Monitoring System

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models import User, Tourist, Incident, get_db
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
        
        # Create user account
        hashed_password = User.get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            role="tourist"
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create tourist profile
        blockchain_id = Tourist.generate_blockchain_id(name)
        tourist_place = get_tourist_place_by_id(location_id)
        
        new_tourist = Tourist(
            user_id=new_user.id,
            name=name,
            blockchain_id=blockchain_id,
            location_id=location_id,
            last_lat=tourist_place["lat"],
            last_lon=tourist_place["lon"]
        )
        
        db.add(new_tourist)
        await db.commit()
        await db.refresh(new_tourist)
        
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
    
    result = await db.execute(select(Tourist).filter(Tourist.id == location_data.tourist_id))
    tourist = result.scalar_one_or_none()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")
    
    # SECURITY: Default-deny authorization - only allow role="tourist" to update their own positions
    # All other roles are explicitly denied
    if str(current_user.role) != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only tourists can update location positions"
        )
    
    # Tourist users can only update their own location
    if int(str(tourist.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only update your own location"
        )
    
    # Store tourist data before session operations to avoid detachment issues
    tourist_id = tourist.id
    tourist_name = tourist.name
    
    # Update location
    tourist.last_lat = location_data.latitude  # type: ignore
    tourist.last_lon = location_data.longitude  # type: ignore
    
    # Check geofence status for tourist's assigned location
    inside_fence = is_inside_geofence(location_data.latitude, location_data.longitude, int(str(tourist.location_id)))
    new_status = "Safe" if inside_fence else "Critical"
    
    # Log incident if status changed to Critical
    current_status = str(tourist.status)
    if current_status != "Critical" and new_status == "Critical":
        incident = Incident(tourist_id=tourist_id, severity="Critical")
        db.add(incident)
    
    tourist.status = new_status  # type: ignore
    await db.commit()
    
    # Broadcast location update via WebSocket using stored values with role-based filtering
    update_message = {
        "type": "location_update",
        "tourist_id": tourist_id,
        "name": tourist_name,
        "latitude": location_data.latitude,
        "longitude": location_data.longitude,
        "status": new_status,
        "inside_fence": inside_fence
    }
    await manager.broadcast_location_update(tourist_id, update_message)
    
    return {"status": new_status, "inside_fence": inside_fence}

@router.get("/map/{tourist_id}")
async def get_map_data(
    tourist_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get initial map data for a specific tourist"""
    result = await db.execute(select(Tourist).filter(Tourist.id == tourist_id))
    tourist = result.scalar_one_or_none()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")
    
    # Check if user has permission to view this tourist's data
    if str(current_user.role) == "tourist" and int(str(tourist.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own tourist data"
        )
    
    # Get the tourist's assigned location
    tourist_place = get_tourist_place_by_id(int(str(tourist.location_id)))
    
    return {
        "tourist": {
            "id": tourist.id,
            "name": tourist.name,
            "last_lat": tourist.last_lat,
            "last_lon": tourist.last_lon,
            "status": tourist.status,
            "location_id": tourist.location_id
        },
        "geofence": {
            "center_lat": tourist_place["lat"],
            "center_lon": tourist_place["lon"],
            "radius": tourist_place["radius"],
            "name": tourist_place["name"]
        }
    }