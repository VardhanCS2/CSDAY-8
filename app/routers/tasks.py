from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.task import Task
from app.models.user import User
from app.models.project import Project
from app.schemas.task import (
    TaskCreate,
    TaskResponse,
    TaskStatusUpdate,
    TaskUpdate,
)


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


# ============================================================
# GET ALL TASKS
#
# Admin -> can view all tasks
# User  -> can view only tasks assigned to them
#
# Filtering:
# status
# assigned_to
# due_after
# due_before
#
# Pagination:
# page
# page_size
#
# Sorting:
# id
# title
# status
# due_date
# project_id
# assigned_to
# assigned_user_name
# assigned_user_email
# project_name
# ============================================================

@router.get("")
async def get_tasks(
    status_filter: str | None = Query(
        default=None,
        alias="status",
    ),
    assigned_to: int | None = Query(
        default=None,
    ),
    due_after: datetime | None = Query(
        default=None,
    ),
    due_before: datetime | None = Query(
        default=None,
    ),
    sort_by: str = Query(
        default="id",
    ),
    sort_order: str = Query(
        default="asc",
    ),
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # --------------------------------------------------------
    # Base query
    # --------------------------------------------------------

    query = (
        select(Task)
        .join(
            User,
            Task.assigned_to == User.id,
        )
        .join(
            Project,
            Task.project_id == Project.id,
        )
    )

    # --------------------------------------------------------
    # Permission filtering
    #
    # Admin -> all tasks
    # User  -> only assigned tasks
    # --------------------------------------------------------

    if current_user.role != "admin":
        query = query.where(
            Task.assigned_to == current_user.id
        )

    # --------------------------------------------------------
    # Filter by status
    # --------------------------------------------------------

    if status_filter is not None:
        query = query.where(
            Task.status == status_filter
        )

    # --------------------------------------------------------
    # Filter by assigned user
    # --------------------------------------------------------

    if assigned_to is not None:
        query = query.where(
            Task.assigned_to == assigned_to
        )

    # --------------------------------------------------------
    # Filter by due date - after
    # --------------------------------------------------------

    if due_after is not None:
        query = query.where(
            Task.due_date >= due_after
        )

    # --------------------------------------------------------
    # Filter by due date - before
    # --------------------------------------------------------

    if due_before is not None:
        query = query.where(
            Task.due_date <= due_before
        )

    # --------------------------------------------------------
    # Allowed sorting fields
    # --------------------------------------------------------

    allowed_sort_fields = {
        "id": Task.id,
        "title": Task.title,
        "status": Task.status,
        "due_date": Task.due_date,
        "project_id": Task.project_id,
        "assigned_to": Task.assigned_to,

        # Related User table
        "assigned_user_name": User.name,
        "assigned_user_email": User.email,

        # Related Project table
        "project_name": Project.name,
    }

    # --------------------------------------------------------
    # Validate sort_by
    # --------------------------------------------------------

    if sort_by not in allowed_sort_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Invalid sort field. Allowed fields: "
                "id, title, status, due_date, project_id, "
                "assigned_to, assigned_user_name, "
                "assigned_user_email, project_name"
            ),
        )

    # --------------------------------------------------------
    # Validate sort_order
    # --------------------------------------------------------

    if sort_order not in ["asc", "desc"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_order must be 'asc' or 'desc'",
        )

    # --------------------------------------------------------
    # Apply sorting
    # --------------------------------------------------------

    sort_column = allowed_sort_fields[sort_by]

    if sort_order == "desc":
        query = query.order_by(
            sort_column.desc()
        )
    else:
        query = query.order_by(
            sort_column.asc()
        )

    # --------------------------------------------------------
    # Count total matching tasks
    # --------------------------------------------------------

    count_query = select(
        func.count()
    ).select_from(
        query.subquery()
    )

    count_result = await db.execute(
        count_query
    )

    total = count_result.scalar_one()

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    offset = (page - 1) * page_size

    query = query.offset(
        offset
    ).limit(
        page_size
    )

    # --------------------------------------------------------
    # Execute query
    # --------------------------------------------------------

    result = await db.execute(query)

    tasks = result.scalars().all()

    # --------------------------------------------------------
    # Response
    # --------------------------------------------------------

    return {
        "items": tasks,
        "page": page,
        "page_size": page_size,
        "total": total,
    }


# ============================================================
# GET ONE TASK
#
# Admin -> any task
# User  -> only assigned task
# ============================================================

@router.get(
    "/{task_id}",
    response_model=TaskResponse,
)
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id
        )
    )

    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    if (
        current_user.role != "admin"
        and task.assigned_to != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access tasks assigned to you",
        )

    return task


# ============================================================
# CREATE TASK
# ADMIN ONLY
# ============================================================

@router.post(
    "",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # --------------------------------------------------------
    # Check project exists
    # --------------------------------------------------------

    project_result = await db.execute(
        select(Project).where(
            Project.id == task_data.project_id
        )
    )

    project = project_result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # --------------------------------------------------------
    # Check assigned user exists
    # --------------------------------------------------------

    user_result = await db.execute(
        select(User).where(
            User.id == task_data.assigned_to
        )
    )

    assigned_user = user_result.scalar_one_or_none()

    if assigned_user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assigned user not found",
        )

    # --------------------------------------------------------
    # Create task
    # --------------------------------------------------------

    new_task = Task(
        title=task_data.title,
        description=task_data.description,
        status=task_data.status,
        due_date=task_data.due_date,
        project_id=task_data.project_id,
        assigned_to=task_data.assigned_to,
    )

    db.add(new_task)

    await db.commit()
    await db.refresh(new_task)

    return new_task


# ============================================================
# UPDATE TASK
# ADMIN ONLY
#
# Admin can change:
# title
# description
# status
# due_date
# project_id
# assigned_to
# ============================================================

@router.put(
    "/{task_id}",
    response_model=TaskResponse,
)
async def update_task(
    task_id: int,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id
        )
    )

    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    update_data = task_data.model_dump(
        exclude_unset=True
    )

    # --------------------------------------------------------
    # Check new project
    # --------------------------------------------------------

    if "project_id" in update_data:
        project_result = await db.execute(
            select(Project).where(
                Project.id == update_data["project_id"]
            )
        )

        project = project_result.scalar_one_or_none()

        if project is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )

    # --------------------------------------------------------
    # Check new assigned user
    # --------------------------------------------------------

    if "assigned_to" in update_data:
        user_result = await db.execute(
            select(User).where(
                User.id == update_data["assigned_to"]
            )
        )

        assigned_user = user_result.scalar_one_or_none()

        if assigned_user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )

    # --------------------------------------------------------
    # Update fields
    # --------------------------------------------------------

    for field, value in update_data.items():
        setattr(
            task,
            field,
            value,
        )

    await db.commit()
    await db.refresh(task)

    return task


# ============================================================
# UPDATE TASK STATUS
#
# Admin -> any task
# User  -> only their assigned task
# ============================================================

@router.patch(
    "/{task_id}/status",
    response_model=TaskResponse,
)
async def update_task_status(
    task_id: int,
    status_data: TaskStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id
        )
    )

    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # --------------------------------------------------------
    # Normal user can update only their assigned task
    # --------------------------------------------------------

    if (
        current_user.role != "admin"
        and task.assigned_to != current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update the status of tasks assigned to you",
        )

    task.status = status_data.status

    await db.commit()
    await db.refresh(task)

    return task


# ============================================================
# DELETE TASK
# ADMIN ONLY
# ============================================================

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Task).where(
            Task.id == task_id
        )
    )

    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    await db.delete(task)
    await db.commit()

    return None