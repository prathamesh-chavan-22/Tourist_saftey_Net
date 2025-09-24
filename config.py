# Configuration settings for the Tourist Safety Monitoring System

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

# WebSocket allowed origins
def get_allowed_origins(host: str) -> list[str]:
    """Get allowed origins for WebSocket connections"""
    return [
        f"http://{host}",
        f"https://{host}",
        "http://localhost:5000",
        "https://localhost:5000"
    ]