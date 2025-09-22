from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List, Optional
import json
import math
from datetime import datetime, timedelta

from models import Tourist, Incident, User, TouristGuide, get_db, create_tables
from auth import (
    authenticate_user, create_access_token, get_current_user, 
    get_current_active_user, require_admin, require_tourist, require_tourist_guide,
    require_admin_or_guide, get_current_user_from_cookie, get_current_active_user_flexible,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Smart Tourist Safety Monitoring System")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create database tables on startup - will be called async in startup event

# Create demo users on startup
async def create_demo_users():
    """Create demo admin and tourist users"""
    from models import AsyncSessionLocal
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
                    role="admin"
                )
                db.add(admin_user)
                await db.commit()
                await db.refresh(admin_user)
                
            # Check if demo tourist exists  
            result = await db.execute(select(User).filter(User.email == "tourist@demo.com"))
            tourist_exists = result.scalar_one_or_none()
            if not tourist_exists:
                tourist_user = User(
                    email="tourist@demo.com",
                    hashed_password=User.get_password_hash("tourist123"),
                    full_name="Demo Tourist",
                    role="tourist"
                )
                db.add(tourist_user)
                await db.commit()
                await db.refresh(tourist_user)
                
                # Create tourist profile for demo tourist  
                blockchain_id = Tourist.generate_blockchain_id("Demo Tourist")
                tourist_place = {"lat": 27.1751, "lon": 78.0421}  # Default Taj Mahal coordinates
                
                demo_tourist = Tourist(
                    user_id=tourist_user.id,
                    name="Demo Tourist",
                    blockchain_id=blockchain_id,
                    location_id=1,
                    last_lat=tourist_place["lat"],
                    last_lon=tourist_place["lon"]
                )
                db.add(demo_tourist)
            
            # Check if demo tourist guide exists
            result = await db.execute(select(User).filter(User.email == "guide@demo.com"))
            guide_exists = result.scalar_one_or_none()
            if not guide_exists:
                guide_user = User(
                    email="guide@demo.com",
                    hashed_password=User.get_password_hash("guide123"),
                    full_name="Demo Guide",
                    role="tourist_guide"
                )
                db.add(guide_user)
                await db.commit()
                await db.refresh(guide_user)
                
                # Create guide profile for demo guide
                guide_id = TouristGuide.generate_guide_id("Demo Guide")
                
                demo_guide = TouristGuide(
                    user_id=guide_user.id,
                    name="Demo Guide",
                    guide_id=guide_id,
                    specializations="Historical Sites, Museums, Cultural Heritage"
                )
                db.add(demo_guide)
            
            await db.commit()
        except Exception as e:
            print(f"Error creating demo users: {e}")
            await db.rollback()

# Startup event to create tables and demo users
@app.on_event("startup")
async def startup_event():
    """Initialize database on startup"""
    await create_tables()
    await create_demo_users()

