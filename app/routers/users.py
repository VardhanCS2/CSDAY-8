from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.user import User
from app.schemas.user import UserResponse


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# ============================================================
# GET MY PROFILE
# Logged-in user
# ============================================================

@router.get(
    "/me",
    response_model=UserResponse,
)
async def get_my_profile(
    current_user: User = Depends(get_current_user),
):
    return current_user


# ============================================================
# GET ALL USERS
# ADMIN ONLY
# ============================================================

@router.get(
    "",
    response_model=list[UserResponse],
)
async def get_all_users(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User)
    )

    users = result.scalars().all()

    return users


# ============================================================
# GET USER BY ID
# ADMIN ONLY
# ============================================================

@router.get(
    "/{user_id}",
    response_model=UserResponse,
)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


# ============================================================
# CHANGE USER ROLE
# ADMIN ONLY
# ============================================================

@router.put(
    "/{user_id}/role",
    response_model=UserResponse,
)
async def change_user_role(
    user_id: int,
    role: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    if role not in ["user", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role must be either 'user' or 'admin'",
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.role = role

    await db.commit()
    await db.refresh(user)

    return user


# ============================================================
# DELETE USER
# ADMIN ONLY
# ============================================================

@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Prevent admin from deleting their own account
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account",
        )

    await db.delete(user)
    await db.commit()

    return None