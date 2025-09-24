# Overview

The Smart Tourist Safety Monitoring & Incident Response System is a FastAPI-based prototype that monitors tourist locations in real-time using WebSocket connections. The system tracks tourists visiting Indian heritage sites, automatically detects when they move outside predefined safe zones (geofences), and provides both tourist-facing maps and authority dashboards for monitoring safety status.

The system uses a simple rule-based AI approach where tourists are classified as "Safe" when inside geofenced areas and "Critical" when outside, with incidents automatically logged to the database. Mock blockchain IDs are generated for each tourist using SHA256 hashing.

## Recent Changes

**September 24, 2025** - Comprehensive Location Tracking System Implementation:
- **Guide GPS Controls**: Implemented complete GPS tracking controls for guide dashboard with enable/disable toggle, status indicators with visual feedback, and manual location update functionality
- **Guide Location Display**: Enhanced guide dashboard to prominently display guide's own current location with real-time coordinates (6-decimal precision), accuracy information, and custom red "G" markers on maps
- **Tourist Guide Visibility**: Enabled tourists to see their assigned guide's location on maps with purple "G" markers and comprehensive guide information panel showing name, status, coordinates, and last updated time
- **Location Validation Enhancement**: Added robust coordinate validation including frontend validation before server submission, backend checks for NaN/infinity/null values, and comprehensive error handling with user-friendly messages
- **Real-time WebSocket Updates**: Fixed and enhanced WebSocket system to properly broadcast guide locations to assigned tourists with role-based access control and connection management
- **Comprehensive Testing**: Completed end-to-end testing with 97.9% success rate (47/48 tests passed) covering GPS controls, location display, visibility features, validation, and real-time updates

**September 24, 2025** - Guide Demo Account & Database Schema Fix:
- **Demo Guide Account**: Added complete demo guide account (guide@demo.com / guide123) to system initialization
- **Database Schema Synchronization**: Fixed critical "column trips.guide_id does not exist" error by adding missing database column
- **Enhanced Login Interface**: Updated login page to display guide demo credentials and registration link
- **Database Migration Repair**: Added guide_id column and foreign key constraint to trips table for proper guide-trip relationships
- **Complete Guide Accessibility**: Guides are no longer "ghost" accounts - fully accessible through demo login and registration

**September 24, 2025** - Comprehensive Guide Role System Implementation:
- **Guide Role Authentication**: Implemented complete guide role system with proper access controls and authentication
- **Guide Dashboard**: Created dedicated guide dashboard at `/guide-dashboard` with purple theme showing only assigned tourists
- **Guide Registration**: Added guide registration system at `/guide-auth/register` similar to tourist registration with automatic login
- **Trip-Guide Assignment**: Updated trip creation to include optional guide selection by email with backend validation
- **Guide Location Tracking**: Enabled guides to update locations for trips they are assigned to, maintaining security
- **Real-time WebSocket Updates**: Fixed critical WebSocket issue to properly broadcast guide locations to admin and assigned tourists
- **Database Schema Enhancement**: Added `guide_id` field to Trip model for optional guide assignment relationships
- **Complete System Integration**: Guides now act as "child admins" who can monitor assigned tourists with full GPS tracking capability

**September 24, 2025** - Registration Flow Simplification & UX Improvements:
- **Simplified Registration Form**: Updated registration to collect only essential user information (name, age, email, contact, password)
- **Removed Forced Trip Selection**: Eliminated mandatory tourist destination selection during registration process
- **Automatic Login Implementation**: Users are now automatically logged in after successful registration using JWT tokens and secure HTTP-only cookies
- **Streamlined User Journey**: Registration now redirects directly to tourist dashboard instead of login page
- **Removed Auto-Trip Creation**: Registration no longer automatically creates trips, allowing users to plan trips when ready
- **Legacy Endpoint Cleanup**: Removed conflicting legacy `/register` endpoint that caused parameter mismatches
- **Enhanced User Experience**: New users can quickly create accounts and explore the platform without forced trip planning

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

**Database Design**: PostgreSQL with comprehensive user management
- `users` table: stores user information (tourists, guides, admins) with role-based access control
- `trips` table: manages tourist trips with optional guide assignment via `guide_id` field
- `incidents` table: logs safety incidents with foreign key relationships
- Database session management through FastAPI dependency injection

**Role-Based Access Control**: Three-tier user system
- **Admins**: Full system access with complete dashboard and user management
- **Guides**: "Child admin" role with access to assigned tourists only via filtered dashboard
- **Tourists**: Standard user role with personal trip management and location tracking

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

**Real-time Communication**: Enhanced WebSocket system for live updates
- Role-based WebSocket connections with authentication
- Guides track assigned trip IDs for targeted location broadcasts
- Live location streaming to tourist maps, guide dashboards, and admin dashboard
- Automatic reconnection handling and connection management

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