# Pydantic models for request validation
class TouristRegistration(BaseModel):
    name: str
    email: str
    password: str
    location_id: int = 1  # Default to Taj Mahal

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
    tourist_id: int
    latitude: float
    longitude: float
    
    def validate_coordinates(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")

# Indian Tourist Places Configuration
INDIAN_TOURIST_PLACES = [
    {"id": 1, "name": "Taj Mahal, Agra", "lat": 27.1751, "lon": 78.0421, "radius": 500},
    {"id": 2, "name": "Red Fort, Delhi", "lat": 28.6562, "lon": 77.2410, "radius": 400},
    {"id": 3, "name": "Gateway of India, Mumbai", "lat": 18.9220, "lon": 72.8347, "radius": 300},
    {"id": 4, "name": "Hawa Mahal, Jaipur", "lat": 26.9239, "lon": 75.8267, "radius": 300},
    {"id": 5, "name": "Golden Temple, Amritsar", "lat": 31.6200, "lon": 74.8765, "radius": 400},
    {"id": 6, "name": "India Gate, New Delhi", "lat": 28.6129, "lon": 77.2295, "radius": 400},
    {"id": 7, "name": "Mysore Palace, Mysore", "lat": 12.3051, "lon": 76.6551, "radius": 400}
]

# Default geofence (Taj Mahal for backwards compatibility)
GEOFENCE_CENTER = {"lat": 27.1751, "lon": 78.0421}
GEOFENCE_RADIUS = 500

# WebSocket connection manager
class AuthenticatedConnection:
    """Represents an authenticated WebSocket connection with user information"""
    def __init__(self, websocket: WebSocket, user: User, tourist: Optional[Tourist] = None):
        self.websocket = websocket
        self.user = user
        self.tourist = tourist

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[AuthenticatedConnection] = []

    async def connect(self, websocket: WebSocket, user: User, tourist: Optional[Tourist] = None):
        """Connect an authenticated user with WebSocket"""
        await websocket.accept()
        connection = AuthenticatedConnection(websocket, user, tourist)
        self.active_connections.append(connection)
        return connection

    def disconnect(self, websocket: WebSocket):
        """Disconnect WebSocket and remove from active connections"""
        self.active_connections = [
            conn for conn in self.active_connections 
            if conn.websocket != websocket
        ]

    async def send_personal_message(self, message: str, websocket: WebSocket):
        """Send message to specific WebSocket"""
        await websocket.send_text(message)

    async def broadcast_to_admins(self, message: str):
        """Broadcast message only to admin users"""
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            if str(connection.user.role) == "admin":
                try:
                    await connection.websocket.send_text(message)
                except Exception as e:
                    connections_to_remove.append(connection)
        
        # Remove disconnected connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def broadcast_to_admins_and_guides(self, message: str):
        """Broadcast message to admin users and tourist guides"""
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            if str(connection.user.role) in ["admin", "tourist_guide"]:
                try:
                    await connection.websocket.send_text(message)
                except Exception as e:
                    connections_to_remove.append(connection)
        
        # Remove disconnected connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def send_to_tourist(self, tourist_id: int, message: str):
        """Send message to specific tourist by their tourist ID"""
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            # Check if this connection belongs to the target tourist
            if (connection.tourist is not None and int(connection.tourist.id) == tourist_id):
                try:
                    await connection.websocket.send_text(message)
                except Exception as e:
                    connections_to_remove.append(connection)
        
        # Remove disconnected connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def broadcast_location_update(self, tourist_id: int, location_data: dict):
        """
        Broadcast location update with role-based filtering:
        - Admin users: receive all tourist location updates
        - Tourist users: only receive their own location updates
        """
        message = json.dumps(location_data)
        
        # Send to all admin users
        await self.broadcast_to_admins(message)
        
        # Send to the specific tourist whose location was updated
        await self.send_to_tourist(tourist_id, message)

    async def broadcast(self, message: str):
        """Legacy broadcast method - sends to all connections (deprecated for security)"""
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            try:
                await connection.websocket.send_text(message)
            except Exception as e:
                connections_to_remove.append(connection)
        
        # Remove disconnected connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

manager = ConnectionManager()

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

# Authentication endpoints
@app.post("/auth/register", response_model=Token)
async def register_user(user_data: UserCreate, db: AsyncSession = Depends(get_db)):
    """Register a new user (admin or tourist)"""
    # Check if user already exists
    result = await db.execute(select(User).filter(User.email == user_data.email))
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # SECURITY: Validate role against allowlist - only allow "admin", "tourist", and "tourist_guide"
    allowed_roles = {"admin", "tourist", "tourist_guide"}
    if user_data.role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role. Only 'admin', 'tourist', and 'tourist_guide' roles are allowed."
        )
    
    # Create new user
    hashed_password = User.get_password_hash(user_data.password)
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name,
        role=user_data.role
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email, "role": new_user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """Login user and return JWT token"""
    user = await authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login-form")
async def login_form(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Form-based login for web interface"""
    user = await authenticate_user(email, password, db)
    if not user:
        # Redirect back to login with error
        return RedirectResponse(
            url=f"/login?error=Invalid email or password",
            status_code=status.HTTP_302_FOUND
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role},
        expires_delta=access_token_expires
    )
    
    # Set cookie and redirect based on role
    if str(user.role) == "admin":
        redirect_url = "/"
    elif str(user.role) == "tourist_guide":
        redirect_url = "/guide-dashboard"
    else:
        redirect_url = f"/tourist-dashboard"
    
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
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

@app.post("/auth/logout")
async def logout_post():
    """Logout user by clearing cookie (POST method)"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

@app.get("/auth/logout")
async def logout():
    """Logout user by clearing cookie (GET method for browser links)"""
    response = RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    response.delete_cookie("access_token")
    return response

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

@app.post("/register")
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
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": f"Registration failed: {str(e)}",
            "tourist_places": INDIAN_TOURIST_PLACES
        })

