"""User API endpoints."""

import json
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_db
from app.db.models import UserDB
from app.models.user import User, UserCreate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("", response_model=User)
async def create_user(
    user_create: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user."""
    db_user = UserDB(
        name=user_create.name,
        year_group=user_create.year_group,
        target_schools=json.dumps(user_create.target_schools),
    )
    db.add(db_user)
    await db.flush()

    return User(
        id=UUID(db_user.id),
        name=db_user.name,
        year_group=db_user.year_group,
        target_schools=user_create.target_schools,
        created_at=db_user.created_at,
        last_active=db_user.last_active,
    )


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a user by ID."""
    result = await db.execute(
        select(UserDB).where(UserDB.id == str(user_id))
    )
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return User(
        id=UUID(db_user.id),
        name=db_user.name,
        year_group=db_user.year_group,
        target_schools=json.loads(db_user.target_schools),
        created_at=db_user.created_at,
        last_active=db_user.last_active,
        total_questions_attempted=db_user.total_questions_attempted,
        total_correct=db_user.total_correct,
        current_streak=db_user.current_streak,
        longest_streak=db_user.longest_streak,
        total_practice_time_minutes=db_user.total_practice_time_minutes,
    )


@router.patch("/{user_id}", response_model=User)
async def update_user(
    user_id: UUID,
    name: str | None = None,
    year_group: int | None = None,
    target_schools: list[str] | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Update a user's details."""
    result = await db.execute(
        select(UserDB).where(UserDB.id == str(user_id))
    )
    db_user = result.scalar_one_or_none()

    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if name is not None:
        db_user.name = name
    if year_group is not None:
        db_user.year_group = year_group
    if target_schools is not None:
        db_user.target_schools = json.dumps(target_schools)

    db_user.last_active = datetime.utcnow()
    await db.flush()

    return User(
        id=UUID(db_user.id),
        name=db_user.name,
        year_group=db_user.year_group,
        target_schools=json.loads(db_user.target_schools),
        created_at=db_user.created_at,
        last_active=db_user.last_active,
        total_questions_attempted=db_user.total_questions_attempted,
        total_correct=db_user.total_correct,
        current_streak=db_user.current_streak,
        longest_streak=db_user.longest_streak,
        total_practice_time_minutes=db_user.total_practice_time_minutes,
    )


@router.get("", response_model=list[User])
async def list_users(
    db: AsyncSession = Depends(get_db),
):
    """List all users (for development/admin)."""
    result = await db.execute(select(UserDB))
    db_users = result.scalars().all()

    return [
        User(
            id=UUID(u.id),
            name=u.name,
            year_group=u.year_group,
            target_schools=json.loads(u.target_schools),
            created_at=u.created_at,
            last_active=u.last_active,
            total_questions_attempted=u.total_questions_attempted,
            total_correct=u.total_correct,
            current_streak=u.current_streak,
            longest_streak=u.longest_streak,
            total_practice_time_minutes=u.total_practice_time_minutes,
        )
        for u in db_users
    ]
