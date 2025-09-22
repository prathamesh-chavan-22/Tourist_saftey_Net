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
    role = Column(String, nullable=False, default="tourist")  # admin, tourist, or tourist_guide
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to tourist (one-to-one)
    tourist = relationship("Tourist", back_populates="user", uselist=False)
    # Relationship to tourist guide (one-to-one)
    tourist_guide = relationship("TouristGuide", back_populates="user", uselist=False)
    
    def verify_password(self, password: str) -> bool:
        """Verify password against hashed password"""
        return pwd_context.verify(password, str(self.hashed_password))
    
    @classmethod
    def get_password_hash(cls, password: str) -> str:
        """Hash a password"""
        return pwd_context.hash(password)

class Tourist(Base):
    __tablename__ = "tourists"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)
    blockchain_id = Column(String, unique=True, nullable=False)
    location_id = Column(Integer, default=1)  # ID of selected tourist place
    last_lat = Column(Float, default=27.1751)  # Default to Taj Mahal
    last_lon = Column(Float, default=78.0421)
    status = Column(String, default="Safe")  # Safe or Critical
    
    # Relationships
    incidents = relationship("Incident", back_populates="tourist")
    user = relationship("User", back_populates="tourist")
    
    @classmethod
    def generate_blockchain_id(cls, name: str) -> str:
        """Generate a mock blockchain ID using SHA256 hash"""
        return hashlib.sha256(f"{name}{datetime.now()}".encode()).hexdigest()

class TouristGuide(Base):
    __tablename__ = "tourist_guides"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String, nullable=False)
    guide_id = Column(String, unique=True, nullable=False)
    current_lat = Column(Float, default=27.1751)  # Default to Taj Mahal
    current_lon = Column(Float, default=78.0421)
    is_available = Column(Boolean, default=True)  # Available for guiding
    specializations = Column(String, nullable=True)  # e.g., "Historical Sites, Museums"
    
    # Relationships
    user = relationship("User", back_populates="tourist_guide")
    
    @classmethod
    def generate_guide_id(cls, name: str) -> str:
        """Generate a unique guide ID using SHA256 hash"""
        return hashlib.sha256(f"guide_{name}{datetime.now()}".encode()).hexdigest()[:16]

class Incident(Base):
    __tablename__ = "incidents"
    
    id = Column(Integer, primary_key=True, index=True)
    tourist_id = Column(Integer, ForeignKey("tourists.id"), nullable=False)
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
    
    # Relationship to tourist
    tourist = relationship("Tourist", back_populates="incidents")

# Database configuration
DATABASE_URL = "sqlite+aiosqlite:///./tourist_safety.db"
engine = create_async_engine(DATABASE_URL, echo=True)
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