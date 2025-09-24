from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from models import Trip, User, get_db, create_tables
from services import create_demo_users, get_tourist_place_by_id
from websocket_manager import ConnectionManager
from config import INDIAN_TOURIST_PLACES, GEOFENCE_CENTER, get_allowed_origins
from auth import verify_token, get_user_from_cookie_token, get_current_active_user, get_current_active_user_flexible
from schemas import LocationUpdate

# Import routers
from routers.auth import router as auth_router
from routers.admin import router as admin_router  
from routers.tourist import router as tourist_router

app = FastAPI(title="Smart Tourist Safety Monitoring System")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# WebSocket connection manager
manager = ConnectionManager()

# Set connection manager for tourist router
from routers.tourist import set_connection_manager
set_connection_manager(manager)

# Include routers
app.include_router(auth_router)
app.include_router(admin_router)  
app.include_router(tourist_router)

# Legacy routes that need to be maintained for backwards compatibility
@app.get("/dashboard")
async def get_dashboard_data_legacy(
    db: AsyncSession = Depends(get_db)
):
    """Legacy dashboard endpoint - returns active trip data for backwards compatibility"""
    result = await db.execute(select(Trip).filter(Trip.is_active == True))
    trips = result.scalars().all()
    trip_data = []
    for trip in trips:
        user_result = await db.execute(select(User).filter(User.id == trip.user_id))
        user = user_result.scalar_one_or_none()
        trip_data.append({
            "id": trip.id,
            "user_name": user.full_name if user else "Unknown",
            "blockchain_id": trip.blockchain_id,
            "last_lat": trip.last_lat,
            "last_lon": trip.last_lon,
            "status": trip.status,
            "tourist_destination_id": trip.tourist_destination_id,
            "tourist_destination_name": get_tourist_place_by_id(int(str(trip.tourist_destination_id)))["name"]
        })
    return trip_data

@app.get("/tourist-places")
async def get_tourist_places_legacy():
    """Legacy tourist places endpoint - redirect to admin router"""
    return INDIAN_TOURIST_PLACES

@app.post("/update_location")
async def update_location_legacy(
    location_data: LocationUpdate,
    current_user: User = Depends(get_current_active_user_flexible),
    db: AsyncSession = Depends(get_db)
):
    """Legacy location update endpoint - redirect to tourist router"""
    from routers.tourist import update_location
    return await update_location(location_data, current_user, db)

@app.get("/map/{tourist_id}")
async def get_map_data_legacy(
    tourist_id: int,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Legacy map data endpoint - redirect to tourist router"""
    from routers.tourist import get_map_data
    return await get_map_data(tourist_id, current_user, db)

@app.post("/register")
async def register_tourist_legacy(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    location_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Legacy registration endpoint - redirect to tourist router"""
    from routers.tourist import register_tourist
    return await register_tourist(request, name, email, password, location_id, db)

@app.get("/me")
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get current user information"""
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "is_active": current_user.is_active
    }

@app.websocket("/ws/location")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """WebSocket endpoint for live location updates with authentication"""
    try:
        # Origin validation to prevent Cross-Site WebSocket Hijacking (CSWSH)
        origin = websocket.headers.get("origin")
        host = websocket.headers.get('host', 'localhost:5000')
        allowed_origins = get_allowed_origins(host)
        
        if origin and origin not in allowed_origins:
            await websocket.close(code=1008, reason="Origin not allowed")
            return
        
        # Authenticate user using HttpOnly cookie
        user = None
        access_token = websocket.cookies.get("access_token")
        
        if access_token:
            try:
                payload = verify_token(access_token)
                email = payload.get("sub")
                if email:
                    result = await db.execute(select(User).filter(User.email == email))
                    user = result.scalar_one_or_none()
            except HTTPException:
                pass
        
        if not user:
            await websocket.close(code=1008, reason="Authentication required")
            return
        
        # Get active trip data if user is a tourist
        trip = None
        if str(user.role) == "tourist":
            result = await db.execute(select(Trip).filter(Trip.user_id == user.id, Trip.is_active == True))
            trip = result.scalar_one_or_none()
        
        # Connect with authenticated user
        await manager.connect(websocket, user, trip)
        
        try:
            while True:
                # Keep connection alive - clients don't need to send data
                data = await websocket.receive_text()
                # Optional: Handle any client messages here if needed
        except WebSocketDisconnect:
            manager.disconnect(websocket)
    except Exception as e:
        # Log error and close connection
        print(f"WebSocket error: {e}")
        try:
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass

# Authentication Web Pages
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None, message: Optional[str] = None):
    """Login page for both admin and tourist users"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error,
        "message": message
    })

@app.get("/register-form", response_class=HTMLResponse)
async def register_page(request: Request, error: Optional[str] = None):
    """Registration page for tourists"""
    return templates.TemplateResponse("register.html", {
        "request": request,
        "error": error,
        "tourist_places": INDIAN_TOURIST_PLACES
    })

