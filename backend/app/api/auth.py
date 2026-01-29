
import json
from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import UserDB
from app.utils.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    verify_password,
    JWTError,
    jwt,
    SECRET_KEY,
    ALGORITHM
)

router = APIRouter(prefix="/auth", tags=["auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# --- Schemas ---
class UserRegister(BaseModel):
    email: str
    password: str
    name: str
    year_group: int = 5

class Token(BaseModel):
    access_token: str
    token_type: str

class UserSettings(BaseModel):
    ai_provider: str = "auto"
    model_name: str | None = None
    api_key: str | None = None

class UserProfile(BaseModel):
    id: str
    email: str
    name: str
    year_group: int
    ai_settings: dict | None

# --- Dependencies ---
async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)], db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    result = await db.execute(select(UserDB).where(UserDB.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

# --- Endpoints ---

@router.post("/register", response_model=Token)
async def register(user: UserRegister, db: AsyncSession = Depends(get_db)):
    # Check if email exists
    result = await db.execute(select(UserDB).where(UserDB.email == user.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Create user
    hashed_pw = get_password_hash(user.password)
    new_user = UserDB(
        email=user.email,
        hashed_password=hashed_pw,
        name=user.name,
        year_group=user.year_group,
        target_schools="[]" # default
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Auto-login
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: AsyncSession = Depends(get_db)):
    # Note: OAuth2 form uses 'username' field, but we treat it as email
    result = await db.execute(select(UserDB).where(UserDB.email == form_data.username))
    user = result.scalar_one_or_none()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserProfile)
async def read_users_me(current_user: Annotated[UserDB, Depends(get_current_user)]):
    settings = json.loads(current_user.ai_settings) if current_user.ai_settings else None
    return UserProfile(
        id=current_user.id,
        email=current_user.email,
        name=current_user.name,
        year_group=current_user.year_group,
        ai_settings=settings
    )

@router.post("/settings")
async def update_settings(settings: UserSettings, current_user: Annotated[UserDB, Depends(get_current_user)], db: AsyncSession = Depends(get_db)):
    # Merge existing or create new
    current_settings = json.loads(current_user.ai_settings) if current_user.ai_settings else {}
    
    # Update fields
    if settings.ai_provider:
        current_settings["ai_provider"] = settings.ai_provider
    if settings.model_name:
        current_settings["model_name"] = settings.model_name
    if settings.api_key:
         # In a real app, encrypt this!
        current_settings["api_key"] = settings.api_key
        
    current_user.ai_settings = json.dumps(current_settings)
    await db.commit()
    return {"status": "updated", "settings": current_settings}
