import asyncio

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.models.task import Task
from app.dependencies.auth import get_current_user
from app.models.user import User


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


async def get_total_tasks(
    db: AsyncSession
):
    result = await db.execute(
        select(func.count(Task.id))
    )

    return result.scalar()


async def get_completed_tasks(
    db: AsyncSession
):
    result = await db.execute(
        select(func.count(Task.id))
        .where(Task.status == "completed")
    )

    return result.scalar()


async def get_pending_tasks(
    db: AsyncSession
):
    result = await db.execute(
        select(func.count(Task.id))
        .where(Task.status == "pending")
    )

    return result.scalar()


@router.get("")
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    total, completed, pending = await asyncio.gather(
        get_total_tasks(db),
        get_completed_tasks(db),
        get_pending_tasks(db),
    )


    return {
        "user": current_user.name,
        "total_tasks": total,
        "completed_tasks": completed,
        "pending_tasks": pending,
    }