@app.get("/tourist-dashboard", response_class=HTMLResponse)
async def tourist_dashboard_page(request: Request, message: Optional[str] = None, error: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Tourist dashboard page - shows user info, trips, and management options"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if str(current_user.role) != "tourist":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Get all trips for this user (both active and past)
    all_trips_result = await db.execute(select(Trip).filter(Trip.user_id == current_user.id).order_by(Trip.created_at.desc()))
    all_trips = all_trips_result.scalars().all()
    
    # Get active trip data for this user
    active_trip = None
    past_trips = []
    
    for trip in all_trips:
        tourist_place = get_tourist_place_by_id(int(str(trip.tourist_destination_id)))
        trip_data = {
            "id": trip.id,
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
            "created_at": trip.created_at,
            "closed_at": trip.closed_at
        }
        
        if bool(trip.is_active):
            active_trip = trip_data
        else:
            past_trips.append(trip_data)
    
    # Set up geofence data for active trip, or default to first tourist place
    geofence_data = {"center_lat": 28.6129, "center_lon": 77.2295, "radius": 400, "name": "Default Location"}
    if active_trip:
        tourist_place = get_tourist_place_by_id(int(str(active_trip["tourist_destination_id"])))
        geofence_data = {
            "center_lat": tourist_place["lat"],
            "center_lon": tourist_place["lon"],
            "radius": tourist_place["radius"],
            "name": tourist_place["name"]
        }
    
    return templates.TemplateResponse("tourist_dashboard.html", {
        "request": request,
        "user": current_user,
        "active_trip": active_trip,
        "past_trips": past_trips,
        "tourist_places": INDIAN_TOURIST_PLACES,
        "geofence": geofence_data,
        "message": message,
        "error": error
    })

@app.get("/create-trip", response_class=HTMLResponse)
async def create_trip_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Create trip page for tourists"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if str(current_user.role) != "tourist":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Check if user already has an active trip
    result = await db.execute(select(Trip).filter(Trip.user_id == current_user.id, Trip.is_active == True))
    active_trip = result.scalar_one_or_none()
    if active_trip:
        return RedirectResponse(url="/tourist-dashboard?message=You already have an active trip", status_code=status.HTTP_302_FOUND)
    
    return templates.TemplateResponse("create_trip.html", {
        "request": request,
        "user": current_user,
        "tourist_places": INDIAN_TOURIST_PLACES
    })

@app.post("/create-trip")
async def create_trip_submit(
    request: Request,
    starting_location: str = Form(...),
    tourist_destination_id: int = Form(...),
    mode_of_travel: str = Form(...),
    hotels: str = Form(None),
    db: AsyncSession = Depends(get_db)
):
    """Handle trip creation form submission"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if str(current_user.role) != "tourist":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        # Check if user already has an active trip
        result = await db.execute(select(Trip).filter(Trip.user_id == current_user.id, Trip.is_active == True))
        active_trip = result.scalar_one_or_none()
        if active_trip:
            return RedirectResponse(url="/tourist-dashboard?error=You already have an active trip", status_code=status.HTTP_302_FOUND)
        
        # Create the new trip
        tourist_place = get_tourist_place_by_id(tourist_destination_id)
        blockchain_id = Trip.generate_blockchain_id(str(current_user.full_name), tourist_place["name"])
        
        new_trip = Trip(
            user_id=current_user.id,
            blockchain_id=blockchain_id,
            starting_location=starting_location,
            tourist_destination_id=tourist_destination_id,
            hotels=hotels,
            mode_of_travel=mode_of_travel,
            last_lat=tourist_place["lat"],
            last_lon=tourist_place["lon"]
        )
        
        db.add(new_trip)
        await db.commit()
        await db.refresh(new_trip)
        
        # Notify admin dashboard about tourist becoming active
        tourist_place = get_tourist_place_by_id(tourist_destination_id)
        trip_start_message = {
            "type": "tourist_status_change",
            "action": "trip_started",
            "tourist_id": current_user.id,
            "trip_id": new_trip.id,
            "name": current_user.full_name,
            "email": current_user.email,
            "contact_number": current_user.contact_number,
            "age": current_user.age,
            "gender": current_user.gender,
            "blockchain_id": blockchain_id,
            "starting_location": starting_location,
            "last_lat": tourist_place["lat"],
            "last_lon": tourist_place["lon"],
            "status": "Safe",
            "tourist_destination_id": tourist_destination_id,
            "location_name": tourist_place["name"],
            "hotels": hotels,
            "mode_of_travel": mode_of_travel
        }
        await manager.broadcast_to_admins(json.dumps(trip_start_message))
        
        # Redirect to dashboard with success message
        return RedirectResponse(url="/tourist-dashboard?message=Trip created successfully!", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        # Handle any errors during trip creation
        return templates.TemplateResponse("create_trip.html", {
            "request": request,
            "user": current_user,
            "tourist_places": INDIAN_TOURIST_PLACES,
            "error": f"Error creating trip: {str(e)}"
        })

@app.post("/close-trip")
async def close_trip(
    request: Request,
    trip_id: int = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Handle trip closure form submission"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if str(current_user.role) != "tourist":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    try:
        # Get the trip to close
        result = await db.execute(
            select(Trip).filter(
                Trip.id == trip_id, 
                Trip.user_id == current_user.id, 
                Trip.is_active == True
            )
        )
        trip = result.scalar_one_or_none()
        
        if not trip:
            return RedirectResponse(url="/tourist-dashboard?error=Trip not found or already closed", status_code=status.HTTP_302_FOUND)
        
        # Close the trip using SQLAlchemy update
        from datetime import datetime
        from sqlalchemy import update
        
        await db.execute(
            update(Trip)
            .where(Trip.id == trip_id)
            .values(is_active=False, closed_at=datetime.utcnow())
        )
        
        await db.commit()
        
        # Notify admin dashboard about tourist becoming inactive
        trip_end_message = {
            "type": "tourist_status_change",
            "action": "trip_ended",
            "tourist_id": current_user.id,
            "trip_id": trip_id,
            "name": current_user.full_name,
            "email": current_user.email,
            "contact_number": current_user.contact_number,
            "age": current_user.age,
            "gender": current_user.gender
        }
        await manager.broadcast_to_admins(json.dumps(trip_end_message))
        
        # Redirect to dashboard with success message
        return RedirectResponse(url="/tourist-dashboard?message=Trip closed successfully!", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        # Handle any errors during trip closure
        return RedirectResponse(url="/tourist-dashboard?error=Error closing trip: " + str(e), status_code=status.HTTP_302_FOUND)

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Authority dashboard page"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user is admin
    if str(current_user.role) != "admin":
        return RedirectResponse(url="/tourist-dashboard", status_code=status.HTTP_302_FOUND)
    
    # Get all tourist users
    tourists_result = await db.execute(select(User).filter(User.role == "tourist"))
    all_tourists = tourists_result.scalars().all()
    
    # Get all active trips
    active_trips_result = await db.execute(select(Trip).filter(Trip.is_active == True))
    active_trips = active_trips_result.scalars().all()
    
    # Create mapping of user_id to active trip
    user_to_active_trip = {}
    for trip in active_trips:
        user_to_active_trip[trip.user_id] = trip
    
    # Categorize tourists
    active_tourists = []  # Tourists with active trips (for map)
    inactive_tourists = []  # Tourists without active trips (for list)
    
    for tourist in all_tourists:
        tourist_data = {
            "id": tourist.id,
            "name": tourist.full_name,
            "email": tourist.email,
            "contact_number": tourist.contact_number,
            "age": tourist.age,
            "gender": tourist.gender
        }
        
        if tourist.id in user_to_active_trip:
            trip = user_to_active_trip[tourist.id]
            tourist_place = get_tourist_place_by_id(int(str(trip.tourist_destination_id)))
            
            tourist_data.update({
                "trip_id": trip.id,
                "blockchain_id": trip.blockchain_id,
                "starting_location": trip.starting_location,
                "last_lat": trip.last_lat,
                "last_lon": trip.last_lon,
                "status": trip.status,
                "tourist_destination_id": trip.tourist_destination_id,
                "location_name": tourist_place["name"],
                "hotels": trip.hotels,
                "mode_of_travel": trip.mode_of_travel,
                "has_active_trip": True
            })
            active_tourists.append(tourist_data)
        else:
            tourist_data.update({
                "has_active_trip": False,
                "status": "No Active Trip"
            })
            inactive_tourists.append(tourist_data)
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "active_tourists": active_tourists,
        "inactive_tourists": inactive_tourists,
        "geofence": GEOFENCE_CENTER
    })

@app.get("/trip/{trip_id}", response_class=HTMLResponse)
async def trip_map_page(
    trip_id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Trip map page with arrow key controls"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    result = await db.execute(select(Trip).filter(Trip.id == trip_id))
    trip = result.scalar_one_or_none()
    if not trip:
        raise HTTPException(status_code=404, detail="Trip not found")
    
    # Check if user has permission to view this trip's map
    if str(current_user.role) == "tourist" and int(str(trip.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own trip map"
        )
    
    # Get the trip's destination geofence
    tourist_place = get_tourist_place_by_id(int(str(trip.tourist_destination_id)))
    
    # Get the tourist user data for the trip
    tourist_result = await db.execute(select(User).filter(User.id == trip.user_id))
    tourist_user = tourist_result.scalar_one_or_none()
    if not tourist_user:
        raise HTTPException(status_code=404, detail="Tourist user not found")
    
    # Create tourist object with trip and user data combined
    tourist = {
        "id": trip.id,  # Use trip ID for compatibility with frontend
        "name": tourist_user.full_name,
        "last_lat": trip.last_lat,
        "last_lon": trip.last_lon,
        "status": trip.status
    }
    
    return templates.TemplateResponse("map.html", {
        "request": request,
        "trip": trip,
        "tourist": tourist,  # Pass tourist data to template
        "current_user": current_user,  # Pass current user to template
        "geofence": {
            "center_lat": tourist_place["lat"],
            "center_lon": tourist_place["lon"],
            "radius": tourist_place["radius"],
            "name": tourist_place["name"]
        }
    })

# Startup event to create tables and demo users
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await create_tables()
    await create_demo_users()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)