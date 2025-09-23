# WebSocket connection management for real-time communication

from fastapi import WebSocket
from typing import List, Optional
import json
from models import User, Tourist

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

    async def send_to_tourist(self, tourist_id: int, message: str):
        """Send message to specific tourist by their tourist ID"""
        connections_to_remove = []
        
        for connection in self.active_connections.copy():
            # Check if this connection belongs to the target tourist
            if (connection.tourist is not None and connection.tourist.id == tourist_id):
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