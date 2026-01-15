from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.database import Base
from src.models.base import UUIDMixin

if TYPE_CHECKING:
    from src.models.contacts import Contact


class ContactTagLink(Base):
    __tablename__ = "contact_tags"

    contact_id: Mapped[UUID] = mapped_column(
        ForeignKey("contacts.id"), primary_key=True
    )
    tag_id: Mapped[UUID] = mapped_column(ForeignKey("tags.id"), primary_key=True)


class Tag(Base, UUIDMixin):
    __tablename__ = "tags"

    name: Mapped[str] = mapped_column(String, unique=True, index=True)
    color: Mapped[str] = mapped_column(String, default="#808080")

    contacts: Mapped[list["Contact"]] = relationship(
        secondary="contact_tags", back_populates="tags"
    )
