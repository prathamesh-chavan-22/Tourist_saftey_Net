# Guide registration routes for the Tourist Safety Monitoring System

from fastapi import APIRouter, Depends, HTTPException, Request, Form, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import timedelta

from models import User, get_db
from auth import create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

router = APIRouter(prefix="/guide-auth", tags=["guide-authentication"])

# Initialize templates
templates = Jinja2Templates(directory="templates")

@router.get("/register", response_class=HTMLResponse)
async def guide_register_page(request: Request):
    """Guide registration page"""
    return templates.TemplateResponse("guide_register.html", {
        "request": request
    })

@router.post("/register")
async def register_guide(
    request: Request,
    name: str = Form(...),
    age: int = Form(...),
    contact_number: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    gender: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    """Register a new guide with both user account and guide profile"""
    try:
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == email))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            return templates.TemplateResponse("guide_register.html", {
                "request": request,
                "error": "Email already registered"
            })
        
        # Create user account with guide role
        hashed_password = User.get_password_hash(password)
        new_user = User(
            email=email,
            hashed_password=hashed_password,
            full_name=name,
            contact_number=contact_number,
            age=age,
            gender=gender,
            role="guide"
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        # Create access token for auto-login
        access_token = create_access_token(data={"sub": new_user.email})
        
        # Create response to redirect to guide dashboard and set login cookie
        response = RedirectResponse(url="/guide-dashboard", status_code=status.HTTP_302_FOUND)
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            httponly=True,
            secure=False,  # Set to True in production with HTTPS
            path="/",
            samesite="lax"
        )
        
        return response
        
    except Exception as e:
        # Return to registration form with error message
        return templates.TemplateResponse("guide_register.html", {
            "request": request,
            "error": f"Registration failed: {str(e)}"
        })