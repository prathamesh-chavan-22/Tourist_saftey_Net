from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
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
    role = Column(String, nullable=False, default="tourist")  # admin or tourist
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship to tourist (one-to-one)
    tourist = relationship("Tourist", back_populates="user", uselist=False)
    
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
DATABASE_URL = "sqlite:///./tourist_safety.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """Database dependency for FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def create_tables():
    """Create all tables in the database"""
    Base.metadata.create_all(bind=engine)