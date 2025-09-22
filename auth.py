from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Cookie
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from models import User, get_db
from dotenv import load_dotenv
import os

load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
# JWT Configuration
  # In production, use environment variable
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

security = HTTPBearer()

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(token: str):
    """Verify JWT token and return user data"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get("sub")
        if email is None or not isinstance(email, str):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
):
    """Get current user from JWT token"""
    token = credentials.credentials
    payload = verify_token(token)
    email = payload.get("sub")
    if email is None or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing email",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user

def get_current_user_from_cookie(
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """Get current user from cookie for template authentication"""
    if not access_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    payload = verify_token(access_token)
    email = payload.get("sub")
    if email is None or not isinstance(email, str):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing email"
        )
    
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    return user

def get_current_active_user(current_user: User = Depends(get_current_user)):
    """Get current active user"""
    if current_user.is_active is False:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def require_admin(current_user: User = Depends(get_current_active_user)):
    """Require admin role"""
    if str(current_user.role) != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    return current_user

def require_tourist(current_user: User = Depends(get_current_active_user)):
    """Require tourist role"""
    if str(current_user.role) != "tourist":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tourist access required"
        )
    return current_user

def get_user_from_cookie_token(access_token: Optional[str], db: Session) -> Optional[User]:
    """Manually get user from cookie token - for use in template endpoints"""
    if not access_token:
        return None
    
    try:
        payload = verify_token(access_token)
        email = payload.get("sub")
        if email is None or not isinstance(email, str):
            return None
        
        user = db.query(User).filter(User.email == email).first()
        return user
    except HTTPException:
        return None

def get_current_user_flexible(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
    access_token: Optional[str] = Cookie(None),
    db: Session = Depends(get_db)
):
    """
    Flexible authentication that tries Bearer token first, then falls back to cookie authentication.
    This allows the same endpoint to work with both API calls (Bearer token) and web requests (cookies).
    """
    user = None
    
    # First try Bearer token from Authorization header
    if credentials and credentials.credentials:
        try:
            payload = verify_token(credentials.credentials)
            email = payload.get("sub")
            if email and isinstance(email, str):
                user = db.query(User).filter(User.email == email).first()
        except HTTPException:
            # Bearer token authentication failed, will try cookie next
            pass
    
    # If Bearer token authentication failed, try cookie authentication
    if not user and access_token:
        try:
            payload = verify_token(access_token)
            email = payload.get("sub")
            if email and isinstance(email, str):
                user = db.query(User).filter(User.email == email).first()
        except HTTPException:
            # Cookie authentication also failed
            pass
    
    # If both authentication methods failed, raise 401
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user

def get_current_active_user_flexible(current_user: User = Depends(get_current_user_flexible)):
    """Get current active user with flexible authentication (Bearer token or cookie)"""
    if current_user.is_active is False:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

def authenticate_user(email: str, password: str, db: Session) -> Optional[User]:
    """Authenticate user with email and password"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return None
    if not user.verify_password(password):
        return None
    return user