from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.database import get_db
from app.dependencies.auth import get_current_user, require_admin
from app.models.project import Project
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
)


router = APIRouter(
    prefix="/projects",
    tags=["Projects"],
)


# Any authenticated user can view all projects
@router.get(
    "",
    response_model=list[ProjectResponse],
)
async def get_projects(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project)
    )

    projects = result.scalars().all()

    return projects


# Admin only
@router.post(
    "",
    response_model=ProjectResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_project(
    project_data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    new_project = Project(
        name=project_data.name,
        description=project_data.description,
        created_by=current_user.id,
    )

    db.add(new_project)
    await db.commit()
    await db.refresh(new_project)

    return new_project


# Any authenticated user can view a project
@router.get(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )

    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    return project


# Admin only
@router.put(
    "/{project_id}",
    response_model=ProjectResponse,
)
async def update_project(
    project_id: int,
    project_data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )

    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if project_data.name is not None:
        project.name = project_data.name

    if project_data.description is not None:
        project.description = project_data.description

    await db.commit()
    await db.refresh(project)

    return project


# Admin only
@router.delete(
    "/{project_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )

    project = result.scalar_one_or_none()

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    await db.delete(project)
    await db.commit()

    return None