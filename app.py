from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json
import math
from datetime import datetime, timedelta

from models import Tourist, Incident, User, get_db, create_tables
from auth import (
    authenticate_user, create_access_token, get_current_user, 
    get_current_active_user, require_admin, require_tourist,
    get_current_user_from_cookie, get_current_active_user_flexible,
    ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(title="Smart Tourist Safety Monitoring System")

# Mount static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Create database tables on startup
create_tables()

# Create demo users on startup
def create_demo_users():
    """Create demo admin and tourist users"""
    from models import SessionLocal
    db = SessionLocal()
    try:
        # Check if demo admin exists
        admin_exists = db.query(User).filter(User.email == "admin@demo.com").first()
        if not admin_exists:
            admin_user = User(
                email="admin@demo.com",
                hashed_password=User.get_password_hash("admin123"),
                full_name="Admin User",
                role="admin"
            )
            db.add(admin_user)
            
        # Check if demo tourist exists  
        tourist_exists = db.query(User).filter(User.email == "tourist@demo.com").first()
        if not tourist_exists:
            tourist_user = User(
                email="tourist@demo.com",
                hashed_password=User.get_password_hash("tourist123"),
                full_name="Demo Tourist",
                role="tourist"
            )
            db.add(tourist_user)
            db.commit()
            db.refresh(tourist_user)
            
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
        
        db.commit()
    except Exception as e:
        print(f"Error creating demo users: {e}")
        db.rollback()
    finally:
        db.close()

# Create demo users
create_demo_users()

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
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Remove disconnected connections
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
async def register_user(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user (admin or tourist)"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
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
    db.commit()
    db.refresh(new_user)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email, "role": new_user.role},
        expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login user and return JWT token"""
    user = authenticate_user(form_data.username, form_data.password, db)
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
    db: Session = Depends(get_db)
):
    """Form-based login for web interface"""
    user = authenticate_user(email, password, db)
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
    else:
        redirect_url = f"/tourist-dashboard"
    
    response = RedirectResponse(url=redirect_url, status_code=status.HTTP_302_FOUND)
    response.set_cookie(
        key="access_token",
        value=access_token,
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        httponly=True,
        secure=False  # Set to True in production with HTTPS
    )
    return response

@app.post("/auth/logout")
async def logout():
    """Logout user by clearing cookie"""
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
async def register_tourist(tourist_data: TouristRegistration, db: Session = Depends(get_db)):
    """Register a new tourist with both user account and tourist profile"""
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == tourist_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user account
    hashed_password = User.get_password_hash(tourist_data.password)
    new_user = User(
        email=tourist_data.email,
        hashed_password=hashed_password,
        full_name=tourist_data.name,
        role="tourist"
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create tourist profile
    blockchain_id = Tourist.generate_blockchain_id(tourist_data.name)
    tourist_place = get_tourist_place_by_id(tourist_data.location_id)
    
    new_tourist = Tourist(
        user_id=new_user.id,
        name=tourist_data.name,
        blockchain_id=blockchain_id,
        location_id=tourist_data.location_id,
        last_lat=tourist_place["lat"],
        last_lon=tourist_place["lon"]
    )
    
    db.add(new_tourist)
    db.commit()
    db.refresh(new_tourist)
    
    return {
        "id": new_tourist.id,
        "name": new_tourist.name,
        "blockchain_id": new_tourist.blockchain_id,
        "status": new_tourist.status,
        "user_id": new_user.id
    }

@app.post("/update_location")
async def update_location(
    location_data: LocationUpdate, 
    current_user: User = Depends(get_current_active_user_flexible),
    db: Session = Depends(get_db)
):
    """Update tourist location and check geofence status"""
    # Validate coordinates
    try:
        location_data.validate_coordinates()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    tourist = db.query(Tourist).filter(Tourist.id == location_data.tourist_id).first()
    if not tourist:
        raise HTTPException(status_code=404, detail="Tourist not found")
    
    # Check if user has permission to update this tourist's location
    if str(current_user.role) == "tourist" and int(str(tourist.user_id)) != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update your own location"
        )
    
    # Update location
    tourist.last_lat = location_data.latitude  # type: ignore
    tourist.last_lon = location_data.longitude  # type: ignore
    
    # Check geofence status for tourist's assigned location
    inside_fence = is_inside_geofence(location_data.latitude, location_data.longitude, int(str(tourist.location_id)))
    new_status = "Safe" if inside_fence else "Critical"
    
    # Log incident if status changed to Critical
    current_status = str(tourist.status)
    if current_status != "Critical" and new_status == "Critical":
        incident = Incident(tourist_id=tourist.id, severity="Critical")
        db.add(incident)
    
    tourist.status = new_status  # type: ignore
    db.commit()
    
    # Broadcast location update via WebSocket
    update_message = {
        "type": "location_update",
        "tourist_id": tourist.id,
        "name": tourist.name,
        "latitude": location_data.latitude,
        "longitude": location_data.longitude,
        "status": new_status,
        "inside_fence": inside_fence
    }
    await manager.broadcast(json.dumps(update_message))
    
    return {"status": new_status, "inside_fence": inside_fence}

@app.get("/dashboard")
async def get_dashboard_data(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Get all tourists data for dashboard"""
    tourists = db.query(Tourist).all()
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
async def get_tourist_places():
    """Get all available Indian tourist places"""
    return INDIAN_TOURIST_PLACES

@app.get("/map/{tourist_id}")
async def get_map_data(
    tourist_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Get initial map data for a specific tourist"""
    tourist = db.query(Tourist).filter(Tourist.id == tourist_id).first()
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
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live location updates"""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo received data back to all connected clients
            await manager.broadcast(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Authentication Web Pages
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    """Login page for both admin and tourist users"""
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
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
async def tourist_dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Tourist dashboard page - shows only their own data"""
    # Try to get current user, redirect to login if not authenticated
    from auth import get_user_from_cookie_token
    current_user = get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    if str(current_user.role) != "tourist":
        return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
    
    # Get tourist data for this user
    tourist = db.query(Tourist).filter(Tourist.user_id == current_user.id).first()
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
        db.commit()
        db.refresh(tourist)
    
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
async def dashboard_page(request: Request, db: Session = Depends(get_db)):
    """Authority dashboard page"""
    # Try to get current user, redirect to login if not authenticated
    from auth import get_user_from_cookie_token
    current_user = get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    # Check if user is admin
    if str(current_user.role) != "admin":
        return RedirectResponse(url="/tourist-dashboard", status_code=status.HTTP_302_FOUND)
    
    tourists = db.query(Tourist).all()
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
    db: Session = Depends(get_db)
):
    """Tourist map page with arrow key controls"""
    # Try to get current user, redirect to login if not authenticated
    from auth import get_user_from_cookie_token
    current_user = get_user_from_cookie_token(
        request.cookies.get("access_token"), db
    )
    if not current_user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    
    tourist = db.query(Tourist).filter(Tourist.id == tourist_id).first()
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