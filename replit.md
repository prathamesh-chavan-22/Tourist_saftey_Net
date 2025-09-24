# Overview

The Smart Tourist Safety Monitoring & Incident Response System is a FastAPI-based prototype that monitors tourist locations in real-time using WebSocket connections. The system tracks tourists visiting Indian heritage sites, automatically detects when they move outside predefined safe zones (geofences), and provides both tourist-facing maps and authority dashboards for monitoring safety status.

The system uses a simple rule-based AI approach where tourists are classified as "Safe" when inside geofenced areas and "Critical" when outside, with incidents automatically logged to the database. Mock blockchain IDs are generated for each tourist using SHA256 hashing.

## Recent Changes

**September 23, 2025** - Major Code Modularization & PostgreSQL Migration:
- Refactored monolithic `app.py` (800+ lines) into modular architecture
- Created `config.py` for centralized configuration and constants  
- Created `schemas.py` for Pydantic request/response models
- Created `services.py` for business logic (geofencing, tourist places, demo users)
- Created `websocket_manager.py` for WebSocket connection management
- Created `routers/` directory with separate route modules:
  - `routers/auth.py` - Authentication endpoints
  - `routers/admin.py` - Admin dashboard endpoints  
  - `routers/tourist.py` - Tourist-specific endpoints
- Maintained all existing functionality and backwards compatibility
- Improved code organization and maintainability without breaking changes
- **Database Migration**: Migrated from SQLite to PostgreSQL using environment variables
- Updated SQLAlchemy configuration to use `asyncpg` driver for async PostgreSQL connections
- Leveraged Replit's built-in PostgreSQL database integration for secure configuration management

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Backend Architecture

**Framework**: FastAPI with Python, chosen for rapid prototyping and built-in WebSocket support
- RESTful API endpoints for tourist registration, location updates, and data retrieval
- WebSocket endpoint (`/ws/location`) for real-time location streaming to connected clients
- SQLAlchemy ORM for database interactions with dependency injection pattern
- Jinja2 templates for server-side rendering of HTML pages

**Database Design**: PostgreSQL with two main entities
- `tourists` table: stores tourist information, blockchain IDs, current location, and safety status
- `incidents` table: logs safety incidents with foreign key relationship to tourists
- Database session management through FastAPI dependency injection

**Geofencing Logic**: Rule-based safety classification system
- Predefined circular geofences for 7 major Indian tourist destinations (Taj Mahal, Red Fort, etc.)
- Real-time coordinate validation and distance calculation
- Automatic status updates (Safe/Critical) based on geofence boundaries

## Frontend Architecture

**Technology Stack**: Vanilla HTML/CSS/JavaScript with Leaflet.js for mapping
- Server-side rendered templates using Jinja2
- WebSocket client integration for real-time updates
- Responsive grid layouts for dashboard and map interfaces

**Map Integration**: Leaflet.js for interactive maps
- Tourist location visualization with real-time updates
- Geofence boundary display as circular overlays
- Alert popups when tourists exit safe zones

**Real-time Communication**: WebSocket connections for live updates
- Bidirectional communication between clients and server
- Automatic reconnection handling
- Live location streaming to both tourist maps and authority dashboard

## Data Flow Architecture

**Location Update Flow**:
1. Tourist location received via POST endpoint
2. Coordinate validation and geofence checking
3. Database status update
4. WebSocket broadcast to connected clients
5. Incident logging if safety threshold breached

**Real-time Monitoring**:
- WebSocket connection manager handles multiple concurrent connections
- Live updates pushed to authority dashboard and individual tourist maps
- Status changes reflected immediately across all connected interfaces

# External Dependencies

## Core Framework Dependencies
- **FastAPI**: Web framework with automatic API documentation and validation
- **SQLAlchemy**: ORM for database operations and model definitions
- **Pydantic**: Data validation and serialization for API endpoints

## Frontend Libraries
- **Leaflet.js**: Open-source mapping library for interactive maps
- **WebSocket API**: Native browser WebSocket support for real-time communication

## Database
- **PostgreSQL**: Production-ready relational database provided by Replit's built-in database integration
- Uses `asyncpg` driver for async database operations with SQLAlchemy
- Environment variable configuration for secure credential management

## Development Tools
- **Uvicorn**: ASGI server for running FastAPI applications
- **Jinja2**: Template engine for server-side HTML rendering

## Geographic Data
- **Predefined Coordinates**: Hardcoded latitude/longitude data for 7 major Indian tourist destinations
- **Mathematical Calculations**: Built-in Python math library for distance calculations and geofence validation

The system is architected for easy migration to more sophisticated frontend frameworks (React) and production databases while maintaining the core real-time monitoring functionality.