from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.database.database import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest,RefreshTokenRequest, TokenResponse
from app.schemas.user import UserCreate, UserResponse


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


# =========================
# REGISTER
# =========================

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    # Check whether email already exists
    result = await db.execute(
        select(User).where(User.email == user_data.email)
    )

    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # Create new user
    new_user = User(
        name=user_data.name,
        email=user_data.email,
        password=hash_password(user_data.password),
        role="user",
    )

    db.add(new_user)

    await db.commit()
    await db.refresh(new_user)

    return new_user


# =========================
# LOGIN
# =========================

@router.post(
    "/login",
    response_model=TokenResponse,
)
async def login(
    login_data: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == login_data.email)
    )

    user = result.scalar_one_or_none()

    # Check user and password
    if user is None or not verify_password(
        login_data.password,
        user.password,
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    # Create access token
    access_token = create_access_token(
        user.id,
        user.role,
    )

    # Create refresh token
    refresh_token = create_refresh_token(
        user.id,
    )

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
async def refresh_access_token(
    token_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(token_data.refresh_token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = int(user_id)
    except (TypeError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    result = await db.execute(
        select(User).where(User.id == user_id)
    )

    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    new_access_token = create_access_token(
        user.id,
        user.role,
    )

    return {
        "access_token": new_access_token,
        "refresh_token": token_data.refresh_token,
        "token_type": "bearer",
    }