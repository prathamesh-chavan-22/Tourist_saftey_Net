# Tourist Safety Net - API Documentation

## Project Overview
This is a FastAPI-based tourist safety monitoring system that provides real-time location tracking, geofencing, and role-based access control for tourists, guides, and administrators.

## Table of Contents
1. [Backend API Endpoints](#backend-api-endpoints)
2. [Authentication Functions](#authentication-functions)
3. [Database Models](#database-models)
4. [Utility Functions](#utility-functions)
5. [WebSocket Endpoints](#websocket-endpoints)
6. [Frontend JavaScript Functions](#frontend-javascript-functions)
7. [Configuration Constants](#configuration-constants)

---

## Backend API Endpoints

### Authentication Endpoints

#### `POST /auth/register`
- **Description**: Register a new user (admin, tourist, or tourist_guide)
- **Request Body**: `UserCreate` model
- **Response**: `Token` model
- **Access**: Public

#### `POST /auth/login`
- **Description**: Login user and return JWT token
- **Request Body**: `OAuth2PasswordRequestForm`
- **Response**: `Token` model
- **Access**: Public

#### `POST /auth/login-form`
- **Description**: Form-based login for web interface
- **Request Body**: Form data (email, password)
- **Response**: Redirect with cookie
- **Access**: Public

#### `POST /auth/logout`
- **Description**: Logout user by clearing cookie (POST method)
- **Response**: Redirect to login
- **Access**: Authenticated

#### `GET /auth/logout`
- **Description**: Logout user by clearing cookie (GET method)
- **Response**: Redirect to login
- **Access**: Authenticated

#### `GET /me`
- **Description**: Get current user information
- **Response**: User details
- **Access**: Authenticated

### Registration Endpoints

#### `POST /register`
- **Description**: Register a new tourist with both user account and tourist profile
- **Request Body**: Form data (name, email, password, location_id)
- **Response**: Redirect to login with success message
- **Access**: Public

#### `POST /register-guide`
- **Description**: Register a new tourist guide with both user account and guide profile
- **Request Body**: Form data (name, email, password, specializations)
- **Response**: Redirect to login with success message
- **Access**: Public

### Location Management Endpoints

#### `POST /update_location`
- **Description**: Update tourist location and check geofence status
- **Request Body**: `LocationUpdate` model
- **Response**: Status and geofence information
- **Access**: Tourist only (own location)

#### `POST /change_tourist_location`
- **Description**: Change tourist's assigned location
- **Request Body**: `TouristLocationChange` model
- **Response**: Success message and new location details
- **Access**: Tourist only (own location)

#### `POST /update_guide_location`
- **Description**: Update tourist guide location
- **Request Body**: `GuideLocationUpdate` model
- **Response**: Success message
- **Access**: Tourist guide only

### Dashboard Endpoints

#### `GET /api/dashboard`
- **Description**: Get all tourists data for dashboard
- **Response**: List of tourist data
- **Access**: Admin and tourist guides

#### `GET /api/guide-dashboard`
- **Description**: Get all tourists and guides data for tourist guide dashboard
- **Response**: Tourists and guides data
- **Access**: Tourist guides only

#### `GET /tourist-places`
- **Description**: Get all available Indian tourist places
- **Response**: List of tourist places
- **Access**: Public

#### `GET /api/guide-positions`
- **Description**: Get all guide positions for tourists to use as safe zones
- **Response**: Guide positions data
- **Access**: Tourists only

#### `GET /map/{tourist_id}`
- **Description**: Get initial map data for a specific tourist
- **Response**: Tourist and geofence data
- **Access**: Authenticated (own data or admin/guide)

### Web Pages

#### `GET /login`
- **Description**: Login page for both admin and tourist users
- **Response**: HTML template
- **Access**: Public

#### `GET /register-form`
- **Description**: Registration page for tourists
- **Response**: HTML template
- **Access**: Public

#### `GET /register-guide-form`
- **Description**: Registration page for tourist guides
- **Response**: HTML template
- **Access**: Public

#### `GET /tourist-dashboard`
- **Description**: Tourist dashboard page - shows only their own data
- **Response**: HTML template
- **Access**: Tourists only

#### `GET /guide-dashboard`
- **Description**: Tourist guide dashboard page
- **Response**: HTML template
- **Access**: Tourist guides only

#### `GET /`
- **Description**: Authority dashboard page
- **Response**: HTML template
- **Access**: Admin only

#### `GET /tourist/{tourist_id}`
- **Description**: Tourist map page with arrow key controls
- **Response**: HTML template
- **Access**: Authenticated (own data or admin/guide)

---

## Authentication Functions

### Token Management
- `create_access_token(data: dict, expires_delta: Optional[timedelta] = None)`
- `verify_token(token: str)`

### User Authentication
- `get_current_user(credentials: HTTPAuthorizationCredentials, db: AsyncSession)`
- `get_current_user_from_cookie(access_token: Optional[str], db: AsyncSession)`
- `get_current_active_user(current_user: User)`
- `get_current_user_flexible(credentials, access_token, db)`
- `get_current_active_user_flexible(current_user: User)`
- `authenticate_user(email: str, password: str, db: AsyncSession)`

### Role-based Access Control
- `require_admin(current_user: User)`
- `require_tourist(current_user: User)`
- `require_tourist_guide(current_user: User)`
- `require_admin_or_guide(current_user: User)`
- `get_user_from_cookie_token(access_token: Optional[str], db: AsyncSession)`

---

## Database Models

### User Model
- `verify_password(self, password: str) -> bool`
- `get_password_hash(cls, password: str) -> str`

### Tourist Model
- `generate_blockchain_id(cls, name: str) -> str`

### TouristGuide Model
- `generate_guide_id(cls, name: str) -> str`

### Database Functions
- `get_db()` - Database dependency for FastAPI
- `create_tables()` - Create all tables in the database

---

## Utility Functions

### Location and Geofencing
- `calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float`
- `is_inside_geofence(lat: float, lon: float, location_id: int = 1) -> bool`
- `get_tourist_place_by_id(location_id: int)`

### Demo Data
- `create_demo_users()` - Create demo admin, tourist, and guide users

---

## WebSocket Endpoints

### `WebSocket /ws/location`
- **Description**: WebSocket endpoint for live location updates with authentication
- **Authentication**: Cookie-based
- **Features**: 
  - Origin validation
  - Role-based message broadcasting
  - Connection management

### WebSocket Connection Manager
- `connect(websocket: WebSocket, user: User, tourist: Optional[Tourist] = None)`
- `disconnect(websocket: WebSocket)`
- `send_personal_message(message: str, websocket: WebSocket)`
- `broadcast_to_admins(message: str)`
- `broadcast_to_admins_and_guides(message: str)`
- `send_to_tourist(tourist_id: int, message: str)`
- `broadcast_location_update(tourist_id: int, location_data: dict)`
- `broadcast(message: str)` (legacy)

---

## Frontend JavaScript Functions

### Dashboard Functions (`dashboard.js`)

#### Map Initialization
- `initializeTouristMarkers(tourists)` - Initialize tourist markers from template data
- `initializeDashboardWebSocket()` - Initialize WebSocket connection for dashboard

#### Real-time Updates
- `updateTouristOnMap(data)` - Update tourist marker on map
- `updateTouristInTable(data)` - Update tourist data in table

### Map Functions (`map.js`)

#### Map Initialization
- `initializeMap(touristData, geofenceData, userRole)` - Initialize map with provided data

#### WebSocket Management
- `initializeWebSocket()` - Initialize WebSocket connection for tourist map

#### Movement Controls
- `moveUp()` - Move tourist up
- `moveDown()` - Move tourist down
- `moveLeft()` - Move tourist left
- `moveRight()` - Move tourist right
- `moveDirection(latChange, lonChange)` - Move tourist in specified direction

#### Location Updates
- `updateLocation()` - Send location update to server
- `updateStatus(data)` - Update tourist status from WebSocket data
- `updateStatusDisplay(status, insideFence)` - Update status display on UI

#### Error Handling
- `showAdminErrorMessage()` - Show error message for admin users trying to control movement

#### Control Initialization
- `initializeControls()` - Initialize keyboard and button controls for non-admin users

---

## Configuration Constants

### JWT Configuration
- `SECRET_KEY` - JWT secret key
- `ALGORITHM` - JWT algorithm (HS256)
- `ACCESS_TOKEN_EXPIRE_MINUTES` - Token expiration time (30 minutes)

### Tourist Places Configuration
```python
INDIAN_TOURIST_PLACES = [
    {"id": 1, "name": "Taj Mahal, Agra", "lat": 27.1751, "lon": 78.0421, "radius": 500},
    {"id": 2, "name": "Red Fort, Delhi", "lat": 28.6562, "lon": 77.2410, "radius": 400},
    {"id": 3, "name": "Gateway of India, Mumbai", "lat": 18.9220, "lon": 72.8347, "radius": 300},
    {"id": 4, "name": "Hawa Mahal, Jaipur", "lat": 26.9239, "lon": 75.8267, "radius": 300},
    {"id": 5, "name": "Golden Temple, Amritsar", "lat": 31.6200, "lon": 74.8765, "radius": 400},
    {"id": 6, "name": "India Gate, New Delhi", "lat": 28.6129, "lon": 77.2295, "radius": 400},
    {"id": 7, "name": "Mysore Palace, Mysore", "lat": 12.3051, "lon": 76.6551, "radius": 400}
]
```

### Default Geofence
- `GEOFENCE_CENTER` - Default center coordinates (Taj Mahal)
- `GEOFENCE_RADIUS` - Default radius (500 meters)

---

## Pydantic Models

### Request Models
- `TouristRegistration` - Tourist registration data
- `UserLogin` - User login data
- `UserCreate` - User creation data
- `LocationUpdate` - Location update data
- `TouristLocationChange` - Tourist location change data
- `GuideLocationUpdate` - Guide location update data

### Response Models
- `Token` - JWT token response

---

## Security Features

1. **Role-based Access Control**: Different access levels for admin, tourist, and tourist_guide roles
2. **JWT Authentication**: Secure token-based authentication
3. **Cookie Security**: HttpOnly cookies for web interface
4. **Origin Validation**: WebSocket origin validation to prevent CSWSH attacks
5. **Input Validation**: Coordinate validation and role validation
6. **Authorization Checks**: Users can only access their own data (except admins/guides)

---

## Database Schema

### Tables
- `users` - User accounts with roles
- `tourists` - Tourist profiles with location data
- `tourist_guides` - Guide profiles with availability status
- `incidents` - Safety incidents and alerts

### Relationships
- User → Tourist (one-to-one)
- User → TouristGuide (one-to-one)
- Tourist → Incidents (one-to-many)

---

## WebSocket Message Types

1. **location_update** - Tourist location updates
2. **guide_location_update** - Guide location updates

---

## Error Handling

- HTTP 401: Unauthorized access
- HTTP 403: Forbidden access (role-based)
- HTTP 404: Resource not found
- HTTP 400: Bad request (validation errors)

---

## Development Notes

- Uses FastAPI with async/await patterns
- SQLite database with aiosqlite for async operations
- Leaflet.js for interactive maps
- WebSocket for real-time updates
- Jinja2 templates for server-side rendering
- Bootstrap for UI styling