@app.post("/register-guide")
async def register_tourist_guide(
    request: Request,
    name: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    specializations: str = Form(""),
    db: AsyncSession = Depends(get_db)
):
    """Register a new tourist guide with both user account and guide profile"""
    try:
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            return templates.TemplateResponse("register_guide.html", {
                "request": request,
                "error": "Email already registered"
            })
        
        # Create user account
        hashed_password = User.get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            role="tourist_guide"
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create tourist guide profile
        guide_id = TouristGuide.generate_guide_id(name)
        
        new_guide = TouristGuide(
            user_id=new_user.id,
            name=name,
            guide_id=guide_id,
            specializations=specializations if specializations else None
        )
        
        db.add(new_guide)
        await db.commit()
        await db.refresh(new_guide)
        
        # Redirect to login page with success message
        return RedirectResponse(url="/login?message=Guide registration successful! Please login.", status_code=status.HTTP_302_FOUND)
        
    except Exception as e:
        # Return to registration form with error message
        return templates.TemplateResponse("register_guide.html", {
            "request": request,
            "error": f"Registration failed: {str(e)}"
        })

@app.post("/update_location")
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
    # Tourist guides can update their own guide position, not tourist positions
    if str(current_user.role) not in ["tourist"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only tourists can update tourist location positions"
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

class TouristLocationChange(BaseModel):
    tourist_id: int
    location_id: int

@app.post("/change_tourist_location")
async def change_tourist_location(
    location_data: TouristLocationChange,
    current_user: User = Depends(get_current_active_user_flexible),
    db: AsyncSession = Depends(get_db)
):
    """Change tourist's assigned location"""
    # Validate coordinates
    if location_data.location_id not in [place["id"] for place in INDIAN_TOURIST_PLACES]:
        raise HTTPException(status_code=400, detail="Invalid location ID")
    
    result = await db.execute(select(Tourist).filter(Tourist.id == location_data.tourist_id))
    tourist = result.scalar_one_or_none()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")
    
    # SECURITY: Only allow tourists to change their own location
    if str(current_user.role) != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: Only tourists can change their location"
        )
    
    # Tourist users can only change their own location
    if int(str(tourist.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: You can only change your own location"
        )
    
    # Get the new tourist place
    new_place = get_tourist_place_by_id(location_data.location_id)
    
    # Update tourist location and position
    tourist.location_id = location_data.location_id
    tourist.last_lat = new_place["lat"]
    tourist.last_lon = new_place["lon"]
    
    # Check if tourist is in the new safe zone
    inside_fence = is_inside_geofence(new_place["lat"], new_place["lon"], location_data.location_id)
    tourist.status = "Safe" if inside_fence else "Critical"
    
    await db.commit()
    
    return {
        "message": "Location changed successfully",
        "new_location": new_place["name"],
        "status": tourist.status,
        "inside_fence": inside_fence
    }

class GuideLocationUpdate(BaseModel):
    latitude: float
    longitude: float
    
    def validate_coordinates(self):
        if not (-90 <= self.latitude <= 90):
            raise ValueError("Latitude must be between -90 and 90 degrees")
        if not (-180 <= self.longitude <= 180):
            raise ValueError("Longitude must be between -180 and 180 degrees")

@app.post("/update_guide_location")
async def update_guide_location(
    location_data: GuideLocationUpdate, 
    current_user: User = Depends(require_tourist_guide),
    db: AsyncSession = Depends(get_db)
):
    """Update tourist guide location"""
    # Validate coordinates
    try:
        location_data.validate_coordinates()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get guide profile
    result = await db.execute(select(TouristGuide).filter(TouristGuide.user_id == current_user.id))
    guide = result.scalar_one_or_none()
    if not guide:
        raise HTTPException(status_code=404, detail="Guide profile not found")
    
    # Update location
    guide.current_lat = location_data.latitude
    guide.current_lon = location_data.longitude
    await db.commit()
    
    # Broadcast guide location update to all admins and other guides
    update_message = {
        "type": "guide_location_update",
        "guide_id": guide.id,
        "name": guide.name,
        "latitude": location_data.latitude,
        "longitude": location_data.longitude,
        "is_available": guide.is_available
    }
    await manager.broadcast_to_admins_and_guides(update_message)
    
    return {"message": "Guide location updated successfully"}

@app.get("/api/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(require_admin_or_guide),
    db: AsyncSession = Depends(get_db)
):
    """Get all tourists data for dashboard - accessible by admin and tourist guides"""
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

@app.get("/api/guide-dashboard")
async def get_guide_dashboard_data(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all tourists and guides data for tourist guide dashboard"""
    # Try to get current user, return error if not authenticated
    from auth import get_user_from_cookie_token
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    if str(current_user.role) != "tourist_guide":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tourist guide access required"
        )
    # Get all tourists
    result = await db.execute(select(Tourist))
    tourists = result.scalars().all()
    
    # Get all guides
    result = await db.execute(select(TouristGuide))
    guides = result.scalars().all()
    
    tourists_data = [
        {
            "id": tourist.id,
            "name": tourist.name,
            "blockchain_id": tourist.blockchain_id,
            "last_lat": tourist.last_lat,
            "last_lon": tourist.last_lon,
            "status": tourist.status,
            "location_id": tourist.location_id,
            "location_name": get_tourist_place_by_id(int(str(tourist.location_id)))["name"],
            "type": "tourist"
        }
        for tourist in tourists
    ]
    
    guides_data = [
        {
            "id": guide.id,
            "name": guide.name,
            "guide_id": guide.guide_id,
            "current_lat": guide.current_lat,
            "current_lon": guide.current_lon,
            "is_available": guide.is_available,
            "specializations": guide.specializations,
            "type": "guide"
        }
        for guide in guides
    ]
    
    return {
        "tourists": tourists_data,
        "guides": guides_data
    }

@app.get("/tourist-places")
async def get_tourist_places():
    """Get all available Indian tourist places"""
    return INDIAN_TOURIST_PLACES

@app.get("/api/guide-positions")
async def get_guide_positions(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Get all guide positions for tourists to use as safe zones"""
    # Try to get current user, return error if not authenticated
    from auth import get_user_from_cookie_token
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    if str(current_user.role) != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tourist access required"
        )
    
    # Get all guides
    result = await db.execute(select(TouristGuide))
    guides = result.scalars().all()
    
    guides_data = [
        {
            "id": guide.id,
            "name": guide.name,
            "guide_id": guide.guide_id,
            "current_lat": guide.current_lat,
            "current_lon": guide.current_lon,
            "is_available": guide.is_available,
            "specializations": guide.specializations
        }
        for guide in guides
    ]
    
    return {"guides": guides_data}

@app.get("/map/{tourist_id}")
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

@app.websocket("/ws/location")
async def websocket_endpoint(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    """WebSocket endpoint for live location updates with authentication"""
    try:
        # Origin validation to prevent Cross-Site WebSocket Hijacking (CSWSH)
        origin = websocket.headers.get("origin")
        allowed_origins = [
            f"http://{websocket.headers.get('host')}",
            f"https://{websocket.headers.get('host')}",
            "http://localhost:5000",
            "https://localhost:5000"
        ]
        
        if origin and origin not in allowed_origins:
            await websocket.close(code=1008, reason="Origin not allowed")
            return
        
        # Authenticate user using HttpOnly cookie
        user = None
        access_token = websocket.cookies.get("access_token")
        
        if access_token:
            from auth import verify_token
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

@app.get("/register-guide-form", response_class=HTMLResponse)
async def register_guide_page(request: Request, error: Optional[str] = None):
    """Registration page for tourist guides"""
    return templates.TemplateResponse("register_guide.html", {
        "request": request,
        "error": error
    })

@app.get("/tourist-dashboard", response_class=HTMLResponse)
async def tourist_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Tourist dashboard page - shows only their own data"""
    # Try to get current user, redirect to login if not authenticated
    from auth import get_user_from_cookie_token
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

@app.get("/guide-dashboard", response_class=HTMLResponse)
async def guide_dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Tourist guide dashboard page - shows all users and allows movement"""
    # Try to get current user, redirect to login if not authenticated
    from auth import get_user_from_cookie_token
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if str(current_user.role) != "tourist_guide":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Get guide data for this user
    result = await db.execute(select(TouristGuide).filter(TouristGuide.user_id == current_user.id))
    guide = result.scalar_one_or_none()
    if not guide:
        # Create guide profile if it doesn't exist
        guide_id = TouristGuide.generate_guide_id(str(current_user.full_name))
        
        guide = TouristGuide(
            user_id=current_user.id,
            name=str(current_user.full_name),
            guide_id=guide_id
        )
        
        db.add(guide)
        await db.commit()
        await db.refresh(guide)
    
    guide_data = {
        "id": guide.id,
        "name": guide.name,
        "guide_id": guide.guide_id,
        "current_lat": guide.current_lat,
        "current_lon": guide.current_lon,
        "is_available": guide.is_available,
        "specializations": guide.specializations
    }
    
    return templates.TemplateResponse("guide_dashboard.html", {
        "request": request,
        "user": current_user,
        "guide": guide_data
    })

@app.get("/", response_class=HTMLResponse)
async def dashboard_page(request: Request, db: AsyncSession = Depends(get_db)):
    """Authority dashboard page"""
    # Try to get current user, redirect to login if not authenticated
    from auth import get_user_from_cookie_token
    
    current_user = await get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user is admin
    if str(current_user.role) == "tourist_guide":
        return RedirectResponse(url="/guide-dashboard", status_code=status.HTTP_302_FOUND)
    elif str(current_user.role) != "admin":
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
    from auth import get_user_from_cookie_token
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
    # Tourist guides and admins can view any tourist map
    
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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)