# WebSocket connection management for real-time communication

from fastapi import WebSocket
from typing import List, Optional
import json
from models import User, Trip

class AuthenticatedConnection:
    """Represents an authenticated WebSocket connection with user information"""
    def __init__(self, websocket: WebSocket, user: User, trip: Optional[Trip] = None):
        self.websocket = websocket
        self.user = user
        self.trip = trip

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[AuthenticatedConnection] = []

    async def connect(self, websocket: WebSocket, user: User, trip: Optional[Trip] = None):
        """Connect an authenticated user with WebSocket"""
        await websocket.accept()
        connection = AuthenticatedConnection(websocket, user, trip)
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

    async def send_to_trip(self, trip_id: int, message: str):
        """Send message to specific trip by their trip ID"""
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            # Check if this connection belongs to the target trip
            if (connection.trip is not None and connection.trip.id == trip_id):
                try:
                    await connection.websocket.send_text(message)
                except Exception as e:
                    connections_to_remove.append(connection)
        
        # Remove disconnected connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def broadcast_location_update(self, trip_id: int, location_data: dict):
        """
        Broadcast location update with role-based filtering:
        - Admin users: receive all trip location updates
        - Tourist users: only receive their own trip location updates
        """
        message = json.dumps(location_data)
        
        # Send to all admin users
        await self.broadcast_to_admins(message)
        
        # Send to the specific trip whose location was updated
        await self.send_to_trip(trip_id, message)

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