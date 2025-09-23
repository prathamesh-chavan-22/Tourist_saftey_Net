from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from models import Tourist, User, get_db, create_tables
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
    """Legacy dashboard endpoint - returns tourist data for backwards compatibility"""
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
        
        # Get tourist data if user is a tourist
        tourist = None
        if str(user.role) == "tourist":
            result = await db.execute(select(Tourist).filter(Tourist.user_id == user.id))
            tourist = result.scalar_one_or_none()
        
        # Connect with authenticated user
        await manager.connect(websocket, user, tourist)
        
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
async def tourist_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Tourist dashboard page - shows only their own data"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if str(current_user.role) != "tourist":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Get tourist data for this user
    result = await db.execute(select(Tourist).filter(Tourist.user_id == current_user.id))
    tourist = result.scalar_one_or_none()
    if not tourist:
        # Create tourist profile if it doesn't exist
        tourist_place = get_tourist_place_by_id(1)  # Default to Taj Mahal
        blockchain_id = Tourist.generate_blockchain_id(str(current_user.full_name))
        
        tourist = Tourist(
            user_id=current_user.id,
            name=str(current_user.full_name),
            blockchain_id=blockchain_id,
            location_id=1,
            last_lat=tourist_place["lat"],
            last_lon=tourist_place["lon"]
        )
        
        db.add(tourist)
        await db.commit()
        await db.refresh(tourist)
    
    tourist_place = get_tourist_place_by_id(int(str(tourist.location_id)))
    tourist_data = {
        "id": tourist.id,
        "name": tourist.name,
        "blockchain_id": tourist.blockchain_id,
        "last_lat": tourist.last_lat,
        "last_lon": tourist.last_lon,
        "status": tourist.status,
        "location_id": tourist.location_id,
        "location_name": tourist_place["name"]
    }
    
    return templates.TemplateResponse("tourist_dashboard.html", {
        "request": request,
        "user": current_user,
        "tourist": tourist_data,
        "geofence": {
            "center_lat": tourist_place["lat"],
            "center_lon": tourist_place["lon"],
            "radius": tourist_place["radius"],
            "name": tourist_place["name"]
        }
    })

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
    
    result = await db.execute(select(Tourist))
    tourists = result.scalars().all()
    # Enrich tourists with location names
    tourists_data = []
    for tourist in tourists:
        tourist_place = get_tourist_place_by_id(int(str(tourist.location_id)))
        tourists_data.append({
            "id": tourist.id,
            "name": tourist.name,
            "blockchain_id": tourist.blockchain_id,
            "last_lat": tourist.last_lat,
            "last_lon": tourist.last_lon,
            "status": tourist.status,
            "location_id": tourist.location_id,
            "location_name": tourist_place["name"]
        })
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request, 
        "tourists": tourists_data,
        "geofence": GEOFENCE_CENTER
    })

@app.get("/tourist/{tourist_id}", response_class=HTMLResponse)
async def tourist_map_page(
    tourist_id: int, 
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Tourist map page with arrow key controls"""
    # Try to get current user, redirect to login if not authenticated
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    result = await db.execute(select(Tourist).filter(Tourist.id == tourist_id))
    tourist = result.scalar_one_or_none()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")
    
    # Check if user has permission to view this tourist's map
    if str(current_user.role) == "tourist" and int(str(tourist.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view your own tourist map"
        )
    
    # Get the tourist's assigned location geofence
    tourist_place = get_tourist_place_by_id(int(str(tourist.location_id)))
    
    return templates.TemplateResponse("map.html", {
        "request": request,
        "tourist": tourist,
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