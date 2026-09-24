from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)

    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30),
        default="pending",
        nullable=False
    )

    due_date: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True
    )

    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id"),
        nullable=False
    )

    assigned_to: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False
    )