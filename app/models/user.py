from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    password: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False
    )