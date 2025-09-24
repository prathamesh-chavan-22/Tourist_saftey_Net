# WebSocket connection management for real-time communication

from fastapi import WebSocket
from typing import List, Optional
import json
from models import User, Trip

class AuthenticatedConnection:
    """Represents an authenticated WebSocket connection with user information"""
    def __init__(self, websocket: WebSocket, user: User, trip: Optional[Trip] = None, assigned_trip_ids: Optional[List[int]] = None):
        self.websocket = websocket
        self.user = user
        self.trip = trip  # For tourists, this is their active trip
        self.assigned_trip_ids = assigned_trip_ids or []  # For guides, these are trip IDs they supervise

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[AuthenticatedConnection] = []

    async def connect(self, websocket: WebSocket, user: User, trip: Optional[Trip] = None, assigned_trip_ids: Optional[List[int]] = None):
        """Connect an authenticated user with WebSocket"""
        await websocket.accept()
        connection = AuthenticatedConnection(websocket, user, trip, assigned_trip_ids)
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
            if (connection.trip is not None and int(str(connection.trip.id)) == trip_id):
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
        - Guide users: receive location updates for trips they are assigned to
        """
        message = json.dumps(location_data)
        
        # Send to all admin users
        await self.broadcast_to_admins(message)
        
        # Send to the specific trip whose location was updated
        await self.send_to_trip(trip_id, message)
        
        # Send to guides assigned to this trip
        await self.send_to_assigned_guides(trip_id, message)

    async def send_to_assigned_guides(self, trip_id: int, message: str):
        """Send message to guides assigned to a specific trip"""
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            # Check if this is a guide connection and if they are assigned to this trip
            if (str(connection.user.role) == "guide" and 
                trip_id in connection.assigned_trip_ids):
                try:
                    await connection.websocket.send_text(message)
                except Exception as e:
                    connections_to_remove.append(connection)
        
        # Remove disconnected connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

    async def broadcast_guide_location_update(self, guide_id: int, guide_data: dict):
        """
        Broadcast guide location update with role-based filtering:
        - Admin users: receive all guide location updates
        - Tourist users: only receive their assigned guide's location updates
        - Guide users: do NOT receive other guides' locations (privacy)
        """
        message = json.dumps(guide_data)
        connections_to_remove = []
        
        # Send to all admin users (they see all guides)
        await self.broadcast_to_admins(message)
        
        # Send to tourists who have this guide assigned to their active trip
        for connection in self.active_connections.copy():
            if str(connection.user.role) == "tourist":
                # Check if this tourist has an active trip with the specific guide
                if (connection.trip is not None and 
                    connection.trip.guide_id is not None and
                    int(str(connection.trip.guide_id)) == guide_id):
                    try:
                        await connection.websocket.send_text(message)
                    except Exception as e:
                        connections_to_remove.append(connection)
        
        # Remove disconnected connections
        for connection in connections_to_remove:
            if connection in self.active_connections:
                self.active_connections.remove(connection)

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