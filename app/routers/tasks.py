from datetime import datetime
import json

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import get_redis
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
# Redis Cache Added
#
# Admin -> all tasks
# User  -> only assigned tasks
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

    redis: Redis = Depends(get_redis),

    current_user: User = Depends(get_current_user),

):

    # ============================
    # Redis cache key
    # ============================

    cache_key = (
        f"tasks:"
        f"user:{current_user.id}:"
        f"status:{status_filter}:"
        f"assigned:{assigned_to}:"
        f"page:{page}:"
        f"size:{page_size}:"
        f"sort:{sort_by}:"
        f"order:{sort_order}"
    )


    cached_tasks = await redis.get(
        cache_key
    )


    if cached_tasks:

        return json.loads(
            cached_tasks
        )


    # ============================
    # Base query
    # ============================

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


    # ============================
    # Permission
    # ============================

    if current_user.role != "admin":

        query = query.where(
            Task.assigned_to == current_user.id
        )


    # ============================
    # Filters
    # ============================

    if status_filter:

        query = query.where(
            Task.status == status_filter
        )


    if assigned_to:

        query = query.where(
            Task.assigned_to == assigned_to
        )


    if due_after:

        query = query.where(
            Task.due_date >= due_after
        )


    if due_before:

        query = query.where(
            Task.due_date <= due_before
        )



    # ============================
    # Sorting
    # ============================

    allowed_sort_fields = {

        "id": Task.id,

        "title": Task.title,

        "status": Task.status,

        "due_date": Task.due_date,

        "project_id": Task.project_id,

        "assigned_to": Task.assigned_to,

        "assigned_user_name": User.name,

        "assigned_user_email": User.email,

        "project_name": Project.name,

    }



    if sort_by not in allowed_sort_fields:

        raise HTTPException(
            status_code=400,
            detail="Invalid sort field",
        )



    sort_column = allowed_sort_fields[sort_by]


    if sort_order == "desc":

        query = query.order_by(
            sort_column.desc()
        )

    else:

        query = query.order_by(
            sort_column.asc()
        )



    # ============================
    # Count total
    # ============================

    count_query = select(
        func.count()
    ).select_from(
        query.subquery()
    )


    count_result = await db.execute(
        count_query
    )


    total = count_result.scalar_one()



    # ============================
    # Pagination
    # ============================

    offset = (
        (page - 1)
        *
        page_size
    )


    query = query.offset(
        offset
    ).limit(
        page_size
    )



    # ============================
    # Execute query
    # ============================

    result = await db.execute(
        query
    )


    tasks = result.scalars().all()



    # ============================
    # Response
    # ============================

    response = {

        "items": tasks,

        "page": page,

        "page_size": page_size,

        "total": total,

    }



    # ============================
    # Store in Redis
    # TTL = 5 minutes
    # ============================

    await redis.set(
        cache_key,
        json.dumps(
            response,
            default=str
        ),
        ex=300,
    )


    return response

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

    redis: Redis = Depends(get_redis),

    current_user: User = Depends(require_admin),

):


    # Check project exists

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



    # Check assigned user exists

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



    # Create task

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



    # Remove old cache

    await redis.delete(
        f"tasks:user:{task_data.assigned_to}:*"
    )


    return new_task






# ============================================================
# UPDATE TASK
# ADMIN ONLY
# ============================================================


@router.put(
    "/{task_id}",
    response_model=TaskResponse,
)
async def update_task(

    task_id: int,

    task_data: TaskUpdate,

    db: AsyncSession = Depends(get_db),

    redis: Redis = Depends(get_redis),

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



    # Check project change

    if "project_id" in update_data:

        project_result = await db.execute(

            select(Project).where(

                Project.id ==
                update_data["project_id"]

            )

        )


        project = project_result.scalar_one_or_none()


        if project is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Project not found",
            )




    # Check assigned user change

    if "assigned_to" in update_data:

        user_result = await db.execute(

            select(User).where(

                User.id ==
                update_data["assigned_to"]

            )

        )


        assigned_user = user_result.scalar_one_or_none()



        if assigned_user is None:

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assigned user not found",
            )




    old_user_id = task.assigned_to



    # Update fields

    for field, value in update_data.items():

        setattr(
            task,
            field,
            value,
        )



    await db.commit()


    await db.refresh(task)



    # Clear cache

    await redis.delete(
        f"tasks:user:{old_user_id}:*"
    )


    if task.assigned_to != old_user_id:

        await redis.delete(
            f"tasks:user:{task.assigned_to}:*"
        )



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

    redis: Redis = Depends(get_redis),

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



    # Normal user can update only assigned task

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



    # Remove old cache

    await redis.delete(

        f"tasks:user:{task.assigned_to}:*"

    )



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

    redis: Redis = Depends(get_redis),

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



    assigned_user_id = task.assigned_to



    await db.delete(task)


    await db.commit()



    # Remove cache after delete

    await redis.delete(

        f"tasks:user:{assigned_user_id}:*"

    )



    return None