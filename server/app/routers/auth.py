"""
Magic Link Authentication Router
Provides login/signup with magic link email verification
"""

from datetime import datetime, timedelta
from typing import Optional
import secrets
import jwt
import os
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import select
from email_validator import validate_email, EmailNotValidError
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.models import SessionLocal, User, MagicLink

router = APIRouter()

# Configuration
SECRET_KEY = os.environ.get("SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
MAGIC_LINK_EXPIRE_MINUTES = 15

# Email configuration
SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "1025"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "noreply@talentflow.dev")

# Frontend URL
FRONTEND_BASE_URL = os.environ.get("FRONTEND_BASE_URL", "http://localhost:3000")


def get_db():
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class EmailRequest(BaseModel):
    """Request to send magic link to email"""
    email: str


class VerifyTokenRequest(BaseModel):
    """Request to verify magic link token"""
    token: str


class UserResponse(BaseModel):
    """User response model"""
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response model"""
    access_token: str
    token_type: str
    user: UserResponse


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def send_magic_link_email(email: str, magic_link: str, background_tasks: BackgroundTasks):
    """Send magic link email (run in background)"""
    def send_email_sync():
        try:
            subject = "Your TalentFlow Login Link"
            html_content = f"""
            <html>
                <body style="font-family: Arial, sans-serif;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
                        <h2>Welcome to TalentFlow</h2>
                        <p>Click the link below to log in to your account. This link expires in 15 minutes.</p>
                        <p>
                            <a href="{magic_link}" 
                               style="background-color: #4CAF50; color: white; padding: 12px 24px; text-decoration: none; border-radius: 4px; display: inline-block;">
                                Login to TalentFlow
                            </a>
                        </p>
                        <p>Or copy this link in your browser:</p>
                        <p style="word-break: break-all; color: #666;">{magic_link}</p>
                        <p style="color: #999; font-size: 12px;">If you didn't request this link, you can safely ignore this email.</p>
                    </div>
                </body>
            </html>
            """
            
            text_content = f"""
            Welcome to TalentFlow
            
            Click the link below to log in to your account. This link expires in 15 minutes.
            
            {magic_link}
            
            If you didn't request this link, you can safely ignore this email.
            """
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = FROM_EMAIL
            msg["To"] = email
            
            msg.attach(MIMEText(text_content, "plain"))
            msg.attach(MIMEText(html_content, "html"))
            
            # For development, print to console if SMTP not configured
            if SMTP_HOST == "localhost" and SMTP_PORT == 1025:
                print(f"\n[MAGIC LINK EMAIL]\nTo: {email}\nSubject: {subject}\n\n{text_content}\n")
            else:
                # Send via SMTP
                import smtplib
                with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                    if SMTP_USER and SMTP_PASSWORD:
                        server.starttls()
                        server.login(SMTP_USER, SMTP_PASSWORD)
                    server.sendmail(FROM_EMAIL, email, msg.as_string())
                    
        except Exception as e:
            print(f"Failed to send magic link email: {e}")
    
    background_tasks.add_task(send_email_sync)


@router.post("/send-magic-link")
async def send_magic_link(
    request: EmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Send magic link to email for login/signup
    """
    # Validate email
    try:
        valid = validate_email(request.email)
        email = valid.email
    except EmailNotValidError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid email: {str(e)}"
        )
    
    # Generate magic link token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=MAGIC_LINK_EXPIRE_MINUTES)
    
    # Store magic link in database
    db_magic_link = MagicLink(
        email=email,
        token=token,
        expires_at=expires_at
    )
    db.add(db_magic_link)
    db.commit()
    
    # Create magic link URL
    magic_link_url = f"{FRONTEND_BASE_URL}/auth/verify?token={token}"
    
    # Send email in background
    await send_magic_link_email(email, magic_link_url, background_tasks)
    
    return {
        "message": "Magic link sent to email",
        "email": email
    }


@router.post("/verify")
async def verify_magic_link(
    request: VerifyTokenRequest,
    db: Session = Depends(get_db)
) -> TokenResponse:
    """
    Verify magic link token and return JWT access token
    """
    # Find and validate magic link
    stmt = select(MagicLink).where(
        MagicLink.token == request.token
    )
    db_magic_link = db.scalar(stmt)
    
    if not db_magic_link:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired magic link"
        )
    
    if db_magic_link.is_used:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic link already used"
        )
    
    if db_magic_link.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Magic link expired"
        )
    
    # Get or create user
    stmt = select(User).where(User.email == db_magic_link.email)
    user = db.scalar(stmt)
    
    if not user:
        user = User(
            email=db_magic_link.email,
            full_name=None,
            is_active=True
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    # Mark magic link as used
    db_magic_link.is_used = True
    db_magic_link.used_at = datetime.utcnow()
    db.commit()
    
    # Create access token
    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )
    
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse.from_orm(user)
    )


@router.get("/me")
async def get_current_user(
    db: Session = Depends(get_db),
    token: str = None
) -> UserResponse:
    """
    Get current authenticated user from token
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    stmt = select(User).where(User.id == int(user_id))
    user = db.scalar(stmt)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return UserResponse.from_orm(user)


@router.post("/logout")
async def logout():
    """
    Logout endpoint (client should remove token from local storage)
    """
    return {"message": "Logged out successfully"}


@router.put("/profile")
async def update_profile(
    full_name: Optional[str] = None,
    db: Session = Depends(get_db),
    token: str = None
) -> UserResponse:
    """
    Update user profile
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    
    stmt = select(User).where(User.id == int(user_id))
    user = db.scalar(stmt)
    
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    if full_name:
        user.full_name = full_name
    user.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(user)
    
    return UserResponse.from_orm(user)
