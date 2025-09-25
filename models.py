from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import hashlib
from passlib.context import CryptContext

Base = declarative_base()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String, nullable=False)
    contact_number = Column(String, nullable=False)
    age = Column(Integer, nullable=False)
    gender = Column(String, nullable=False)  # 'M' or 'F'
    role = Column(String, nullable=False, default="tourist")  # admin or tourist
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to trips (one-to-many)
    trips = relationship("Trip", back_populates="user", foreign_keys="Trip.user_id")
    guided_trips = relationship("Trip", foreign_keys="Trip.guide_id")
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hashed password"""
        return pwd_context.verify(password, str(self.hashed_password))
    
    @classmethod
    def get_password_hash(cls, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

class Trip(Base):
    __tablename__ = "trips"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    guide_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional guide assignment
    blockchain_id = Column(String, unique=True, nullable=False)
    
    # Trip details
    starting_location = Column(String, nullable=False)
    tourist_destination_id = Column(Integer, nullable=False)  # ID of tourist place
    hotels = Column(String, nullable=True)  # JSON string of hotel list
    mode_of_travel = Column(String, nullable=False)  # car, train, bus, flight
    
    # Current location tracking
    last_lat = Column(Float, nullable=True)
    last_lon = Column(Float, nullable=True)
    status = Column(String, default="Safe")  # Safe or Critical
    
    # Trip status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    closed_at = Column(DateTime, nullable=True)
    
    # Relationships
    incidents = relationship("Incident", back_populates="trip")
    user = relationship("User", back_populates="trips", foreign_keys=[user_id])
    guide = relationship("User", foreign_keys=[guide_id], overlaps="guided_trips")
    
    @classmethod
    def generate_blockchain_id(cls, user_name: str, destination: str) -> str:
        """Generate a mock blockchain ID using SHA256 hash"""
        return hashlib.sha256(f"{user_name}_{destination}_{datetime.now()}".encode()).hexdigest()

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    trip_id = Column(Integer, ForeignKey("trips.id"), nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)
    severity = Column(String, default="Critical")  # Low, Medium, High, Critical
    incident_type = Column(String, default="Geofence")  # Geofence, SOS, Manual
    status = Column(String, default="Open")  # Open, Acknowledged, Resolved
    description = Column(String, nullable=True)  # Optional description
    latitude = Column(Float, nullable=True)  # Location where incident occurred
    longitude = Column(Float, nullable=True)
    acknowledged_by = Column(String, nullable=True)  # Admin who acknowledged
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    
    # Relationship to trip
    trip = relationship("Trip", back_populates="incidents")

class GuideLocation(Base):
    __tablename__ = "guide_locations"
    
    id = Column(Integer, primary_key=True, index=True)
    guide_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to guide user
    guide = relationship("User", foreign_keys=[guide_id])
    
    def __repr__(self):
        return f"<GuideLocation(guide_id={self.guide_id}, lat={self.latitude}, lon={self.longitude}, updated_at={self.updated_at})>"

# Database configuration
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")

# Convert postgresql:// or postgres:// to postgresql+asyncpg:// for async driver
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
elif DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)

# Use echo=False in production to avoid logging sensitive data
engine = create_async_engine(DATABASE_URL, echo=os.environ.get("DEBUG", "False").lower() == "true")
AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

async def get_db():
    """Database dependency for FastAPI"""
    async with AsyncSessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()

async def create_tables():
    """Create all tables in the database"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)