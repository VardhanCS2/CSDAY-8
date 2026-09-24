from datetime import datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict


class TaskStatus(str, Enum):
    pending = "pending"
    inprogress = "inprogress"
    completed = "completed"


class TaskCreate(BaseModel):
    title: str
    description: str | None = None
    status: TaskStatus = TaskStatus.pending
    due_date: datetime | None = None
    project_id: int
    assigned_to: int


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: TaskStatus | None = None
    due_date: datetime | None = None
    project_id: int | None = None
    assigned_to: int | None = None


class TaskStatusUpdate(BaseModel):
    status: TaskStatus


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str | None
    status: TaskStatus
    due_date: datetime | None
    project_id: int
    assigned_to: int

    model_config = ConfigDict(from_attributes=True)